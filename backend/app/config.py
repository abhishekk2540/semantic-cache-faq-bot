import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
DB_PATH = BASE_DIR / "cache_app.db"

# --- auth ---
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-secret-change-me-before-deploying-0123456789")
JWT_HOURS = 24

# --- cache behaviour ---
DEFAULT_THRESHOLD = float(os.getenv("DEFAULT_THRESHOLD", "0.85"))
DEFAULT_TTL_DAYS = float(os.getenv("DEFAULT_TTL_DAYS", "7"))

# --- LLM ---
# "mock"      -> fake LLM with a delay (works offline, good for demos)
# "anthropic" -> real Claude call (needs ANTHROPIC_API_KEY and `pip install anthropic`)
LLM_MODE = os.getenv("LLM_MODE", "mock")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-5-5")
MOCK_LLM_MS = int(os.getenv("MOCK_LLM_MS", "1500"))

# Assumed cost of one LLM call in rupees. This is an ASSUMPTION; say so in the README.
COST_PER_CALL_INR = float(os.getenv("COST_PER_CALL_INR", "0.50"))

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
