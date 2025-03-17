# Agentic LLM Chatbot API

## Overview

This repository provides an API for an agentic LLM (Large Language Model) chatbot. It leverages the `autogen` library to create a team of agents that can collaborate to fulfill user requests. The API supports chat functionality via WebSockets, allowing for real-time interaction, and also includes endpoints for managing chat history.

## Features

* **Agentic Chat:** The chatbot uses a team of agents to process user requests, enabling more complex and collaborative responses.
* **WebSocket Support:** Real-time chat functionality is provided through WebSocket connections.
* **Chat History Management:** The API includes endpoints for retrieving and clearing chat history.
* **Web Search Integration:** Agents can use web search tools to retrieve up-to-date information.
* **Configurable Agents:** The behavior and capabilities of agents can be customized through configuration files.
* **State Management:** The state of the agent team is saved and loaded to preserve context across sessions.

## Technologies Used

* `Python 3.9+`
* `FastAPI`
* `autogen`
* `aiohttp`
* `WebSockets`
* `Python-dotenv`
* `PyYAML`
* `aiofiles`

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**

    * Create a `.env` file in the root directory.
    * Add the following variables to the `.env` file:

        ```
        MODEL_CONFIG_PATH=app/config/model_config.yaml  # Path to your model config file
        HISTORY_PATH=app/local/team_history.json      # Path to the chat history file
        STATE_PATH=app/local/team_state.json        # Path to the team state file
        ```

    * Ensure that you have a `model_config.yaml` file that contains the configuration for your LLM. This configuration should include necessary API keys and model settings. Example:

        ```yaml
        models:
          gpt-4o-mini:
            config:
              model: "gpt-4o-mini"
              api_key: "YOUR_API_KEY"
          o3-mini:
            config:
              model: "o3-mini"
              api_key: "YOUR_API_KEY"
        ```

5.  **Run the application:**

    ```bash
    python app/main.py
    ```

    The API will be accessible at `http://0.0.0.0:8080`.

## API Endpoints

### Health Check

* `GET /health`

    * Checks the health of the API.
    * Returns: `{"status": "ok"}`

### Root

* `GET /`

    * Serves the chat interface HTML file (`app/static/index.html`).

### Chat

* `WebSocket /ws/chat`

    * Handles real-time chat communication.
    * **Client sends:** JSON messages with the following structure:

        ```json
        {
          "content": "User message content",
          "source": "user"
        }
        ```

    * **Server sends:** JSON messages with various structures, including:

        * `TextMessage`: Chat messages from agents.
        * `UserInputRequestedEvent`: Requests for user input.
        * `ToolCallRequestEvent`: Requests for tool calls.
        * `ToolCallExecutionEvent`: Results of tool calls.
        * `TaskResult`: Result of a task.
        * `WebPageContent`: Content from web pages.
        * `error`: Error messages.

### History

* `GET /api/history`

    * Retrieves the chat history.
    * Returns: A JSON array of chat messages.

* `GET /api/history/clear`

    * Clears the chat history and agent state.
    * Returns: `None`

## Project Structure

```
├── app
│   ├── init.py
│   ├── api
│   │   ├── init.py
│   │   ├── chat.py      # WebSocket chat handler
│   │   └── history.py   # Chat history management
│   ├── core
│   │   ├── init.py
│   │   ├── agents
│   │   │   ├── init.py
│   │   │   ├── _intent_agent.py
│   │   │   ├── assistant_agent.py
│   │   │   ├── base_agent.py
│   │   │   ├── intent_agent.py
│   │   │   ├── orchestrator.py  # Agent team orchestration
│   │   │   ├── prompts.py     # Agent prompts
│   │   │   └── user_agent.py
│   │   └── tools
│   │   │   ├── init.py
│   │   │   └── web_search.py  # Web search tool
│   ├── logger.py    # Logging setup
│   ├── main.py      # FastAPI application entry point
│   └── static
│       └── index.html # Chat interface HTML
├── app/config
│   └── model_config.yaml  # Model configuration
├── app/local
│   ├── team_history.json  # Chat history file
│   └── team_state.json    # Agent team state file
├── .env           # Environment variables
├── README.md      # Project README
└── requirements.txt # Python dependencies
```

## Agent Configuration

The behavior of the agents is configured in the `app/core/agents` directory.

* `orchestrator.py`: This file defines the agent team and how they interact. It uses a `SelectorGroupChat` to route messages between agents based on a selection function.
* `assistant_agent.py`: Defines the `KijangAgent`, an assistant agent that can use tools like web search.
* `intent_agent.py`: Defines the `IntentAgent`, which is responsible for determining the user's intent.
* `prompts.py`: Contains the prompts used to guide the behavior of the agents.

## Running the Application

1.  Ensure that you have completed the installation steps.
2.  Run the application using the following command:

    ```bash
    python app/main.py
    ```

3.  The API will be available at `http://0.0.0.0:8080`. You can access the chat interface by opening this URL in your web browser.

## Using the Chat Interface

The chat interface is located at the root of the API (`http://0.0.0.0:8080`). It provides a simple way to interact with the chatbot.

* **Send Messages:** Type your message in the input field and press Enter or click the send button.
* **View Responses:** The chatbot's responses will appear in the chat window.
* **Clear History:** Click the "Clear" button to clear the chat history.
* **Dark Mode:** Toggle dark mode using the moon icon in the sidebar.

## Extending the Functionality

You can extend the functionality of the chatbot by:

* **Adding new agents:** Create new agent classes in the `app/core/agents` directory and add them to the team in `orchestrator.py`.
* **Creating new tools:** Implement new tools in the `app/core/tools` directory and make them available to the agents.
* **Customizing prompts:** Modify the prompts in `app/core/agents/prompts.py` to change the behavior of the agents.
* **Integrating with other systems:** Use the API endpoints to integrate the chatbot with other applications.


_README generated by gitingest and Gemini_
