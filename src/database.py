"""
Database layer for the Sportsbook RAG Assistant.

Provides hybrid storage combining:
- SQLite for structured data (exact lookups, filtering, aggregations)
- FAISS-based vector store for embeddings (scalable semantic search)

Currency Note:
- Python uses Decimal for exact currency arithmetic
- SQLite stores stake as REAL (for backwards compatibility)
- Conversion happens at the boundary via to_decimal()
- For production, store as INTEGER pence (bet.stake_pence())
"""

import sqlite3
import json
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any, Set
from contextlib import contextmanager
from decimal import Decimal

from .models import Bet, RetrievalResult, to_decimal, to_pence, from_pence
from .config import DATABASE_PATH, EMBEDDING_DIMENSIONS
from .vector_store import VectorStore, compute_content_hash, EmbeddingVersionManager


class Database:
    """
    Hybrid database combining SQLite for structured data
    and FAISS-based vector storage for embeddings.
    
    Scalability improvements:
    - Uses FAISS for O(log N) approximate nearest neighbor search
    - Supports filtered vector search without loading all data into Python
    - Content hashing for embedding versioning
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the database connection."""
        self.db_path = db_path or DATABASE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Scalable vector storage using FAISS
        # Three stores for different search strategies:
        # - Document: full bet context (broad semantic search)
        # - Team1: first team/player (precise team search)
        # - Team2: second team/player (precise team search)
        self._vector_store = VectorStore(EMBEDDING_DIMENSIONS)
        self._team1_vector_store = VectorStore(EMBEDDING_DIMENSIONS)
        self._team2_vector_store = VectorStore(EMBEDDING_DIMENSIONS)
        
        # Legacy compatibility - keep bet_ids list for ID lookups
        self._bet_ids: List[str] = []
        
        # Embedding version manager
        self._version_manager = EmbeddingVersionManager(self.db_path)
        
        # Initialize SQLite schema
        self._init_schema()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_schema(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Main bets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bets (
                    bet_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    sport TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    market TEXT NOT NULL,
                    selection TEXT NOT NULL,
                    stake_gbp REAL NOT NULL,
                    status TEXT NOT NULL,
                    incident_tag TEXT NOT NULL,
                    price_delay_ms INTEGER NOT NULL,
                    document TEXT NOT NULL
                )
            """)
            
            # Embeddings table with content hash for versioning
            # Stores multiple embeddings per bet for precise search:
            # - embedding: full document (captures overall context)
            # - team1_embedding: first team/player name (for precise team search)
            # - team2_embedding: second team/player name (for precise team search)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    bet_id TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    team1_embedding BLOB,
                    team2_embedding BLOB,
                    content_hash TEXT,
                    FOREIGN KEY (bet_id) REFERENCES bets(bet_id)
                )
            """)
            
            # Metadata table for embedding model configuration
            # This ensures we detect dimension/model mismatches
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embedding_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            # Add columns if they don't exist (migration)
            cursor.execute("PRAGMA table_info(embeddings)")
            columns = {row['name'] for row in cursor.fetchall()}
            if 'content_hash' not in columns:
                cursor.execute("ALTER TABLE embeddings ADD COLUMN content_hash TEXT")
            if 'team1_embedding' not in columns:
                cursor.execute("ALTER TABLE embeddings ADD COLUMN team1_embedding BLOB")
            if 'team2_embedding' not in columns:
                cursor.execute("ALTER TABLE embeddings ADD COLUMN team2_embedding BLOB")
            # Remove old event_embedding column if it exists (superseded by team embeddings)
            # Note: SQLite doesn't support DROP COLUMN before 3.35, so we just ignore it
            
            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_id ON bets(customer_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sport ON bets(sport)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON bets(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_incident_tag ON bets(incident_tag)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_delay ON bets(price_delay_ms)")
    
    def _get_metadata(self, key: str) -> Optional[str]:
        """Get a metadata value from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM embedding_metadata WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None
    
    def _set_metadata(self, key: str, value: str):
        """Set a metadata value in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO embedding_metadata (key, value) VALUES (?, ?)",
                (key, value)
            )
    
    def get_embedding_config(self) -> Optional[Dict[str, Any]]:
        """Get the stored embedding configuration."""
        model = self._get_metadata("embedding_model")
        dim_str = self._get_metadata("embedding_dimension")
        
        if model and dim_str:
            return {
                "model": model,
                "dimension": int(dim_str),
                "created_at": self._get_metadata("embedding_created_at")
            }
        return None
    
    def set_embedding_config(self, model: str, dimension: int):
        """
        Store the embedding configuration.
        
        This is called during ingestion to record what model/dimension was used.
        """
        from datetime import datetime
        
        self._set_metadata("embedding_model", model)
        self._set_metadata("embedding_dimension", str(dimension))
        self._set_metadata("embedding_created_at", datetime.now().isoformat())
    
    def validate_embedding_config(self, model: str, dimension: int) -> None:
        """
        Validate that the current config matches stored config.
        
        Raises ValueError if there's a mismatch.
        """
        stored = self.get_embedding_config()
        
        if stored is None:
            # No stored config - this is first ingestion
            return
        
        if stored["dimension"] != dimension:
            raise ValueError(
                f"Embedding dimension mismatch!\n"
                f"  Stored in DB: {stored['dimension']} (from model '{stored['model']}')\n"
                f"  Current config: {dimension} (from model '{model}')\n"
                f"  Solution: Either use the same model, or delete the database and re-ingest."
            )
        
        if stored["model"] != model:
            # Warn but don't fail - dimension is what matters
            import warnings
            warnings.warn(
                f"Embedding model changed from '{stored['model']}' to '{model}'. "
                f"Dimensions match ({dimension}), but semantic compatibility is not guaranteed. "
                f"Consider re-ingesting for best results."
            )
    
    def clear(self):
        """Clear all data from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM embeddings")
            cursor.execute("DELETE FROM bets")
        self._vector_store.clear()
        self._bet_ids = []
    
    # ==================== INSERT OPERATIONS ====================
    
    def insert_bet(self, bet: Bet, embedding: Optional[np.ndarray] = None):
        """Insert a single bet with optional embedding."""
        document = bet.to_document()
        content_hash = compute_content_hash(document)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert bet record (convert Decimal to float for SQLite REAL)
            cursor.execute("""
                INSERT OR REPLACE INTO bets 
                (bet_id, customer_id, sport, event_name, market, selection,
                 stake_gbp, status, incident_tag, price_delay_ms, document)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bet.bet_id, bet.customer_id, bet.sport, bet.event_name,
                bet.market, bet.selection, float(bet.stake_gbp), bet.status,
                bet.incident_tag, bet.price_delay_ms, document
            ))
            
            # Insert embedding with content hash if provided
            if embedding is not None:
                cursor.execute("""
                    INSERT OR REPLACE INTO embeddings (bet_id, embedding, content_hash)
                    VALUES (?, ?, ?)
                """, (bet.bet_id, embedding.tobytes(), content_hash))
    
    def insert_bets_batch(
        self, 
        bets: List[Bet], 
        embeddings: Optional[np.ndarray] = None,
        team1_embeddings: Optional[np.ndarray] = None,
        team2_embeddings: Optional[np.ndarray] = None
    ):
        """
        Insert multiple bets with optional embeddings (batch operation).
        
        Args:
            bets: List of Bet objects
            embeddings: Full document embeddings (for broad semantic search)
            team1_embeddings: First team/player embeddings (for precise team search)
            team2_embeddings: Second team/player embeddings (for precise team search)
        """
        # Pre-compute documents and hashes
        documents = [b.to_document() for b in bets]
        content_hashes = [compute_content_hash(doc) for doc in documents]
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Batch insert bets (convert Decimal stake to float for SQLite REAL)
            bet_data = [
                (b.bet_id, b.customer_id, b.sport, b.event_name, b.market,
                 b.selection, float(b.stake_gbp), b.status, b.incident_tag,
                 b.price_delay_ms, documents[i])
                for i, b in enumerate(bets)
            ]
            cursor.executemany("""
                INSERT OR REPLACE INTO bets 
                (bet_id, customer_id, sport, event_name, market, selection,
                 stake_gbp, status, incident_tag, price_delay_ms, document)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, bet_data)
            
            # Batch insert embeddings with team-level embeddings if provided
            if embeddings is not None:
                embedding_data = []
                for i in range(len(bets)):
                    team1_emb = team1_embeddings[i].tobytes() if team1_embeddings is not None else None
                    team2_emb = team2_embeddings[i].tobytes() if team2_embeddings is not None else None
                    embedding_data.append((
                        bets[i].bet_id, 
                        embeddings[i].tobytes(), 
                        team1_emb,
                        team2_emb,
                        content_hashes[i]
                    ))
                cursor.executemany("""
                    INSERT OR REPLACE INTO embeddings (bet_id, embedding, team1_embedding, team2_embedding, content_hash)
                    VALUES (?, ?, ?, ?, ?)
                """, embedding_data)
    
    # ==================== STRUCTURED QUERIES ====================
    
    def get_by_bet_id(self, bet_id: str) -> Optional[Bet]:
        """Get a single bet by its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bets WHERE bet_id = ?", (bet_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_bet(row)
            return None
    
    def get_by_customer_id(self, customer_id: str) -> List[Bet]:
        """Get all bets for a customer."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bets WHERE customer_id = ? ORDER BY bet_id",
                (customer_id,)
            )
            return [self._row_to_bet(row) for row in cursor.fetchall()]
    
    def filter_by_status(self, status: str) -> List[Bet]:
        """Get all bets with a specific status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bets WHERE status = ? ORDER BY bet_id",
                (status,)
            )
            return [self._row_to_bet(row) for row in cursor.fetchall()]
    
    def filter_by_incident(self, incident_tag: str) -> List[Bet]:
        """Get all bets with a specific incident tag."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bets WHERE incident_tag = ? ORDER BY bet_id",
                (incident_tag,)
            )
            return [self._row_to_bet(row) for row in cursor.fetchall()]
    
    def filter_by_sport(self, sport: str) -> List[Bet]:
        """Get all bets for a specific sport."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bets WHERE sport = ? ORDER BY bet_id",
                (sport,)
            )
            return [self._row_to_bet(row) for row in cursor.fetchall()]
    
    def get_top_by_delay(self, limit: int = 10) -> List[Bet]:
        """Get bets with highest price_delay_ms."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bets ORDER BY price_delay_ms DESC LIMIT ?",
                (limit,)
            )
            return [self._row_to_bet(row) for row in cursor.fetchall()]
    
    def get_top_by_stake(self, limit: int = 10) -> List[Bet]:
        """Get bets with highest stakes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bets ORDER BY stake_gbp DESC LIMIT ?",
                (limit,)
            )
            return [self._row_to_bet(row) for row in cursor.fetchall()]
    
    def filter_by_delay_range(self, min_ms: int = 0, max_ms: int = 999999) -> List[Bet]:
        """Get bets within a price_delay_ms range."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bets WHERE price_delay_ms BETWEEN ? AND ? ORDER BY price_delay_ms DESC",
                (min_ms, max_ms)
            )
            return [self._row_to_bet(row) for row in cursor.fetchall()]
    
    def advanced_filter(
        self,
        customer_ids: Optional[List[str]] = None,
        sports: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        incident_tags: Optional[List[str]] = None,
        min_stake: Optional[float] = None,
        max_stake: Optional[float] = None,
        min_delay: Optional[int] = None,
        max_delay: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Bet]:
        """
        Advanced filtering with multiple criteria.
        All filters are combined with AND logic.
        """
        conditions = []
        params = []
        
        if customer_ids:
            placeholders = ",".join("?" * len(customer_ids))
            conditions.append(f"customer_id IN ({placeholders})")
            params.extend(customer_ids)
        
        if sports:
            placeholders = ",".join("?" * len(sports))
            conditions.append(f"sport IN ({placeholders})")
            params.extend(sports)
        
        if statuses:
            placeholders = ",".join("?" * len(statuses))
            conditions.append(f"status IN ({placeholders})")
            params.extend(statuses)
        
        if incident_tags:
            placeholders = ",".join("?" * len(incident_tags))
            conditions.append(f"incident_tag IN ({placeholders})")
            params.extend(incident_tags)
        
        if min_stake is not None:
            conditions.append("stake_gbp >= ?")
            params.append(min_stake)
        
        if max_stake is not None:
            conditions.append("stake_gbp <= ?")
            params.append(max_stake)
        
        if min_delay is not None:
            conditions.append("price_delay_ms >= ?")
            params.append(min_delay)
        
        if max_delay is not None:
            conditions.append("price_delay_ms <= ?")
            params.append(max_delay)
        
        query = "SELECT * FROM bets"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY bet_id"
        
        if limit:
            query += f" LIMIT {limit}"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._row_to_bet(row) for row in cursor.fetchall()]
    
    # ==================== AGGREGATION QUERIES ====================
    
    def get_all_bets(self) -> List[Bet]:
        """Get all bets."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bets ORDER BY bet_id")
            return [self._row_to_bet(row) for row in cursor.fetchall()]
    
    def count_by_status(self) -> Dict[str, int]:
        """Count bets by status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, COUNT(*) as count FROM bets GROUP BY status"
            )
            return {row["status"]: row["count"] for row in cursor.fetchall()}
    
    def count_by_incident(self) -> Dict[str, int]:
        """Count bets by incident tag."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT incident_tag, COUNT(*) as count FROM bets GROUP BY incident_tag"
            )
            return {row["incident_tag"]: row["count"] for row in cursor.fetchall()}
    
    def get_customers_by_incident(self, incident_tag: str) -> List[Tuple[str, int]]:
        """Get customers affected by an incident with bet counts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT customer_id, COUNT(*) as bet_count
                FROM bets 
                WHERE incident_tag = ?
                GROUP BY customer_id
                ORDER BY bet_count DESC
            """, (incident_tag,))
            return [(row["customer_id"], row["bet_count"]) for row in cursor.fetchall()]
    
    def get_stats_by_sport(self) -> List[Dict[str, Any]]:
        """Get aggregate statistics by sport."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    sport,
                    COUNT(*) as bet_count,
                    SUM(stake_gbp) as total_stake,
                    AVG(stake_gbp) as avg_stake,
                    AVG(price_delay_ms) as avg_delay
                FROM bets 
                GROUP BY sport
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_unique_customers(self) -> List[str]:
        """Get all unique customer IDs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT customer_id FROM bets ORDER BY customer_id")
            return [row["customer_id"] for row in cursor.fetchall()]
    
    def get_bet_count(self) -> int:
        """Get total number of bets."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM bets")
            return cursor.fetchone()["count"]
    
    # ==================== SEMANTIC SEARCH ====================
    
    def load_embeddings_to_memory(self):
        """
        Load all embeddings into FAISS vector stores for fast similarity search.
        
        Loads three sets of embeddings:
        - Document embeddings: for broad semantic search
        - Team1 embeddings: first team/player (precise team search)
        - Team2 embeddings: second team/player (precise team search)
        
        Uses FAISS for efficient O(log N) approximate nearest neighbor search.
        Falls back to brute force if FAISS is not installed.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check which columns exist (backwards compatibility)
            cursor.execute("PRAGMA table_info(embeddings)")
            columns = {row['name'] for row in cursor.fetchall()}
            has_content_hash = 'content_hash' in columns
            has_team1_embedding = 'team1_embedding' in columns
            has_team2_embedding = 'team2_embedding' in columns
            
            # Build SELECT clause based on available columns
            select_cols = ["bet_id", "embedding"]
            if has_content_hash:
                select_cols.append("content_hash")
            if has_team1_embedding:
                select_cols.append("team1_embedding")
            if has_team2_embedding:
                select_cols.append("team2_embedding")
            
            cursor.execute(f"SELECT {', '.join(select_cols)} FROM embeddings ORDER BY bet_id")
            rows = cursor.fetchall()
            
            if not rows:
                self._vector_store.clear()
                self._team1_vector_store.clear()
                self._team2_vector_store.clear()
                self._bet_ids = []
                return
            
            self._bet_ids = [row["bet_id"] for row in rows]
            
            # Validate embedding dimensions before loading
            first_embedding = np.frombuffer(rows[0]["embedding"], dtype=np.float32)
            actual_dim = len(first_embedding)
            expected_dim = EMBEDDING_DIMENSIONS
            
            if actual_dim != expected_dim:
                stored_config = self.get_embedding_config()
                if stored_config:
                    raise ValueError(
                        f"Embedding dimension mismatch!\n"
                        f"  Stored embeddings: {actual_dim} dimensions (model: {stored_config['model']})\n"
                        f"  Expected (config): {expected_dim} dimensions\n"
                        f"  Stored at: {stored_config['created_at']}\n"
                        f"  Solution: Delete the database and re-ingest with the current model."
                    )
                else:
                    raise ValueError(
                        f"Embedding dimension mismatch!\n"
                        f"  Stored embeddings: {actual_dim} dimensions\n"
                        f"  Expected (config): {expected_dim} dimensions\n"
                        f"  Solution: Delete the database and re-ingest."
                    )
            
            # Load document embeddings
            bet_ids = [row["bet_id"] for row in rows]
            embeddings = np.vstack([
                np.frombuffer(row["embedding"], dtype=np.float32)
                for row in rows
            ])
            
            content_hashes = [row["content_hash"] or "" for row in rows] if has_content_hash else ["" for _ in rows]
            
            self._vector_store.clear()
            self._vector_store.add_batch(bet_ids, embeddings, content_hashes)
            
            # Load team1 embeddings if available
            self._team1_vector_store.clear()
            if has_team1_embedding:
                team1_embeddings_list = []
                valid_bet_ids = []
                for row in rows:
                    if row["team1_embedding"]:
                        team1_embeddings_list.append(
                            np.frombuffer(row["team1_embedding"], dtype=np.float32)
                        )
                        valid_bet_ids.append(row["bet_id"])
                
                if team1_embeddings_list:
                    team1_embeddings = np.vstack(team1_embeddings_list)
                    self._team1_vector_store.add_batch(
                        valid_bet_ids, 
                        team1_embeddings, 
                        ["" for _ in valid_bet_ids]
                    )
            
            # Load team2 embeddings if available
            self._team2_vector_store.clear()
            if has_team2_embedding:
                team2_embeddings_list = []
                valid_bet_ids = []
                for row in rows:
                    if row["team2_embedding"]:
                        # Check for non-zero embedding (team2 may be empty for some events)
                        emb = np.frombuffer(row["team2_embedding"], dtype=np.float32)
                        if np.any(emb != 0):
                            team2_embeddings_list.append(emb)
                            valid_bet_ids.append(row["bet_id"])
                
                if team2_embeddings_list:
                    team2_embeddings = np.vstack(team2_embeddings_list)
                    self._team2_vector_store.add_batch(
                        valid_bet_ids, 
                        team2_embeddings, 
                        ["" for _ in valid_bet_ids]
                    )
    
    def semantic_search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[Tuple[str, float]]:
        """
        Find most similar bets using cosine similarity via FAISS.
        
        Args:
            query_embedding: The embedding vector to search with
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of (bet_id, similarity_score) tuples
        """
        if self._vector_store.size() == 0:
            self.load_embeddings_to_memory()
        
        if self._vector_store.size() == 0:
            return []
        
        # Use FAISS vector store for efficient search
        results = self._vector_store.search(query_embedding, top_k=top_k)
        
        # Filter by threshold
        return [(bet_id, score) for bet_id, score in results if score >= threshold]
    
    def semantic_search_teams(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[Tuple[str, float]]:
        """
        Search using team-level embeddings (both team1 and team2).
        
        This is the most precise search for team/player names - it searches
        each team individually, handling misspellings well because embeddings
        for "Raptors" and "Rapters" are close in vector space.
        
        Args:
            query_embedding: The embedding vector to search with
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of (bet_id, max_similarity_score) tuples
        """
        if self._team1_vector_store.size() == 0:
            self.load_embeddings_to_memory()
        
        # Search both team stores
        team1_results = self._team1_vector_store.search(query_embedding, top_k=top_k * 2) if self._team1_vector_store.size() > 0 else []
        team2_results = self._team2_vector_store.search(query_embedding, top_k=top_k * 2) if self._team2_vector_store.size() > 0 else []
        
        # Merge results, taking the MAX score for each bet_id
        # (if query matches team1 OR team2, we want that bet)
        scores = {}
        for bet_id, score in team1_results:
            scores[bet_id] = max(scores.get(bet_id, 0.0), score)
        for bet_id, score in team2_results:
            scores[bet_id] = max(scores.get(bet_id, 0.0), score)
        
        # Filter by threshold and sort
        results = [(bet_id, score) for bet_id, score in scores.items() if score >= threshold]
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def semantic_search_dual(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        threshold: float = 0.0,
        team_weight: float = 0.7
    ) -> List[Tuple[str, float]]:
        """
        Search using both document and team-level embeddings, merging results.
        
        This provides the best recall by combining:
        - Document embeddings: captures broad semantic meaning
        - Team embeddings: precise matching for team/player names with misspelling tolerance
        
        Args:
            query_embedding: The embedding vector to search with
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)
            team_weight: Weight for team embedding scores (0-1), rest goes to document
            
        Returns:
            List of (bet_id, combined_score) tuples, sorted by score descending
        """
        if self._vector_store.size() == 0:
            self.load_embeddings_to_memory()
        
        # Search document store
        doc_results = self._vector_store.search(query_embedding, top_k=top_k * 2)
        doc_scores = {bet_id: score for bet_id, score in doc_results}
        
        # Search team stores (get MAX of team1 and team2 for each bet)
        team_scores = {}
        if self._team1_vector_store.size() > 0:
            for bet_id, score in self._team1_vector_store.search(query_embedding, top_k=top_k * 2):
                team_scores[bet_id] = max(team_scores.get(bet_id, 0.0), score)
        if self._team2_vector_store.size() > 0:
            for bet_id, score in self._team2_vector_store.search(query_embedding, top_k=top_k * 2):
                team_scores[bet_id] = max(team_scores.get(bet_id, 0.0), score)
        
        # Combine all bet_ids
        all_bet_ids = set(doc_scores.keys()) | set(team_scores.keys())
        
        combined = []
        doc_weight = 1.0 - team_weight
        
        for bet_id in all_bet_ids:
            doc_score = doc_scores.get(bet_id, 0.0)
            team_score = team_scores.get(bet_id, 0.0)
            
            # Weighted combination - team embeddings get higher weight for name searches
            combined_score = doc_weight * doc_score + team_weight * team_score
            
            if combined_score >= threshold:
                combined.append((bet_id, combined_score))
        
        # Sort by combined score
        combined.sort(key=lambda x: x[1], reverse=True)
        return combined[:top_k]
    
    def hybrid_search(
        self,
        query_embedding: np.ndarray,
        filters: Dict[str, Any],
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Hybrid search combining semantic similarity with structured filters.
        
        Strategy:
        1. SQL filter first (efficient structured filtering)
        2. If embeddings available: rank by semantic similarity
        3. If no embeddings: return by recency (bet_id DESC) as explicit fallback
        
        NOTE: We removed the unused `semantic_weight` parameter. If weighted
        scoring is needed in the future, implement it explicitly with:
        - final_score = semantic_weight * semantic_score + (1 - semantic_weight) * sql_score
        - This requires defining what "sql_score" means for your use case
        """
        # Get filtered bets via SQL
        filtered_bets = self.advanced_filter(**filters)
        
        if not filtered_bets:
            return []
        
        # Get bet IDs that passed the filter
        filtered_ids = {bet.bet_id for bet in filtered_bets}
        
        # Ensure embeddings are loaded
        if self._vector_store.size() == 0:
            self.load_embeddings_to_memory()
        
        if self._vector_store.size() == 0:
            # No embeddings available - return by bet_id descending (most recent first)
            # This is explicit about the ordering rather than arbitrary
            sorted_bets = sorted(filtered_bets, key=lambda b: b.bet_id, reverse=True)
            return [
                RetrievalResult(
                    bet=bet, 
                    score=None, 
                    match_type="filtered_no_embeddings"  # Explicit about no semantic ranking
                )
                for bet in sorted_bets[:top_k]
            ]
        
        # Use FAISS filtered search - efficient for any filter size
        search_results = self._vector_store.search(
            query_embedding, 
            top_k=top_k, 
            filter_ids=filtered_ids
        )
        
        # Build result objects - O(n) dict creation + O(k) lookups = O(n+k)
        bet_map = {bet.bet_id: bet for bet in filtered_bets}
        results = []
        for bet_id, score in search_results:
            if bet_id in bet_map:
                results.append(RetrievalResult(
                    bet=bet_map[bet_id],
                    score=score,
                    match_type="hybrid"
                ))
        
        return results
    
    def find_stale_embeddings(self) -> List[str]:
        """
        Find bets whose embeddings are stale due to document content changes.
        
        This checks the content_hash stored with each embedding against
        the current document representation. If they differ, the embedding
        is stale and should be regenerated.
        
        Returns:
            List of bet_ids that need re-embedding
        """
        stale_ids = []
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all bets with their current documents and stored hashes
            cursor.execute("""
                SELECT b.bet_id, b.document, e.content_hash
                FROM bets b
                LEFT JOIN embeddings e ON b.bet_id = e.bet_id
            """)
            
            for row in cursor.fetchall():
                bet_id = row["bet_id"]
                document = row["document"]
                stored_hash = row["content_hash"]
                
                if stored_hash is None:
                    # No embedding exists
                    stale_ids.append(bet_id)
                else:
                    # Check if content changed
                    current_hash = compute_content_hash(document)
                    if current_hash != stored_hash:
                        stale_ids.append(bet_id)
        
        return stale_ids
    
    # ==================== HELPER METHODS ====================
    
    def _row_to_bet(self, row: sqlite3.Row) -> Bet:
        """
        Convert a database row to a Bet object.
        
        Converts stake from REAL to Decimal for exact currency handling.
        """
        return Bet(
            bet_id=row["bet_id"],
            customer_id=row["customer_id"],
            sport=row["sport"],
            event_name=row["event_name"],
            market=row["market"],
            selection=row["selection"],
            stake_gbp=to_decimal(row["stake_gbp"]),  # Convert to Decimal
            status=row["status"],
            incident_tag=row["incident_tag"],
            price_delay_ms=row["price_delay_ms"],
            stored_document=row["document"]  # Include the stored document text
        )
    
    def get_customer_stats(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get complete aggregated statistics for a customer via SQL."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    customer_id,
                    COUNT(*) as total_bets,
                    SUM(stake_gbp) as total_stake,
                    AVG(stake_gbp) as avg_stake,
                    AVG(price_delay_ms) as avg_delay,
                    MIN(price_delay_ms) as min_delay,
                    MAX(price_delay_ms) as max_delay
                FROM bets 
                WHERE customer_id = ?
                GROUP BY customer_id
            """, (customer_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            # Get status breakdown
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM bets WHERE customer_id = ? 
                GROUP BY status
            """, (customer_id,))
            status_breakdown = {r["status"]: r["count"] for r in cursor.fetchall()}
            
            # Get incident breakdown
            cursor.execute("""
                SELECT incident_tag, COUNT(*) as count 
                FROM bets WHERE customer_id = ? 
                GROUP BY incident_tag
            """, (customer_id,))
            incident_breakdown = {r["incident_tag"]: r["count"] for r in cursor.fetchall()}
            
            # Get sport breakdown
            cursor.execute("""
                SELECT sport, COUNT(*) as count 
                FROM bets WHERE customer_id = ? 
                GROUP BY sport
            """, (customer_id,))
            sport_breakdown = {r["sport"]: r["count"] for r in cursor.fetchall()}
            
            return {
                "customer_id": row["customer_id"],
                "total_bets": row["total_bets"],
                "total_stake": row["total_stake"],
                "avg_stake": row["avg_stake"],
                "avg_delay": row["avg_delay"],
                "min_delay": row["min_delay"],
                "max_delay": row["max_delay"],
                "status_breakdown": status_breakdown,
                "incident_breakdown": incident_breakdown,
                "sport_breakdown": sport_breakdown
            }
    
    def get_incident_stats(self, incident_tag: str) -> Optional[Dict[str, Any]]:
        """Get complete aggregated statistics for an incident type via SQL."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    incident_tag,
                    COUNT(*) as total_bets,
                    COUNT(DISTINCT customer_id) as unique_customers,
                    SUM(stake_gbp) as total_stake,
                    AVG(stake_gbp) as avg_stake,
                    AVG(price_delay_ms) as avg_delay,
                    MIN(price_delay_ms) as min_delay,
                    MAX(price_delay_ms) as max_delay
                FROM bets 
                WHERE incident_tag = ?
                GROUP BY incident_tag
            """, (incident_tag,))
            row = cursor.fetchone()
            if not row:
                return None
            
            # Get status breakdown
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM bets WHERE incident_tag = ? 
                GROUP BY status
            """, (incident_tag,))
            status_breakdown = {r["status"]: r["count"] for r in cursor.fetchall()}
            
            # Get customers ranked by impact (number of affected bets, then total delay)
            cursor.execute("""
                SELECT 
                    customer_id, 
                    COUNT(*) as bet_count,
                    SUM(price_delay_ms) as total_delay,
                    MAX(price_delay_ms) as max_delay
                FROM bets 
                WHERE incident_tag = ?
                GROUP BY customer_id
                ORDER BY bet_count DESC, total_delay DESC
            """, (incident_tag,))
            customers_affected = [
                {
                    "customer_id": r["customer_id"],
                    "bet_count": r["bet_count"],
                    "total_delay": r["total_delay"],
                    "max_delay": r["max_delay"]
                }
                for r in cursor.fetchall()
            ]
            
            return {
                "incident_tag": row["incident_tag"],
                "total_bets": row["total_bets"],
                "unique_customers": row["unique_customers"],
                "total_stake": row["total_stake"],
                "avg_stake": row["avg_stake"],
                "avg_delay": row["avg_delay"],
                "min_delay": row["min_delay"],
                "max_delay": row["max_delay"],
                "status_breakdown": status_breakdown,
                "customers_affected": customers_affected
            }
    
    def get_status_stats(self, status: str) -> Optional[Dict[str, Any]]:
        """Get complete aggregated statistics for a status via SQL."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    status,
                    COUNT(*) as total_bets,
                    COUNT(DISTINCT customer_id) as unique_customers,
                    SUM(stake_gbp) as total_stake,
                    AVG(stake_gbp) as avg_stake,
                    AVG(price_delay_ms) as avg_delay
                FROM bets 
                WHERE status = ?
                GROUP BY status
            """, (status,))
            row = cursor.fetchone()
            if not row:
                return None
            
            # Get incident breakdown for this status
            cursor.execute("""
                SELECT incident_tag, COUNT(*) as count 
                FROM bets WHERE status = ? 
                GROUP BY incident_tag
            """, (status,))
            incident_breakdown = {r["incident_tag"]: r["count"] for r in cursor.fetchall()}
            
            return {
                "status": row["status"],
                "total_bets": row["total_bets"],
                "unique_customers": row["unique_customers"],
                "total_stake": row["total_stake"],
                "avg_stake": row["avg_stake"],
                "avg_delay": row["avg_delay"],
                "incident_breakdown": incident_breakdown
            }
    
    def get_top_delay_stats(self, limit: int = 10) -> Dict[str, Any]:
        """Get statistics for top N highest delay bets via SQL."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get aggregate stats for top N
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as count,
                    SUM(stake_gbp) as total_stake,
                    AVG(price_delay_ms) as avg_delay,
                    MIN(price_delay_ms) as min_delay,
                    MAX(price_delay_ms) as max_delay
                FROM (
                    SELECT * FROM bets 
                    ORDER BY price_delay_ms DESC 
                    LIMIT ?
                )
            """, (limit,))
            row = cursor.fetchone()
            
            # Get incident breakdown for top N
            cursor.execute(f"""
                SELECT incident_tag, COUNT(*) as count 
                FROM (
                    SELECT * FROM bets 
                    ORDER BY price_delay_ms DESC 
                    LIMIT ?
                )
                GROUP BY incident_tag
            """, (limit,))
            incident_breakdown = {r["incident_tag"]: r["count"] for r in cursor.fetchall()}
            
            # Get status breakdown for top N
            cursor.execute(f"""
                SELECT status, COUNT(*) as count 
                FROM (
                    SELECT * FROM bets 
                    ORDER BY price_delay_ms DESC 
                    LIMIT ?
                )
                GROUP BY status
            """, (limit,))
            status_breakdown = {r["status"]: r["count"] for r in cursor.fetchall()}
            
            return {
                "limit": limit,
                "total_stake": row["total_stake"],
                "avg_delay": row["avg_delay"],
                "min_delay": row["min_delay"],
                "max_delay": row["max_delay"],
                "incident_breakdown": incident_breakdown,
                "status_breakdown": status_breakdown
            }

    def text_search(self, query: str, limit: int = 10) -> List[Bet]:
        """
        Simple text search across event_name, market, and selection.
        Uses SQLite LIKE for basic matching.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT * FROM bets 
                WHERE event_name LIKE ? 
                   OR market LIKE ?
                   OR selection LIKE ?
                   OR bet_id LIKE ?
                   OR customer_id LIKE ?
                ORDER BY bet_id
                LIMIT ?
            """, (search_pattern, search_pattern, search_pattern, 
                  search_pattern, search_pattern, limit))
            return [self._row_to_bet(row) for row in cursor.fetchall()]
