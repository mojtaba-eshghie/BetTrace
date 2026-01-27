"""
Centralized Embedding Service for the Sportsbook RAG Assistant.

This module provides a single, shared embedding service with:
- Singleton pattern for shared OpenAI client
- LRU caching to avoid re-embedding identical texts
- Exponential backoff retry for API failures
- Batch processing for bulk embeddings

Usage:
    from src.embedding_service import get_embedding_service
    
    service = get_embedding_service()
    embedding = service.embed_text("some text")
    embeddings = service.embed_batch(["text1", "text2", "text3"])
"""

import time
import hashlib
from functools import lru_cache
from typing import List, Optional
import numpy as np
from openai import OpenAI, RateLimitError, APIError, APIConnectionError

from .config import OPENAI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, validate_config


class EmbeddingService:
    """
    Centralized embedding service with caching and retry logic.
    
    Features:
    - Single OpenAI client instance (lazy initialization)
    - LRU cache for individual embeddings (avoids re-embedding same text)
    - Exponential backoff retry for transient failures
    - Batch processing with progress reporting
    """
    
    # Retry configuration
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds
    MAX_DELAY = 60.0  # seconds
    
    # Cache configuration
    CACHE_SIZE = 1000  # Max number of cached embeddings
    
    def __init__(self):
        """Initialize the embedding service."""
        self._client: Optional[OpenAI] = None
        self._cache: dict = {}  # text_hash -> embedding
    
    @property
    def client(self) -> OpenAI:
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            validate_config()
            self._client = OpenAI(api_key=OPENAI_API_KEY)
        return self._client
    
    def _text_hash(self, text: str) -> str:
        """Generate a hash for cache key."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Execute a function with exponential backoff retry.
        
        Retries on:
        - RateLimitError (429)
        - APIConnectionError (network issues)
        - APIError (5xx server errors)
        """
        last_exception = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except RateLimitError as e:
                last_exception = e
                delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                print(f"  ⚠ Rate limited. Retrying in {delay:.1f}s (attempt {attempt + 1}/{self.MAX_RETRIES})")
                time.sleep(delay)
            except APIConnectionError as e:
                last_exception = e
                delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                print(f"  ⚠ Connection error. Retrying in {delay:.1f}s (attempt {attempt + 1}/{self.MAX_RETRIES})")
                time.sleep(delay)
            except APIError as e:
                # Only retry on 5xx errors
                if hasattr(e, 'status_code') and e.status_code >= 500:
                    last_exception = e
                    delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                    print(f"  ⚠ Server error ({e.status_code}). Retrying in {delay:.1f}s (attempt {attempt + 1}/{self.MAX_RETRIES})")
                    time.sleep(delay)
                else:
                    raise  # Don't retry 4xx errors
        
        # All retries exhausted
        raise last_exception
    
    def embed_text(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            use_cache: Whether to use/update cache (default: True)
            
        Returns:
            NumPy array of shape (EMBEDDING_DIMENSIONS,)
        """
        # Check cache first
        if use_cache:
            text_hash = self._text_hash(text)
            if text_hash in self._cache:
                return self._cache[text_hash]
        
        # Generate embedding with retry
        def _call_api():
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            return np.array(response.data[0].embedding, dtype=np.float32)
        
        embedding = self._retry_with_backoff(_call_api)
        
        # Update cache (with LRU-like eviction)
        if use_cache:
            if len(self._cache) >= self.CACHE_SIZE:
                # Remove oldest entry (first key)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[text_hash] = embedding
        
        return embedding
    
    def embed_batch(
        self, 
        texts: List[str], 
        batch_size: int = 100,
        use_cache: bool = True,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Uses caching to skip already-embedded texts, then batches
        the remaining texts for efficient API calls.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (max 2048 for OpenAI)
            use_cache: Whether to use/update cache
            show_progress: Whether to print progress updates
            
        Returns:
            NumPy array of shape (len(texts), EMBEDDING_DIMENSIONS)
        """
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, EMBEDDING_DIMENSIONS)
        
        # Separate cached and uncached texts
        embeddings = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []
        
        if use_cache:
            for i, text in enumerate(texts):
                text_hash = self._text_hash(text)
                if text_hash in self._cache:
                    embeddings[i] = self._cache[text_hash]
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(text)
            
            if show_progress and len(texts) - len(uncached_texts) > 0:
                print(f"  → Using cached embeddings for {len(texts) - len(uncached_texts)}/{len(texts)} texts")
        else:
            uncached_indices = list(range(len(texts)))
            uncached_texts = texts
        
        # Batch process uncached texts
        if uncached_texts:
            for batch_start in range(0, len(uncached_texts), batch_size):
                batch_end = min(batch_start + batch_size, len(uncached_texts))
                batch = uncached_texts[batch_start:batch_end]
                
                def _call_api():
                    response = self.client.embeddings.create(
                        model=EMBEDDING_MODEL,
                        input=batch
                    )
                    return [np.array(item.embedding, dtype=np.float32) for item in response.data]
                
                batch_embeddings = self._retry_with_backoff(_call_api)
                
                # Store results and update cache
                for j, emb in enumerate(batch_embeddings):
                    idx = uncached_indices[batch_start + j]
                    embeddings[idx] = emb
                    
                    if use_cache:
                        text_hash = self._text_hash(uncached_texts[batch_start + j])
                        if len(self._cache) >= self.CACHE_SIZE:
                            oldest_key = next(iter(self._cache))
                            del self._cache[oldest_key]
                        self._cache[text_hash] = emb
                
                if show_progress:
                    total_done = sum(1 for e in embeddings if e is not None)
                    print(f"  → Generated embeddings for {total_done}/{len(texts)} documents")
        
        result = np.array(embeddings, dtype=np.float32)
        
        # Validate dimensions
        if result.shape[1] != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Embedding dimension mismatch!\n"
                f"  Model '{EMBEDDING_MODEL}' produced: {result.shape[1]} dimensions\n"
                f"  Config EMBEDDING_DIMENSIONS: {EMBEDDING_DIMENSIONS}\n"
                f"  Solution: Update EMBEDDING_DIMENSIONS in config.py to {result.shape[1]}"
            )
        
        return result
    
    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()
    
    def cache_stats(self) -> dict:
        """Return cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.CACHE_SIZE
        }


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get the singleton EmbeddingService instance.
    
    This ensures all parts of the application share the same
    OpenAI client and embedding cache.
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
