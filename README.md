-----

# Multi-Purpose Chatbot (MCP) Quickstart

This project is a Proof-of-Concept (PoC) demonstrating a powerful, **agentic AI chatbot**. The application features a web-based chat interface that connects to large language models (LLMs) and leverages a local **Model Context Protocol (MCP)** server to execute a wide range of real-world tasks. This architecture allows the AI to go beyond simple text generation and interact with its local environment, databases, and external APIs.

-----

## 🚀 Key Features

  * **Agentic AI**: The LLM can interpret user requests and autonomously decide to call one or more tools to fulfill the request.
  * **Intuitive Web UI** 💬: A new, modern chat interface built with FastAPI and vanilla JavaScript. It's protected by a simple login and streams responses in real-time via WebSockets, providing a highly responsive user experience.
  * **Flexible LLM Providers** 🤖: Seamlessly switch between **OpenAI's** cloud models and a locally-run **Ollama** instance directly from the UI. The list of available Ollama models is detected automatically and populated in a dropdown menu.
  * **Multi-Database Connectivity** 📊: The agent can query different data sources, including an in-memory **SQLite** database and an external **MongoDB** instance. A dropdown in the UI allows you to select the target database for your queries.
  * **Rich Toolset**: The MCP server exposes a comprehensive set of tools for:
      * **File System Operations**: Listing, reading, and writing files.
      * **System Interaction**: Executing shell commands and checking system resource usage.
      * **Data Analysis**: Querying structured and unstructured data with natural language.
      * **External API Calls**: Fetching real-time weather data from the OpenWeatherMap API.
  * **Dynamic Tool-Use**: A simple toggle switch allows the user to enable or disable the agent's ability to use tools, demonstrating the modularity of the MCP integration.
  * **Secure & Containerized**: The entire application stack is containerized with Docker, making it easy to set up and deploy.

-----

## ⚙️ Architecture

The application consists of a microservice architecture with three main components that work together to create the agentic experience.

1.  **Web Client (`mcp-client`)**: This is the user-facing application and the central orchestrator. It's a FastAPI web server that serves the chat UI. When a user sends a message, the client is responsible for communicating with the selected LLM, managing the conversation history, and invoking the MCP server when a tool call is needed.
2.  **LLM Provider (OpenAI or Ollama)**: This is the "brain" of the agent. The client sends the conversation history and a description of the available MCP tools to the LLM. The LLM then decides whether to respond with text or to request a tool call to gather more information or perform an action.
3.  **MCP Server (`mcp-server`)**: This is the "hands" of the agent. It's a local server that exposes a set of capabilities (tools) to the client via the Model Context Protocol. It handles the actual execution of tasks like reading a file, running a SQL query, or calling a weather API.

### The Role of the Model Context Protocol (MCP)

**MCP** is the standardized communication layer that connects the **Web Client** and the **MCP Server**. It defines how the client can discover the server's capabilities and how it can execute them.

  * **Tool Discovery**: When the client starts, it connects to the MCP server, which sends back a list of all its available tools and their schemas (i.e., names, descriptions, and required arguments). The client then formats this information to be included in the prompt for the LLM.
  * **Tool Invocation**: When the LLM decides to use a tool, the client sends a request to the MCP server, specifying the tool's name and arguments. The server executes the corresponding function and sends the result back to the client.
  * **Message Format**: All communication between the client and server follows a JSON-based format, ensuring reliable and interoperable message passing.

-----

<img width="1406" height="790" alt="Screenshot 2025-09-23 at 11 05 47 AM" src="https://github.com/user-attachments/assets/94eb274b-a6c2-474e-ae1a-0dc8d937733e" />




## 🚀 Getting Started

### Prerequisites

  * Docker and Docker Compose
  * An OpenAI API key (if you plan to use OpenAI models)

### 1\. Configure Environment Variables

Create a file named `.env` in the root of the project. This file stores your API keys and configuration.

```env
# REQUIRED for the client to find the server
SERVER_URL=http://mcp-server:8000

# Optional: To use the OpenAI API
OPENAI_API_KEY=your_openai_api_key_here
# By default, uses gpt-4o-mini. Change as needed.
OPENAI_MODEL=gpt-4o-mini

# Optional: To configure Ollama
# By default, uses llama3. Change as needed.
OLLAMA_BASE_URL=http://ollama-server:11434
OLLAMA_MODEL_NAME=llama3

# Database Connections
# The client UI will automatically detect and display connections.
# The 'sqlite_demo' is in-memory and always available.
# To connect to a local MongoDB instance, uncomment and configure these:
# DB_CONN_MONGO_TYPE=mongodb
# DB_CONN_MONGO_URI=mongodb://root:example@mongo:27017/
# DB_CONN_MONGO_DBNAME=mcp-retail-db
```

