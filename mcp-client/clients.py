# clients.py
"""
Web-based chatbot client for MCP using OpenAI + Ollama APIs.
Enhanced: fixed MCP tool argument parsing, robust session & streaming, detailed debug logging.
"""

import os
import asyncio
import logging
import traceback
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from fastapi import (
    FastAPI, Request, WebSocket, WebSocketDisconnect,
    status, HTTPException, Form
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic_settings import BaseSettings
from pydantic import Field

from openai import AsyncOpenAI
from mcp import ClientSession
from mcp.client.sse import sse_client
from chat_manager import ChatManager
from llm_utils import OllamaClientWrapper, format_mcp_tools_for_openai
import httpx

# --- Load .env ---
load_dotenv()

# --- Logging setup ---
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("clients")

# --- Settings ---
class Settings(BaseSettings):
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OLLAMA_BASE_URL: str = Field(default="http://ollama-server:11434", env="OLLAMA_BASE_URL")
    OLLAMA_MODEL_NAME: str = Field(default="llama3", env="OLLAMA_MODEL_NAME")
    MCP_SERVER_URL: str = Field(default="http://mcp-server:8000", env="SERVER_URL")

settings = Settings()
current_dir = Path(__file__).parent

def is_debug_enabled() -> bool:
    val = os.getenv("MCP_CLIENT_DEBUG", "false").lower()
    return val in ("1", "true", "yes", "on")

# --- Global storage for active chat sessions ---
active_sessions: Dict[str, ChatManager] = {}
session_lock = asyncio.Lock()

# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Starting app lifespan...")

        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set in .env!")
        app.state.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

        app.state.ollama_client = OllamaClientWrapper(settings.OLLAMA_BASE_URL)
        app.state.mcp_session = None
        app.state.openai_tools = []
        app.state.mcp_server_info = {}
        app.state.db_connections = []
        app.state.available_tools = []
        app.state.available_resources = []
        app.state.available_prompts = []
        app.state.ollama_models = []

        task = asyncio.create_task(_manage_mcp_session(app))
        app.state.mcp_task = task

        # Wait for MCP session to initialize
        for i in range(20):
            if getattr(app.state, "mcp_session", None):
                logger.debug(f"MCP session initialized after {i*0.5}s")
                break
            await asyncio.sleep(0.5)
        else:
            logger.warning("MCP session not ready after 10s")

        yield
    finally:
        logger.info("Shutting down app lifespan...")
        if getattr(app.state, "mcp_task", None):
            app.state.mcp_task.cancel()
            try:
                await app.state.mcp_task
            except asyncio.CancelledError:
                logger.debug("MCP session manager task cancelled successfully")
        active_sessions.clear()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

templates = Jinja2Templates(directory=current_dir / "templates")
app.mount("/static", StaticFiles(directory=current_dir / "static"), name="static")


# --- Helpers ---
async def get_mcp_session_http(request: Request) -> ClientSession:
    mcp_session = getattr(request.app.state, "mcp_session", None)
    if not mcp_session:
        logger.debug("HTTP request received but MCP session is not ready")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP session not ready",
        )
    return mcp_session

