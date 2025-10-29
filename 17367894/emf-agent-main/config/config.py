import os
from dotenv import load_dotenv

# Loads .env variables
load_dotenv() 
BASE_URL = os.getenv("BASE_URL")
API_USER = os.getenv("API_USER")
API_PASSWORD = os.getenv("API_PASSWORD")


# Load environment variables from .env file if it exists
load_dotenv()

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate API key
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it before running the application.") 

# Ollama's Configuration
OLLAMA_MODEL = "llama3.2"
OLLAMA_TEMPERATURE = 0.1
OLLAMA_MAX_RETRIES = 2