### 2\. Launch the Application

Run the following command in your terminal:

```bash
docker compose up --build
```

Docker will build and start three containers:

  - `mcp-server`: The core tool server.
  - `mcp-client`: The web-based chatbot client.
  - `ollama-server`: A local Ollama instance for hosting open-source models.

### 3\. Access the Chatbot

Open your web browser and navigate to:
`http://localhost:3000`

You'll be directed to a login page. Enter a username to start a new chat session. The UI will automatically connect to the `mcp-server` and populate the sidebar with available tools and database connections.

-----

## 🛠️ Maintenance & Troubleshooting

### `reset_mcp.sh` Utility

The `reset_mcp.sh` script is a crucial utility for completely resetting the application stack. It's particularly useful when you're making changes to the code or need to clean up data volumes from previous runs.

#### What it does:

1.  **Stops and removes** all running Docker containers defined in `docker-compose.yml`.
2.  **Removes all associated data volumes** (`mongo_data`, `ollama_data`), ensuring a clean state.
3.  **Removes the Docker network** for the project.
4.  **Deletes residual Ollama data** on the host machine.
5.  **Rebuilds all Docker images** from scratch, ensuring any code changes are included.
6.  **Restarts all services** in detached mode (`-d`).
7.  **Monitors container health** with a 30-step loop, waiting for each service to become `healthy` before declaring the setup complete.

#### How to use it:

To use the script, simply make it executable and run it from your terminal:

```bash
chmod +x ./reset_mcp.sh
./reset_mcp.sh
```

This will perform a full, clean restart of your application, resolving most common issues that might arise from caching or corrupted data.

-----

## 📖 Example Queries

The agent will automatically use the correct tool (`run_sql_query` for SQLite or `find_documents` for MongoDB) based on your chosen database connection.

### SQLite Database Queries (`sqlite_demo` connection)

  - "How many products are in the `electronics` category?"
  - "List the top 5 most expensive products."
  - "What is the schema for the `products` table?"
  - "Who is the highest-paid employee?"

### MongoDB Database Queries (`mcp-retail-db` connection)

  - "What collections are in the `retail_otc_poc` database?"
  - "Show me a sample document from the `customers` collection."
  - "Find the customer with the email `customer1@example.com`."
  - "How many orders are there with the status `Shipped`?"

### General Queries (with tools enabled)

  - "What is the current system usage?"
  - "What is the weather like in New York?"

Feel free to explore the full capabilities of the agent and discover how it seamlessly integrates LLM intelligence with real-world tasks.

### Documentation for `fastmcp_quickstart.py`

This is a comprehensive documentation for the `fastmcp_quickstart.py` script. You can add this directly to a GitHub repository or a project wiki.


### Documentation of the MCP Project Structure 📂

This project is a multi-container application that uses Docker Compose to run a server-client architecture with a database and a local LLM server.

***

### Purpose of Key Folders and Files

* **`mcp-client/`**: This directory contains the code for the **user-facing web application**. It's the front end that users interact with.
    * `auth.py`: Handles user authentication, likely managing logins and sessions.
    * `clients.py`: The entry point for the web application, likely a FastAPI or Flask server that serves the HTML pages and manages WebSocket connections.
    * `llm_utils.py`: Contains utility functions for interacting with different LLM providers like Ollama and OpenAI, including tool formatting.
    * `templates/`: A folder that stores HTML files (`index.html`, `login.html`) which are rendered by the client application.
    * `static/`: Contains static assets like CSS (`style.css`, `login.css`) and JavaScript (`script.js`) files that define the look and dynamic behavior of the web pages.

* **`mcp-server/`**: This is the core of the application, acting as the **backend API**.
    * `database.py`: Manages the connection and interaction with the database, likely MongoDB as indicated by the `mongo` service in Docker Compose.
    * `fastmcp_quickstart.py`: This is likely the main application file that defines the API endpoints and the logic for the MCP agent.

* **`ollama-custom/`**, **`ollama-models/`**, **`ollama-models-backup/`**: These folders are used for managing the Ollama LLM models. The `ollama-custom` and `ollama-models` folders likely hold the active models, while `ollama-models-backup` is for storing copies.

* **`nginx/`**: This directory holds the configuration for the **Nginx reverse proxy server**. Nginx is used to route incoming web traffic to the correct application services.

* **`docker-compose.yml`**: This file defines the entire multi-container application stack. It specifies each service (e.g., `mcp-client`, `mcp-server`, `nginx`), their images, ports, and dependencies, orchestrating the entire system.

***

