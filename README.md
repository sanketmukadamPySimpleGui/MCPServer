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
