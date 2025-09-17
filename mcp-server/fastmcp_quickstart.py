"""
FastMCP quickstart example with enhanced debug logging.
Includes weather tool and a Google Search tool.
"""

import os
import platform
import subprocess
import sqlite3
import psutil
import sys
from typing import Any
from datetime import datetime

import httpx
from dotenv import load_dotenv
from serpapi import GoogleSearch # New import

from mcp.server.fastmcp import FastMCP, Context
from database import DatabaseManager
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("fastmcp_quickstart")
load_dotenv()

# --- API Key Setup ---
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY") # New environment variable

if not OPENWEATHERMAP_API_KEY:
    logger.warning(
        "OPENWEATHERMAP_API_KEY not found. Weather tool disabled."
    )
if not SERPAPI_API_KEY:
    logger.warning(
        "SERPAPI_API_KEY not found. Google Search tool disabled."
    )

# --- Constants for Shell Command Safety ---
ALLOWED_SHELL_COMMANDS = {"ls", "echo", "pwd", "date", "uname", "whoami"}

# Create MCP server
# Removed the invalid 'system_prompt' keyword argument from the FastMCP constructor.
mcp = FastMCP(
    "Demo"
)

# --- Database Setup ---
db_manager = DatabaseManager()
db_manager.connect_all()
logger.info("Database connections initialized")

# --------------------- TOOLS --------------------- #

@mcp.tool()
def add(a: int, b: int) -> int:
    """Adds two integers and returns the result."""
    return a + b

@mcp.tool()
def get_current_datetime() -> str:
    """Returns the current date and time in ISO format."""
    now = datetime.now().isoformat()
    logger.debug(f"get_current_datetime: {now}")
    return now

@mcp.tool()
def list_files(path: str = ".") -> dict[str, Any]:
    """Lists files and directories in a given path.
    :param path: The directory path. Defaults to '.' (current directory).
    """
    try:
        files = os.listdir(path)
        logger.debug(f"Listing files in {path}: {files}")
        return {"files": files}
    except Exception as e:
        logger.error(f"list_files error: {e}")
        return {"error": str(e)}

@mcp.tool()
def read_file(path: str) -> str:
    """Reads the content of a text file.
    :param path: The path to the file.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.debug(f"Read file {path} ({len(content)} chars)")
        return content
    except Exception as e:
        logger.error(f"read_file error: {e}")
        return f"Error: {e}"

@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Writes content to a text file.
    :param path: The path to the file.
    :param content: The content to write.
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.debug(f"Wrote {len(content)} chars to {path}")
        return f"Successfully wrote {len(content)} characters to '{path}'"
    except Exception as e:
        logger.error(f"write_file error: {e}")
        return f"Error: {e}"

@mcp.tool()
def run_shell_command(command: str) -> str:
    """Executes a simple, allowed shell command and returns the output.
    Only allows a predefined set of safe commands.
    :param command: The shell command to run.
    """
    try:
        command_parts = command.strip().split()
        if not command_parts or command_parts[0] not in ALLOWED_SHELL_COMMANDS:
            logger.warning(f"Shell command not allowed: {command}")
            return f"Error: Command '{command_parts[0]}' is not allowed."

        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True, timeout=30
        )
        output = f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}"
        logger.debug(f"run_shell_command output: {output}")
        return output
    except Exception as e:
        logger.error(f"run_shell_command error: {e}")
        return f"Error executing command: {e}"

@mcp.tool()
def get_system_usage() -> dict[str, str]:
    """Returns key system usage metrics like CPU and memory utilization."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    usage = {
        "cpu_usage": f"{cpu_percent}%",
        "memory_usage": f"{memory_info.percent}%",
        "available_memory": f"{memory_info.available / (1024**3):.2f} GB",
    }
    logger.debug(f"System usage: {usage}")
    return usage

@mcp.tool(name="list_database_connections")
def list_db_connections_simple() -> list[str]:
    """Lists all available database connections."""
    conns = db_manager.list_connections()
    logger.debug(f"Database connections: {conns}")
    return conns

@mcp.tool()
def get_database_info(db_connection_name: str) -> dict[str, Any]:
    """Returns information about a specific database connection, including its type.
    :param db_connection_name: The name of the database connection.
    """
    conn_info = db_manager.get_connector_info(db_connection_name)
    if conn_info:
        return {"connection_info": conn_info}
    else:
        return {"error": f"Database '{db_connection_name}' not found."}

