"""LLM-powered agent tailored for the stateless EMF MCP server."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent

from mcp_client import MCPClient
from config import (
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MAX_RETRIES,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_MAX_RETRIES,
)
from prompts import SYSTEM_PROMPT_TEMPLATE
from tools import build_emf_tools
from utils import content_to_str, extract_classes_from_routes, extract_final_answer, format_invoke_result


class EMFStatelessAgent:
    """Interactive agent that orchestrates MCP tool calls for EMF metamodels."""

    def __init__(
        self,
        client: MCPClient,
        metamodel_path: Optional[str] = None,
        *,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        recursion_limit: int = 60,
    ) -> None:
        self._client = client
        self._metamodel_path = metamodel_path
        self._max_tokens = max_tokens
        self._recursion_limit = recursion_limit

        self._session = None
        self._session_id: Optional[str] = None
        self._routes: Dict[str, Any] = {}
        self._classes: List[str] = []

        self._llm = self._create_llm(model_name, temperature, max_tokens)
        self._agent = None
        self._system_message: Optional[SystemMessage] = None
        self._state: Dict[str, List[BaseMessage]] = {"messages": []}

    # --- Properties ---

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    @property
    def metamodel_path(self) -> str:
        return self._metamodel_path

    @property
    def classes(self) -> List[str]:
        return self._classes

    # --- Initialization ---

    async def initialize(self) -> None:
        """Connect to the MCP server, start a session, and prepare the agent graph."""
        self._session = await self._client.get_session()

        tools = build_emf_tools(
            session_getter=self._get_session,
            session_id_getter=lambda: self._session_id,
            classes_getter=lambda: self._classes,
            start_session_handler=self._start_session,
        )

        self._agent = create_react_agent(self._llm, tools)
        self._system_message = None
        self._state = {"messages": []}
        self._refresh_system_prompt()

        if self._metamodel_path:
            await self._start_session(self._metamodel_path)

    async def _get_session(self):
        """Get the current MCP session."""
        return self._session

    def _create_llm(
        self,
        model_name: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
    ):
        """Create and configure the LLM instance (Ollama or OpenAI)."""

        # Decide which backend to use.
        provider = (LLM_PROVIDER or "ollama").lower()

        # --- OpenAI backend ---
        if provider == "openai":
            effective_model = model_name or OPENAI_MODEL
            kwargs: Dict[str, Any] = {
                "model": effective_model,
                "temperature": (
                    temperature if temperature is not None else OPENAI_TEMPERATURE
                ),
            }

            if OPENAI_MAX_RETRIES:
                kwargs["max_retries"] = OPENAI_MAX_RETRIES

            # ChatOpenAI uses max_tokens instead of num_predict
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens

            return ChatOpenAI(**kwargs)

        # --- Ollama backend (default) ---
        effective_model = model_name or OLLAMA_MODEL
        kwargs = {
            "model": effective_model,
            "temperature": temperature if temperature is not None else OLLAMA_TEMPERATURE,
        }

        if OLLAMA_BASE_URL:
            kwargs["base_url"] = OLLAMA_BASE_URL

        if OLLAMA_MAX_RETRIES:
            kwargs["max_retries"] = OLLAMA_MAX_RETRIES

        if max_tokens is not None:
            kwargs["num_predict"] = max_tokens

        return ChatOllama(**kwargs)

    # --- Session Management ---

    async def _start_session(self, metamodel_path: str) -> str:
        """Start a new EMF session by uploading a metamodel."""
        if self._session is None:
            raise RuntimeError("No active MCP session. Did you call 'initialize'?")

        payload = {"metamodel_file_path": metamodel_path}
        # NOTE: This maps the agent-level ``start_session`` tool to the actual MCP
        # tool implemented by the EMF server, ``start_metamodel_session_stateless``.
        result = await self._session.call_tool(
            "start_metamodel_session_stateless", payload
        )
        response = format_invoke_result(result)

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
        self._classes = extract_classes_from_routes(self._routes)
        self._refresh_system_prompt()

        return response

    def _refresh_system_prompt(self) -> None:
        """Update the system prompt with current session context."""
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

    # --- Agent Execution ---

    async def run(self, user_message: str) -> Dict[str, Any]:
        """Execute the agent with a user message and return the response."""
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
        state_input = {"messages": messages + [HumanMessage(content=user_message)]}

        try:
            self._state = await self._agent.ainvoke(
                state_input,
                config={"recursion_limit": self._recursion_limit},
            )
        except GraphRecursionError:
            warning = (
                "Recursion limit reached before completing the task. "
                "Consider simplifying the request or increasing the recursion limit."
            )
            return {"answer": warning, "messages": []}

        messages = self._state.get("messages", [])
        new_messages = messages[previous_count:]
        answer = extract_final_answer(messages)

        return {"answer": answer, "messages": new_messages}

    # --- Static Utility (kept for backward compatibility) ---

    @staticmethod
    def content_to_str(content: Any) -> str:
        """Convert message content to string. Delegates to utils."""
        return content_to_str(content)