### The Purpose of the Nginx Server 🌐

In this architecture, the **Nginx server acts as a reverse proxy**. Its primary purpose is to receive all incoming web requests on standard HTTP/S ports (80 and 443) and forward them to the appropriate internal services running inside the Docker network.

* **Single Entry Point**: The Docker Compose output shows that the Nginx container exposes ports 80 and 443 to the host machine. This means all external traffic comes through Nginx first. This provides a single, clean entry point for the entire application.
* **Routing**: The Nginx configuration file (`nginx/`) contains rules to route requests based on their path. For example, it might direct requests for static files and the main application (`/`, `/login`, etc.) to the `mcp-client` service and API requests (`/api/`) to the `mcp-server` service.
* **SSL/TLS Termination**: Although not explicitly shown in the `docker-compose` output, Nginx is commonly used for **SSL/TLS termination**. This means it can handle the secure HTTPS connection, decrypting the traffic before it's sent to the internal, non-HTTPS services (`mcp-client` and `mcp-server`), which simplifies the application's security management.
* **Static File Serving**: Nginx is highly efficient at serving static assets like CSS, JavaScript, and images. It can be configured to directly serve files from the `static/` directory without involving the `mcp-client` application, which significantly improves performance and reduces the load on the application server.


-----

# FastMCP Quickstart Server

This project is a demonstration of an **MCP (Model Context Protocol)** server built using the `FastMCP` framework. It exposes a variety of tools, resources, and prompts, allowing Large Language Models (LLMs) to interact with the external environment, including the file system, databases, web APIs, and the internet.

### 📝 Features

This server provides a rich set of capabilities, categorized by function:

  * **Core Functions**:
      * `add`: Adds two numbers.
      * `get_current_datetime`: Retrieves the current date and time.
      * `list_files`: Lists files and directories.
      * `read_file`: Reads the content of a file.
      * `write_file`: Writes content to a file.
      * `run_shell_command`: Executes a predefined set of safe shell commands.
      * `get_system_usage`: Returns system metrics like CPU and memory usage.
  * **Database Management**:
      * `list_database_connections`: Lists all available database connections.
      * `get_database_info`: Retrieves information about a specific database.
      * `list_tables`: Lists tables or collections in a database.
      * `get_table_schema`: Gets the schema for a table or collection.
      * `run_sql_query`: Executes a SQL query.
      * `find_documents`: Finds documents in a MongoDB collection.
      * `count_documents`: Counts documents in a MongoDB collection.
  * **Internet & Web Tools**:
      * `web_scrape`: Scrapes text content from a URL.
      * `get_current_weather`: Fetches current weather data from OpenWeatherMap.
      * `Google Search`: Performs a Google search using SerpApi.
  * **Resources & Prompts**:
      * `get_greeting`: A resource that returns a greeting.
      * `system_info`: A resource that provides basic system information.
      * `greet_user`: A prompt to generate a user greeting.
      * `summarize_text`: A prompt to summarize a given text.
      * `translate_text`: A prompt to translate text.

### ⚙️ Prerequisites

Before you can run the server, you need to set up the following:

#### 1\. Environment Variables (`.env`)

Create a `.env` file in the project's root directory with the following variables:

```
# Required for the `get_current_weather` tool
OPENWEATHERMAP_API_KEY=your_openweathermap_api_key

# Required for the `Google Search` tool
SERPAPI_API_KEY=your_serpapi_api_key

# Optional: Limits the number of characters scraped by `web_scrape`
MAX_SCRAPED_CHARS=20000
```

#### 2\. Python Dependencies

Install the required Python packages using pip. Your `requirements.txt` file should contain:

```
fastmcp
python-dotenv
psutil
httpx
requests
beautifulsoup4
serpapi
pymongo
```

### 🚀 Installation and Usage

Follow these steps to get the server up and running:

1.  **Clone the repository**:

    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```

2.  **Set up a virtual environment** (recommended):

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
    ```

3.  **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4.  **Start the server**:

    ```bash
    python fastmcp_quickstart.py
    ```

    This command starts the server using the default `stdio` transport. The server will now be listening for requests.

### 🌐 Transports

The server supports multiple transport protocols. You can specify the desired transport when running the script:

  * **`stdio` (Default)**: For local testing and CLI-based interactions. Communication happens over standard input and output.
    ```bash
    python fastmcp_quickstart.py --transport stdio
    ```
  * **`sse`**: For streaming communication over HTTP, used by the `mcp-client`. The server runs as a web service.
    ```bash
    python fastmcp_quickstart.py --transport sse
    ```
    The server will be available at `http://localhost:8000`. The SSE endpoint is at `/sse`.
  * **`streamable-http`**: Similar to SSE, but uses HTTP streaming.
    ```bash
    python fastmcp_quickstart.py --transport streamable-http
    ```

