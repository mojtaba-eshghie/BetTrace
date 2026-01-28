"""
Data models for the Sportsbook RAG Assistant.

Defines the Bet model and related data structures.

Currency Handling:
- All monetary values use Python's Decimal for exact precision
- Database stores stake as INTEGER (pence) to avoid float precision issues
- Conversion functions provided for boundary handling
"""

from dataclasses import dataclass, asdict
from typing import Optional, List, Any, Union
from decimal import Decimal, ROUND_HALF_UP
import json

from .config import DEBUG_MODE
from rich.console import Console
console = Console()

# =============================================================================
# Currency Utility Functions
# =============================================================================

def to_decimal(value: Any) -> Decimal:
    """
    Convert a value to Decimal with proper precision for currency.
    
    This handles the conversion safely to avoid float precision issues.
    Always rounds to 2 decimal places for GBP currency.
    """
    if isinstance(value, Decimal):
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if isinstance(value, float):
        # Convert float to string first to avoid float precision issues
        # Round to 2 decimal places for currency
        return Decimal(str(round(value, 2))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if isinstance(value, int):
        return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def to_pence(value: Union[Decimal, float, int]) -> int:
    """
    Convert pounds to pence for database storage.
    
    Storing as INTEGER pence avoids all floating point issues in SQLite.
    """
    if not isinstance(value, Decimal):
        value = to_decimal(value)
    return int((value * 100).to_integral_value(rounding=ROUND_HALF_UP))


def from_pence(value: int) -> Decimal:
    """
    Convert pence from database back to pounds as Decimal.
    """
    return (Decimal(value) / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Bet:
    """
    Represents a single bet record.
    
    Currency Handling:
    - stake_gbp is stored as Decimal for exact precision in Python
    - Use stake_pence() when storing to database
    - Database stores as INTEGER (pence) to avoid float issues
    """
    
    bet_id: str
    customer_id: str
    sport: str
    event_name: str
    market: str
    selection: str
    stake_gbp: Decimal  # Use Decimal for exact currency representation
    status: str
    incident_tag: str
    price_delay_ms: int
    # Stored document text (the exact text that was embedded)
    # This is populated when loading from database, None when creating new
    stored_document: Optional[str] = None
    
    def __post_init__(self):
        """Ensure stake_gbp is always a Decimal."""
        if not isinstance(self.stake_gbp, Decimal):
            self.stake_gbp = to_decimal(self.stake_gbp)
    
    def stake_pence(self) -> int:
        """Get stake in pence for database storage."""
        return to_pence(self.stake_gbp)
    
    def to_dict(self) -> dict:
        """Convert bet to dictionary (excludes stored_document as it's derived)."""
        return {
            "bet_id": self.bet_id,
            "customer_id": self.customer_id,
            "sport": self.sport,
            "event_name": self.event_name,
            "market": self.market,
            "selection": self.selection,
            "stake_gbp": float(self.stake_gbp),  # Convert for JSON serialization
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
        if DEBUG_MODE:
            console.log(f"[blue]DEBUG MODE: Generating document for Bet ID:[/blue] {self.bet_id}")
        # Return stored document if available (ensures consistency with embedding)
        if self.stored_document is not None:
            return self.stored_document
        
        # Generate document text for new bets
        return self._generate_document()
    
    def _generate_document(self) -> str:
        """Generate the document text from bet fields."""
        if DEBUG_MODE:
            console.log(f"[blue]DEBUG MODE: Generating new document text for Bet ID:[/blue] {self.bet_id}")
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
        if DEBUG_MODE:
            console.log(f"[blue]DEBUG MODE: Generating summary for Bet ID:[/blue] {self.bet_id}")
        return (
            f"[{self.bet_id}] {self.sport.upper()} | {self.event_name} | "
            f"{self.market}: {self.selection} | £{self.stake_gbp} | "
            f"{self.status} | {self.incident_tag} | {self.price_delay_ms}ms"
        )
    
    @classmethod
    def from_dict(cls, data: dict) -> "Bet":
        """Create a Bet from a dictionary."""
        if DEBUG_MODE:
            console.log(f"[blue]DEBUG MODE: Creating Bet from dict:[/blue] {data}")
        return cls(
            bet_id=str(data["bet_id"]),
            customer_id=str(data["customer_id"]),
            sport=str(data["sport"]),
            event_name=str(data["event_name"]),
            market=str(data["market"]),
            selection=str(data["selection"]),
            stake_gbp=to_decimal(data["stake_gbp"]),
            status=str(data["status"]),
            incident_tag=str(data["incident_tag"]),
            price_delay_ms=int(data["price_delay_ms"])
        )
    
    @classmethod
    def from_db_row_pence(cls, row: dict) -> "Bet":
        """
        Create a Bet from a database row where stake is stored as pence.
        
        Args:
            row: Database row as dict with stake_pence column
        """
        if DEBUG_MODE:
            console.log(f"[blue]DEBUG MODE: Creating Bet from DB row (pence):[/blue] {row}")
        return cls(
            bet_id=str(row["bet_id"]),
            customer_id=str(row["customer_id"]),
            sport=str(row["sport"]),
            event_name=str(row["event_name"]),
            market=str(row["market"]),
            selection=str(row["selection"]),
            stake_gbp=from_pence(row["stake_pence"]),
            status=str(row["status"]),
            incident_tag=str(row["incident_tag"]),
            price_delay_ms=int(row["price_delay_ms"]),
            stored_document=row.get("document")
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
    min_stake: Optional[Decimal] = None
    max_stake: Optional[Decimal] = None
    min_delay: Optional[int] = None
    max_delay: Optional[int] = None
    top_k: int = 10
    
    def has_filters(self) -> bool:
        """Check if any structured filters are set."""
        if DEBUG_MODE:
            console.log(f"[blue]DEBUG MODE: Checking filters in QueryContext:[/blue] {self}")
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


# =============================================================================
# Event Name Parsing Utilities
# =============================================================================

def parse_event_teams(event_name: str) -> tuple:
    """
    Parse an event name into individual team/player names.
    
    Handles formats like:
    - "Team1 vs Team2" → ("Team1", "Team2")
    - "Player1 vs Player2" → ("Player1", "Player2")
    - "Team1 v Team2" → ("Team1", "Team2")
    - "Team1 - Team2" → ("Team1", "Team2")
    
    Returns:
        Tuple of (team1, team2) or (event_name, "") if parsing fails
    """
    if DEBUG_MODE:
        console.log(f"[blue]DEBUG MODE: Parsing event name into teams:[/blue] '{event_name}'")
    import re
    
    # Try common separators: " vs ", " v ", " - ", " @ "
    separators = [r'\s+vs\.?\s+', r'\s+v\s+', r'\s+-\s+', r'\s+@\s+']
    
    for sep in separators:
        parts = re.split(sep, event_name, flags=re.IGNORECASE)
        if len(parts) == 2:
            team1, team2 = parts[0].strip(), parts[1].strip()
            if team1 and team2:
                return (team1, team2)
    
    # Fallback: return event name as team1, empty string as team2
    return (event_name.strip(), "")


# =============================================================================
# Phonetic Normalization for Typo-Tolerant Matching
# =============================================================================

def phonetic_normalize(text: str) -> str:
    """
    Convert text to phonetic representation for typo-tolerant embedding matching.
    
    Uses a simplified Double Metaphone-like algorithm that:
    - Removes vowels (except leading)
    - Normalizes common letter substitutions
    - Handles double letters
    
    Examples:
        "Raptors" → "RPTRS"
        "Rapters" → "RPTRS"  (same!)
        "Lakers"  → "LKRS"
        "Lakkers" → "LKRS"   (same!)
        "Celtics" → "CLTCS"
        "Celtcs"  → "CLTCS"  (same!)
    """
    if DEBUG_MODE:
        console.log(f"[blue]DEBUG MODE: Phonetic normalizing text:[/blue] '{text}'")
    if not text:
        return ""
    
    text = text.upper().strip()
    
    # Keep first letter, then process rest
    if len(text) <= 1:
        return text
    
    first = text[0]
    rest = text[1:]
    
    # Remove vowels from rest (they cause most spelling variations)
    vowels = set('AEIOU')
    rest = ''.join(c for c in rest if c not in vowels)
    
    # Remove consecutive duplicate letters
    result = [first]
    for c in rest:
        if c != result[-1]:
            result.append(c)
    
    # Common phonetic normalizations
    normalized = ''.join(result)
    normalized = normalized.replace('PH', 'F')
    normalized = normalized.replace('GH', 'G')
    normalized = normalized.replace('CK', 'K')
    normalized = normalized.replace('SCH', 'SK')
    normalized = normalized.replace('KN', 'N')
    normalized = normalized.replace('WR', 'R')
    
    return normalized


def get_team_phonetic_variants(team_name: str) -> list:
    if DEBUG_MODE:
        console.log(f"[blue]DEBUG MODE: Getting phonetic variants for team name:[/blue] '{team_name}'")
    """
    Get the team name and its phonetic normalization for embedding.
    
    Returns list of strings to embed - the phonetic version provides
    typo tolerance while the original provides exact match capability.
    """
    phonetic = phonetic_normalize(team_name)
    return [team_name, phonetic] if phonetic != team_name.upper() else [team_name]
