import os
from dotenv import load_dotenv


# Loads .env variables
load_dotenv() 
BASE_URL = os.getenv("BASE_URL")
API_USER = os.getenv("API_USER")
API_PASSWORD = os.getenv("API_PASSWORD")


# Ollama's Configuration
OLLAMA_MODEL = "llama3.2"
OLLAMA_TEMPERATURE = 0.1
OLLAMA_MAX_RETRIES = 2