async def _manage_mcp_session(app: FastAPI):
    base_mcp_url = settings.MCP_SERVER_URL.rstrip("/") + "/sse"
    while True:
        try:
            logger.info(f"Connecting to MCP server at {base_mcp_url} ...")
            async with sse_client(base_mcp_url) as (read, write):
                async with ClientSession(read, write) as mcp_session:
                    app.state.mcp_session = mcp_session
                    logger.info("✅ MCP session established")

                    try:
                        init_result = await mcp_session.initialize()
                        app.state.mcp_server_info = getattr(init_result, "serverInfo", None).model_dump() or {}
                        logger.info(f"MCP server info: {app.state.mcp_server_info}")
                    except Exception as e:
                        logger.warning(f"Failed to initialize MCP session: {e}")
                        logger.debug(traceback.format_exc())
                        app.state.mcp_server_info = {}

                    try:
                        tools_result = await mcp_session.list_tools()
                        app.state.available_tools = tools_result.model_dump().get("tools", [])
                        resources_result = await mcp_session.list_resources()
                        app.state.available_resources = resources_result.model_dump().get("resources", [])
                        prompts_result = await mcp_session.list_prompts()
                        app.state.available_prompts = prompts_result.model_dump().get("prompts", [])
                        logger.debug("Tools/resources/prompts loaded successfully")
                    except Exception as e:
                        logger.error(f"Failed to load MCP metadata: {e}")

                    try:
                        db_tool_result = await mcp_session.call_tool("list_database_connections")
                        db_connections = getattr(db_tool_result, "structuredContent", None) or db_tool_result or {}
                        if isinstance(db_connections, dict):
                            db_connections = db_connections.get("connections", db_connections.get("result", []))
                        app.state.db_connections = db_connections or []
                        logger.debug(f"DB connections loaded: {app.state.db_connections}")
                    except Exception as e:
                        logger.warning(f"Failed to list DB connections: {e}")
                        app.state.db_connections = []

                    app.state.openai_tools = format_mcp_tools_for_openai(app.state.available_tools)

                    try:
                        ollama_models_raw = await app.state.ollama_client.get_models()
                        # The fix is here: Change 'name' to 'id' as per the curl response.
                        app.state.ollama_models = [model["id"] for model in ollama_models_raw]
                        logger.debug(f"Ollama models loaded: {app.state.ollama_models}")
                    except Exception as e:
                        logger.warning(f"Failed to fetch Ollama models: {e}")
                        app.state.ollama_models = []

                    while True:
                        await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"MCP connection lost: {e}\n{traceback.format_exc()}")
            app.state.mcp_session = None
            app.state.openai_tools = []
            app.state.db_connections = []
            app.state.available_tools = []
            app.state.available_resources = []
            app.state.available_prompts = []
            app.state.ollama_models = []
            await asyncio.sleep(5)


def get_username_from_ws_cookie(websocket: WebSocket) -> str:
    cookie_header = websocket.headers.get("cookie")
    if cookie_header:
        cookies = dict([c.strip().split("=", 1) for c in cookie_header.split(";")])
        return cookies.get("username", "Guest")
    return "Guest"


# --- API Endpoints ---
@app.get("/api/ui-config")
async def get_ui_config(request: Request):
    if not request.app.state.mcp_session:
        return JSONResponse({"error": "MCP session not ready"}, status_code=503)

    def to_serializable(data):
        if isinstance(data, list):
            return [to_serializable(item) for item in data]
        if isinstance(data, dict):
            return {key: to_serializable(value) for key, value in data.items()}
        if hasattr(data, "model_dump"):
            return data.model_dump()
        return str(data)

    return JSONResponse({
        "server_name": request.app.state.mcp_server_info.get("name", "Unknown Server"),
        "mcp_version": request.app.state.mcp_server_info.get("version", "N/A"),
        "mcp_runtime": "FastAPI",
        "tools": to_serializable(request.app.state.available_tools),
        "resources": to_serializable(request.app.state.available_resources),
        "prompts": to_serializable(request.app.state.available_prompts),
        "db_connections": to_serializable(request.app.state.db_connections),
        "ollama_models": to_serializable(request.app.state.ollama_models),
    })


@app.get("/health")
async def health_check(request: Request):
    status_ok = True
    details = {}

    mcp_session = getattr(request.app.state, "mcp_session", None)
    details["mcp_session"] = "connected" if mcp_session else "not connected"
    if not mcp_session:
        status_ok = False

    ollama_client = getattr(request.app.state, "ollama_client", None)
    if ollama_client:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                r = await client.get(f"{settings.OLLAMA_BASE_URL}/v1/models")
            details["ollama"] = "reachable" if r.status_code == 200 else f"error {r.status_code}"
            if r.status_code != 200:
                status_ok = False
        except Exception as e:
            details["ollama"] = f"error {e}"
            status_ok = False
    else:
        details["ollama"] = "not configured"

    return {"status": "ok" if status_ok else "error", "details": details}


@app.get("/", include_in_schema=False)
@app.get("/index", include_in_schema=False)
async def serve_index(request: Request):
    username = get_username_from_ws_cookie(request)
    if not username or username == "Guest":
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", include_in_schema=False)
async def serve_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", include_in_schema=False)
async def handle_login(response: RedirectResponse, request: Request, username: str = Form(...)):
    response = RedirectResponse(url="/index", status_code=302)
    response.set_cookie(key="username", value=username)
    return response


