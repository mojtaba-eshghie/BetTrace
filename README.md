# BetTrace: A Sportsbook RAG Assistant

A Retrieval-Augmented Generation (RAG) system for querying sports betting records using natural language. Built with a hybrid architecture combining structured SQL queries, semantic vector search, and LLM-powered response generation.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Query Pipeline](#query-pipeline)
- [Design Decisions](#design-decisions)
- [Database Schema](#database-schema)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Features

- **Natural Language Queries**: Ask questions like "Show me all VOID bets with FEED_OUTAGE incidents"
- **Hybrid Search**: Combines SQL filtering with semantic vector search
- **Typo-Tolerant Team Search**: Phonetic normalization handles misspellings ("Raptors" → "Rapters")
- **SQL-Based Computation**: All arithmetic performed via SafeCalculator (LLMs don't do math)
- **Citation Enforcement**: Every answer includes evidence with bet IDs
- **Analysis Mode**: Detects when users want summaries vs. simple counts

---

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key

### Installation

```bash
# Clone and setup
cd sportsbook-rag
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Usage

```bash
# 1. Ingest data (generates embeddings)
python main.py ingest

# 2. Ask questions
python main.py ask "How many bets were rejected?"
python main.py ask "Show all bets for customer C068" --show-context
python main.py ask "Find bets involving the Lakers team"

# 3. Interactive mode
python main.py chat
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SPORTSBOOK RAG SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User Query                                                                  │
│      │                                                                       │
│      ▼                                                                       │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │ QueryParser  │────▶│QueryExecutor │────▶│    RAG       │                │
│  │              │     │              │     │  Assistant   │                │
│  │ • Entity IDs │     │ • Routing    │     │              │                │
│  │ • Filters    │     │ • SQL/Vector │     │ • Context    │                │
│  │ • Aggregates │     │ • Calculator │     │ • LLM Call   │                │
│  │ • Intent     │     │              │     │ • Citations  │                │
│  └──────────────┘     └──────────────┘     └──────────────┘                │
│                              │                     │                        │
│                              ▼                     ▼                        │
│                       ┌─────────────┐       ┌─────────────┐                │
│                       │  Database   │       │   OpenAI    │                │
│                       │             │       │             │                │
│                       │ • SQLite    │       │ • Embeddings│                │
│                       │ • FAISS     │       │ • GPT-4     │                │
│                       │ • Bets      │       │             │                │
│                       │ • Embeddings│       │             │                │
│                       └─────────────┘       └─────────────┘                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component | File | Responsibility |
|-----------|------|----------------|
| **QueryParser** | `query_parser.py` | Extracts entities, filters, aggregations from natural language |
| **QueryExecutor** | `query_executor.py` | Routes queries and orchestrates retrieval strategies |
| **Retriever** | `retrieval.py` | Hybrid search (SQL + semantic), embedding generation |
| **Database** | `database.py` | SQLite storage, FAISS vector indices, query execution |
| **SafeCalculator** | `calculator.py` | SQL-based arithmetic (counts, sums, averages) |
| **RAGAssistant** | `rag.py` | Context building, LLM calls, citation enforcement |
| **VectorStore** | `vector_store.py` | FAISS index management, similarity search |

---

## Query Pipeline

### 1. Query Parsing

The `QueryParser` analyzes natural language to extract structured information:

```python
"Show rejected bets for customer C068 with stake > £50"
    ↓
ParsedQuery(
    customer_ids=["C068"],
    filters={"status": "REJECTED"},
    min_stake=50.0,
    aggregation=AggregationType.NONE,
    query_type=QueryType.ENTITY_LOOKUP
)
```

**Extraction Capabilities:**
- Entity IDs: `B0042`, `C068` (with normalization: `B42` → `B0042`)
- Status filters: `SETTLED`, `PENDING`, `VOID`, `REJECTED`
- Incident filters: `LATENCY_SPIKE`, `FEED_OUTAGE`, `MARKET_SUSPENDED`, `MANUAL_REVIEW`
- Numeric ranges: `stake > £50`, `delay > 1000ms`
- Aggregations: `count`, `sum`, `average`, `top N`, `bottom N`
- Sort criteria: `highest stake`, `most delayed`

### 2. Query Routing

The `QueryExecutor` routes queries to the optimal execution strategy:

```
┌─────────────────────────────────────────────────────────────────┐
│                      QUERY TYPE ROUTING                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Has bet_id/customer_id?                                        │
│      YES → ENTITY_LOOKUP (direct SQL lookup)                    │
│                                                                  │
│  Has aggregation (count/sum/avg)?                               │
│      With filters → AGGREGATE (SQL with SafeCalculator)         │
│      With semantic terms → SEMANTIC (vector search)             │
│                                                                  │
│  Has TOP_N/BOTTOM_N?                                            │
│      With sort column → TOP_N (SQL ORDER BY)                    │
│      Otherwise → HYBRID                                          │
│                                                                  │
│  Has filters + semantic terms?                                   │
│      → HYBRID (SQL filter + vector rerank)                      │
│                                                                  │
│  Has filters only?                                               │
│      → FILTERED (pure SQL)                                       │
│                                                                  │
│  Default?                                                        │
│      → SEMANTIC (vector search with team embeddings)            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Retrieval Strategies

#### SQL-Based Retrieval
```python
# Direct lookups and filtered queries
SELECT * FROM bets WHERE customer_id = 'C068' AND status = 'REJECTED'
```

#### Semantic Vector Search
```python
# Team-level embeddings with phonetic normalization
query = "Raptors"
    ↓ phonetic_normalize()
"RPTRS"
    ↓ embed()
query_vector
    ↓ FAISS search against team1/team2 embeddings
matches "Rapters" (stored as "RPTRS" embedding)
```

#### Hybrid Search
```python
# SQL filter first, then semantic rerank
1. SQL: Get all REJECTED bets
2. Vector: Rerank by similarity to "suspicious activity"
3. Return top-k results
```

### 4. Computation (SafeCalculator)

**Critical Design**: LLMs cannot reliably perform arithmetic. All calculations use SQL:

```python
# SafeCalculator generates SQL for all numeric operations
"What's the average stake for VOID bets?"
    ↓
SELECT AVG(stake_gbp), COUNT(*), SUM(stake_gbp) 
FROM bets WHERE status = 'VOID'
    ↓
COMPUTED FACTS (injected into LLM context):
• Total Bets: 5
• Total Stake: £135.00
• Average Stake: £27.00
```

### 5. Response Generation

```
┌─────────────────────────────────────────────────────────────────┐
│                    RESPONSE GENERATION                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Build Context                                                │
│     • COMPUTED FACTS (from SafeCalculator)                      │
│     • Bet records (formatted for LLM)                           │
│     • Instructions based on query type                          │
│                                                                  │
│  2. Detect Analysis Intent                                       │
│     Keywords: summarize, explain, analyze, what happened...     │
│     → Triggers detailed response mode                           │
│                                                                  │
│  3. LLM Call                                                     │
│     • System prompt (field meanings, rules)                     │
│     • User message (question + context + instructions)          │
│                                                                  │
│  4. Citation Enforcement                                         │
│     • Extract bet IDs from response                             │
│     • Validate against retrieved bets                           │
│     • Append "Evidence: [B0001, B0002, ...]"                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

### 1. Team-Level Embeddings with Phonetic Normalization

**Problem**: Event names like "Bulls vs Rapters" dilute team signal when embedded as one string. Users searching for "Raptors" (correct spelling) wouldn't match "Rapters" (data typo).

**Solution**: Three-tier embedding strategy:

```
Event: "Bulls vs Rapters"
           │
           ▼ parse_event_teams()
    ┌──────┴──────┐
    │             │
 "Bulls"     "Rapters"
    │             │
    ▼             ▼
phonetic_normalize()
    │             │
 "BLS"       "RPTRS"
    │             │
    ▼             ▼
 embed()      embed()
    │             │
    ▼             ▼
team1_emb   team2_emb   ← Stored in DB
```

**Search Flow**:
```
Query: "Raptors"
    ↓ phonetic_normalize()
"RPTRS"
    ↓ embed()
query_vector
    ↓ compare against team2_emb
EXACT MATCH with "Rapters"!
```

**Phonetic Algorithm**:
```python
def phonetic_normalize(text):
    # 1. Keep first letter
    # 2. Remove vowels from rest
    # 3. Remove consecutive duplicates
    # 4. Apply phonetic rules (PH→F, CK→K, etc.)
    
    "Raptors"  → "RPTRS"
    "Rapters"  → "RPTRS"  ← Same!
    "Lakers"   → "LKRS"
    "Lakkers"  → "LKRS"   ← Same!
```

### 2. SQL-Based Computation (No LLM Math)

**Problem**: LLMs hallucinate arithmetic. "Count these 7 items" might return 6 or 8.

**Solution**: `SafeCalculator` executes all math via SQL:

```python
class SafeCalculator:
    def compute_stats(self, filters):
        # ALL arithmetic happens in SQLite
        query = """
            SELECT 
                COUNT(*) as total_bets,
                SUM(stake_gbp) as total_stake,
                AVG(stake_gbp) as avg_stake,
                AVG(price_delay_ms) as avg_delay
            FROM bets
            WHERE {filters}
        """
        return self.execute(query)
```

**Result**: LLM receives pre-computed facts:
```
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
• Total Bets: 7
• Total Stake: £190.00
• Average Stake: £27.14
⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
```

### 3. Query Type Detection with Analysis Intent

**Problem**: "How many VOID bets?" vs "How many VOID bets? List them and explain." require different response styles.

**Solution**: Two-phase detection:

```python
# Phase 1: Query Type (structural)
if has_bet_id: return ENTITY_LOOKUP
if has_aggregation + filters: return AGGREGATE
if has_top_n: return TOP_N
...

# Phase 2: Analysis Intent (semantic)
analysis_keywords = ['summarize', 'explain', 'analyze', 'list them', 
                     'what happened', 'highlight', 'severely']

if any(kw in query.lower() for kw in analysis_keywords):
    # Switch to detailed response mode
    instruction = "ANALYZE each bet record..."
else:
    # Keep concise
    instruction = "State the count only..."
```

### 4. Hybrid Search Strategy

**Problem**: Pure SQL misses semantic queries. Pure vector search ignores structured filters.

**Solution**: Combine both based on query type:

```python
def hybrid_search(query, filters):
    # 1. SQL filter (fast, precise)
    candidates = sql_filter(filters)  # e.g., status='REJECTED'
    
    # 2. If no candidates or need semantic ranking
    if semantic_terms:
        query_emb = embed(query)
        # Rerank candidates by semantic similarity
        results = rerank_by_similarity(candidates, query_emb)
    
    return results
```

### 5. Citation Enforcement

**Problem**: LLM might reference bets not in context, or forget to cite sources.

**Solution**: Post-processing enforcement:

```python
def enforce_citations(answer, retrieved_bets):
    # Extract cited bet IDs
    cited = re.findall(r'B\d{4}', answer)
    valid_ids = {b.bet_id for b in retrieved_bets}
    
    # Filter to only valid citations
    valid_citations = [id for id in cited if id in valid_ids]
    
    # Ensure Evidence line exists
    if "Evidence:" not in answer:
        answer += f"\n\nEvidence: [{', '.join(valid_citations)}]"
    
    return answer
```

---

## Database Schema

### Bets Table
```sql
CREATE TABLE bets (
    bet_id TEXT PRIMARY KEY,      -- e.g., "B0042"
    customer_id TEXT NOT NULL,    -- e.g., "C068"
    sport TEXT NOT NULL,          -- football, tennis, basketball
    event_name TEXT NOT NULL,     -- "Bulls vs Rapters"
    market TEXT,                  -- "Moneyline", "Spread", etc.
    selection TEXT,               -- "Home", "Away", "Over 2.5"
    stake_gbp REAL NOT NULL,      -- Stake in GBP
    status TEXT NOT NULL,         -- SETTLED, PENDING, VOID, REJECTED
    incident_tag TEXT,            -- NONE, LATENCY_SPIKE, FEED_OUTAGE, etc.
    price_delay_ms INTEGER,       -- Latency in milliseconds
    document TEXT                 -- Full text for semantic search
)
```

### Embeddings Table
```sql
CREATE TABLE embeddings (
    bet_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,        -- Full document embedding (1536 dim)
    team1_embedding BLOB,           -- First team/player phonetic embedding
    team2_embedding BLOB,           -- Second team/player phonetic embedding
    content_hash TEXT,              -- For change detection
    FOREIGN KEY (bet_id) REFERENCES bets(bet_id)
)
```

### Indices
```sql
CREATE INDEX idx_customer ON bets(customer_id);
CREATE INDEX idx_status ON bets(status);
CREATE INDEX idx_sport ON bets(sport);
CREATE INDEX idx_incident ON bets(incident_tag);
```

---

## Configuration

### Environment Variables (`.env`)

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (defaults shown)
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-5-mini-2025-08-07
DATABASE_PATH=data/bets.db
CSV_PATH=data/bets.csv
```

### Application Settings (`config.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `EMBEDDING_DIMENSIONS` | 1536 | Vector dimensions for text-embedding-3-small |
| `DEFAULT_TOP_K` | 10 | Default number of results to retrieve |
| `SIMILARITY_THRESHOLD` | 0.3 | Minimum cosine similarity for semantic matches |

---

## CLI Reference

### Ingest Data
```bash
python main.py ingest [--csv PATH]

# Generates:
# - Document embeddings (full bet description)
# - Team1 embeddings (phonetic normalized)
# - Team2 embeddings (phonetic normalized)
```

### Ask Questions
```bash
python main.py ask "your question" [OPTIONS]

Options:
  --top-k N        Number of results (default: 10)
  --show-context   Display retrieved bets and stats
```

### Interactive Chat
```bash
python main.py chat

# Commands in chat:
# /help     - Show available commands
# /clear    - Clear conversation
# /quit     - Exit
```

### Database Stats
```bash
python main.py stats

# Shows:
# - Total bets
# - Bets by status
# - Bets by incident
# - Embedding info
```

---

## Testing

You can run acceptance tests in `ACCEPTANCE_TESTS.md` file manually which includes 7 questions. 


### Unit Tests

The following are unit tests to test the functionality of individual system components. 

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_retrieval.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

| Test File | Coverage |
|-----------|----------|
| `test_retrieval.py` | Query parsing, ID normalization, filters, phonetic normalization |
| `test_dimension_validation.py` | Embedding dimension checks |

---

## Troubleshooting

### "No bets found" for valid queries

1. **Check ingestion**: Ensure you ran `python main.py ingest`
2. **Check filters**: Some filter combinations may have zero matches
3. **Check spelling**: Team searches use phonetic matching, but very different spellings may not match

### Empty or minimal LLM responses

1. **Check API key**: Ensure `OPENAI_API_KEY` is set correctly
2. **Check model**: Default model should work; try different models for better analysis
3. **Increase tokens**: Modify `max_completion_tokens` in `rag.py` if responses are truncated

### Embedding dimension mismatch

```
ValueError: Embedding dimension mismatch!
  Stored: 1536, Expected: 3072
```

**Solution**: Delete database and re-ingest:
```bash
rm data/bets.db
python main.py ingest
```

### FAISS not installed warning

```
Warning: FAISS not installed. Using brute-force search.
```

**Solution** (optional, for better performance):
```bash
pip install faiss-cpu
```

---

## Project Structure

```
BetTrace/
├── main.py                 # CLI entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── data/
│   ├── bets.csv           # Source data
│   └── bets.db            # SQLite + embeddings (generated)
├── src/
│   ├── config.py          # Configuration management
│   ├── models.py          # Data models (Bet, ParsedQuery)
│   ├── database.py        # SQLite + FAISS operations
│   ├── vector_store.py    # FAISS index wrapper
│   ├── embedding_service.py # OpenAI embedding calls
│   ├── ingestion.py       # CSV → DB + embeddings
│   ├── query_parser.py    # NL → structured query
│   ├── query_executor.py  # Query routing + execution
│   ├── retrieval.py       # Search strategies
│   ├── calculator.py      # SQL-based arithmetic
│   ├── rag.py             # LLM response generation
│   └── cli.py             # Command-line interface
└── tests/
    ├── test_retrieval.py
    └── test_dimension_validation.py
```

