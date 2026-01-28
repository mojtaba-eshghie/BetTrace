"""
Vector Store for the Sportsbook RAG Assistant.

Provides efficient vector storage and similarity search using FAISS.
Includes:
- FAISS indexing for O(log N) approximate nearest neighbor search
- Filtered vector search (pre-filter then search)
- Content hashing for embedding versioning
"""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Set, Any
import numpy as np
from .config import DEBUG_MODE
from rich.console import Console
console = Console()

# Try to import FAISS - fall back to brute force if not available
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("Warning: FAISS not installed. Using brute-force search (slower for large datasets).")
    print("Install with: pip install faiss-cpu")

from .config import EMBEDDING_DIMENSIONS


class VectorStore:
    """
    Scalable vector store with FAISS indexing.
    
    Key features:
    - Uses FAISS IndexFlatIP (Inner Product) for cosine similarity
    - Supports filtered search via ID mapping
    - Content hashing for embedding versioning
    
    Scalability:
    - For < 10K vectors: IndexFlatIP (exact search, O(N))
    - For > 10K vectors: Could upgrade to IndexIVFFlat (approximate, O(sqrt(N)))
    """
    
    def __init__(self, dimension: int = EMBEDDING_DIMENSIONS):
        self.dimension = dimension
        self._index: Optional[Any] = None  # FAISS index
        self._id_to_idx: Dict[str, int] = {}  # bet_id -> FAISS index position
        self._idx_to_id: Dict[int, str] = {}  # FAISS index position -> bet_id
        self._embeddings: Optional[np.ndarray] = None  # Fallback for non-FAISS
        self._content_hashes: Dict[str, str] = {}  # bet_id -> content hash
        
        if FAISS_AVAILABLE:
            # Use Inner Product index (equivalent to cosine sim for normalized vectors)
            self._index = faiss.IndexFlatIP(dimension)
    
    def add(
        self, 
        bet_id: str, 
        embedding: np.ndarray, 
        content_hash: str
    ) -> None:
        """Add a single embedding to the store."""
        if DEBUG_MODE:
            console.log(f"[red]DEBUG MODE: Adding embedding for bet_id:[/red] {bet_id}")
        if bet_id in self._id_to_idx:
            # Update existing
            idx = self._id_to_idx[bet_id]
            if FAISS_AVAILABLE:
                # FAISS doesn't support update - need to rebuild
                # For now, just update the hash
                # self._content_hashes[bet_id] = content_hash
                raise NotImplementedError("FAISS index update not implemented")
            else:
                self._embeddings[idx] = embedding
                self._content_hashes[bet_id] = content_hash
            return
        
        # Add new
        idx = len(self._id_to_idx)
        self._id_to_idx[bet_id] = idx
        self._idx_to_id[idx] = bet_id
        self._content_hashes[bet_id] = content_hash
        
        # Normalize embedding for cosine similarity
        norm = np.linalg.norm(embedding)
        # Let's avoid division by zero when turning the embeddings into unit vectors
        if norm > 0:
            embedding = embedding / norm
        
        embedding = embedding.astype(np.float32).reshape(1, -1)
        
        if FAISS_AVAILABLE:
            self._index.add(embedding)
        else:
            if self._embeddings is None:
                self._embeddings = embedding
            else:
                self._embeddings = np.vstack([self._embeddings, embedding])
    
    def add_batch(
        self, 
        bet_ids: List[str], 
        embeddings: np.ndarray,
        content_hashes: List[str]
    ) -> None:
        """Add multiple embeddings at once (more efficient)."""
        if DEBUG_MODE:
            console.log(f"[red]DEBUG MODE: Adding batch of embeddings (count: {len(bet_ids)})[/red]")
        if len(bet_ids) != embeddings.shape[0]:
            raise ValueError("Number of IDs must match number of embeddings")
        
        # Normalize all embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        normalized = (embeddings / norms).astype(np.float32)
        
        for i, (bet_id, content_hash) in enumerate(zip(bet_ids, content_hashes)):
            idx = len(self._id_to_idx)
            self._id_to_idx[bet_id] = idx
            self._idx_to_id[idx] = bet_id
            self._content_hashes[bet_id] = content_hash
        
        if FAISS_AVAILABLE:
            self._index.add(normalized)
        else:
            if self._embeddings is None:
                self._embeddings = normalized
            else:
                self._embeddings = np.vstack([self._embeddings, normalized])
    
    def search(
        self, 
        query_embedding: np.ndarray, 
        top_k: int = 10,
        filter_ids: Optional[Set[str]] = None
    ) -> List[Tuple[str, float]]:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter_ids: Optional set of bet_ids to restrict search to
            
        Returns:
            List of (bet_id, similarity_score) tuples
        """
        if DEBUG_MODE:
            console.log(f"[red]DEBUG MODE: Searching for top_k={top_k} similar vectors[/red]")
        if len(self._id_to_idx) == 0:
            return []
        
        # Normalize query
        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_embedding = query_embedding / norm
        query_embedding = query_embedding.astype(np.float32).reshape(1, -1) # to required data type for FAISS & also the 2D vector shape FAISS needs (.reshape(1, -1) is similar to arr.reshape(1, len(arr)))
         
        if filter_ids is not None:
            # Filtered search - get more results then filter
            return self._filtered_search(query_embedding, top_k, filter_ids)
        
        # Unfiltered search; by default we use this 
        if FAISS_AVAILABLE:
            # FAISS search
            k = min(top_k, self._index.ntotal)
            scores, indices = self._index.search(query_embedding, k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx in self._idx_to_id:
                    bet_id = self._idx_to_id[idx]
                    results.append((bet_id, float(score)))
            return results
        else:
            # Brute force fallback
            return self._brute_force_search(query_embedding, top_k)
    
    def _filtered_search(
        self, 
        query_embedding: np.ndarray, 
        top_k: int,
        filter_ids: Set[str]
    ) -> List[Tuple[str, float]]:
        """
        Perform filtered vector search.
        
        Strategy: For small filter sets, compute scores only for filtered IDs.
        For large filter sets, get more results from index and filter.
        """
        if DEBUG_MODE:
            console.log(f"[red]DEBUG MODE: Performing filtered search with filter_ids count={len(filter_ids)}[/red]")
        filter_indices = [self._id_to_idx[bid] for bid in filter_ids if bid in self._id_to_idx]
        
        if not filter_indices:
            return []
        
        if FAISS_AVAILABLE:
            # For filtered search with FAISS, we have two strategies:
            # 1. Small filter (<=100): Compute scores directly for filtered items
            # 2. Large filter: Search more results and filter
            
            if len(filter_indices) <= 100:
                # Strategy 1: Direct computation for small filter sets
                results = []
                for idx in filter_indices:
                    # Reconstruct the vector (FAISS IndexFlatIP supports this)
                    vec = self._index.reconstruct(idx)
                    score = float(np.dot(query_embedding.flatten(), vec)) # cosine similarity (for normalized vectors)
                    bet_id = self._idx_to_id[idx]
                    results.append((bet_id, score))
                
                # Sort by score descending
                results.sort(key=lambda x: x[1], reverse=True)
                return results[:top_k]
            else:
                # Strategy 2: Over-fetch and filter
                # Fetch 10x results to ensure we get enough after filtering
                fetch_k = min(top_k * 10, self._index.ntotal)
                scores, indices = self._index.search(query_embedding, fetch_k)
                
                filter_set = set(filter_indices)
                results = []
                for score, idx in zip(scores[0], indices[0]):
                    if idx in filter_set and idx in self._idx_to_id:
                        bet_id = self._idx_to_id[idx]
                        results.append((bet_id, float(score)))
                        if len(results) >= top_k:
                            break
                return results
        else:
            # Brute force with filtering
            filter_set = set(filter_indices)
            scores = np.dot(self._embeddings, query_embedding.T).flatten()
            
            # Only consider filtered indices
            filtered_scores = [(self._idx_to_id[i], scores[i]) 
                              for i in filter_set if i in self._idx_to_id]
            filtered_scores.sort(key=lambda x: x[1], reverse=True)
            return filtered_scores[:top_k]
    
    def _brute_force_search(
        self, 
        query_embedding: np.ndarray, 
        top_k: int
    ) -> List[Tuple[str, float]]:
        """Brute force search (O(N)) - fallback when FAISS not available."""
        if DEBUG_MODE:
            console.log(f"[red]DEBUG MODE: Performing brute-force search[/red]")
        scores = np.dot(self._embeddings, query_embedding.T).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if idx in self._idx_to_id:
                bet_id = self._idx_to_id[idx]
                results.append((bet_id, float(scores[idx])))
        return results
    
    def get_content_hash(self, bet_id: str) -> Optional[str]:
        """Get the stored content hash for a bet."""
        return self._content_hashes.get(bet_id)
    
    def needs_reembedding(self, bet_id: str, current_content: str) -> bool:
        """Check if a bet needs re-embedding due to content change."""
        if DEBUG_MODE:
            console.log(f"[red]DEBUG MODE: Checking if bet_id:[/red] {bet_id} [red]needs re-embedding[/red]")
        stored_hash = self.get_content_hash(bet_id)
        if stored_hash is None:
            return True  # New bet, needs embedding
        
        current_hash = compute_content_hash(current_content)
        return stored_hash != current_hash
    
    def get_stale_embeddings(self, bets_with_content: List[Tuple[str, str]]) -> List[str]:
        """
        Find bets whose embeddings are stale (content changed).
        
        Args:
            bets_with_content: List of (bet_id, current_document_content) tuples
            
        Returns:
            List of bet_ids that need re-embedding
        """
        if DEBUG_MODE:
            console.log(f"[red]DEBUG MODE: Checking for stale embeddings in batch (count: {len(bets_with_content)})[/red]")
        stale = []
        for bet_id, content in bets_with_content:
            if self.needs_reembedding(bet_id, content):
                stale.append(bet_id)
        return stale
    
    def size(self) -> int:
        """Return number of vectors in the store."""
        return len(self._id_to_idx)
    
    def clear(self) -> None:
        """Clear all vectors from the store."""
        if FAISS_AVAILABLE:
            self._index = faiss.IndexFlatIP(self.dimension)
        self._embeddings = None
        self._id_to_idx = {}
        self._idx_to_id = {}
        self._content_hashes = {}


def compute_content_hash(content: str) -> str:
    """
    Compute a hash of document content for versioning.
    
    This is used to detect when the document representation has changed,
    indicating that embeddings need to be regenerated.
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


