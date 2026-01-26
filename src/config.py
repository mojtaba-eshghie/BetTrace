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
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5-nano")

# Embedding dimensions for text-embedding-3-small
EMBEDDING_DIMENSIONS = 1536

# Database paths
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", DATA_DIR / "bets.db"))
CSV_PATH = Path(os.getenv("CSV_PATH", DATA_DIR / "bets.csv"))

# Retrieval settings
DEFAULT_TOP_K = 10
SIMILARITY_THRESHOLD = 0.5  # Minimum cosine similarity for semantic search

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
