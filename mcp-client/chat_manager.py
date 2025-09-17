# chat_manager.py
import copy
import json
import logging
import uuid
from typing import AsyncGenerator, Any, Dict, List, Optional

from openai import AsyncOpenAI
from mcp import ClientSession

logger = logging.getLogger("chat_manager")
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.DEBUG)


class ChatManager:
    """
    Manages chat interactions using MCP tools + LLMs (OpenAI / Ollama).
    """

    def __init__(
        self,
        mcp_session: ClientSession,
        openai_client: Optional[AsyncOpenAI],
        openai_tools: Optional[List[Dict[str, Any]]],
        ollama_client: Any,
        username: str,
        session_id: str,
        debug: bool = False,
        force_functions: bool = False,
        available_tools: Optional[List[Dict[str, Any]]] = None,
        db_connection_name: Optional[str] = None,
    ):
        self.mcp_session = mcp_session
        self.openai_client = openai_client
        self.openai_tools = openai_tools or []
        self.ollama_client = ollama_client
        self.user_id = username
        self.session_id = session_id
        self.debug = debug
        self.force_functions = force_functions
        self.available_tools = available_tools or []
        
        # Store the db_connection_name as an instance variable
        self.db_connection_name = db_connection_name
        
        # System prompt is now a property to allow for dynamic updates
        self.history: List[Dict[str, Any]] = self._initialize_history()
        logger.debug(f"[ChatManager] Initialized user={self.user_id}, session={self.session_id}, debug={self.debug}, db_connection_name={self.db_connection_name}")

    def _initialize_history(self) -> List[Dict[str, Any]]:
        """Initializes chat history with a dynamic system prompt."""
        system_prompt = self._get_system_prompt()
        return [{"role": "system", "content": system_prompt}]

    def _get_system_prompt(self) -> str:
        """
        Generates the system prompt, including database awareness and explicit formatting rules.
        """
        db_prompt_part = ""
        if self.db_connection_name:
            db_prompt_part = (
                f"You are currently connected to the database named '{self.db_connection_name}'. "
                "You must use this connection for all database-related queries. "
                "NEVER ask the user for the database name. "
                "Any database-related query from the user should be executed on this database.\n"
            )

        # --- UPDATED SYSTEM PROMPT ---
        # The key change is adding a more explicit and bolded rule about the "projection" parameter.
        base_prompt = (
            f"You are an enterprise assistant. {db_prompt_part}"
            "You MUST always use MCP tools when available. "
            "Do not answer from your own knowledge if a tool exists. "
            "If the user asks about the weather, ALWAYS call `get_current_weather` with the `city` parameter "
            "(and `state_code` or `country_code` if given). "
            "For database-related tasks, follow these rules strictly:\n"
            "1. When asked about a specific database, first call `get_database_info` to determine its type (e.g., 'sqlite' or 'mongodb').\n"
            "2. Based on the database type, use the correct tool for the task. **Do NOT use SQL tools for a MongoDB connection.**\n"
            "   - **For 'sqlite' databases**, use `run_sql_query` for all queries.\n"
            "   - **For 'mongodb' databases**, use `find_documents` to retrieve data and `count_documents` to get the number of records.\n"
            "3. If the user asks for a table count, use the appropriate counting tool (`run_sql_query` for 'sqlite' or `count_documents` for 'mongodb').\n"
            "4. **CRITICAL RULE FOR MONGODB**: The `find_documents` and `count_documents` tools always require a parameter named **`collection`**, NOT `collection_name`. "
            "The `find_documents` tool also requires a `filter` parameter. If the user wants to list all documents from a collection "
            "(e.g., \"list any 3 customers\"), you MUST pass an empty dictionary as the filter: `{\"filter\": {}}` and a `limit` of 3. "
            "**Furthermore, if the user asks for specific fields (e.g., 'name' and 'email'), you MUST include a `projection` parameter with a dictionary of those fields set to 1, e.g., `{\"projection\": {\"name\": 1, \"email\": 1}}`."
            "For example, to get 3 customers with their names and emails from a MongoDB database, the correct tool call is `find_documents(collection=\"customers\", filter={}, projection={\"name\": 1, \"email\": 1}, limit=3)`.\n"
            "When responding, always provide a clear, concise, and natural language summary of the tool results. "
            "If the tool returns a list of items or table data, **format the response using Markdown**. "
            "For lists, use Markdown bullet points (`- item`). For tabular data, use Markdown tables (`| Header | ... |`). "
            "Do not output raw JSON directly to the user. "
            "Ensure all lists and multi-line content are correctly formatted to preserve newlines and readability."
        )
        return base_prompt

    # --- Tool validation ---
    def _tool_accepts_db(self, tool_name: str) -> bool:
        for tool in self.available_tools:
            if tool.get("name") == tool_name:
                props = tool.get("parameters", {}).get("properties", {})
                if "db_connection_name" in props:
                    return True
        return False

    def _check_required_args(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        if tool_name == "get_current_weather" and not args.get("city"):
            return "The 'city' parameter is required to get the weather. Please provide a city name."
            
        if self._tool_accepts_db(tool_name) and not args.get("db_connection_name"):
            return "The 'db_connection_name' parameter is required for this database tool."
            
        if tool_name == "run_sql_query" and not args.get("sql_query"):
            return "The 'sql_query' parameter is required to run a query."
        
        # Corrected checks for MongoDB tools
        if tool_name == "find_documents":
            if not args.get("collection"):
                return "The 'collection' parameter is required to find documents."
            if "filter" not in args:
                return "The 'filter' parameter is required to find documents."
        
        if tool_name == "count_documents" and not args.get("collection"):
            return "The 'collection' parameter is required to count documents."
        
        return None

    # --- Safe parsing ---
    def _parse_tool_args(self, raw_args: Any) -> Dict[str, Any]:
        if not raw_args:
            return {}
        if isinstance(raw_args, dict):
            return raw_args
        if isinstance(raw_args, str):
            try:
                parsed = json.loads(raw_args)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                try:
                    result = {}
                    # Handles cases like 'city: New York'
                    for part in raw_args.split(","):
                        if ":" in part:
                            k, v = part.split(":", 1)
                            result[k.strip()] = v.strip().strip("'\"")
                    return result
                except Exception:
                    return {}
        return {}

    # --- Main chat handler ---
    async def handle_chat_stream(
        self,
        message: str,
        use_mcp: bool,
        llm_provider: str,
        llm_model: str,
        db_connection_name: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
        correlation_id = str(uuid.uuid4())
        logger.info(f"[{correlation_id}] New chat session started. User: '{message}'")
        
        # Check if the database connection has changed and update the history
        if db_connection_name and db_connection_name != self.db_connection_name:
            self.db_connection_name = db_connection_name
            self.history = self._initialize_history()
            logger.info(f"[{correlation_id}] Database connection changed to '{self.db_connection_name}'. Chat history reset.")

        self.history.append({"role": "user", "content": message})

        if self.debug:
            yield {"type": "debug", "message": f"[{correlation_id}] provider={llm_provider}, model={llm_model}, use_mcp={use_mcp}, db_connection={db_connection_name}"}

        if llm_provider == "openai":
            if not self.openai_client:
                yield {"type": "error", "message": "OpenAI client not configured."}
                return
            if use_mcp and self.openai_tools:
                async for chunk in self._handle_llm_with_mcp_tools("openai", llm_model, correlation_id):
                    yield chunk
            else:
                async for chunk in self._handle_openai_simple_stream(llm_model):
                    yield chunk
        elif llm_provider == "ollama":
            if use_mcp:
                async for chunk in self._handle_llm_with_mcp_tools("ollama", llm_model, correlation_id):
                    yield chunk
            else:
                async for chunk in self._handle_ollama_simple_stream(llm_model):
                    yield chunk
        else:
            yield {"type": "error", "message": f"Unknown LLM provider: {llm_provider}"}
            logger.error(f"[{correlation_id}] Unknown LLM provider: {llm_provider}")

    # --- Unified LLM + MCP tools handler ---
    async def _handle_llm_with_mcp_tools(self, provider: str, model: str, correlation_id: str) -> AsyncGenerator[dict, None]:
        try:
            # Filter tools based on the selected database
            if self.db_connection_name:
                filtered_tools = [
                    tool for tool in self.available_tools
                    if not self._tool_accepts_db(tool.get("name")) or tool.get("name") in ["list_tables", "run_sql_query", "find_documents", "count_documents", "get_table_schema", "get_database_info"]
                ]
            else:
                filtered_tools = self.available_tools
            
            # **CORRECTED LOGIC**: Standardize tools for OpenAI and Ollama
            standardized_tools = []
            for tool in filtered_tools:
                standardized_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.get("name"),
                        "description": tool.get("description"),
                        "parameters": tool.get("parameters")
                    }
                })

            messages_for_call = [m.copy() for m in self.history]
            
            is_tool_call_stream = False
            full_response_content = ""
            tool_calls_by_id: Dict[str, Dict[str, str]] = {}

            if provider == "openai":
                call_args = {
                    "model": model,
                    "messages": messages_for_call,
                    "stream": True,
                    "temperature": 0.0,
                    "tools": standardized_tools,  # Use the standardized tool list
                    "tool_choice": "auto",
                }
                if self.force_functions:
                    call_args["tool_choice"] = "required"
                
                stream = await self.openai_client.chat.completions.create(**call_args)
                async for chunk in stream:
                    choice = getattr(chunk, "choices", [None])[0]
                    delta = getattr(choice, "delta", None)
                    if delta and getattr(delta, "content", None):
                        full_response_content += delta.content
                        yield {"type": "response", "message": delta.content}
                    if delta and getattr(delta, "tool_calls", None):
                        is_tool_call_stream = True
                        for tc in delta.tool_calls:
                            tid = getattr(tc, "id", None) or (list(tool_calls_by_id.keys())[-1] if tool_calls_by_id else str(uuid.uuid4()))
                            tool_calls_by_id.setdefault(tid, {"name": "", "arguments": ""})
                            fn_obj = getattr(tc, "function", None)
                            if fn_obj:
                                if getattr(fn_obj, "name", None):
                                    tool_calls_by_id[tid]["name"] += fn_obj.name
                                if getattr(fn_obj, "arguments", None):
                                    tool_calls_by_id[tid]["arguments"] += fn_obj.arguments
            
            elif provider == "ollama":
                # Ollama client should also use the standardized tools
                response_stream = self.ollama_client.chat_with_tools(model=model, messages=messages_for_call, available_tools=standardized_tools, stream=True)
                async for chunk in response_stream:
                    if "tool_calls" in chunk:
                        is_tool_call_stream = True
                        for tc in chunk.get("tool_calls", []):
                            tid = tc.get("id") or (list(tool_calls_by_id.keys())[-1] if tool_calls_by_id else str(uuid.uuid4()))
                            tool_calls_by_id.setdefault(tid, {"name": "", "arguments": ""})
                            fn_obj = tc.get("function", {})
                            if fn_obj:
                                if fn_obj.get("name"):
                                    tool_calls_by_id[tid]["name"] += fn_obj["name"]
                                if fn_obj.get("arguments"):
                                    tool_calls_by_id[tid]["arguments"] += fn_obj["arguments"]
                    elif "choices" in chunk and chunk["choices"][0].get("delta", {}).get("content"):
                        content_chunk = chunk["choices"][0]["delta"]["content"]
                        full_response_content += content_chunk
                        yield {"type": "response", "message": content_chunk}

            if not is_tool_call_stream:
                self.history.append({"role": "assistant", "content": full_response_content})
                if self.debug:
                    yield {"type": "debug", "message": f"[{provider}+MCP] No tool calls. Direct answer."}
                return

            final_tool_calls = []
            for cid, call in tool_calls_by_id.items():
                try:
                    parsed_args = json.loads(call["arguments"])
                except json.JSONDecodeError:
                    logger.error(f"[{correlation_id}] Failed to parse tool arguments for '{call['name']}': {call['arguments']}")
                    parsed_args = {}
            
                final_tool_calls.append({
                    "id": cid,
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": parsed_args
                    }
                })
            
            if self.debug:
                logger.debug(f"[{correlation_id}] Full LLM tool call response: {json.dumps(final_tool_calls, indent=2)}")

            history_tool_calls = []
            for call in final_tool_calls:
                history_tool_calls.append({
                    "id": call["id"],
                    "type": "function",
                    "function": {
                        "name": call["function"]["name"],
                        "arguments": json.dumps(call["function"]["arguments"])
                    }
                })

            self.history.append({
                "role": "assistant",
                "tool_calls": history_tool_calls
            })

            for call in final_tool_calls:
                fn_name = call["function"].get("name")
                fn_args = call["function"].get("arguments") or {}
                call_id = call.get("id")

                # Unified logic to inject db_connection_name
                if self.db_connection_name and self._tool_accepts_db(fn_name):
                    fn_args.setdefault("db_connection_name", self.db_connection_name)

                missing_error = self._check_required_args(fn_name, fn_args)
                if missing_error:
                    yield {"type": "error", "message": missing_error}
                    self.history.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps({"error": missing_error})})
                    continue

                logger.info(f"[{correlation_id}] 🚀 Calling MCP tool '{fn_name}' with args={fn_args}")
                yield {"type": "tool-call", "message": {"name": fn_name, "arguments": fn_args}}
            
                try:
                    result = await self.mcp_session.call_tool(fn_name, arguments=fn_args)
                    tool_output = getattr(result, "structuredContent", result) or {}
                
                    if fn_name == "list_database_connections" and self.db_connection_name:
                        tool_output = {"result": [self.db_connection_name]}

                    output_content = self._format_tool_output_for_llm(tool_output, fn_name)

                except Exception as e:
                    output_content = f"Error calling tool '{fn_name}': {e}"
                    tool_output = {"error": output_content}

                self.history.append({"role": "tool", "tool_call_id": call_id, "content": output_content})

            async for chunk in self._run_final_llm_call(model, correlation_id):
                yield chunk

        except Exception as e:
            logger.error(f"[{correlation_id}] LLM/MCP error: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}
            
    # --- Simple streams ---
    async def _handle_openai_simple_stream(self, model: str) -> AsyncGenerator[dict, None]:
        try:
            stream = await self.openai_client.chat.completions.create(model=model, messages=self.history, stream=True)
            full_response = ""
            async for chunk in stream:
                content = getattr(chunk.choices[0].delta, "content", None)
                if content:
                    full_response += content
                    yield {"type": "response", "message": content}
            self.history.append({"role": "assistant", "content": full_response})
        except Exception as e:
            yield {"type": "error", "message": str(e)}

    async def _handle_ollama_simple_stream(self, model: str) -> AsyncGenerator[dict, None]:
        try:
            stream = self.ollama_client.chat_stream(model=model, messages=self.history)
            full_response = ""
            async for chunk in stream:
                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                if content:
                    full_response += content
                    yield {"type": "response", "message": content}
            self.history.append({"role": "assistant", "content": full_response})
        except Exception as e:
            yield {"type": "error", "message": str(e)}
            
    # NEW FUNCTION: This is now a unified function for both OpenAI and Ollama final calls
    # It must be called with `async for`
    async def _run_final_llm_call(self, model: str, correlation_id: str) -> AsyncGenerator[dict, None]:
        """Makes a final LLM call after tool execution to get a user-facing response."""
        try:
            history_for_final_call = [m.copy() for m in self.history]
            
            if self.debug:
                logger.debug(f"[{correlation_id}] Making final LLM call. History: {json.dumps(history_for_final_call, indent=2)}")

            # Use LLM provider to determine client
            client = self.openai_client if "gpt" in model else self.ollama_client

            if "gpt" in model:
                stream = await client.chat.completions.create(
                    model=model,
                    messages=history_for_final_call,
                    stream=True,
                    temperature=0.0
                )
                full_response = ""
                async for chunk in stream:
                    content = getattr(chunk.choices[0].delta, "content", None)
                    if content:
                        full_response += content
                        yield {"type": "response", "message": content}
                self.history.append({"role": "assistant", "content": full_response})
            else: # Assumes Ollama
                stream = client.chat_stream(
                    model=model,
                    messages=history_for_final_call
                )
                full_response = ""
                async for chunk in stream:
                    content = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                    if content:
                        full_response += content
                        yield {"type": "response", "message": content}
                self.history.append({"role": "assistant", "content": full_response})

        except Exception as e:
            logger.error(f"[{correlation_id}] Final LLM call error: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}

    def _format_tool_output_for_llm(self, tool_output: Any, tool_name: str) -> str:
        """
        Formats the raw tool output into a clean, descriptive string for the LLM.
        """
        if tool_name == "list_files":
            if isinstance(tool_output, dict) and "files" in tool_output and isinstance(tool_output["files"], list):
                file_list = "\n".join([f"- {file}" for file in tool_output["files"]])
                return f"The `list_files` tool returned the following files:\n{file_list}"
            return "The list of files was retrieved successfully."
            
        # New: Specific handler for count_documents
        if tool_name == "count_documents":
            if isinstance(tool_output, dict) and "count" in tool_output:
                return f"The `count_documents` tool returned a count of {tool_output['count']} documents."
            return "The count operation was successful, but no count value was returned."
            
        if isinstance(tool_output, dict) and "result" in tool_output and isinstance(tool_output["result"], list):
            if not tool_output["result"]:
                return f"The tool call returned an empty list of results for {tool_name}."
            
            if len(tool_output["result"]) > 0 and isinstance(tool_output["result"][0], dict):
                headers = list(tool_output["result"][0].keys())
                header_row = "| " + " | ".join(headers) + " |"
                separator_row = "|-" + "-|-".join([""] * len(headers)) + "-|"
                data_rows = []
                for row in tool_output["result"]:
                    values = [str(row.get(h, '')) for h in headers]
                    data_rows.append("| " + " | ".join(values) + " |")
                
                table_str = "\n".join([header_row, separator_row] + data_rows)
                return f"The tool call returned the following data:\n{table_str}"
            else:
                list_str = "\n".join([f"- {item}" for item in tool_output["result"]])
                return f"The tool call returned the following list of items:\n{list_str}"

        return f"The tool call returned the following information:\n{json.dumps(tool_output, indent=2)}"