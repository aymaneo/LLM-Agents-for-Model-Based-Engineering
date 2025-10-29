# EMF MCP Server

A dynamic MCP (Model Context Protocol) server that creates tools on-the-fly for Eclipse Modeling Framework (EMF) metamodels.

## Overview

The **EMF MCP Server** acts as a bridge between MCP clients and an EMF server, automatically generating tools based on metamodel specifications. Upload an `.ecore` file and get instant access to create, update, and manage model objects.

---

## Quick Start

### Prerequisites

- Python 3.8+  
- EMF Server running on `localhost:8080`  
- Required packages: `mcp`, `requests`, `fastmcp`

### Installation

```bash
pip install mcp requests fastmcp
```

### Running the Server

```bash
python emf_mcp_server.py
```

---

## Usage Example

### 1. Start a Session

```python
# Upload your metamodel file
start_metamodel_session("Family.ecore")
```

Returns:

```json
{
  "sessionId": "7fdeb0c7-90d9-4da0-aab1-ec647e74343d",
  "availableClasses": ["Family", "Member"],
  "message": "Session started successfully. Created dynamic tools for classes: Family, Member"
}
```

---

### 2. Create Objects

```python
# Dynamically created tools based on your metamodel
create_family_7fdeb0c7()
create_member_7fdeb0c7()
```

Returns:

```
Family object created successfully!  
ID: 1779607988 (type: int)
```

---

### 3. Update Features

```python
# Update object properties
update_member_firstName_7fdeb0c7("867423344", "John")
update_family_father_7fdeb0c7("1779607988", "867423344")
```

---

### 4. List Objects

```python
# View all created objects
list_session_objects("7fdeb0c7-90d9-4da0-aab1-ec647e74343d")
```

Returns:

```
Session 7fdeb0c7-90d9-4da0-aab1-ec647e74343d objects:

Family (1 objects):
  ID 1779607988 (int)

Member (1 objects):
  ID 867423344 (int)

Total objects: 2
```

---

## LLM Agent CLI

The repository now ships with an interactive CLI that mirrors the agentic setup from
`ATL-LLM-agent` but targets the stateless MCP server defined in `emf_mcp_stateless.py`.

### Prerequisites

- All requirements from `requirements.txt` (including `langchain-openai`).
- An `OPENAI_API_KEY` environment variable for the chat model.

### Launching the Agent

```bash
python simple_emf_agent.py --server /absolute/path/to/emf_mcp_stateless.py
```

Optionally provide `--metamodel /path/to/file.ecore` to upload a metamodel immediately. If you omit it, start a session from the chat by calling the `start_session` tool and pass the absolute path to the `.ecore` file.
python simple_emf_agent.py /Users/aymane/Documents/AI/LLM-Agents-for-Model-Based-Engineering/Paper Artifacts SAM 2025/atl_zoo-master/Families2Persons/Families.ecore \
  --server /Users/aymane/Documents/AI/LLM-Agents-for-Model-Based-Engineering/17367894/emf-agent-main/emf_agent/emf_mcp_stateless.py

Optional flags:

- `--model`: Chat model identifier (default: `gpt-4o-mini`).
- `--temperature`: Sampling temperature (default: `0.1`).
- `--max-tokens`: Limit the length of each model response.
- `--python`: Provide a custom Python executable for running the MCP server process.

When the agent starts it will:

1. Launch or connect to the stateless MCP server.
2. If a metamodel path is provided (via `--metamodel` or the `start_session` tool), upload it and extract available classes.
3. Enter an interactive loop where natural-language instructions are translated into MCP tool
   calls (`start_session`, `create_object`, `update_feature`, `list_session_objects`, etc.).

Type `exit` or `quit` to end the session.

---

## API Reference

### Core Tools

```
Tool                           Description
-----------------------------  -----------------------------------------------
start_metamodel_session(path)  Initialize session with metamodel file
get_session_info(session_id)   Get session details and available classes
list_session_objects(session_id) List all objects in a session
```

---

### Dynamic Tools

```
Pattern                                 Description                Example
--------------------------------------  ------------------------  ----------------------------------------
create_{class}_{session}                Create new object          create_family_7fdeb0c7()
update_{class}_{feature}_{session}      Update object feature      update_member_firstName_7fdeb0c7()
delete_{class}_{session}                Delete object              delete_family_7fdeb0c7()
clear_{class}_{feature}_{session}       Clear feature value        clear_member_firstName_7fdeb0c7()
```

---

## Architecture

### Data Flow

```
MCP Client → EMF MCP Server → EMF Server (localhost:8080)
     ↑              ↓
   Tools &      OpenAPI Spec
  Results       & Responses
```

---

### Session Management

```python
# Global state
active_sessions = {
    "session_id": {
        "openapi_spec": {...},
        "metamodel_file": "/path/to/file.ecore"
    }
}

session_objects = {
    "session_id": {
        "ClassName": [object_id1, object_id2, ...]
    }
}
```