@mcp.tool()
def list_tables(db_connection_name: str) -> dict[str, Any]:
    """Lists all tables or collections in a specified database connection.
    :param db_connection_name: The name of the database connection.
    """
    connector = db_manager.get_connector(db_connection_name)
    if not connector:
        logger.warning(f"Database '{db_connection_name}' not found for list_tables")
        return {"error": f"Database '{db_connection_name}' not found."}
    tables = connector.list_tables()
    logger.debug(f"Tables in {db_connection_name}: {tables}")
    return {"tables_or_collections": tables}

@mcp.tool()
def get_table_schema(db_connection_name: str, collection_name: str) -> dict[str, Any]:
    """Retrieves the schema for a specific table or collection.
    :param db_connection_name: The name of the database connection.
    :param collection_name: The name of the table or collection.
    """
    connector = db_manager.get_connector(db_connection_name)
    if not connector:
        return {"error": f"Database '{db_connection_name}' not found."}
    schema = connector.get_table_schema(collection_name)
    logger.debug(f"Schema for {collection_name} in {db_connection_name}: {schema}")
    return schema

@mcp.tool()
def run_sql_query(db_connection_name: str, sql_query: str) -> dict[str, Any]:
    """Executes a SQL query against a database.
    :param db_connection_name: The name of the database connection.
    :param sql_query: The SQL query to execute.
    """
    connector = db_manager.get_connector(db_connection_name)
    if not connector:
        return {"error": f"Database '{db_connection_name}' not found."}
    try:
        result = connector.run_sql_query(sql_query)
        logger.debug(f"SQL query result: {result}")
        return result
    except Exception as e:
        logger.error(f"SQL query execution error: {e}")
        return {"error": f"An error occurred while executing the query: {e}"}

@mcp.tool()
def find_documents(db_connection_name: str, collection: str, filter: dict, projection: dict | None = None, limit: int = 50) -> dict[str, Any]:
    """Finds documents in a specified collection based on a filter.
    :param db_connection_name: The name of the database connection.
    :param collection: The name of the collection.
    :param filter: A dictionary specifying the search criteria.
    :param projection: Optional dictionary to specify which fields to return.
    :param limit: Maximum number of documents to return.
    """
    connector = db_manager.get_connector(db_connection_name)
    if not connector:
        return {"error": f"Database '{db_connection_name}' not found."}
    docs = connector.find_documents(collection, filter, projection, limit)
    logger.debug(f"Found {len(docs.get('result', []))} documents in {collection}")
    return docs

@mcp.tool()
def count_documents(db_connection_name: str, collection: str, filter: dict | None = None) -> dict[str, Any]:
    """
    Counts the number of documents in a specified collection based on a filter.
    This tool should only be used for MongoDB connections.
    :param db_connection_name: The name of the database connection.
    :param collection: The name of the collection.
    :param filter: A dictionary specifying the search criteria.
    """
    connector = db_manager.get_connector(db_connection_name)
    if not connector:
        return {"error": f"Database '{db_connection_name}' not found."}
    if connector.get_type() != "mongodb":
        return {"error": f"This tool is for MongoDB databases only. The database '{db_connection_name}' is of type '{connector.get_type()}'."}
    try:
        count = connector.count_documents(collection, filter)
        return {"count": count}
    except Exception as e:
        return {"error": str(e)}

# ---------------- WEATHER TOOL ---------------- #
@mcp.tool()
async def get_current_weather(city: str, state_code: str | None = None, country_code: str | None = None) -> dict[str, Any]:
    """
    Gets the current weather for a specified location.
    
    This tool should be used when the user asks about the weather in a specific city.
    
    :param city: The name of the city, e.g., 'London' or 'New York City'. This is a required parameter.
    :param state_code: The 2-letter state code for the city, e.g., 'CA' for California. Optional.
    :param country_code: The 2-letter country code, e.g., 'US' for United States. Optional.
    """
    if not OPENWEATHERMAP_API_KEY:
        return {"error": "Weather API key is not configured."}
    
    if not city:
        return {"error": "The 'city' parameter is required to get the weather."}

    geo_url = "http://api.openweathermap.org/geo/1.0/direct"
    weather_url = "https://api.openweathermap.org/data/2.5/weather"

    try:
        async with httpx.AsyncClient() as client:
            location_parts = [city]
            if state_code:
                location_parts.append(state_code)
            if country_code:
                location_parts.append(country_code)

            geo_resp = await client.get(
                geo_url,
                params={"q": ",".join(location_parts), "limit": 1, "appid": OPENWEATHERMAP_API_KEY},
                timeout=10
            )
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()
            if not geo_data:
                return {"error": f"City '{city}' not found."}

            lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]

            weather_resp = await client.get(
                weather_url,
                params={"lat": lat, "lon": lon, "appid": OPENWEATHERMAP_API_KEY, "units": "metric"},
                timeout=10
            )
            weather_resp.raise_for_status()
            data = weather_resp.json()

            temp_c = data["main"]["temp"]
            temp_f = (temp_c * 9 / 5) + 32

            result = {
                "location": data["name"],
                "description": data["weather"][0]["description"],
                "temperature": f"{temp_c:.1f}°C ({temp_f:.1f}°F)",
                "humidity": f"{data['main']['humidity']}%",
                "wind_speed": f"{data['wind']['speed']} m/s",
            }
            logger.debug(f"Weather data: {result}")
            return result

    except Exception as e:
        logger.error(f"Weather tool error: {e}", exc_info=True)
        return {"error": str(e)}
        