# --- WebSocket ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(id(websocket))
    username = get_username_from_ws_cookie(websocket)

    if not username or username == "Guest":
        await websocket.send_json({"type": "error", "message": "Authentication failed. Please log in again."})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    mcp_session = None
    for i in range(40):
        if websocket.app.state.mcp_session and websocket.app.state.available_tools:
            mcp_session = websocket.app.state.mcp_session
            logger.debug(f"MCP session ready for WebSocket after {i*0.5}s")
            break
        await asyncio.sleep(0.5)

    if not mcp_session:
        await websocket.send_json({"type": "error", "message": "MCP session not ready"})
        await websocket.close()
        return

    debug_flag = is_debug_enabled()
    if debug_flag:
        logger.info("MCP client debug mode ENABLED (MCP_CLIENT_DEBUG=true)")

    try:
        # Await the first message to get the db_connection_name from the UI
        initial_data = await websocket.receive_json()
        db_connection_name = initial_data.get("db_connection_name")
        logger.info(f"Initial message received with db_connection_name: {db_connection_name}")
        
        async with session_lock:
            if session_id not in active_sessions:
                chat_manager = ChatManager(
                    mcp_session=mcp_session,
                    openai_client=websocket.app.state.openai_client,
                    openai_tools=websocket.app.state.openai_tools,
                    ollama_client=websocket.app.state.ollama_client,
                    username=username,
                    session_id=session_id,
                    debug=debug_flag,
                    force_functions=False,
                    available_tools=websocket.app.state.available_tools,
                    db_connection_name=db_connection_name # Pass the db connection name to ChatManager
                )
                active_sessions[session_id] = chat_manager
                logger.info(f"New chat session initialized for {username} (ID: {session_id}).")
            else:
                chat_manager = active_sessions[session_id]
                logger.info(f"Reusing existing chat session for {username} (ID: {session_id}).")
                # Update the chat manager with the new DB name if it changes
                chat_manager.db_connection_name = db_connection_name


        # Handle the user's first message
        user_message = initial_data.get("text")
        if user_message:
            use_mcp = initial_data.get("use_mcp", False)
            llm_provider = initial_data.get("llm_provider", "openai")
            llm_model_from_ui = initial_data.get("llm_model")

            llm_model = (
                llm_model_from_ui if llm_model_from_ui
                else settings.OPENAI_MODEL if llm_provider == "openai"
                else settings.OLLAMA_MODEL_NAME
            )
            
            async for chunk in chat_manager.handle_chat_stream(
                user_message,
                use_mcp=use_mcp,
                llm_provider=llm_provider,
                llm_model=llm_model,
                db_connection_name=db_connection_name
            ):
                if chunk.get("type") == "debug" and not debug_flag:
                    continue
                await websocket.send_json(chunk)
                if debug_flag:
                    logger.debug(f"Sent chunk: {chunk}")


        # Enter the main message loop
        while True:
            data = await websocket.receive_json()
            user_message = data.get("text")
            if not user_message:
                continue

            use_mcp = data.get("use_mcp", False)
            llm_provider = data.get("llm_provider", "openai")
            llm_model_from_ui = data.get("llm_model")

            llm_model = (
                llm_model_from_ui if llm_model_from_ui
                else settings.OPENAI_MODEL if llm_provider == "openai"
                else settings.OLLAMA_MODEL_NAME
            )
            db_connection_name = data.get("db_connection_name")

            if debug_flag:
                logger.debug(f"Received WebSocket message: {data}, using model: {llm_model}")

            async for chunk in chat_manager.handle_chat_stream(
                user_message,
                use_mcp=use_mcp,
                llm_provider=llm_provider,
                llm_model=llm_model,
                db_connection_name=db_connection_name
            ):
                if chunk.get("type") == "debug" and not debug_flag:
                    continue
                await websocket.send_json(chunk)
                if debug_flag:
                    logger.debug(f"Sent chunk: {chunk}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket {session_id} disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}\n{traceback.format_exc()}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        async with session_lock:
            if session_id in active_sessions:
                del active_sessions[session_id]
                logger.info(f"Cleaned up session {session_id}.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("clients:app", host="0.0.0.0", port=3000, reload=True, log_level="debug")
