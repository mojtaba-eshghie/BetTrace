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
│               (ask, chat, search, filter, stats)                │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        RAG Layer                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Query     │  │  Context    │  │   LLM Generation        │ │
│  │  Analysis   │→ │  Formatting │→ │   (GPT-5-nano)          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
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

### RAG Workflow

1. **Query Analysis**: Extract bet IDs, customer IDs, incidents, or keywords
2. **Smart Retrieval**: Choose optimal retrieval strategy based on query type
3. **Context Formatting**: Format retrieved bets as structured context for LLM
4. **LLM Generation**: Generate grounded answer using GPT-5-nano with strict citation rules
5. **Citation Extraction**: Parse and validate bet ID citations from response

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
│   ├── database.py      # SQLite + FAISS hybrid storage
│   ├── vector_store.py  # FAISS-based vector storage with content hashing
│   ├── ingestion.py     # CSV loading and embedding generation
│   ├── retrieval.py     # Retrieval strategies
│   ├── rag.py           # RAG generation with LLM
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

### Ask Questions (RAG)

The main way to interact with the assistant - ask natural language questions:

```bash
# Single question
python main.py ask "Why was bet B0004 rejected?"
python main.py ask "Which customers were most impacted by LATENCY_SPIKE?"
python main.py ask "Find the top 5 highest price_delay_ms bets and summarize"
python main.py ask "For customer C068, summarize their bets and any incidents"

# Show the retrieved context used
python main.py ask "Why was B0004 rejected?" --show-context

# Interactive chat session
python main.py chat
```

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

### RAG System Design

**Prompt Engineering**:
The system prompt instructs the LLM to:
- Only use information from provided bet records
- Always cite bet_ids that support the answer
- Explicitly state when evidence is insufficient
- Focus on operational insights

**Citation Extraction**:
Citations are validated against retrieved bets to prevent hallucinated bet IDs.

**Context Formatting**:
Each bet is formatted with all fields clearly labeled, plus summary statistics when multiple bets are retrieved (status breakdown, incident counts, delay ranges).

### Why Hybrid (Structured + Embeddings)?

1. **Exact queries are common**: Ops teams often query by bet_id or customer_id
2. **Fuzzy matching needed**: Event names contain misspellings (e.g., "Lakkers vs Celtcs")
3. **Range queries**: Filtering by latency thresholds, stake amounts
4. **Small dataset**: 100 rows fits comfortably in memory

### Why SQLite + FAISS (Scalable Design)?

The system uses a hybrid approach that scales from 100 to 100K+ rows:

**FAISS Vector Store** (`vector_store.py`):
- O(log N) approximate nearest neighbor search (vs O(N) brute force)
- Filtered vector search without loading all data into Python
- Falls back to NumPy if FAISS not installed

**Embedding Versioning**:
- Content hash stored with each embedding
- Detects when document format changes require re-embedding
- Prevents semantic drift between stored embeddings and current documents

**Filtered Hybrid Search**:
- SQL pre-filters bets (e.g., `sport='football'`)
- FAISS searches only among filtered IDs
- Avoids O(N) Python loop over all embeddings

```python
# Old (O(N) Python loop):
for bet_id in all_bet_ids:
    if bet_id in filtered_ids:
        compute_similarity(embedding)

# New (FAISS filtered search):
vector_store.search(query, filter_ids=filtered_ids)  # O(log K) where K=filter size
```

### Document Representation

Each bet is converted to a natural language document for embedding:

```
Bet B0004: Customer C060 placed a £30 BTTS bet on West Ham vs Fullham (football). 
Selection: No. Status: REJECTED. Incident: MARKET_SUSPENDED. High latency: 635ms.
```

**Important**: The document text is stored in the database alongside the embedding. When retrieving bets for RAG:
- The stored embedding is used for similarity search (no re-embedding)
- The stored document text is returned (no re-generation)
- This ensures the text sent to the LLM exactly matches what was embedded

This allows semantic search to match concepts like "rejected bets" or "high latency incidents".

### Currency Handling (No Float Precision Errors)

Financial applications must avoid floating-point precision errors (e.g., `0.1 + 0.2 ≠ 0.3`).

**Python Layer** (`models.py`):
- All monetary values use `Decimal` for exact arithmetic
- `to_decimal()` - converts any input safely to Decimal
- `to_pence()` / `from_pence()` - for INTEGER storage

```python
from src.models import Bet, to_decimal

# Creating bets - stake is always converted to Decimal
bet = Bet.from_dict({"stake_gbp": 10.99, ...})
print(type(bet.stake_gbp))  # <class 'decimal.Decimal'>

# Arithmetic is exact
total = bet1.stake_gbp + bet2.stake_gbp  # Returns Decimal
```

**Database Layer** (`database.py`):
- Currently stores as `REAL` for backwards compatibility
- For production: store as `INTEGER` pence (`bet.stake_pence()`)
- Conversion happens at boundary in `_row_to_bet()`

## Future Improvements

With more time, I would add:

1. **Query intent classification**: Use LLM to parse complex queries into structured filters
2. **Re-ranking**: Two-stage retrieval with cross-encoder re-ranking
3. **Caching**: Cache embeddings and frequent queries
4. **Streaming**: Support larger datasets with chunked processing
5. **Evaluation**: Build test set with ground truth for retrieval metrics

## Key Design Decision: LLMs Do Not Do Math

**Problem**: LLMs are notoriously bad at arithmetic. Asking them to count items, sum values, or calculate averages produces unreliable results.

**Solution**: The `SafeCalculator` module (`src/calculator.py`) handles ALL numeric computations:

```python
# All calculations are executed via SQL (deterministic, exact)
calculator = SafeCalculator(db_path)

# Count, sum, average - all computed in SQL
result = calculator.sum_stake(status="SETTLED")
# Returns: CalculationResult(value=Decimal('2230.00'), sql_used="SELECT SUM...")

# Rankings
top_5 = calculator.top_by_delay(n=5)

# Groupings
by_status = calculator.group_by_status()
```

**How it works**:
1. Query analysis determines what calculations are needed
2. `SafeCalculator` executes calculations via parameterized SQL
3. Results are formatted as **COMPUTED FACTS** in the LLM context
4. LLM's job is ONLY to narrate and explain - never to calculate

**Example context sent to LLM**:
```
============================================================
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
============================================================
Status: SETTLED

• Total Bets: 80
• Total Stake: £2230.00
• Average Stake: £27.88

⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
============================================================

The bet records below are ONLY for citing evidence.
```

**Safety features**:
- Only whitelisted columns allowed (no SQL injection)
- All queries are parameterized
- Read-only database connection
- Uses Decimal for exact currency arithmetic
6. **Web UI**: Flask/FastAPI endpoint with React frontend

## License

Internal use only - FDJ United
