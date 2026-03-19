import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# CONSTANTS

## OPENROUTER CONFIG

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if OPENROUTER_API_KEY is None:
    raise ValueError("OPENROUTER_API_KEY is not set in the environment variables.")
OPENROUTER_DEFAULT_MODEL = os.getenv("OPENROUTER_DEFAULT_MODEL", "openai/gpt-5.4-nano")

## LLM CONFIG

MAX_TOKENS = int(os.getenv("OPENROUTER_MAX_TOKENS", "4096"))
TEMPERATURE = float(os.getenv("OPENROUTER_TEMPERATURE", "0.7"))

## PATH CONFIG

SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "data/sessions"))
AUDIT_DIR = Path(os.getenv("AUDIT_DIR", "data/audit"))
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", "workspace"))
