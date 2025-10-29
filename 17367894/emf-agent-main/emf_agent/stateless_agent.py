"""LLM-powered agent tailored for the stateless EMF MCP server."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from .mcp_client import MCPClient
from .prompts.system_prompt import SYSTEM_PROMPT_TEMPLATE
from config.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MAX_RETRIES,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
)


class EMFStatelessAgent:
    """Interactive agent that orchestrates MCP tool calls for EMF metamodels."""

    def __init__(
        self,
        client: MCPClient,
        metamodel_path: str,
        *,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        self._client = client
        self._metamodel_path = metamodel_path
        self._max_tokens = max_tokens

        self._session = None
        self._session_id: Optional[str] = None
        self._routes: Dict[str, Any] = {}
        self._classes: List[str] = []

        self._llm = self._create_llm(model_name, temperature, max_tokens)

        self._agent = None
        self._system_message: Optional[SystemMessage] = None
        self._state: Dict[str, List[BaseMessage]] = {"messages": []}

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    @property
    def metamodel_path(self) -> str:
        return self._metamodel_path

    @property
    def classes(self) -> List[str]:
        return self._classes

    async def initialize(self) -> None:
        """Connect to the MCP server, start a session, and prepare the agent graph."""

        self._session = await self._client.get_session()

        tools = self._build_tools()
        self._agent = create_react_agent(
            self._llm,
            tools,
        )
        self._system_message = None
        self._state = {"messages": []}

        self._refresh_system_prompt()

        if self._metamodel_path:
            await self._start_session(self._metamodel_path)

    def _create_llm(
        self,
        model_name: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> ChatOllama:
        kwargs: Dict[str, Any] = {
            "model": model_name or OLLAMA_MODEL,
            "temperature": temperature if temperature is not None else OLLAMA_TEMPERATURE,
        }

        if OLLAMA_BASE_URL:
            kwargs["base_url"] = OLLAMA_BASE_URL

        if OLLAMA_MAX_RETRIES:
            kwargs["max_retries"] = OLLAMA_MAX_RETRIES

        if max_tokens is not None:
            kwargs["num_predict"] = max_tokens

        return ChatOllama(**kwargs)

    async def _start_session(self, metamodel_path: str) -> str:
        if self._session is None:
            raise RuntimeError("No active MCP session. Did you call 'initialize'?")

        payload = {"metamodel_file_path": metamodel_path}
        result = await self._session.call_tool("start_metamodel_session_stateless", payload)
        response = self.format_invoke_result(result)

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            return "Failed to parse session response. Server returned: " + response

        session_id = data.get("sessionId")
        if not session_id:
            return "Server did not return a sessionId. Response: " + response

        self._metamodel_path = metamodel_path
        self._session_id = session_id
        self._routes = data.get("routes", {})
        self._classes = self._extract_classes_from_routes(self._routes)

        self._refresh_system_prompt()

        return response

    def _refresh_system_prompt(self) -> None:
        content = SYSTEM_PROMPT_TEMPLATE.format(
            session_id=self._session_id or "<none>",
            metamodel_path=self._metamodel_path or "<not started>",
            class_list=", ".join(self._classes) if self._classes else "(none discovered)",
        )

        self._system_message = SystemMessage(content=content)

        messages = self._state.get("messages", [])
        if messages and isinstance(messages[0], SystemMessage):
            messages[0] = self._system_message
            self._state["messages"] = messages
        else:
            self._state["messages"] = [self._system_message] + messages

    def _build_tools(self) -> List[Any]:
        tools = []

        @tool("start_session")
        async def start_session_tool(metamodel_path: str) -> str:
            """Start a new EMF session by uploading a metamodel file."""
            return await self._start_session(metamodel_path)

        tools.append(start_session_tool)

        @tool("create_object")
        async def create_object_tool(class_name: str) -> str:
            """Create a new instance of a metamodel class in the active session."""
            return await self._call_server_tool("create_object", {"class_name": class_name})

        tools.append(create_object_tool)

        @tool("update_feature")
        async def update_feature_tool(
            class_name: str,
            object_id: str,
            feature_name: str,
            value: str,
        ) -> str:
            """Update an attribute or reference on an existing object."""
            return await self._call_server_tool(
                "update_feature",
                {
                    "class_name": class_name,
                    "object_id": object_id,
                    "feature_name": feature_name,
                    "value": value,
                },
            )

        tools.append(update_feature_tool)

        @tool("clear_feature")
        async def clear_feature_tool(class_name: str, object_id: str, feature_name: str) -> str:
            """Unset a feature on an existing object."""
            return await self._call_server_tool(
                "clear_feature",
                {
                    "class_name": class_name,
                    "object_id": object_id,
                    "feature_name": feature_name,
                },
            )

        tools.append(clear_feature_tool)

        @tool("delete_object")
        async def delete_object_tool(class_name: str, object_id: str) -> str:
            """Delete an object instance from the current session."""
            return await self._call_server_tool(
                "delete_object",
                {
                    "class_name": class_name,
                    "object_id": object_id,
                },
            )

        tools.append(delete_object_tool)

        @tool("list_features")
        async def list_features_tool(class_name: str) -> str:
            """List the structural features available on a class."""
            return await self._call_server_tool("list_features", {"class_name": class_name})

        tools.append(list_features_tool)

        @tool("inspect_instance")
        async def inspect_instance_tool(class_name: str, object_id: str) -> str:
            """Inspect the current feature values of an object instance."""
            return await self._call_server_tool(
                "inspect_instance",
                {
                    "class_name": class_name,
                    "object_id": object_id,
                },
            )

        tools.append(inspect_instance_tool)

        @tool("list_session_objects")
        async def list_session_objects_tool() -> str:
            """List locally tracked objects created in this client session."""
            return await self._call_server_tool("list_session_objects", {})

        tools.append(list_session_objects_tool)

        @tool("get_session_info")
        async def get_session_info_tool() -> str:
            """Display metadata about the active session."""
            return await self._call_server_tool("get_session_info", {})

        tools.append(get_session_info_tool)

        @tool("debug_tools")
        async def debug_tools_tool() -> str:
            """List registered MCP tools on the server (debugging aid)."""
            return await self._call_server_tool("debug_tools", {}, include_session_id=False)

        tools.append(debug_tools_tool)

        @tool("list_known_classes")
        def list_known_classes_tool() -> str:
            """Show the classes discovered from the metamodel routes without calling the server."""
            if not self._classes:
                return "No classes discovered from the OpenAPI specification."
            return "Available classes: " + ", ".join(self._classes)

        tools.append(list_known_classes_tool)

        return tools

    async def run(self, user_message: str) -> Dict[str, Any]:
        if self._agent is None:
            raise RuntimeError("Agent not initialized. Call 'initialize' first.")

        messages = list(self._state.get("messages", []))
        if not messages and self._system_message is not None:
            messages.append(self._system_message)
        elif (
            self._system_message is not None
            and messages
            and not isinstance(messages[0], SystemMessage)
        ):
            messages.insert(0, self._system_message)

        previous_count = len(messages)
        state_input = {
            "messages": messages + [HumanMessage(content=user_message)]
        }
        self._state = await self._agent.ainvoke(state_input)

        messages = self._state.get("messages", [])
        new_messages = messages[previous_count:]
        answer = self._extract_final_answer(messages)

        return {"answer": answer, "messages": new_messages}

    async def _call_server_tool(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        *,
        include_session_id: bool = True,
    ) -> str:
        if self._session is None:
            raise RuntimeError("No active MCP session. Did you call 'initialize'?")

        args = dict(payload)
        if include_session_id:
            if not self._session_id:
                return "No active EMF session. Call start_session with a metamodel path first."
            args.setdefault("session_id", self._session_id)

        result = await self._session.call_tool(tool_name, args)
        return self.format_invoke_result(result)

    @staticmethod
    def format_invoke_result(result: Any) -> str:
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

    @staticmethod
    def content_to_str(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, Iterable) and not isinstance(content, (bytes, bytearray)):
            fragments = []
            for element in content:  # type: ignore[arg-type]
                if isinstance(element, dict):
                    if "text" in element:
                        fragments.append(str(element["text"]))
                    else:
                        fragments.append(json.dumps(element, indent=2))
                else:
                    fragments.append(str(element))
            return "\n".join(fragments)
        return json.dumps(content) if isinstance(content, (dict, list)) else str(content)

    @staticmethod
    def _extract_final_answer(messages: List[BaseMessage]) -> str:
        for message in reversed(messages):
            if isinstance(message, AIMessage) and not message.tool_calls:
                return EMFStatelessAgent.content_to_str(message.content)
        return ""

    @staticmethod
    def _extract_classes_from_routes(routes: Dict[str, Any]) -> List[str]:
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

