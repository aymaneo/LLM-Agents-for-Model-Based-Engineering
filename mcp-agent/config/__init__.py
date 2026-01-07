"""Configuration module for the EMF MCP Agent."""

from .config import (
    OLLAMA_BASE_URL,
    OLLAMA_MAX_RETRIES,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
)

__all__ = [
    "OLLAMA_BASE_URL",
    "OLLAMA_MAX_RETRIES",
    "OLLAMA_MODEL",
    "OLLAMA_TEMPERATURE",
]
