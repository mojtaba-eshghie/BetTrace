"""
Database layer for the Sportsbook RAG Assistant.

Provides hybrid storage combining:
- SQLite for structured data (exact lookups, filtering, aggregations)
- NumPy-based vector store for embeddings (semantic search)
"""

import sqlite3
import json
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from contextlib import contextmanager

from .models import Bet, RetrievalResult
from .config import DATABASE_PATH, EMBEDDING_DIMENSIONS


class Database:
    """
    Hybrid database combining SQLite for structured data
    and in-memory vector storage for embeddings.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the database connection."""
        self.db_path = db_path or DATABASE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Vector storage (in-memory for this small dataset)
        self._embeddings: Optional[np.ndarray] = None
        self._bet_ids: List[str] = []
        
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
            
            # Embeddings table (stored as JSON blob for simplicity)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    bet_id TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    FOREIGN KEY (bet_id) REFERENCES bets(bet_id)
                )
            """)
            
            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_id ON bets(customer_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sport ON bets(sport)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON bets(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_incident_tag ON bets(incident_tag)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_delay ON bets(price_delay_ms)")
    
    def clear(self):
        """Clear all data from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM embeddings")
            cursor.execute("DELETE FROM bets")
        self._embeddings = None
        self._bet_ids = []
    
    # ==================== INSERT OPERATIONS ====================
    
    def insert_bet(self, bet: Bet, embedding: Optional[np.ndarray] = None):
        """Insert a single bet with optional embedding."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert bet record
            cursor.execute("""
                INSERT OR REPLACE INTO bets 
                (bet_id, customer_id, sport, event_name, market, selection,
                 stake_gbp, status, incident_tag, price_delay_ms, document)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bet.bet_id, bet.customer_id, bet.sport, bet.event_name,
                bet.market, bet.selection, bet.stake_gbp, bet.status,
                bet.incident_tag, bet.price_delay_ms, bet.to_document()
            ))
            
            # Insert embedding if provided
            if embedding is not None:
                cursor.execute("""
                    INSERT OR REPLACE INTO embeddings (bet_id, embedding)
                    VALUES (?, ?)
                """, (bet.bet_id, embedding.tobytes()))
    
    def insert_bets_batch(self, bets: List[Bet], embeddings: Optional[np.ndarray] = None):
        """Insert multiple bets with optional embeddings (batch operation)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Batch insert bets
            bet_data = [
                (b.bet_id, b.customer_id, b.sport, b.event_name, b.market,
                 b.selection, b.stake_gbp, b.status, b.incident_tag,
                 b.price_delay_ms, b.to_document())
                for b in bets
            ]
            cursor.executemany("""
                INSERT OR REPLACE INTO bets 
                (bet_id, customer_id, sport, event_name, market, selection,
                 stake_gbp, status, incident_tag, price_delay_ms, document)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, bet_data)
            
            # Batch insert embeddings if provided
            if embeddings is not None:
                embedding_data = [
                    (bets[i].bet_id, embeddings[i].tobytes())
                    for i in range(len(bets))
                ]
                cursor.executemany("""
                    INSERT OR REPLACE INTO embeddings (bet_id, embedding)
                    VALUES (?, ?)
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
        """Load all embeddings into memory for fast similarity search."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT bet_id, embedding FROM embeddings ORDER BY bet_id")
            rows = cursor.fetchall()
            
            if not rows:
                self._embeddings = None
                self._bet_ids = []
                return
            
            self._bet_ids = [row["bet_id"] for row in rows]
            embeddings_list = [
                np.frombuffer(row["embedding"], dtype=np.float32)
                for row in rows
            ]
            self._embeddings = np.vstack(embeddings_list)
    
    def semantic_search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[Tuple[str, float]]:
        """
        Find most similar bets using cosine similarity.
        
        Args:
            query_embedding: The embedding vector to search with
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of (bet_id, similarity_score) tuples
        """
        if self._embeddings is None:
            self.load_embeddings_to_memory()
        
        if self._embeddings is None or len(self._bet_ids) == 0:
            return []
        
        # Normalize query embedding
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        
        # Normalize stored embeddings (row-wise)
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        normalized_embeddings = self._embeddings / norms
        
        # Compute cosine similarities
        similarities = np.dot(normalized_embeddings, query_norm)
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Filter by threshold and return results
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= threshold:
                results.append((self._bet_ids[idx], score))
        
        return results
    
    def hybrid_search(
        self,
        query_embedding: np.ndarray,
        filters: Dict[str, Any],
        top_k: int = 10,
        semantic_weight: float = 0.5
    ) -> List[RetrievalResult]:
        """
        Hybrid search combining semantic similarity with structured filters.
        
        First applies structured filters, then ranks by semantic similarity.
        """
        # Get filtered bets
        filtered_bets = self.advanced_filter(**filters)
        
        if not filtered_bets:
            return []
        
        # Get bet IDs that passed the filter
        filtered_ids = {bet.bet_id for bet in filtered_bets}
        
        # Get semantic scores for filtered bets only
        if self._embeddings is None:
            self.load_embeddings_to_memory()
        
        if self._embeddings is None:
            # No embeddings, return filtered results without scores
            return [
                RetrievalResult(bet=bet, score=None, match_type="filtered")
                for bet in filtered_bets[:top_k]
            ]
        
        # Compute similarities for filtered bets only
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        
        results = []
        for i, bet_id in enumerate(self._bet_ids):
            if bet_id in filtered_ids:
                embedding = self._embeddings[i]
                embedding_norm = embedding / np.linalg.norm(embedding)
                score = float(np.dot(embedding_norm, query_norm))
                
                # Find the corresponding bet object
                bet = next(b for b in filtered_bets if b.bet_id == bet_id)
                results.append(RetrievalResult(
                    bet=bet,
                    score=score,
                    match_type="hybrid"
                ))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x.score or 0, reverse=True)
        return results[:top_k]
    
    # ==================== HELPER METHODS ====================
    
    def _row_to_bet(self, row: sqlite3.Row) -> Bet:
        """Convert a database row to a Bet object."""
        return Bet(
            bet_id=row["bet_id"],
            customer_id=row["customer_id"],
            sport=row["sport"],
            event_name=row["event_name"],
            market=row["market"],
            selection=row["selection"],
            stake_gbp=row["stake_gbp"],
            status=row["status"],
            incident_tag=row["incident_tag"],
            price_delay_ms=row["price_delay_ms"],
            stored_document=row["document"]  # Include the stored document text
        )
    
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