### 🔒 Safety Measures

The `run_shell_command` tool is designed with a strong emphasis on security. It **only allows** a predefined set of safe shell commands listed in the `ALLOWED_SHELL_COMMANDS` constant. Any attempt to execute a command not on this list will be rejected with an error. This prevents malicious command injection.

### Documentation for `database.py`

This documentation outlines the `database.py` script, which defines the core components for handling various database connections within the MCP server. This file is responsible for abstracting database operations, managing connections, and populating sample data for demonstration purposes.

-----

### 📝 Key Components and Architecture

The file follows a structured, object-oriented design to support different database types while providing a consistent interface for the MCP tools.

  * **`DatabaseConnector` (Abstract Class)**: This is the foundation of the system. It defines a contract for all database connectors. Any new database type (e.g., PostgreSQL, MySQL) must implement the methods specified here, such as `connect`, `list_tables`, and `run_sql_query`. This ensures all connectors can be used interchangeably by the MCP server.

  * **`SQLiteInMemoryConnector`**: A concrete implementation of `DatabaseConnector` for an in-memory SQLite database. This is a **hardcoded demo connection** that automatically creates and populates two sample schemas:

      * **Supply Chain**: Includes tables like `products`, `suppliers`, `warehouses`, and `inventory`.
      * **HR**: Includes `departments` and `employees` tables.
        This connector is designed for proof-of-concept and local testing, ensuring the server has functional database tools out-of-the-box without any external dependencies.

  * **`MongoDbConnector`**: An implementation for **MongoDB**. It requires the `pymongo` library and connects to a MongoDB server using a URI and database name provided in the environment variables. Upon connection, it populates a sample **Retail Order-to-Cash** schema with `customers`, `products`, and `orders` collections.

  * **`DatabaseManager`**: The central class that manages all database connectors. It automatically discovers and initializes connectors based on `DB_CONN_*` environment variables. It provides methods to connect to all databases at once (`connect_all`), disconnect from them, and retrieve specific connectors by name (`get_connector`).

-----

### ⚙️ Configuration

The `DatabaseManager` automatically loads database connections from your environment variables.

#### Hardcoded SQLite Connection

A connection named **`sqlite_demo`** is always available by default. You do not need to configure any environment variables for it to work. It's a great way to test the database tools immediately.

#### MongoDB Connection

To enable a MongoDB connection, you must set the following environment variables. The name of the connection is derived from the variable prefix (e.g., `DB_CONN_MONGO_PROD` creates a connection named `mongo_prod`).

```ini
# Example for a MongoDB connection named 'mongo_prod'
DB_CONN_MONGO_PROD_TYPE=mongodb
DB_CONN_MONGO_PROD_URI=mongodb://localhost:27017/
DB_CONN_MONGO_PROD_DBNAME=mcp_demo_db
```

### 🛠️ Usage in `fastmcp_quickstart.py`

This file is imported by `fastmcp_quickstart.py`. The `DatabaseManager` is instantiated, and its `connect_all()` method is called to set up all configured databases.

The tools in `fastmcp_quickstart.py` then use the `DatabaseManager` to interact with the databases, for example:

  * `list_tables(db_connection_name)` calls `db_manager.get_connector(db_connection_name).list_tables()`.
  * `run_sql_query(db_connection_name, sql_query)` calls `db_manager.get_connector(db_connection_name).run_sql_query(sql_query)`.

This design allows the LLM to access different databases by simply specifying the correct `db_connection_name` in its tool calls, without needing to know the underlying database type or connection details.

### Documentation for `clients.py`

This documentation outlines the `clients.py` file, which serves as a web-based chat client for the MCP server. It's built with FastAPI and uses WebSockets to provide a real-time, interactive user experience. This client connects to an MCP server and an LLM provider (OpenAI or Ollama) to enable an agentic conversational interface.

-----

### 📝 Key Components and Architecture

