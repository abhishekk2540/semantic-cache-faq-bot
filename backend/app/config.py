import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
DB_PATH = BASE_DIR / "cache_app.db"

# Auto-load .env file if present
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip("\"'")
                if k not in os.environ:
                    os.environ[k] = v

# --- Clerk auth ---
CLERK_FRONTEND_API = os.getenv("CLERK_FRONTEND_API", "").rstrip("/")

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

raw_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)
CORS_ORIGINS = [orig.strip().rstrip("/") for orig in raw_origins.split(",") if orig.strip()]
