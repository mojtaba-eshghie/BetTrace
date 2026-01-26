"""
Data models for the Sportsbook RAG Assistant.

Defines the Bet model and related data structures.
"""

from dataclasses import dataclass, asdict
from typing import Optional, List
import json


@dataclass
class Bet:
    """Represents a single bet record."""
    
    bet_id: str
    customer_id: str
    sport: str
    event_name: str
    market: str
    selection: str
    stake_gbp: float
    status: str
    incident_tag: str
    price_delay_ms: int
    # Stored document text (the exact text that was embedded)
    # This is populated when loading from database, None when creating new
    stored_document: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert bet to dictionary (excludes stored_document as it's derived)."""
        return {
            "bet_id": self.bet_id,
            "customer_id": self.customer_id,
            "sport": self.sport,
            "event_name": self.event_name,
            "market": self.market,
            "selection": self.selection,
            "stake_gbp": self.stake_gbp,
            "status": self.status,
            "incident_tag": self.incident_tag,
            "price_delay_ms": self.price_delay_ms
        }
    
    def to_document(self) -> str:
        """
        Convert bet to a text document for embedding.
        
        This creates a natural language representation of the bet
        that can be embedded for semantic search.
        
        Note: If this bet was loaded from database, returns the stored
        document to ensure consistency with the stored embedding.
        """
        # Return stored document if available (ensures consistency with embedding)
        if self.stored_document is not None:
            return self.stored_document
        
        # Generate document text for new bets
        return self._generate_document()
    
    def _generate_document(self) -> str:
        """Generate the document text from bet fields."""
        # Build a descriptive text representation
        incident_text = ""
        if self.incident_tag != "NONE":
            incident_text = f" Incident: {self.incident_tag}."
        
        latency_text = ""
        if self.price_delay_ms > 500:
            latency_text = f" High latency: {self.price_delay_ms}ms."
        elif self.price_delay_ms > 0:
            latency_text = f" Latency: {self.price_delay_ms}ms."
            
        document = (
            f"Bet {self.bet_id}: Customer {self.customer_id} placed a £{self.stake_gbp} "
            f"{self.market} bet on {self.event_name} ({self.sport}). "
            f"Selection: {self.selection}. Status: {self.status}.{incident_text}{latency_text}"
        )
        return document
    
    def to_summary(self) -> str:
        """Create a brief summary for display in results."""
        return (
            f"[{self.bet_id}] {self.sport.upper()} | {self.event_name} | "
            f"{self.market}: {self.selection} | £{self.stake_gbp} | "
            f"{self.status} | {self.incident_tag} | {self.price_delay_ms}ms"
        )
    
    @classmethod
    def from_dict(cls, data: dict) -> "Bet":
        """Create a Bet from a dictionary."""
        return cls(
            bet_id=str(data["bet_id"]),
            customer_id=str(data["customer_id"]),
            sport=str(data["sport"]),
            event_name=str(data["event_name"]),
            market=str(data["market"]),
            selection=str(data["selection"]),
            stake_gbp=float(data["stake_gbp"]),
            status=str(data["status"]),
            incident_tag=str(data["incident_tag"]),
            price_delay_ms=int(data["price_delay_ms"])
        )


@dataclass
class RetrievalResult:
    """Represents a retrieval result with optional similarity score."""
    
    bet: Bet
    score: Optional[float] = None  # Similarity score for semantic search
    match_type: str = "exact"  # "exact", "filtered", "semantic", "hybrid"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "bet": self.bet.to_dict(),
            "score": self.score,
            "match_type": self.match_type
        }


@dataclass
class QueryContext:
    """Context for a retrieval query."""
    
    query_text: str
    bet_ids: Optional[List[str]] = None
    customer_ids: Optional[List[str]] = None
    sports: Optional[List[str]] = None
    statuses: Optional[List[str]] = None
    incident_tags: Optional[List[str]] = None
    min_stake: Optional[float] = None
    max_stake: Optional[float] = None
    min_delay: Optional[int] = None
    max_delay: Optional[int] = None
    top_k: int = 10
    
    def has_filters(self) -> bool:
        """Check if any structured filters are set."""
        return any([
            self.bet_ids,
            self.customer_ids,
            self.sports,
            self.statuses,
            self.incident_tags,
            self.min_stake is not None,
            self.max_stake is not None,
            self.min_delay is not None,
            self.max_delay is not None
        ])