The client application is built around several key components:

  * **`FastAPI` Framework**: Provides the web server, handling HTTP endpoints for serving web pages (`/`, `/login`) and API endpoints (`/api/ui-config`, `/health`). It also manages the core WebSocket connection (`/ws`) for real-time communication.
  * **`Settings`**: A Pydantic `BaseSettings` class that manages configuration through environment variables. It defines the addresses for the Ollama and MCP servers, as well as the OpenAI model and API key.
  * **`lifespan`**: An `asynccontextmanager` that handles the application's startup and shutdown. During startup, it establishes a persistent connection to the MCP server via `_manage_mcp_session`, retrieves all available tools and resources, and connects to the Ollama server to get a list of available models.
  * **`_manage_mcp_session`**: A crucial asynchronous task that maintains a connection to the MCP server. It uses `sse_client` to listen for MCP events and dynamically updates the FastAPI application state with metadata about available tools, resources, and database connections. This ensures the client's UI always has the most up-to-date information.
  * **`ChatManager`**: This class (imported from `chat_manager.py`) is at the heart of the conversational logic. For each user WebSocket session, a dedicated `ChatManager` instance is created. This manager orchestrates the flow:
    1.  Receiving a user message.
    2.  Sending the message to the selected LLM (OpenAI or Ollama).
    3.  Handling tool calls returned by the LLM by calling the appropriate methods on the `mcp_session`.
    4.  Streaming the LLM's response or tool output back to the user via the WebSocket.
  * **`WebSocket` Endpoint (`/ws`)**: This is the main channel for communication between the user's browser and the server. It handles incoming chat messages, manages user sessions with `ChatManager`, and streams back responses as they are generated. The session is identified by the WebSocket's unique ID and managed with a global lock to prevent race conditions.

### 🌐 API Endpoints

  * **`/` or `/index`**: Serves the main chat interface. Requires a username to be set in a cookie, otherwise redirects to the login page.
  * **`/login`**: Serves the login page to set a username.
  * **`/api/ui-config`**: An API endpoint that provides the UI with all necessary information, including the server name, version, and a list of available tools, resources, prompts, and database connections from the connected MCP server.
  * **`/health`**: A simple endpoint to check the status of the MCP session and the Ollama server connection.

### 🛠️ Configuration and Setup

To run this client, you must configure the following environment variables in your `.env` file:

```ini
# Address of the MCP server.
# Example: http://mcp-server:8000
SERVER_URL=
MCP_SERVER_URL=

# Address of the Ollama server.
# Example: http://ollama-server:11434
OLLAMA_BASE_URL=

# The name of the Ollama model to use.
# Example: llama3
OLLAMA_MODEL_NAME=

# Your OpenAI API key (optional, for using OpenAI models).
# OPENAI_API_KEY=
# The OpenAI model to use if the API key is set.
# OPENAI_MODEL=gpt-4o-mini

# Set to 'true' to enable detailed debug logs in the UI.
# MCP_CLIENT_DEBUG=false
```

### Documentation for `chat_manager.py`

This documentation describes the `chat_manager.py` file, a core component of the MCP client application. Its primary function is to manage conversational flow by integrating user messages, large language models (LLMs), and MCP tools. It handles the logic of determining when to call a tool, executing the tool, and then generating a final, user-friendly response based on the tool's output.

---

### 📋 Class: `ChatManager`

The `ChatManager` class is instantiated for each individual user session to maintain state, including the chat history and the current database connection.

#### **Constructor (`__init__`)**
The constructor initializes the `ChatManager` instance with several key dependencies and settings:
* `mcp_session`: A `ClientSession` object that provides the connection to the MCP server for executing tools.
* `openai_client`: An `AsyncOpenAI` client for interacting with OpenAI models.
* `ollama_client`: An object for communicating with Ollama models.
* `openai_tools`: A list of tool definitions formatted for the OpenAI API.
* `available_tools`: A comprehensive list of all tools available from the MCP server.
* `username`, `session_id`, `debug`: Metadata for logging and session management.
* `db_connection_name`: An optional parameter to specify which database connection to use for all database-related tasks in the session. This is dynamically updated based on user selection in the UI.

---

### ⚙️ Core Methods

#### **`handle_chat_stream`**
This is the main public method that orchestrates the entire chat flow. It's an `async` generator, which allows it to stream the response back to the client in real time.

1.  **Updates State**: It first checks if the `db_connection_name` has changed. If so, it resets the chat history to ensure the system prompt is updated with the correct database context.
2.  **Appends Message**: The user's message is added to the conversation history.
3.  **Chooses Provider**: It determines whether to use OpenAI or Ollama based on the `llm_provider` parameter.
4.  **Handles Tool-Use**:
    * If `use_mcp` is `True`, it calls `_handle_llm_with_mcp_tools`, which is the core logic for tool-enabled conversations.
    * If `use_mcp` is `False`, it calls a simpler streaming method (`_handle_openai_simple_stream` or `_handle_ollama_simple_stream`) that doesn't involve tool calls.

---

### 🔗 LLM and Tool Interaction Logic

#### **`_handle_llm_with_mcp_tools`**
This method is the brain of the agentic behavior. It performs the following steps in a loop:

