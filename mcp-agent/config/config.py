"""Configuration settings loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

# LLM backend selection: "ollama" (default) or "openai"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

# Ollama LLM Configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))
OLLAMA_MAX_RETRIES = int(os.getenv("OLLAMA_MAX_RETRIES", "2"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# OpenAI LLM Configuration
# OPENAI_API_KEY is read by the OpenAI SDK from the environment.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
