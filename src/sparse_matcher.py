"""
Sparse Team Matcher for the Sportsbook RAG Assistant.

Provides efficient team name matching using edit distance (Levenshtein)
via the rapidfuzz library. This is an alternative to the embedding-based
approach that is:
- Faster: No API calls, O(n) string operations
- Cheaper: $0 cost
- More interpretable: "Matched because similarity = 85%"
- Better for typos: Directly measures character-level errors

Usage:
    from src.sparse_matcher import SparseTeamMatcher
    
    matcher = SparseTeamMatcher()
    matcher.build_index(["Lakers", "Celtics", "Raptors", "Warriors"])
    
    matches = matcher.find_matches("Lakkers", threshold=70)
    # Returns: [("Lakers", 92.3, "edit_distance")]
"""

from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from .config import DEBUG_MODE, SPARSE_TEAM_THRESHOLD

if DEBUG_MODE:
    from rich.console import Console
    console = Console()


@dataclass
class TeamMatch:
    """A matched team name with score and method."""
    team_name: str
    score: float  # 0-100 scale
    method: str   # "exact", "edit_distance", "phonetic_exact"


class SparseTeamMatcher:
    """
    Sparse team name matcher using edit distance.
    
    This provides an alternative to embedding-based team search that:
    - Works offline (no API calls)
    - Is faster (<1ms vs ~15ms for embeddings)
    - Handles typos directly via character-level similarity
    
    Matching Strategy (in order of priority):
    1. Exact match (case-insensitive) → score 100
    2. Edit distance similarity (fuzz.ratio) → score 0-100
    
    The fuzz.ratio uses normalized Levenshtein distance:
    - "Raptors" vs "Rapters" → 85.7 (1 character difference)
    - "Lakers" vs "Lakkers" → 92.3 (1 extra character)
    - "Thunder" vs "Thundr" → 92.9 (1 missing character)
    """
    
    def __init__(self, threshold: float = SPARSE_TEAM_THRESHOLD):
        """
        Initialize the matcher.
        
        Args:
            threshold: Minimum similarity score (0-100) to consider a match
        """
        self.threshold = threshold
        self._teams: List[str] = []
        self._teams_lower: Dict[str, str] = {}  # lower -> original
        self._team_to_bet_ids: Dict[str, Set[str]] = {}  # team -> set of bet_ids
    
    def build_index(
        self, 
        team_names: List[str],
        team_to_bet_ids: Optional[Dict[str, Set[str]]] = None
    ) -> None:
        """
        Build the team name index.
        
        Args:
            team_names: List of team names to index
            team_to_bet_ids: Optional mapping of team name -> bet IDs
        """
        if DEBUG_MODE:
            console.log(f"[blue]SparseTeamMatcher: Building index with {len(team_names)} teams[/blue]")
        
        self._teams = list(set(team_names))  # Deduplicate
        self._teams_lower = {t.lower(): t for t in self._teams}
        self._team_to_bet_ids = team_to_bet_ids or {}
    
    def find_matches(
        self, 
        query: str, 
        threshold: Optional[float] = None,
        top_k: int = 10
    ) -> List[TeamMatch]:
        """
        Find teams matching the query using edit distance.
        
        Args:
            query: The search query (team name, possibly misspelled)
            threshold: Minimum similarity score (0-100). Uses instance default if None.
            top_k: Maximum number of matches to return
            
        Returns:
            List of TeamMatch objects, sorted by score descending
        """
        if DEBUG_MODE:
            console.log(f"[blue]find_matches called with threshold={threshold}, top_k={top_k}[/blue]")
        if not self._teams:
            return []
        
        threshold = threshold if threshold is not None else self.threshold
        query_lower = query.lower().strip()
        
        if DEBUG_MODE:
            console.log(f"[blue]SparseTeamMatcher: Searching for '{query}' with threshold {threshold}[/blue]")
        
        # Stage 1: Exact match (instant)
        if query_lower in self._teams_lower:
            original = self._teams_lower[query_lower]
            if DEBUG_MODE:
                console.log(f"[green]SparseTeamMatcher: Exact match found: {original}[/green]")
            return [TeamMatch(team_name=original, score=100.0, method="exact")]
        
        # Stage 2: Edit distance matching
        matches = []
        for team in self._teams:
            # Use fuzz.ratio for normalized Levenshtein similarity (0-100)
            score = fuzz.ratio(query_lower, team.lower())
            
            if score >= threshold:
                matches.append(TeamMatch(
                    team_name=team,
                    score=score,
                    method="edit_distance"
                ))
        
        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)
        
        if DEBUG_MODE and matches:
            console.log(f"[green]SparseTeamMatcher: Found {len(matches)} matches, top: {matches[0]}[/green]")
        
        return matches[:top_k]
    
    def find_bet_ids_for_query(
        self, 
        query: str, 
        threshold: Optional[float] = None
    ) -> List[Tuple[str, float]]:
        """
        Find bet IDs that match the query via team name similarity.
        
        Args:
            query: The search query (team name, possibly misspelled)
            threshold: Minimum similarity score (0-100)
            
        Returns:
            List of (bet_id, score) tuples
        """
        matches = self.find_matches(query, threshold)
        
        if not matches:
            return []
        
        # Collect bet IDs from all matching teams
        result_scores: Dict[str, float] = {}
        
        for match in matches:
            team = match.team_name
            if team in self._team_to_bet_ids:
                for bet_id in self._team_to_bet_ids[team]:
                    # Keep the highest score for each bet_id
                    if bet_id not in result_scores or match.score > result_scores[bet_id]:
                        result_scores[bet_id] = match.score
        
        # Sort by score descending
        results = [(bid, score) for bid, score in result_scores.items()]
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def get_edit_distance(self, s1: str, s2: str) -> int:
        """
        Get the raw Levenshtein edit distance between two strings.
        
        Useful for debugging and understanding matches.
        """
        return Levenshtein.distance(s1.lower(), s2.lower())
    
    def get_similarity(self, s1: str, s2: str) -> float:
        """
        Get the normalized similarity (0-100) between two strings.
        
        This is what fuzz.ratio returns.
        """
        return fuzz.ratio(s1.lower(), s2.lower())
    
    def explain_match(self, query: str, team: str) -> str:
        """
        Explain why/how a query matches a team name.
        
        Useful for debugging and transparency.
        """
        query_lower = query.lower()
        team_lower = team.lower()
        
        if query_lower == team_lower:
            return f"Exact match: '{query}' == '{team}'"
        
        distance = self.get_edit_distance(query, team)
        similarity = self.get_similarity(query, team)
        
        return (
            f"Edit distance match:\n"
            f"  Query: '{query}'\n"
            f"  Team:  '{team}'\n"
            f"  Levenshtein distance: {distance} character(s)\n"
            f"  Similarity score: {similarity:.1f}%"
        )
    
    @property
    def team_count(self) -> int:
        """Number of teams in the index."""
        return len(self._teams)
    
    @property
    def teams(self) -> List[str]:
        """List of all indexed team names."""
        return self._teams.copy()


# Singleton instance for the application
_sparse_matcher: Optional[SparseTeamMatcher] = None


def get_sparse_matcher() -> SparseTeamMatcher:
    """Get the singleton SparseTeamMatcher instance."""
    global _sparse_matcher
    if _sparse_matcher is None:
        _sparse_matcher = SparseTeamMatcher()
    return _sparse_matcher


def reset_sparse_matcher() -> None:
    """Reset the singleton (useful for testing)."""
    global _sparse_matcher
    _sparse_matcher = None
