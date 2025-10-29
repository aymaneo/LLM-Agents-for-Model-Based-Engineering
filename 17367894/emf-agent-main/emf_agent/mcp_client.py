"""Utilities for connecting to MCP servers via stdio transport."""

from __future__ import annotations

import asyncio
import sys
from contextlib import AsyncExitStack
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """Thin wrapper around the MCP stdio client with lifecycle helpers."""

    def __init__(self) -> None:
        self._session: Optional[ClientSession] = None
        self._exit_stack = AsyncExitStack()
        self._stdio_transport = None

    async def connect(
        self,
        server_script_path: str,
        *,
        python_executable: Optional[str] = None,
        env: Optional[dict[str, str]] = None,
    ) -> ClientSession:
        """Connect to the MCP server defined by ``server_script_path``.

        Parameters
        ----------
        server_script_path:
            Absolute path to the MCP server script (Python or Node).
        python_executable:
            Optional path to the Python executable to use. Defaults to ``sys.executable``.
        env:
            Optional environment variables to expose to the child process.
        """

        command = python_executable or sys.executable
        params = StdioServerParameters(command=command, args=[server_script_path], env=env)

        stdio_transport = await self._exit_stack.enter_async_context(stdio_client(params))
        self._stdio_transport = stdio_transport
        stdin, stdout_writer = stdio_transport
        self._session = await self._exit_stack.enter_async_context(ClientSession(stdin, stdout_writer))
        await self._session.initialize()
        return self._session

    async def get_session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("MCP client is not connected. Call 'connect' first.")
        return self._session

    async def cleanup(self) -> None:
        """Close transports and release resources."""

        try:
            await self._exit_stack.aclose()
        except RuntimeError as exc:
            # Raised when cleanup happens before connection completes. Log silently.
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None:
                loop.call_exception_handler(
                    {
                        "message": "Error while closing MCP client resources",
                        "exception": exc,
                    }
                )

        self._session = None
        self._stdio_transport = None