1.  **Prepares Tools**: It filters the list of available tools and formats them into a standardized format compatible with both OpenAI and Ollama.
2.  **Calls LLM**: It makes a call to the selected LLM (`openai_client` or `ollama_client`) with the current chat history and the list of available tools.
3.  **Parses Response**: It streams the response from the LLM. It looks for either a direct text response or a tool call.
4.  **Handles Tool Calls**:
    * If a tool call is detected, it logs the call, formats the arguments, and adds a `tool-call` message to the stream for the UI.
    * Crucially, it **injects the `db_connection_name`** into the tool arguments for any database-related tool, overriding the need for the user to specify it.
    * It then calls the MCP tool using `self.mcp_session.call_tool()`.
5.  **Processes Tool Output**: It receives the raw output from the tool. The `_format_tool_output_for_llm` helper function is used to convert this output (which may be a complex JSON object) into a clean, human-readable string. This formatted output is then added back to the conversation history with the role "tool".
6.  **Final LLM Call**: After a tool call is executed and its result is added to the history, the manager makes a **second LLM call** (`_run_final_llm_call`). This is a critical step; the LLM uses the tool's output to generate the final, natural-language response for the user.

---

### 🔍 Helper Methods

* **`_get_system_prompt`**: This method dynamically generates the initial system prompt for the LLM. It's updated to include specific instructions for the `web_scrape` tool and a critical rule for handling MongoDB queries, ensuring the LLM uses the correct parameters (`collection`, `filter`, `projection`) and not incorrect ones like `collection_name`. It also adds context about the current database connection if one is active.
* **`_tool_accepts_db`**: A helper that checks if a given tool's schema includes a `db_connection_name` parameter, which is used to automatically inject the connection name.
* **`_check_required_args`**: Validates that all necessary arguments are present for a tool call, providing helpful error messages if something is missing (e.g., a city for the weather tool, or a collection for a MongoDB tool).
* **`_parse_tool_args`**: A utility function to safely parse the arguments provided by the LLM, handling potential formatting inconsistencies.
* **`_format_tool_output_for_llm`**: Converts raw JSON or other data types from a tool's output into a clean string for the LLM. It includes specific formatting rules for file lists, counts, and tabular data, ensuring the LLM receives well-structured information to base its final response on.

* ### Documentation for `llm_utils.py`

This documentation describes the `llm_utils.py` file, which contains utilities for interacting with different LLMs, specifically **Ollama**, and for formatting tool definitions to be compatible with various LLM APIs.

---

### 📋 Class: `OllamaClientWrapper`

This class provides an asynchronous client for the Ollama API. It includes built-in retry logic and handles streaming responses efficiently.

#### **Constructor (`__init__`)**
The constructor initializes the client with the following parameters:
* `base_url`: The base URL of the Ollama API server.
* `retries`: The number of times to retry a failed request (default: 3).
* `backoff`: The initial backoff time in seconds for retries, which increases exponentially with each attempt (default: 1.0).

#### **Core Methods**

* **`get_models()`**: This async method retrieves a list of available models from the Ollama server. It includes robust error handling and retries. It correctly parses the API response, which typically returns a list of models under a `"data"` key.
* **`chat_stream(model_name, messages)`**: This async generator method sends a chat request to the Ollama API and streams the response back. It handles network errors and retries, yielding each JSON chunk of the streamed response.
* **`chat_with_tools(model, messages, available_tools, stream)`**: **This is the key new method.** It is designed to handle **Ollama's native tool-calling feature**. It first uses the `format_mcp_tools_for_ollama` function to format the MCP tools into a structure that Ollama understands. It then sends this payload to the `/v1/chat/completions` endpoint and uses the `chat_stream` method to handle the request. Importantly, it also **adjusts the format** of the tool call chunk in the response to align with what the `chat_manager.py` module expects (specifically, by ensuring each tool call has an `id`, `type`, and `function` key).

---

### 🛠️ Tool Formatting Helpers

These are a set of utility functions responsible for converting raw MCP tool metadata into a standardized JSON Schema format that is understood by LLM APIs like OpenAI and Ollama.

