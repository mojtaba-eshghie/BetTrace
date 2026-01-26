#!/usr/bin/env python3
"""
Sportsbook RAG Assistant - Main Entry Point

Usage:
    python main.py ingest              # Ingest data from CSV
    python main.py search "query"      # Search for bets
    python main.py filter --help       # Filter bets
    python main.py stats               # Show statistics
"""

import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent))

from src.cli import main

if __name__ == "__main__":
    main()
