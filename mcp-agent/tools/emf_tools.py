"""EMF MCP tool definitions extracted from the agent.

This module contains all the LangChain tools for interacting with the EMF MCP server.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Union

from langchain_core.tools import tool

from utils.serialization import format_invoke_result


def build_emf_tools(
    session_getter: Callable,
    session_id_getter: Callable[[], str | None],
    classes_getter: Callable[[], List[str]],
    start_session_handler: Callable[[str], Any],
) -> List[Any]:
    """Build the EMF MCP tools for the agent.
    
    Args:
        session_getter: Async callable that returns the MCP session.
        session_id_getter: Callable that returns the current session ID.
        classes_getter: Callable that returns the list of known classes.
        start_session_handler: Async callable to start a new session.
        
    Returns:
        List of LangChain tool functions.
    """
    
    async def _call_server_tool(
        tool_name: str,
        payload: Dict[str, Any],
        *,
        include_session_id: bool = True,
    ) -> str:
        """Internal helper to call an MCP server tool."""
        session = await session_getter()
        if session is None:
            raise RuntimeError("No active MCP session. Did you call 'initialize'?")

        args = dict(payload)
        if include_session_id:
            session_id = session_id_getter()
            if not session_id:
                return "No active EMF session. Call start_session with a metamodel path first."
            args.setdefault("session_id", session_id)

        result = await session.call_tool(tool_name, args)
        return format_invoke_result(result)

    tools = []

    # --- Session Management Tools ---
    
    @tool("start_session")
    async def start_session_tool(metamodel_path: str) -> str:
        """Start a new EMF session by uploading a metamodel file."""
        return await start_session_handler(metamodel_path)

    tools.append(start_session_tool)

    @tool("get_session_info")
    async def get_session_info_tool() -> str:
        """Display metadata about the active session."""
        return await _call_server_tool("get_session_info", {})

    tools.append(get_session_info_tool)

    # --- Object Management Tools ---

    @tool("create_object")
    async def create_object_tool(class_name: str) -> str:
        """Create a new instance of a metamodel class in the active session."""
        return await _call_server_tool("create_object", {"class_name": class_name})

    tools.append(create_object_tool)

    @tool("delete_object")
    async def delete_object_tool(class_name: str, object_id: Union[str, int]) -> str:
        """Delete an object instance from the current session."""
        object_id_str = str(object_id) if object_id else ""
        return await _call_server_tool(
            "delete_object",
            {"class_name": class_name, "object_id": object_id_str},
        )

    tools.append(delete_object_tool)

    # --- Feature Management Tools ---

    @tool("update_feature")
    async def update_feature_tool(
        class_name: str,
        object_id: Union[str, int],
        feature_name: str,
        value: Any,
    ) -> str:
        """Update an attribute or reference on an existing object.

        Args:
            class_name: The metamodel class name
            object_id: Object ID (numeric or string, will be converted)
            feature_name: The feature/attribute name to update
            value: The value to set (string, number, list, etc. - will be auto-serialized)
        """
        object_id_str = str(object_id) if object_id else ""
        value_str = json.dumps(value) if not isinstance(value, str) else value

        return await _call_server_tool(
            "update_feature",
            {
                "class_name": class_name,
                "object_id": object_id_str,
                "feature_name": feature_name,
                "value": value_str,
            },
        )

    tools.append(update_feature_tool)

    @tool("clear_feature")
    async def clear_feature_tool(
        class_name: str, object_id: Union[str, int], feature_name: str
    ) -> str:
        """Unset a feature on an existing object."""
        object_id_str = str(object_id) if object_id else ""
        return await _call_server_tool(
            "clear_feature",
            {
                "class_name": class_name,
                "object_id": object_id_str,
                "feature_name": feature_name,
            },
        )

    tools.append(clear_feature_tool)

    @tool("list_features")
    async def list_features_tool(class_name: str) -> str:
        """List the structural features available on a class."""
        return await _call_server_tool("list_features", {"class_name": class_name})

    tools.append(list_features_tool)

    # --- Inspection Tools ---

    @tool("inspect_instance")
    async def inspect_instance_tool(class_name: str, object_id: Union[str, int]) -> str:
        """Inspect the current feature values of an object instance.

        Args:
            class_name: The metamodel class name
            object_id: The object ID (numeric or string, will be auto-converted)
        """
        object_id_str = str(object_id) if object_id else ""
        return await _call_server_tool(
            "inspect_instance",
            {"class_name": class_name, "object_id": object_id_str},
        )

    tools.append(inspect_instance_tool)

    @tool("list_session_objects")
    async def list_session_objects_tool() -> str:
        """List locally tracked objects created in this client session."""
        return await _call_server_tool("list_session_objects", {})

    tools.append(list_session_objects_tool)

    # --- Utility Tools ---

    @tool("debug_tools")
    async def debug_tools_tool() -> str:
        """List registered MCP tools on the server (debugging aid)."""
        return await _call_server_tool("debug_tools", {}, include_session_id=False)

    tools.append(debug_tools_tool)

    @tool("list_known_classes")
    def list_known_classes_tool() -> str:
        """Show the classes discovered from the metamodel routes without calling the server."""
        classes = classes_getter()
        if not classes:
            return "No classes discovered from the OpenAPI specification."
        return "Available classes: " + ", ".join(classes)

    tools.append(list_known_classes_tool)

    return tools