* **`_sanitize_fn_name(name)`**: A helper function that takes a string and sanitizes it to be a valid function name (e.g., removing special characters, converting to lowercase, and ensuring it doesn't start with a number). It also truncates the name to a maximum of 64 characters.
* **`_map_type_to_json(ptype)`**: Maps common programming language data types (e.g., `'int'`, `'list'`) to their corresponding JSON Schema types (e.g., `'integer'`, `'array'`).
* **`_build_parameters_from_raw(raw)`**: The central function for parsing tool parameter definitions. It is highly flexible and can handle various input formats, including a list of parameter descriptors or a simple dictionary of parameter names and types. It correctly identifies and extracts `required` parameters, ensuring the final JSON Schema is accurate.
* **`format_mcp_tools_for_openai(tools)`**: This function iterates through a list of MCP tools and uses the helper functions (`_sanitize_fn_name`, `_build_parameters_from_raw`) to transform them into the specific `{"type": "function", "function": {...}}` format required by the OpenAI API.
* **`format_mcp_tools_for_ollama(tools)`**: This function performs the same transformation as the OpenAI formatter but tailors the output to the slightly different tool-calling format required by Ollama's API.

* Based on the HTML files, here is a description of the user interface for the MCP client.

***

### Login Page (`login.html`)

The login page is a simple, minimalist interface with a centered container for user credentials.

* **Header**: It displays "SM" in a logo-like circle and a dynamic server name (e.g., `{{ server_name }}`) to inform the user which server they are connecting to.
* **Form**: The form has two input fields: `username` and `password`, both of which are required.
* **Action**: The form submits a `POST` request to the `/login` endpoint.
* **Error Handling**: If a login fails, a styled error message is displayed in a `div` with the `id` `error-message`.
* **Footer**: A simple footer with a "🔒 Secure Login" message is present at the bottom of the page.

***

### Chat Interface (`index.html`)

The main chat interface is a two-column layout consisting of a left-hand sidebar and the main chat area.

#### **Sidebar (`<aside>`)**
The sidebar provides information and controls related to the MCP server.

* **Header**: Displays "MCP Server" and a dynamic server name (`<p id="server-name">`).
* **Details Sections**: Uses HTML `<details>` and `<summary>` tags to create collapsible sections for:
    * **Server Information**: Shows details about the connected server.
    * **Available Tools**: Lists the tools the agent can use.
    * **Available Resources**: Lists resources like database connections.
    * **Available Prompts**: Lists predefined prompts that users can select.

#### **Main Chat Area (`<main>`)**

* **Header (`<header>`)**:
    * **Title**: Displays "Agentic AI Chatbot" and "Powered by OpenAI & MCP."
    * **Controls**: Contains several controls for customizing the chat session:
        * An **"Enable MCP Tools" toggle switch** (`<input type="checkbox" id="mcp-toggle">`).
        * A **"LLM Provider" dropdown** (`<select id="llm-provider-select">`) with options for "OpenAI" and "Ollama (Local)."
        * A **model selection dropdown** for Ollama (`<select id="ollama-model-select">`), which is initially hidden.
        * A **"Database" dropdown** (`<select id="db-connection-select">`) to select the active database.
        * A **"Logout" button** that submits a logout request.

* **Messages Section (`<section id="messages">`)**:
    * This is the main display area for the chat conversation.
    * It contains an initial welcome message from the bot.
    * A hidden `div` with the message "🤔 Thinking..." (`<div id="thinking" class="hidden">`) is used to indicate when the bot is processing a request.
* **Input Area (`<footer>`)**:
    * A **textarea** (`<textarea id="message-input">`) for the user to type their message.
    * A **send button** (`<button id="send-button">`) with an arrow emoji to submit the message.
 
* ### JavaScript Functionality (`script.js`)

The `script.js` file manages the dynamic behavior of the MCP client's chat interface. It handles user interactions, manages the WebSocket connection for real-time communication, and fetches configuration data from the server to populate the UI.

***

### ⚙️ Core Features & Logic

1.  **UI Initialization**: The script waits for the `DOMContentLoaded` event before selecting all the necessary HTML elements and setting up event listeners.

2.  **Responsive Sidebar**:
    * It checks if the user is on a mobile device by checking the viewport width.
    * On mobile, a click event listener is added to the sidebar header, which toggles a `visible` class on the sidebar to show or hide it.

3.  **Logout Functionality**:
    * An event listener on the "Logout" button clears the `username` cookie and redirects the user to the `/login` page.

4.  **WebSocket Communication**:
    * A `connectWebSocket` function establishes a real-time connection to the server at `/ws`.
    * **Message Handling**: The `onmessage` event listener processes different types of incoming JSON messages from the server:
        * **`"response"`**: This is a streaming text response from the LLM. It accumulates message chunks and updates the last message element in the chat, formatted as markdown using the `marked.js` library.
        * **`"error"`**: Displays an error message and hides the "Thinking" indicator.
        * **`"tool-call"`**: When the LLM decides to use a tool, this message type is received. It displays a formatted box showing the tool's name and arguments. A loading indicator is added to signal that a tool is being executed.
        * **`"tool-result"`**: Displays the result of a tool execution in a formatted box and removes the tool-specific loading indicator.
    * **Reconnection**: If the WebSocket connection closes unexpectedly, the script attempts to reconnect after a 5-second delay.

5.  **Sending Messages**:
    * The `sendMessage` function is triggered when the user clicks the "Send" button or presses `Enter`.
    * It collects the user's message and the current state of the UI controls (**MCP toggle**, **LLM provider**, **Ollama model**, and **database connection**).
    * It sends this information to the server as a JSON payload via the WebSocket connection.
    * The UI is updated to show the user's message and a "Thinking" indicator is displayed.

6.  **Dynamic UI Population**:
    * The `loadUiConfig` function fetches configuration data from the `/api/ui-config` endpoint.
    * This data is used to dynamically populate the sidebar with **server details**, **available tools**, **resources**, and **prompts**.
    * The `LLM Provider` and `Database` dropdowns are also populated with options fetched from the server.
    * The `populateSelect` and `populateList` helper functions are used to render this data into the correct HTML elements. A specific `populatePromptsList` function also adds a click listener to each prompt item, allowing the user to quickly send a predefined prompt to the chatbot.
  

### Stylesheets for MCP Client

The provided CSS files, `style.css` and `login.css`, define the visual appearance and responsive behavior of the MCP client's user interfaces. They establish a modern, clean design with a focus on user experience across different devices.

---

### `login.css` - Login Page Styling

This stylesheet is dedicated to the login page and establishes a focused, branded look.

* **Color Palette**: It uses CSS custom properties (`:root`) to define a consistent color scheme, including a **primary blue (`--primary-color`)**, a background gradient (`--background-start`, `--background-end`), and text/border colors.
* **Layout**: The body uses a flexbox layout to **center the login container** both horizontally and vertically.
* **Login Box**: The main login form is contained within a box with a translucent white background (`--card-background`), rounded corners, and a subtle box shadow. This design is enhanced with a `backdrop-filter` for a modern, blurred glass effect.
* **Elements**:
    * The `server-info` section features a circular logo with a gradient background, a server name, and a descriptive paragraph.
    * Input fields (`.input-group`) have a clean design with rounded borders that change color and apply a shadow on focus.
    * The **Login button** has a solid blue background that darkens and lifts on hover, providing visual feedback.
    * Error messages are styled with a specific red color (`--error-color`) for clear visibility.
* **Responsiveness**: A media query ensures the login box is responsive, reducing its width on smaller screens to fit a mobile view.
* **Animation**: The `.login-container` uses a `fadeIn` keyframe animation to smoothly transition into view on page load.

---

### `style.css` - Chat Interface Styling

This comprehensive stylesheet handles the layout and aesthetics of the main chat application, prioritizing a **mobile-first approach** before adapting for larger screens.

* **Mobile-First Layout**:
    * The `#app-container` is a column-based flexbox layout, stacking the chat interface on top (`order: 1`) and the sidebar on the bottom (`order: 2`). This is a key design choice for smaller screens.
    * The sidebar (`#sidebar`) is initially hidden off-screen using `transform: translateY(100%)` and a `transition` to create a smooth slide-up animation.
    * The sidebar header is made clickable (`cursor: pointer`) to trigger a JavaScript-based toggle that adds a `.visible` class to show the sidebar.
    * The header of the chat area also stacks its content vertically on mobile, and controls wrap to a new line.

* **Desktop Layout (`@media (min-width: 768px)`)**:
    * A media query completely reconfigures the layout for screens 768px and wider.
    * The `#app-container` switches to a **row-based flexbox layout**, placing the sidebar on the left (`order: 1`) and the chat container on the right (`order: 2`).
    * The sidebar and header layouts are adjusted to a traditional horizontal arrangement, and the sidebar's toggle functionality is disabled by changing its `cursor` to `default`.

* **Chat Bubbles & Messaging**:
    * The `.message` class defines a rounded, word-wrapping container for chat messages.
    * **User messages** have a blue background and are aligned to the right (`align-self: flex-end`).
    * **Bot messages** are styled with a light gray background and are aligned to the left (`align-self: flex-start`).
    * **Tool call** messages are given a distinct, yellowish background to visually separate them from regular chat text.
    * The "Thinking..." indicator is styled to appear below the messages and uses a `display: flex` property to center its content.

* **Input & Controls**:
    * The input area (`#input-container`) uses flexbox to align the text area and send button.
    * The **text area (`#message-input`)** has a rounded design that can grow in height as the user types, up to a maximum height.
    * The **send button** is a rounded circle with a blue background that animates on hover.

* **Loading Indicator**: A CSS-only `loading-indicator` class creates a spinning circular animation using a `border` and a `@keyframes` rule. This is likely used by the JavaScript to provide visual feedback during tool execution.

* 
