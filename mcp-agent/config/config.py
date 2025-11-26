import os
from dotenv import load_dotenv


load_dotenv()

BASE_URL = os.getenv("BASE_URL")
API_USER = os.getenv("API_USER")
API_PASSWORD = os.getenv("API_PASSWORD")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))
OLLAMA_MAX_RETRIES = int(os.getenv("OLLAMA_MAX_RETRIES", "2"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", os.getenv("BASE_URL", "http://localhost:11434"))
