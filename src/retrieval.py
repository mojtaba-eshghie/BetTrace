"""
Retrieval module for the Sportsbook RAG Assistant.

Provides high-level retrieval interface combining:
- Exact lookups (by bet_id, customer_id)
- Structured filtering (by status, incident, sport, etc.)
- Semantic search (using embeddings via shared EmbeddingService)
- Hybrid search (combining structured + semantic)
"""

import re
import numpy as np
from typing import List, Optional, Dict, Any, Tuple

from .config import (
    DEFAULT_TOP_K,
    SIMILARITY_THRESHOLD,
    VALID_SPORTS,
    VALID_STATUSES,
    VALID_INCIDENTS,
)
from .models import Bet, RetrievalResult, QueryContext
from .database import Database
from .embedding_service import get_embedding_service


class Retriever:
    """
    High-level retrieval interface for the RAG system.
    
    Supports multiple retrieval strategies:
    1. Exact match: Direct lookup by bet_id or customer_id
    2. Filtered: SQL-based filtering on structured columns
    3. Semantic: Embedding-based similarity search (via shared EmbeddingService)
    4. Hybrid: Combining structured filters with semantic ranking
    """
    
    def __init__(self, db: Database):
        """Initialize the retriever with a database connection."""
        self.db = db
        self._embedding_service = None
    
    @property
    def embedding_service(self):
        """Get the shared embedding service (lazy initialization)."""
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text using the shared EmbeddingService.
        
        Benefits:
        - Caching: Same query won't be re-embedded
        - Retry: Handles rate limits and transient errors
        - Shared client: Single connection pool across the app
        """
        return self.embedding_service.embed_text(text, use_cache=True)
    
    # ==================== EXACT LOOKUPS ====================
    
    def get_bet(self, bet_id: str) -> Optional[RetrievalResult]:
        """
        Retrieve a single bet by its ID.
        
        Args:
            bet_id: The bet identifier (e.g., "B0042")
            
        Returns:
            RetrievalResult if found, None otherwise
        """
        # Normalize bet_id format (e.g., "42" -> "B0042")
        normalized_id = self._normalize_bet_id(bet_id)
        
        bet = self.db.get_by_bet_id(normalized_id)
        if bet:
            return RetrievalResult(bet=bet, score=1.0, match_type="exact")
        return None
    
    def get_customer_bets(self, customer_id: str) -> List[RetrievalResult]:
        """
        Retrieve all bets for a customer.
        
        Args:
            customer_id: The customer identifier (e.g., "C029")
            
        Returns:
            List of RetrievalResults for the customer
        """
        # Normalize customer_id format
        normalized_id = self._normalize_customer_id(customer_id)
        
        bets = self.db.get_by_customer_id(normalized_id)
        return [
            RetrievalResult(bet=bet, score=1.0, match_type="exact")
            for bet in bets
        ]
    
    # ==================== FILTERED QUERIES ====================
    
    def filter_by_status(self, status: str) -> List[RetrievalResult]:
        """Get all bets with a specific status."""
        status = status.upper()
        if status not in VALID_STATUSES:
            return []
        
        bets = self.db.filter_by_status(status)
        return [
            RetrievalResult(bet=bet, match_type="filtered")
            for bet in bets
        ]
    
    def filter_by_incident(self, incident_tag: str) -> List[RetrievalResult]:
        """Get all bets with a specific incident tag."""
        incident_tag = incident_tag.upper()
        if incident_tag not in VALID_INCIDENTS:
            return []
        
        bets = self.db.filter_by_incident(incident_tag)
        return [
            RetrievalResult(bet=bet, match_type="filtered")
            for bet in bets
        ]
    
    def filter_by_sport(self, sport: str) -> List[RetrievalResult]:
        """Get all bets for a specific sport."""
        sport = sport.lower()
        if sport not in VALID_SPORTS:
            return []
        
        bets = self.db.filter_by_sport(sport)
        return [
            RetrievalResult(bet=bet, match_type="filtered")
            for bet in bets
        ]
    
    def get_top_by_delay(self, limit: int = 10) -> List[RetrievalResult]:
        """Get bets with highest price_delay_ms."""
        bets = self.db.get_top_by_delay(limit)
        return [
            RetrievalResult(bet=bet, match_type="filtered")
            for bet in bets
        ]
    
    def get_top_by_stake(self, limit: int = 10) -> List[RetrievalResult]:
        """Get bets with highest stakes."""
        bets = self.db.get_top_by_stake(limit)
        return [
            RetrievalResult(bet=bet, match_type="filtered")
            for bet in bets
        ]
    
    def filter_high_latency(self, threshold_ms: int = 1000) -> List[RetrievalResult]:
        """Get bets with latency above a threshold."""
        bets = self.db.filter_by_delay_range(min_ms=threshold_ms)
        return [
            RetrievalResult(bet=bet, match_type="filtered")
            for bet in bets
        ]
    
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
    ) -> List[RetrievalResult]:
        """
        Advanced multi-criteria filtering.
        """
        bets = self.db.advanced_filter(
            customer_ids=customer_ids,
            sports=sports,
            statuses=statuses,
            incident_tags=incident_tags,
            min_stake=min_stake,
            max_stake=max_stake,
            min_delay=min_delay,
            max_delay=max_delay,
            limit=limit
        )
        return [
            RetrievalResult(bet=bet, match_type="filtered")
            for bet in bets
        ]
    
    # ==================== SEMANTIC SEARCH ====================
    
    def semantic_search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        threshold: float = SIMILARITY_THRESHOLD
    ) -> List[RetrievalResult]:
        """
        Search for bets using semantic similarity.
        
        Args:
            query: Natural language query
            top_k: Number of results to return
            threshold: Minimum similarity score
            
        Returns:
            List of RetrievalResults ranked by similarity
        """
        # Generate embedding for the query
        query_embedding = self._get_embedding(query)
        
        # Search in vector store
        results = self.db.semantic_search(
            query_embedding=query_embedding,
            top_k=top_k,
            threshold=threshold
        )
        
        # Convert to RetrievalResults
        retrieval_results = []
        for bet_id, score in results:
            bet = self.db.get_by_bet_id(bet_id)
            if bet:
                retrieval_results.append(RetrievalResult(
                    bet=bet,
                    score=score,
                    match_type="semantic"
                ))
        
        return retrieval_results
    
    # ==================== HYBRID SEARCH ====================
    
    def hybrid_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = DEFAULT_TOP_K
    ) -> List[RetrievalResult]:
        """
        Hybrid search combining semantic similarity with structured filters.
        
        Args:
            query: Natural language query for semantic matching
            filters: Dict of structured filters to apply first
            top_k: Number of results to return
            
        Returns:
            List of RetrievalResults
        """
        # Generate query embedding
        query_embedding = self._get_embedding(query)
        
        # Apply hybrid search
        filters = filters or {}
        results = self.db.hybrid_search(
            query_embedding=query_embedding,
            filters=filters,
            top_k=top_k
        )
        
        return results
    
    # ==================== TEXT SEARCH ====================
    
    def text_search(self, query: str, limit: int = 10) -> List[RetrievalResult]:
        """
        Simple text search using SQL LIKE matching.
        Good for searching event names, markets, etc.
        """
        bets = self.db.text_search(query, limit)
        return [
            RetrievalResult(bet=bet, match_type="text")
            for bet in bets
        ]
    
    # ==================== AGGREGATION QUERIES ====================
    
    def get_customers_affected_by_incident(
        self, 
        incident_tag: str
    ) -> List[Tuple[str, int, List[Bet]]]:
        """
        Get customers affected by a specific incident.
        
        Returns:
            List of (customer_id, bet_count, bets) tuples
        """
        incident_tag = incident_tag.upper()
        customer_counts = self.db.get_customers_by_incident(incident_tag)
        
        results = []
        for customer_id, count in customer_counts:
            # Get the actual bets for this customer with this incident
            bets = self.db.advanced_filter(
                customer_ids=[customer_id],
                incident_tags=[incident_tag]
            )
            results.append((customer_id, count, bets))
        
        return results
    
    def get_incident_summary(self, incident_tag: str) -> Dict[str, Any]:
        """
        Get a summary of bets affected by an incident.
        """
        incident_tag = incident_tag.upper()
        bets = self.db.filter_by_incident(incident_tag)
        
        if not bets:
            return {"incident": incident_tag, "count": 0}
        
        # Calculate statistics
        stakes = [b.stake_gbp for b in bets]
        delays = [b.price_delay_ms for b in bets]
        statuses = {}
        customers = set()
        
        for bet in bets:
            statuses[bet.status] = statuses.get(bet.status, 0) + 1
            customers.add(bet.customer_id)
        
        return {
            "incident": incident_tag,
            "count": len(bets),
            "customers_affected": len(customers),
            "total_stake": sum(stakes),
            "avg_stake": sum(stakes) / len(stakes),
            "avg_delay_ms": sum(delays) / len(delays),
            "max_delay_ms": max(delays),
            "status_breakdown": statuses,
            "bet_ids": [b.bet_id for b in bets]
        }
    
    # ==================== SMART RETRIEVAL ====================
    
    def retrieve(
        self,
        query: str,
        context: Optional[QueryContext] = None,
        top_k: int = DEFAULT_TOP_K
    ) -> List[RetrievalResult]:
        """
        Smart retrieval that automatically chooses the best strategy.
        
        This method analyzes the query and context to determine
        the optimal retrieval approach.
        
        Args:
            query: The user's query
            context: Optional query context with filters
            top_k: Maximum results to return
            
        Returns:
            List of RetrievalResults
        """
        # Check for specific bet ID in query
        bet_id_match = self._extract_bet_id(query)
        if bet_id_match:
            result = self.get_bet(bet_id_match)
            return [result] if result else []
        
        # Check for customer ID in query
        customer_id_match = self._extract_customer_id(query)
        if customer_id_match:
            return self.get_customer_bets(customer_id_match)
        
        # Check for incident tag in query
        incident_match = self._extract_incident_tag(query)
        if incident_match:
            return self.filter_by_incident(incident_match)
        
        # Check for status in query
        status_match = self._extract_status(query)
        if status_match:
            return self.filter_by_status(status_match)
        
        # Check for sport in query
        sport_match = self._extract_sport(query)
        
        # Check for high latency keywords
        if self._is_latency_query(query):
            if "top" in query.lower() or "highest" in query.lower():
                limit = self._extract_number(query) or 5
                return self.get_top_by_delay(limit)
            return self.filter_high_latency()
        
        # If we have context with filters, use hybrid search
        if context and context.has_filters():
            filters = {
                "customer_ids": context.customer_ids,
                "sports": context.sports,
                "statuses": context.statuses,
                "incident_tags": context.incident_tags,
                "min_stake": context.min_stake,
                "max_stake": context.max_stake,
                "min_delay": context.min_delay,
                "max_delay": context.max_delay,
            }
            # Remove None values
            filters = {k: v for k, v in filters.items() if v is not None}
            return self.hybrid_search(query, filters, top_k)
        
        # Default to semantic search
        return self.semantic_search(query, top_k)
    
    # ==================== HELPER METHODS ====================
    
    def _normalize_bet_id(self, bet_id: str) -> str:
        """
        Normalize bet ID format.
        
        Examples:
            '42' -> 'B0042'
            'B42' -> 'B0042'
            'B00042' -> 'B0042'  (extra zeros stripped)
            'b0042' -> 'B0042'
        """
        bet_id = bet_id.upper().strip()
        if bet_id.startswith("B"):
            num = bet_id[1:].lstrip('0') or '0'
        else:
            num = bet_id.lstrip('0') or '0'
        return f"B{num.zfill(4)}"
    
    def _normalize_customer_id(self, customer_id: str) -> str:
        """
        Normalize customer ID format.
        
        Examples:
            '29' -> 'C029'
            'C29' -> 'C029'
            'C0029' -> 'C029'  (extra zero stripped)
            'c029' -> 'C029'
        """
        customer_id = customer_id.upper().strip()
        if customer_id.startswith("C"):
            num = customer_id[1:].lstrip('0') or '0'
        else:
            num = customer_id.lstrip('0') or '0'
        return f"C{num.zfill(3)}"
    
    def _extract_bet_id(self, text: str) -> Optional[str]:
        """Extract first bet ID from text (for backwards compatibility)."""
        all_ids = self._extract_all_bet_ids(text)
        return all_ids[0] if all_ids else None
    
    def _extract_all_bet_ids(self, text: str) -> List[str]:
        """Extract ALL bet IDs from text."""
        bet_ids = []
        
        # Find all explicit bet ID patterns (B0042, B042, B42, B00042)
        # Allow up to 5 digits to handle typos with extra zeros
        explicit_matches = re.findall(r'\b[Bb](\d{1,5})\b', text)
        for match in explicit_matches:
            # Normalize: strip leading zeros, then pad to 4 digits
            # B00042 → 42 → B0042
            # B42 → 42 → B0042
            num = match.lstrip('0') or '0'  # Handle edge case of '0000'
            bet_ids.append(f"B{num.zfill(4)}")
        
        # Also check for "bet X" patterns without B prefix
        if "bet" in text.lower():
            # Find "bet 42" or "bets 1, 2, 3" patterns
            bet_number_matches = re.findall(r'bets?\s+(\d{1,5})', text.lower())
            for match in bet_number_matches:
                num = match.lstrip('0') or '0'
                bid = f"B{num.zfill(4)}"
                if bid not in bet_ids:
                    bet_ids.append(bid)
        
        return bet_ids
    
    def _extract_customer_id(self, text: str) -> Optional[str]:
        """Extract first customer ID from text (for backwards compatibility)."""
        all_ids = self._extract_all_customer_ids(text)
        return all_ids[0] if all_ids else None
    
    def _extract_all_customer_ids(self, text: str) -> List[str]:
        """Extract ALL customer IDs from text."""
        customer_ids = []
        
        # Find all explicit customer ID patterns (C029, C29, C0029)
        # Allow 1-4 digits to handle typos like C0029
        explicit_matches = re.findall(r'\b[Cc](\d{1,4})\b', text)
        for match in explicit_matches:
            # Normalize: strip leading zeros, then pad to 3 digits
            # C0029 → 29 → C029
            # C29 → 29 → C029
            num = match.lstrip('0') or '0'  # Handle edge case of '000'
            customer_ids.append(f"C{num.zfill(3)}")
        
        # Also check for "customer X" patterns without C prefix
        if "customer" in text.lower():
            customer_number_matches = re.findall(r'customers?\s+(\d{1,4})', text.lower())
            for match in customer_number_matches:
                num = match.lstrip('0') or '0'
                cid = f"C{num.zfill(3)}"
                if cid not in customer_ids:
                    customer_ids.append(cid)
        
        return customer_ids
    
    def _extract_incident_tag(self, text: str) -> Optional[str]:
        """Extract incident tag from text."""
        text_upper = text.upper()
        for incident in VALID_INCIDENTS:
            if incident in text_upper:
                return incident
        
        # Also check for partial matches
        incident_keywords = {
            "LATENCY": "LATENCY_SPIKE",
            "SPIKE": "LATENCY_SPIKE",
            "OUTAGE": "FEED_OUTAGE",
            "FEED": "FEED_OUTAGE",
            "SUSPENDED": "MARKET_SUSPENDED",
            "SUSPEND": "MARKET_SUSPENDED",
            "MANUAL": "MANUAL_REVIEW",
            "REVIEW": "MANUAL_REVIEW",
        }
        
        for keyword, incident in incident_keywords.items():
            if keyword in text_upper:
                return incident
        
        return None
    
    def _extract_status(self, text: str) -> Optional[str]:
        """Extract status from text."""
        text_upper = text.upper()
        for status in VALID_STATUSES:
            if status in text_upper:
                return status
        return None
    
    def _extract_sport(self, text: str) -> Optional[str]:
        """Extract sport from text."""
        text_lower = text.lower()
        for sport in VALID_SPORTS:
            if sport in text_lower:
                return sport
        return None
    
    def _extract_number(self, text: str) -> Optional[int]:
        """Extract a number from text (for top-k queries)."""
        match = re.search(r'\b(\d+)\b', text)
        if match:
            return int(match.group(1))
        return None
    
    def _is_latency_query(self, text: str) -> bool:
        """Check if query is about latency/delay."""
        latency_keywords = [
            "latency", "delay", "price_delay", "slow", "lag",
            "ms", "millisecond", "stale", "pricing"
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in latency_keywords)


def create_retriever(db: Optional[Database] = None) -> Retriever:
    """
    Factory function to create a Retriever instance.
    
    Args:
        db: Optional database instance. Creates new one if None.
        
    Returns:
        Configured Retriever instance
    """
    if db is None:
        db = Database()
        db.load_embeddings_to_memory()
    return Retriever(db)
