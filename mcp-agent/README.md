# EMF Stateless MCP Agent

A powerful Python-based agent designed to interact with the EMF Stateless MCP Server. This agent leverages Large Language Models (LLMs) to orchestrate Model Context Protocol (MCP) tool calls, allowing you to manipulate EMF models using natural language.

## Features

- **LLM-Powered**: Uses LangChain and LangGraph to create a ReAct agent capable of reasoning and executing complex tasks.
- **Stateless Architecture**: Designed to work with the stateless EMF MCP server, managing sessions and state transitions effectively.
- **Flexible LLM Support**: Built-in support for local LLMs via **Ollama** and cloud models via **OpenAI**.
- **Interactive CLI**: A user-friendly command-line interface for chatting with the agent.
- **Metamodel Awareness**: Can upload and understand EMF Ecore metamodels to guide its actions.

## Prerequisites

Before running the agent, ensure you have the following components ready:

1.  **Java EMF Server**: The backend EMF Model Server must be running (typically on port 8095).
2.  **EMF MCP Server**: The Python MCP server script (`emf_mcp_stateless.py`) that acts as the bridge.
3.  **Python 3.10+**: Installed on your machine.

## Installation

1.  **Navigate to the agent directory**:
    ```bash
    cd mcp-agent
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

The agent is configured via environment variables, which can be set in a `.env` file in the `mcp-agent` directory.

### 1. Create a `.env` file
Copy the following template into a new `.env` file:

```env
# --- LLM Selection ---
# Options: llama3.2, llama3.1, mistral, etc.
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TEMPERATURE=0.1

# --- OpenAI (Optional) ---
# If you prefer OpenAI, set this and the agent can be adapted to use it.
# OPENAI_API_KEY=sk-...
```

### 2. Ensure Ollama is running (if using local LLMs)
Make sure you have [Ollama](https://ollama.com/) installed and running. Pull the model you intend to use:
```bash
ollama pull llama3.2
```

## Usage

The main entry point is `simple_emf_agent.py`. You need to point it to the MCP server script.

### Basic Command

```bash
python simple_emf_agent.py \
  --server /path/to/emf_mcp_stateless.py
```

### Full Options

```bash
python simple_emf_agent.py \
  --server /absolute/path/to/emf_mcp_stateless.py \
  --metamodel /absolute/path/to/your.ecore \
  --model llama3.2 \
  --temperature 0.1
```

| Argument | Description |
| :--- | :--- |
| `--server` | **Required**. Absolute path to the `emf_mcp_stateless.py` script. |
| `--metamodel` | Optional. Path to an `.ecore` file to upload immediately at startup. |
| `--model` | The LLM model name to use (default: `llama3.2`). |
| `--temperature` | Creativity of the model (0.0 to 1.0). Default is `0.1` for precision. |
| `--python` | Custom Python executable to launch the MCP server with. |

## Example Interaction

Once the agent is running, you can give it natural language commands:

```text
You> Start a session with the library.ecore metamodel
Agent> [Starts session, uploads metamodel, analyzes classes]
Agent> Session started. I see classes: Library, Book, Author.

You> Create a Library named "City Library"
Agent> [Calls create_object tool]
Agent> Created Library object with ID: 12345

You> Add a Book "The Great Gatsby" to the library
Agent> [Calls create_object for Book, then update_feature to link it]
Agent> Added "The Great Gatsby" to "City Library".
```

## Architecture

- **`stateless_agent.py`**: Contains the `EMFStatelessAgent` class, which defines the LangGraph workflow, manages the conversation state, and builds the MCP tools.
- **`mcp_client.py`**: Handles the low-level stdio connection to the MCP server using the `mcp` Python SDK.
- **`simple_emf_agent.py`**: The CLI wrapper that parses arguments and runs the interactive loop.
