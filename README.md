# Sportsbook RAG Assistant

A Retrieval-Augmented Generation (RAG) system for querying sports betting data using natural language.

## Overview

This assistant helps ops teams query bet records using a hybrid retrieval approach that combines:
- **Structured queries**: Exact lookups, filtering, and aggregations via SQLite
- **Semantic search**: Embedding-based similarity search using OpenAI's text-embedding-3-small

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                           │
│                    (search, filter, stats)                      │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Retrieval Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Exact     │  │  Filtered   │  │  Semantic / Hybrid      │ │
│  │   Lookup    │  │   Queries   │  │      Search             │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database Layer                             │
│  ┌───────────────────────────┐  ┌─────────────────────────────┐│
│  │   SQLite (Structured)     │  │  Vector Store (Embeddings)  ││
│  │   - Bets table            │  │  - NumPy in-memory          ││
│  │   - Indexed columns       │  │  - Cosine similarity        ││
│  └───────────────────────────┘  └─────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Ingestion Layer                             │
│         CSV → Bet Objects → Documents → Embeddings              │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
sportsbook-rag/
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── main.py              # CLI entry point
├── src/
│   ├── __init__.py
│   ├── config.py        # Configuration and settings
│   ├── models.py        # Data models (Bet, RetrievalResult)
│   ├── database.py      # SQLite + vector storage
│   ├── ingestion.py     # CSV loading and embedding generation
│   ├── retrieval.py     # Retrieval strategies
│   └── cli.py           # Command-line interface
├── data/
│   └── bets.csv         # Bet data (100 rows)
└── tests/
    └── test_retrieval.py # Test suite
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. Ingest Data

```bash
python main.py ingest
```

This will:
- Load the CSV file (100 bets)
- Generate embeddings via OpenAI API
- Store data in SQLite database
- Load embeddings into memory

## Usage

### Search (Natural Language)

```bash
# Search using natural language
python main.py search "Why was bet B0004 rejected?"
python main.py search "Customer C068 bets"
python main.py search "high latency bets" --top-k 10

# Specify search method
python main.py search "Lakers game" --method semantic
python main.py search "B0042" --method exact
```

### Filter (Structured Queries)

```bash
# Filter by specific criteria
python main.py filter --bet-id B0042
python main.py filter --customer C068
python main.py filter --status REJECTED
python main.py filter --incident LATENCY_SPIKE
python main.py filter --sport football
python main.py filter --top-delay 5
```

### Incident Reports

```bash
# Generate incident summary
python main.py incident-report LATENCY_SPIKE
python main.py incident-report MARKET_SUSPENDED
```

### Statistics

```bash
# View database statistics
python main.py stats
```

## Retrieval Strategies

### 1. Exact Lookup
Direct lookup by bet_id or customer_id. O(1) via indexed SQLite queries.

```python
retriever.get_bet("B0042")
retriever.get_customer_bets("C068")
```

### 2. Filtered Queries
SQL-based filtering on structured columns.

```python
retriever.filter_by_status("REJECTED")
retriever.filter_by_incident("LATENCY_SPIKE")
retriever.advanced_filter(
    sports=["football"],
    statuses=["SETTLED", "PENDING"],
    min_stake=20.0
)
```

### 3. Semantic Search
Embedding-based similarity search for fuzzy matching.

```python
retriever.semantic_search("Lakers vs Celtics game", top_k=5)
```

### 4. Hybrid Search
Combines structured filters with semantic ranking.

```python
retriever.hybrid_search(
    query="high stakes basketball bets",
    filters={"sports": ["basketball"], "min_stake": 30.0},
    top_k=10
)
```

### 5. Smart Retrieval
Automatically chooses the best strategy based on query analysis.

```python
# Detects bet ID → exact lookup
retriever.retrieve("Why was bet B0004 rejected?")

# Detects customer ID → customer lookup
retriever.retrieve("Show bets for customer C068")

# Detects incident → filtered query
retriever.retrieve("Which bets had LATENCY_SPIKE?")

# No specific entity → semantic search
retriever.retrieve("high value football bets with incidents")
```

## Data Model

### Bet Record

| Column | Type | Description |
|--------|------|-------------|
| bet_id | string | Unique identifier (e.g., B0042) |
| customer_id | string | Customer identifier (e.g., C029) |
| sport | string | football, tennis, basketball |
| event_name | string | Match/fixture name |
| market | string | Bet type (Match Winner, BTTS, etc.) |
| selection | string | Selected outcome |
| stake_gbp | float | Stake amount in GBP |
| status | string | SETTLED, PENDING, VOID, REJECTED |
| incident_tag | string | NONE, LATENCY_SPIKE, FEED_OUTAGE, etc. |
| price_delay_ms | int | Latency in milliseconds |

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

## Design Decisions & Tradeoffs

### Why Hybrid (Structured + Embeddings)?

1. **Exact queries are common**: Ops teams often query by bet_id or customer_id
2. **Fuzzy matching needed**: Event names contain misspellings (e.g., "Lakkers vs Celtcs")
3. **Range queries**: Filtering by latency thresholds, stake amounts
4. **Small dataset**: 100 rows fits comfortably in memory

### Why SQLite + NumPy (not a Vector DB)?

For 100 rows, a full vector database (Pinecone, Weaviate) is overkill:
- SQLite provides fast indexed lookups
- NumPy cosine similarity is sufficient for in-memory search
- No external dependencies or infrastructure needed

### Document Representation

Each bet is converted to a natural language document for embedding:

```
Bet B0004: Customer C060 placed a £30 BTTS bet on West Ham vs Fullham (football). 
Selection: No. Status: REJECTED. Incident: MARKET_SUSPENDED. Latency: 635ms.
```

This allows semantic search to match concepts like "rejected bets" or "high latency incidents".

## Future Improvements

With more time, I would add:

1. **Query intent classification**: Use LLM to parse complex queries into structured filters
2. **Re-ranking**: Two-stage retrieval with cross-encoder re-ranking
3. **Caching**: Cache embeddings and frequent queries
4. **Streaming**: Support larger datasets with chunked processing
5. **Evaluation**: Build test set with ground truth for retrieval metrics
6. **Web UI**: Flask/FastAPI endpoint with React frontend

## License

Internal use only - FDJ United
