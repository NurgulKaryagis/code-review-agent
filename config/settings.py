import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT")

_missing = [name for name, val in [("GITHUB_TOKEN", GITHUB_TOKEN), ("OPENAI_API_KEY", OPENAI_API_KEY)] if not val]
if _missing:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(_missing)}. "
        "Please set them in your .env file or environment."
    )