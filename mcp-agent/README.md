# EMF Stateless MCP Agent

A Python-based agent that uses LLMs to manipulate Eclipse Modeling Framework (EMF) models through the Model Context Protocol (MCP).

## Features

- **LLM-Powered**: Uses LangChain and LangGraph to create a ReAct agent for complex reasoning
- **Stateless Architecture**: Works with the stateless EMF MCP server, managing sessions effectively
- **Local LLM Support**: Built-in support for local LLMs via Ollama
- **Interactive CLI**: Command-line interface for natural language model manipulation

## Project Structure

```
mcp-agent/
├── cli.py                 # Main CLI entry point
├── stateless_agent.py     # EMFStatelessAgent class (agent orchestration)
├── mcp_client.py          # MCP server connection handling
├── config/                # Configuration management
│   └── config.py          # Environment variable loading
├── prompts/               # LLM prompt templates
│   └── system_prompt.py   # System prompt for EMF operations
├── tools/                 # MCP tool definitions
│   └── emf_tools.py       # All EMF manipulation tools
└── utils/                 # Utility functions
    └── serialization.py   # Parsing and formatting helpers
```

## Prerequisites

1. **Java EMF Server**: Running on port 8095
2. **EMF MCP Server**: The `emf_mcp_stateless.py` bridge script
3. **Python 3.10+**
4. **Ollama** (if using local LLMs)

## Installation

```bash
# Navigate to the agent directory
cd mcp-agent

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key settings:
- `OLLAMA_MODEL`: Model name (default: `llama3.2`)
- `OLLAMA_BASE_URL`: Ollama server URL (default: `http://localhost:11434`)
- `OLLAMA_TEMPERATURE`: Creativity level 0.0-1.0 (default: `0.1`)

## Usage

### Basic Command

```bash
python cli.py --server /path/to/emf_mcp_stateless.py
```

### With Metamodel

```bash
python cli.py \
  --server /path/to/emf_mcp_stateless.py \
  --metamodel /path/to/library.ecore \
  --model llama3.2
```

### Options

| Argument | Description |
|----------|-------------|
| `--server` | **Required**. Path to the MCP server script |
| `--metamodel` | Optional `.ecore` file to load at startup |
| `--model` | LLM model name (default: `llama3.2`) |
| `--temperature` | Sampling temperature (default: `0.1`) |
| `--python` | Custom Python executable for MCP server |

## Example Interaction

```text
You> Create a Library named "City Library"
Agent> [Calls create_object tool]
Agent> Created Library object with ID: 12345

You> Add an author "Jules Verne" 
Agent> [Calls create_object, update_feature]
Agent> Created Author "Jules Verne" with ID: 67890
```

## Architecture

```
User → CLI → EMFStatelessAgent → MCPClient → MCP Server → Java EMF Server
             ↓
         LangGraph (ReAct Loop)
             ↓
         EMF Tools (11 tools)
```