class EmbeddingVersionManager:
    """
    Manages embedding versions in SQLite.
    
    Stores content hashes alongside embeddings to detect when
    re-embedding is needed due to document format changes.
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def ensure_schema(self) -> None:
        """Ensure the content_hash column exists in embeddings table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if content_hash column exists
            cursor.execute("PRAGMA table_info(embeddings)")
            columns = {row['name'] for row in cursor.fetchall()}
            
            if 'content_hash' not in columns:
                cursor.execute("""
                    ALTER TABLE embeddings 
                    ADD COLUMN content_hash TEXT
                """)
                conn.commit()
    
    def get_stored_hash(self, bet_id: str) -> Optional[str]:
        """Get the stored content hash for a bet."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT content_hash FROM embeddings WHERE bet_id = ?",
                (bet_id,)
            )
            row = cursor.fetchone()
            return row['content_hash'] if row else None
    
    def update_hash(self, bet_id: str, content_hash: str) -> None:
        """Update the content hash for a bet."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE embeddings SET content_hash = ? WHERE bet_id = ?",
                (content_hash, bet_id)
            )
            conn.commit()
    
    def find_stale_embeddings(self, bets_with_content: List[Tuple[str, str]]) -> List[str]:
        """
        Find bets whose embeddings are stale.
        
        Args:
            bets_with_content: List of (bet_id, document_content) tuples
            
        Returns:
            List of bet_ids needing re-embedding
        """
        if DEBUG_MODE:
            console.log(f"[red]DEBUG MODE: Checking for stale embeddings in batch (count: {len(bets_with_content)})[/red]")
        stale = []
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            for bet_id, content in bets_with_content:
                cursor.execute(
                    "SELECT content_hash FROM embeddings WHERE bet_id = ?",
                    (bet_id,)
                )
                row = cursor.fetchone()
                
                current_hash = compute_content_hash(content)
                
                if row is None:
                    # No embedding exists
                    stale.append(bet_id)
                elif row['content_hash'] is None or row['content_hash'] != current_hash:
                    # Hash mismatch - content changed
                    stale.append(bet_id)
        
        return stale
