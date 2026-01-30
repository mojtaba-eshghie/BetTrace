"""
Configuration management for the Sportsbook RAG Assistant.

Handles environment variables and application settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5-mini-2025-08-07")

# Embedding dimensions for text-embedding-3-small
EMBEDDING_DIMENSIONS = 1536

# Database paths
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", DATA_DIR / "bets.db"))
CSV_PATH = Path(os.getenv("CSV_PATH", DATA_DIR / "bets.csv"))

# Retrieval settings
DEFAULT_TOP_K = 10
SIMILARITY_THRESHOLD = 0.3  # Minimum cosine similarity for semantic search (lowered to catch more results)

# Team matching configuration
# Options: "sparse" (default, uses edit distance via rapidfuzz) or "embedding" (phonetic + vector search)
TEAM_MATCHING_METHOD = os.getenv("TEAM_MATCHING_METHOD", "sparse")
# Threshold for sparse team matching (0-100 scale, using fuzz.ratio)
SPARSE_TEAM_THRESHOLD = float(os.getenv("SPARSE_TEAM_THRESHOLD", "70"))

# Debug mode
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Schema definitions
BET_COLUMNS = [
    "bet_id",
    "customer_id", 
    "sport",
    "event_name",
    "market",
    "selection",
    "stake_gbp",
    "status",
    "incident_tag",
    "price_delay_ms"
]

# Valid values for categorical columns (for validation)
VALID_SPORTS = {"football", "tennis", "basketball"}
VALID_STATUSES = {"SETTLED", "PENDING", "VOID", "REJECTED"}
VALID_INCIDENTS = {"NONE", "LATENCY_SPIKE", "FEED_OUTAGE", "MARKET_SUSPENDED", "MANUAL_REVIEW"}


def validate_config() -> bool:
    """Validate that required configuration is present."""
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is not set. "
            "Please set it in your .env file or environment variables."
        )
    return True
