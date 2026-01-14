"""Serialization and parsing utilities for MCP responses."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from langchain_core.messages import AIMessage, BaseMessage


def format_invoke_result(result: Any) -> str:
    """Format an MCP tool invocation result into a string.
    
    Args:
        result: The raw result from an MCP tool call.
        
    Returns:
        A formatted string representation of the result.
    """
    content = getattr(result, "content", None)
    if not content:
        return "No content returned by MCP tool."

    parts: List[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
            continue

        data = getattr(block, "data", None)
        if data:
            try:
                parts.append(json.dumps(data, indent=2))
            except (TypeError, ValueError):
                parts.append(str(data))
            continue

        parts.append(str(block))

    return "\n".join(parts)


def content_to_str(content: Any) -> str:
    """Convert message content to a string representation.
    
    Args:
        content: Message content which can be a string, list, dict, or other types.
        
    Returns:
        A string representation of the content.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, Iterable) and not isinstance(content, (bytes, bytearray)):
        fragments = []
        for element in content:
            if isinstance(element, dict):
                if "text" in element:
                    fragments.append(str(element["text"]))
                else:
                    fragments.append(json.dumps(element, indent=2))
            else:
                fragments.append(str(element))
        return "\n".join(fragments)
    return json.dumps(content) if isinstance(content, (dict, list)) else str(content)


def extract_final_answer(messages: List[BaseMessage]) -> str:
    """Extract the final textual answer from a list of messages.
    
    Args:
        messages: List of LangChain messages from the agent.
        
    Returns:
        The final AI response text, or empty string if none found.
    """
    for message in reversed(messages):
        if isinstance(message, AIMessage) and not message.tool_calls:
            return content_to_str(message.content)
    return ""


def extract_classes_from_routes(routes: Dict[str, Any]) -> List[str]:
    """Extract class names from OpenAPI route definitions.
    
    Args:
        routes: OpenAPI specification dict containing paths.
        
    Returns:
        Sorted list of unique class names found in the routes.
    """
    if not isinstance(routes, dict):
        return []

    classes = set()
    paths = routes.get("paths", {})
    for path in paths:
        parts = path.split("/")
        if len(parts) >= 4 and parts[1] == "metamodel" and parts[2] == "{sessionId}":
            class_name = parts[3]
            if "{" not in class_name:
                classes.add(class_name)
    return sorted(classes)
