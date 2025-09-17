// mcp-client/static/script.js
console.log("✅ script.js: File loaded by browser.");

document.addEventListener("DOMContentLoaded", () => {
    console.log("✅ DOMContentLoaded fired. Initializing chat UI.");

    const messagesDiv = document.getElementById("messages");
    const messageInput = document.getElementById("message-input");
    const sendButton = document.getElementById("send-button");
    const thinkingDiv = document.getElementById("thinking");
    const llmProviderSelect = document.getElementById("llm-provider-select");
    const ollamaModelSelect = document.getElementById("ollama-model-select");
    const dbConnectionSelect = document.getElementById("db-connection-select");
    const mcpToggle = document.getElementById("mcp-toggle");
    const serverNameP = document.getElementById("server-name");
    const serverInfoContentDiv = document.getElementById("server-info-content");
    const toolsListUl = document.getElementById("tools-list");
    const resourcesListUl = document.getElementById("resources-list");
    const promptsListUl = document.getElementById("prompts-list");
    const logoutButton = document.getElementById("logout-button");

    // --- Logout Handler ---
    if (logoutButton) {
        logoutButton.addEventListener("click", () => {
            console.log("🔒 Logout button clicked.");
            document.cookie = "username=; Max-Age=0; path=/";
            window.location.href = "/login";
        });
    } else {
        console.warn("⚠️ Logout button not found in DOM.");
    }

    // --- WebSocket setup ---
    let ws = null;
    let lastBotMessageElement = null;
    let currentLoadingIndicator = null;
    let accumulatedMessageText = "";

    function connectWebSocket() {
        if (ws && ws.readyState === WebSocket.OPEN) {
            return;
        }

        try {
            const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
            console.log("🌐 Connecting WebSocket:", wsUrl);
            ws = new WebSocket(wsUrl);

            ws.onopen = () => console.log("✅ WebSocket connected");
            ws.onerror = (err) => console.error("❌ WebSocket error:", err);
            ws.onclose = () => {
                console.warn("⚠️ WebSocket closed. Attempting to reconnect in 5s...");
                showThinking(false);
                setTimeout(connectWebSocket, 5000);
            };

            ws.onmessage = (event) => {
                let parsedData;
                try {
                    parsedData = JSON.parse(event.data);
                    
                    if (parsedData.type === "debug") {
                        console.debug("DEBUG CHUNK:", parsedData.message);
                        return;
                    }

                    if (parsedData.type === "response") {
                        // This is the first chunk of a new message
                        if (lastBotMessageElement === null) {
                            // Hide the "Thinking" indicator as soon as the final response starts to stream
                            showThinking(false); 
                            lastBotMessageElement = appendMessage("", "bot");
                        }
                        
                        // Accumulate the content chunks
                        accumulatedMessageText += parsedData.message;

                        // Update the innerHTML with the accumulated message, formatted as markdown.
                        lastBotMessageElement.innerHTML = formatMessage(accumulatedMessageText);

                        // If there's a tool call indicator, remove it on the first response chunk
                        if (currentLoadingIndicator) {
                            currentLoadingIndicator.remove();
                            currentLoadingIndicator = null;
                        }

                    } else if (parsedData.type === "error") {
                        // Reset everything on error
                        accumulatedMessageText = "";
                        lastBotMessageElement = null;
                        appendMessage(`Error: ${parsedData.message}`, "error");
                        showThinking(false);
                    } else if (parsedData.type === "tool-call") {
                        // Reset message state and start the tool call animation
                        accumulatedMessageText = "";
                        lastBotMessageElement = null;

                        const toolCallContent = `
                            <pre class="tool-call-box"><code>🔧 <b>Tool Call:</b> ${parsedData.message.name}\n${JSON.stringify(parsedData.message.arguments, null, 2)}</code></pre>
                        `;
                        const toolCallMessage = appendMessage(toolCallContent, "tool-call");
                        
                        // Create and show the loading indicator
                        const loadingDiv = document.createElement("div");
                        loadingDiv.className = "loading-indicator";
                        toolCallMessage.appendChild(loadingDiv);
                        currentLoadingIndicator = loadingDiv;
                        
                        // Show "Thinking" while the tool is being used
                        showThinking(true);
                        
                    } else if (parsedData.type === "tool-result") {
                        // Reset message state and stop the tool call animation
                        accumulatedMessageText = "";
                        lastBotMessageElement = null;
                        
                        const toolResultContent = `
                            <pre class="tool-result-box"><code>✅ <b>Tool Result:</b>\n${JSON.stringify(parsedData.message, null, 2)}</code></pre>
                        `;
                        appendMessage(toolResultContent, "tool-result");
                        
                        // Hide the tool-specific loading indicator, but keep "Thinking"
                        // This prepares for the final LLM response
                        if (currentLoadingIndicator) {
                            currentLoadingIndicator.remove();
                            currentLoadingIndicator = null;
                        }
                    } else {
                        // Handle unknown message types
                        accumulatedMessageText = "";
                        lastBotMessageElement = null;
                        appendMessage(JSON.stringify(parsedData, null, 2), "bot");
                        showThinking(false);
                    }
                } catch (e) {
                    console.error("⚠️ WS parse error:", e);
                    accumulatedMessageText = "";
                    lastBotMessageElement = null;
                    appendMessage(event.data, "bot");
                    showThinking(false);
                }
                
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            };
        } catch (e) {
            console.error("❌ Failed to create WebSocket:", e);
        }
    }

    connectWebSocket();

    function formatMessage(text) {
        if (typeof marked === 'undefined') {
            console.warn("⚠️ marked.js library not loaded. Falling back to plain text.");
            return text;
        }
        return marked.parse(text);
    }

    // --- Helpers ---
    function showThinking(isThinking) {
        thinkingDiv.style.display = isThinking ? "flex" : "none";
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    function appendMessage(text, type) {
        const message = document.createElement("div");
        message.className = "message " + type + "-message";
        
        if (type === "bot" || type === "error") {
            message.innerHTML = formatMessage(text);
        } else {
            message.innerHTML = text;
        }

        messagesDiv.insertBefore(message, thinkingDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        return message;
    }

    // --- Sending messages ---
    function sendMessage() {
        const text = messageInput.value.trim();
        const useMcp = mcpToggle.checked;
        const provider = llmProviderSelect.value;
        const model = ollamaModelSelect.value;
        const dbConnectionName = dbConnectionSelect.value;

        if (!text) {
            console.warn("⚠️ Empty message, skipping send.");
            return;
        }
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            console.error("❌ WebSocket not open, cannot send.");
            appendMessage("Connection to server lost. Please refresh or check server status.", "error");
            return;
        }

        appendMessage(text, "user");
        const payload = {
            text,
            use_mcp: useMcp,
            llm_provider: provider,
            llm_model: provider === "ollama" ? model : null,
            db_connection_name: dbConnectionName,
        };
        lastBotMessageElement = null;
        accumulatedMessageText = "";
        ws.send(JSON.stringify(payload));
        messageInput.value = "";
        messageInput.style.height = "auto";
        showThinking(true);
    }

    sendButton.addEventListener("click", sendMessage);
    messageInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
    messageInput.addEventListener("input", () => {
        messageInput.style.height = "auto";
        messageInput.style.height = messageInput.scrollHeight + "px";
    });
    llmProviderSelect.addEventListener("change", (e) => {
        if (e.target.value === "ollama") {
            ollamaModelSelect.classList.remove("hidden");
        } else {
            ollamaModelSelect.classList.add("hidden");
        }
    });
    
    dbConnectionSelect.addEventListener("change", (e) => {
        console.log(`🌐 Database connection changed to: ${e.target.value}`);
    });

    // --- Load UI config ---
    async function loadUiConfig() {
        console.log("📡 Fetching UI configuration...");
        // Resetting content to 'Loading...'
        serverNameP.textContent = "Connecting...";
        serverInfoContentDiv.innerHTML = '<p>Loading...</p>';
        toolsListUl.innerHTML = '<li>Loading...</li>';
        resourcesListUl.innerHTML = '<li>Loading...</li>';
        promptsListUl.innerHTML = '<li>Loading...</li>';
        dbConnectionSelect.innerHTML = '<option>Loading...</option>';
        ollamaModelSelect.innerHTML = '<option>Loading...</option>';

        try {
            const response = await fetch("/api/ui-config");
            if (!response.ok) throw new Error(`Server returned ${response.status}`);
            const config = await response.json();
            console.log("✅ Received UI config:", config);

            // Correctly set the content after receiving data
            serverNameP.textContent = config.server_name || "Unknown Server";
            serverInfoContentDiv.innerHTML = `<p><b>Version:</b> ${config.mcp_version}</p><p><b>Runtime:</b> ${config.mcp_runtime}</p>`;
            populateList(toolsListUl, config.tools, "No tools available.");
            populateList(resourcesListUl, config.resources, "No resources available.");
            populatePromptsList(promptsListUl, config.prompts, "No prompts available.");
            populateSelect(dbConnectionSelect, config.db_connections, "No DBs found");
            populateSelect(ollamaModelSelect, config.ollama_models, "No models found");

            ollamaModelSelect.classList.toggle("hidden", llmProviderSelect.value !== "ollama");
        } catch (err) {
            console.error("❌ Error loading UI config:", err);
            serverNameP.textContent = "Error";
            serverInfoContentDiv.innerHTML = `<p class="error">Failed to load server details.</p>`;
            toolsListUl.innerHTML = '<li>Error</li>';
            resourcesListUl.innerHTML = '<li>Error</li>';
            promptsListUl.innerHTML = '<li>Error</li>';
            dbConnectionSelect.innerHTML = '<option>Error</option>';
            ollamaModelSelect.innerHTML = '<option>Error</option>';
        }
    }

    function populateList(ul, items, emptyMessage) {
        ul.innerHTML = "";
        if (items && items.length > 0) {
            items.forEach(item => {
                const li = document.createElement("li");
                li.textContent = item.name;
                li.title = item.description || "No description";
                ul.appendChild(li);
            });
        } else {
            ul.innerHTML = `<li>${emptyMessage}</li>`;
        }
    }

    function populatePromptsList(ul, items, emptyMessage) {
        ul.innerHTML = "";
        if (items && items.length > 0) {
            items.forEach(item => {
                const li = document.createElement("li");
                li.classList.add("prompt-item");
                li.innerHTML = `
                    <div class="prompt-name">${item.name}</div>
                    <div class="prompt-description">${item.description || "No description."}</div>
                `;
                li.title = `Prompt: ${item.name}`;
                li.addEventListener("click", () => {
                    const messageText = `Use the '${item.name}' prompt.`;
                    messageInput.value = messageText;
                    sendMessage();
                });
                ul.appendChild(li);
            });
        } else {
            ul.innerHTML = `<li>${emptyMessage}</li>`;
        }
    }

    function populateSelect(select, items, emptyMessage) {
        select.innerHTML = "";
        if (items && items.length > 0) {
            const defaultOption = document.createElement("option");
            defaultOption.value = "";
            defaultOption.textContent = "Select a database...";
            select.appendChild(defaultOption);

            items.forEach(item => {
                const option = document.createElement("option");
                option.value = item;
                option.textContent = item;
                select.appendChild(option);
            });
        } else {
            select.innerHTML = `<option>${emptyMessage}</option>`;
        }
    }

    loadUiConfig();
});