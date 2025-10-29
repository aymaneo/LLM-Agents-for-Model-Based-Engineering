"""Interactive CLI for the EMF stateless MCP agent."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

from langchain_core.messages import AIMessage, ToolMessage

from emf_agent import EMFStatelessAgent, MCPClient
from config.config import OLLAMA_MODEL, OLLAMA_TEMPERATURE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the EMF stateless LLM agent over MCP.")
    parser.add_argument(
        "--metamodel",
        help="Optional path to a .ecore metamodel to upload at startup. If omitted, start a session by calling the start_session tool in chat.",
    )
    parser.add_argument(
        "--server",
        required=True,
        help="Absolute path to the MCP server script (e.g. emf_mcp_stateless.py).",
    )
    parser.add_argument(
        "--model",
        default=OLLAMA_MODEL,
        help=f"Chat model identifier to use for reasoning (default: {OLLAMA_MODEL}).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=OLLAMA_TEMPERATURE,
        help=f"Sampling temperature for the chat model (default: {OLLAMA_TEMPERATURE}).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Optional max tokens for each model response.",
    )
    parser.add_argument(
        "--recursion-limit",
        type=int,
        default=60,
        help="Maximum LangGraph recursion depth for a single request (default: 60).",
    )
    parser.add_argument(
        "--python",
        dest="python_exec",
        default=None,
        help="Custom Python executable to launch the MCP server with.",
    )
    return parser.parse_args()


async def interactive_loop(agent: EMFStatelessAgent) -> None:
    print("\nType 'exit' or 'quit' to end the conversation. Press Ctrl+C to abort.\n")
    while True:
        try:
            user_input = await asyncio.to_thread(input, "You> ")
        except EOFError:
            print("\nEOF received. Exiting.")
            break

        if not user_input:
            continue

        normalized = user_input.strip().lower()
        if normalized in {"exit", "quit"}:
            print("Goodbye!")
            break

        result = await agent.run(user_input)

        for message in result["messages"]:
            if isinstance(message, ToolMessage):
                content = EMFStatelessAgent.content_to_str(message.content)
                print(f"[tool:{message.name}] {content}")
            elif isinstance(message, AIMessage) and message.tool_calls:
                print(f"[call] {message.tool_calls}")

        answer = result.get("answer", "").strip()
        if answer:
            print(f"Agent> {answer}")
        else:
            print("Agent> (no textual response)")


async def run() -> int:
    args = parse_args()

    metamodel_path: Optional[Path] = None
    if args.metamodel:
        metamodel_path = Path(args.metamodel).expanduser().resolve()
        if not metamodel_path.exists():
            print(f"Metamodel file not found: {metamodel_path}", file=sys.stderr)
            return 1

    server_path = Path(args.server).expanduser().resolve()
    if not server_path.exists():
        print(f"MCP server script not found: {server_path}", file=sys.stderr)
        return 1

    client = MCPClient()
    agent: Optional[EMFStatelessAgent] = None

    try:
        await client.connect(str(server_path), python_executable=args.python_exec)
        agent = EMFStatelessAgent(
            client,
            str(metamodel_path) if metamodel_path else None,
            model_name=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            recursion_limit=args.recursion_limit,
        )
        await agent.initialize()

        session_id = agent.session_id or "<unknown>"
        classes = ", ".join(agent.classes) if agent.classes else "(none discovered)"

        print("Connected to EMF stateless MCP server")
        if agent.session_id:
            print(f"Session ID: {session_id}")
        if metamodel_path:
            print(f"Metamodel: {metamodel_path}")
        print(f"Available classes: {classes}")

        await interactive_loop(agent)
        return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user. Cleaning up...")
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        await client.cleanup()


def main() -> None:
    exit_code = asyncio.run(run())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()