# ---------------- GOOGLE SEARCH TOOL ---------------- #
@mcp.tool()
def google_search(query: str) -> dict[str, Any]:
    """
    Performs a Google search and returns a list of results.
    
    This tool should be used when the user asks a question that requires up-to-date
    information or a web search to answer.
    
    :param query: The search query string.
    """
    if not SERPAPI_API_KEY:
        return {"error": "SerpApi key is not configured. Google Search tool is disabled."}
    
    try:
        params = {
            "api_key": SERPAPI_API_KEY,
            "engine": "google",
            "q": query,
            "hl": "en", # host language
            "gl": "us" # geo location
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Restrict the results to reduce token size for cost purposes
        organic_results = results.get("organic_results", [])[:3]    
        
        processed_results = []
        for res in organic_results:
            processed_results.append({
                "title": res.get("title"),
                "snippet": res.get("snippet"),
                "link": res.get("link")
            })

        logger.debug(f"Google Search for '{query}' returned {len(processed_results)} results.")
        return {"results": processed_results}
        
    except Exception as e:
        logger.error(f"Google Search tool error: {e}", exc_info=True)
        return {"error": str(e)}

# ---------------- RESOURCES ---------------- #
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Returns a greeting for a specified name."""
    greeting = f"Hello, {name}!"
    logger.debug(f"Greeting resource: {greeting}")
    return greeting

@mcp.resource("resource://system/info")
def system_info() -> dict[str, str]:
    """Returns basic system information."""
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "python_version": sys.version,
    }
    logger.debug(f"System info resource: {info}")
    return info

# ---------------- PROMPTS ---------------- #
@mcp.prompt()
def greet_user(name: str, style: str = "friendly") -> str:
    """Generates a greeting message for a user based on a specific style."""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }
    return f"{styles.get(style, styles['friendly'])} for someone named {name}."

@mcp.prompt()
def summarize_text(text: str) -> str:
    """Generates a prompt for summarizing a given text."""
    return f"Please provide a concise summary of the following text:\n{text}"

@mcp.prompt()
def translate_text(text: str, target_language: str) -> str:
    """Generates a prompt for translating a given text to a target language."""
    return f"Translate the following text to {target_language}:\n{text}"

# ---------------- CUSTOM ROUTES ---------------- #
@mcp.custom_route("/", methods=["GET"], include_in_schema=False)
async def root(request: Request) -> HTMLResponse:
    return HTMLResponse(
        "<html><head><title>MCP Server</title></head>"
        "<body><h1>✅ MCP Server is running!</h1>"
        "<p>The SSE endpoint is at <code>/sse</code>.</p></body></html>"
    )

@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(request: Request) -> JSONResponse:
    try:
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Health endpoint error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# ---------------- RUN SERVER ---------------- #
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the FastMCP Demo Server.")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse", "streamable-http"], help="Transport protocol")
    parser.add_argument("--host", default=None, help="Host to bind")
    parser.add_argument("--port", default=None, type=int, help="Port to bind")
    cli_args = parser.parse_args()

    if cli_args.host:
        mcp.settings.host = cli_args.host
    if cli_args.port:
        mcp.settings.port = cli_args.port

    logger.info(f"Starting MCP server on {mcp.settings.host}:{mcp.settings.port} with transport={cli_args.transport}")
    mcp.run(transport=cli_args.transport)