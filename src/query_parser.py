"""
Unified Query Parser for the Sportsbook RAG Assistant.

Parses natural language queries into structured components that can be
executed via SQL, embeddings, or a hybrid of both.

This replaces all the special-case _is_X_query() methods with a single,
composable parsing system.

Architecture:
    Query String → QueryParser → ParsedQuery → QueryExecutor → Results

Example:
    "Top 5 tennis bets with highest delay"
    → ParsedQuery(
        filters={"sport": "tennis"},
        sort_by="price_delay_ms",
        sort_order="desc",
        limit=5,
        aggregation="top_n"
      )
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum


class AggregationType(Enum):
    """Types of aggregations we support."""
    NONE = "none"           # No aggregation - return records
    COUNT = "count"         # Count records
    SUM = "sum"             # Sum a column
    AVG = "avg"             # Average a column
    TOP_N = "top_n"         # Top N by column
    BOTTOM_N = "bottom_n"   # Bottom N by column
    GROUP_BY = "group_by"   # Group and aggregate


class QueryType(Enum):
    """High-level query classification."""
    ENTITY_LOOKUP = "entity_lookup"     # Specific bet/customer lookup
    FILTERED = "filtered"               # SQL-filterable query
    AGGREGATE = "aggregate"             # Aggregation query (count, sum, etc.)
    TOP_N = "top_n"                     # Top/bottom N ranking
    SEMANTIC = "semantic"               # Pure semantic search
    HYBRID = "hybrid"                   # SQL filter + semantic ranking


@dataclass
class ParsedQuery:
    """
    Structured representation of a parsed query.
    
    All fields are optional - a query may only use some components.
    The combination of fields determines the execution strategy.
    """
    
    # Original query (for semantic fallback)
    original_query: str
    
    # Entity lookups (direct ID-based retrieval)
    bet_ids: List[str] = field(default_factory=list)
    customer_ids: List[str] = field(default_factory=list)
    
    # Flag for invalid entity references (e.g., "customer F029" where F is not valid)
    invalid_entity_reference: Optional[str] = None  # Stores the invalid reference for error message
    
    # Flag for incomplete ID queries (e.g., "give me a bet with id" without specifying which ID)
    incomplete_id_query: Optional[str] = None  # Stores what type of ID is missing: "bet" or "customer"
    
    # Structured filters (converted to SQL WHERE)
    filters: Dict[str, Any] = field(default_factory=dict)
    # Supported filter keys:
    #   sport: str
    #   status: str
    #   incident_tag: str
    #   min_stake, max_stake: float
    #   min_delay, max_delay: int
    
    # Sorting
    sort_by: Optional[str] = None       # Column name: "stake_gbp", "price_delay_ms"
    sort_order: str = "desc"            # "desc" (top/highest) or "asc" (bottom/lowest)
    limit: Optional[int] = None         # Number of results
    
    # Aggregation
    aggregation: AggregationType = AggregationType.NONE
    aggregation_column: Optional[str] = None  # Column to aggregate
    group_by_column: Optional[str] = None     # Column to group by
    
    # Semantic component (text that couldn't be parsed structurally)
    semantic_terms: List[str] = field(default_factory=list)
    
    # Confidence scores for parsing decisions
    parse_confidence: float = 1.0
    
    @property
    def query_type(self) -> QueryType:
        """Determine the query type based on parsed components."""
        # Invalid entity reference should return empty (not fall to semantic)
        if self.invalid_entity_reference:
            return QueryType.ENTITY_LOOKUP  # Will return empty in executor
        
        # Incomplete ID query should return empty (not fall to semantic)
        if self.incomplete_id_query:
            return QueryType.ENTITY_LOOKUP  # Will return empty in executor with helpful message
        
        # Entity lookup takes priority
        if self.bet_ids or self.customer_ids:
            return QueryType.ENTITY_LOOKUP
        
        # Top N queries with explicit sort criteria should ALWAYS be TOP_N
        # Semantic terms here are for LLM analysis AFTER retrieval, not for routing
        if self.aggregation in (AggregationType.TOP_N, AggregationType.BOTTOM_N):
            if self.sort_by:  # We have a concrete column to sort by
                return QueryType.TOP_N
            # No sort column but semantic terms - let hybrid figure it out
            if self.semantic_terms:
                return QueryType.HYBRID
            return QueryType.TOP_N
        
        # COUNT/SUM/AVG with FILTERS should go to AGGREGATE (filters are the search criteria)
        # e.g., "How many VOID bets due to FEED_OUTAGE?" → use filters, not semantic search
        if self.aggregation not in (AggregationType.NONE, AggregationType.TOP_N, AggregationType.BOTTOM_N):
            if self.filters:
                return QueryType.AGGREGATE
        
        # COUNT aggregation with meaningful semantic terms but NO filters = SEMANTIC search
        # e.g., "All bets involving Marsile team" → search for Marsile
        if self.aggregation == AggregationType.COUNT and self._has_meaningful_search_terms():
            if not self.filters:  # Only if no structured filters
                return QueryType.SEMANTIC
        
        # Pure aggregation (count, sum, avg) without search terms
        if self.aggregation not in (AggregationType.NONE, AggregationType.TOP_N, AggregationType.BOTTOM_N):
            return QueryType.AGGREGATE
        
        # Has filters but also semantic terms → hybrid
        if self.filters and self.semantic_terms:
            return QueryType.HYBRID
        
        # Has filters only → filtered
        if self.filters:
            return QueryType.FILTERED
        
        # Default to semantic
        return QueryType.SEMANTIC
    
    def _has_meaningful_search_terms(self) -> bool:
        """Check if semantic_terms contain meaningful search criteria (not just filler)."""
        if not self.semantic_terms:
            return False
        
        # Filler words that don't indicate a search
        filler_words = {
            'that', 'which', 'where', 'when', 'what', 'how', 'who',
            'involves', 'involving', 'include', 'includes', 'including',
            'related', 'about', 'with', 'from', 'have', 'has', 'had',
            'there', 'these', 'those', 'this', 'the', 'a', 'an',
        }
        
        # Check if any semantic term is NOT a filler word
        meaningful = [term for term in self.semantic_terms 
                      if term.lower().rstrip('.?,!') not in filler_words]
        
        return len(meaningful) > 0
    
    @property
    def is_fully_structured(self) -> bool:
        """Check if query can be answered entirely via SQL."""
        return self.query_type in (
            QueryType.ENTITY_LOOKUP,
            QueryType.FILTERED,
            QueryType.AGGREGATE,
            QueryType.TOP_N
        )
    
    @property
    def needs_semantic_search(self) -> bool:
        """Check if query requires embedding-based search."""
        return self.query_type in (QueryType.SEMANTIC, QueryType.HYBRID)
    
    @property
    def needs_aggregation_context(self) -> bool:
        """Check if we should compute SQL aggregations for context."""
        return self.aggregation != AggregationType.NONE or bool(self.filters)
    
    def __repr__(self) -> str:
        parts = [f"ParsedQuery(type={self.query_type.value}"]
        if self.bet_ids:
            parts.append(f"bet_ids={self.bet_ids}")
        if self.customer_ids:
            parts.append(f"customer_ids={self.customer_ids}")
        if self.filters:
            parts.append(f"filters={self.filters}")
        if self.sort_by:
            parts.append(f"sort={self.sort_by} {self.sort_order}")
        if self.limit:
            parts.append(f"limit={self.limit}")
        if self.aggregation != AggregationType.NONE:
            parts.append(f"agg={self.aggregation.value}")
        if self.semantic_terms:
            parts.append(f"semantic={self.semantic_terms}")
        return ", ".join(parts) + ")"


class QueryParser:
    """
    Parses natural language queries into structured ParsedQuery objects.
    
    Uses rule-based parsing for known patterns, with semantic fallback
    for unrecognized terms.
    
    Thread-safe and stateless - can be used as a singleton.
    """
    
    # ==========================================================================
    # Configuration: Keywords and Patterns
    # ==========================================================================
    
    # Entity ID patterns
    BET_ID_PATTERN = re.compile(r'\b[Bb](\d{1,5})\b')
    CUSTOMER_ID_PATTERN = re.compile(r'\b[Cc](\d{1,4})\b')
    CUSTOMER_WORD_PATTERN = re.compile(r'customers?\s+(\d{1,4})', re.IGNORECASE)
    BET_WORD_PATTERN = re.compile(r'bets?\s+(\d{1,5})', re.IGNORECASE)
    
    # Incomplete ID query patterns (compiled once for performance)
    INCOMPLETE_BET_PATTERNS = [
        re.compile(r'\bbet\s+(?:with\s+)?id\b(?!\s*[bcBC]?\d)', re.IGNORECASE),  # "bet with id" not followed by actual ID
        re.compile(r'\ba\s+bet\s+(?:with\s+)?id\b(?!\s*[bcBC]?\d)', re.IGNORECASE),  # "a bet with id"
        re.compile(r'\bsome\s+(?:a\s+)?bet\s+(?:with\s+)?id\b(?!\s*[bcBC]?\d)', re.IGNORECASE),  # "some a bet with id"
        re.compile(r'\bshow\s+(?:me\s+)?(?:the\s+)?bet\s+id\b(?!\s*[bcBC]?\d)', re.IGNORECASE),  # "show bet id"
        re.compile(r'\bget\s+(?:me\s+)?(?:the\s+)?bet\s+id\b(?!\s*[bcBC]?\d)', re.IGNORECASE),  # "get bet id"
        re.compile(r'\bfind\s+(?:me\s+)?(?:the\s+)?bet\s+id\b(?!\s*[bcBC]?\d)', re.IGNORECASE),  # "find bet id"
    ]
    
    INCOMPLETE_CUSTOMER_PATTERNS = [
        re.compile(r'\bcustomer\s+(?:with\s+)?id\b(?!\s*[bcBC]?\d)', re.IGNORECASE),  # "customer with id"
        re.compile(r'\ba\s+customer\s+(?:with\s+)?id\b(?!\s*[bcBC]?\d)', re.IGNORECASE),  # "a customer with id"
        re.compile(r'\bsome\s+(?:a\s+)?customer\s+(?:with\s+)?id\b(?!\s*[bcBC]?\d)', re.IGNORECASE),  # "some a customer with id"
        re.compile(r'\bshow\s+(?:me\s+)?(?:the\s+)?customer\s+id\b(?!\s*[bcBC]?\d)', re.IGNORECASE),  # "show customer id"
        re.compile(r'\bget\s+(?:me\s+)?(?:the\s+)?customer\s+id\b(?!\s*[bcBC]?\d)', re.IGNORECASE),  # "get customer id"
        re.compile(r'\bfind\s+(?:me\s+)?(?:the\s+)?customer\s+id\b(?!\s*[bcBC]?\d)', re.IGNORECASE),  # "find customer id"
    ]
    
    # Sort keywords → (column, order)
    SORT_KEYWORDS: Dict[str, Tuple[str, str]] = {
        # Stake sorting
        "highest stake": ("stake_gbp", "desc"),
        "largest stake": ("stake_gbp", "desc"),
        "biggest stake": ("stake_gbp", "desc"),
        "most expensive": ("stake_gbp", "desc"),
        "top stake": ("stake_gbp", "desc"),
        "lowest stake": ("stake_gbp", "asc"),
        "smallest stake": ("stake_gbp", "asc"),
        "cheapest": ("stake_gbp", "asc"),
        # Delay sorting
        "highest delay": ("price_delay_ms", "desc"),
        "longest delay": ("price_delay_ms", "desc"),
        "most delay": ("price_delay_ms", "desc"),
        "slowest": ("price_delay_ms", "desc"),
        "highest latency": ("price_delay_ms", "desc"),
        "most latency": ("price_delay_ms", "desc"),
        "lowest delay": ("price_delay_ms", "asc"),
        "shortest delay": ("price_delay_ms", "asc"),
        "fastest": ("price_delay_ms", "asc"),
        "lowest latency": ("price_delay_ms", "asc"),
    }
    
    # Column name synonyms → canonical column
    COLUMN_SYNONYMS: Dict[str, str] = {
        # Stake (exact column name first)
        "stake_gbp": "stake_gbp",
        "stake": "stake_gbp",
        "amount": "stake_gbp",
        "value": "stake_gbp",
        "money": "stake_gbp",
        "wager": "stake_gbp",
        "gbp": "stake_gbp",
        "£": "stake_gbp",
        # Delay (exact column name first)
        "price_delay_ms": "price_delay_ms",
        "delay": "price_delay_ms",
        "latency": "price_delay_ms",
        "ms": "price_delay_ms",
        "milliseconds": "price_delay_ms",
        "pricing": "price_delay_ms",
        "slow": "price_delay_ms",
        "lag": "price_delay_ms",
    }
    
    # Sport keywords → canonical sport
    SPORT_KEYWORDS: Dict[str, str] = {
        "football": "football",
        "soccer": "football",
        "tennis": "tennis",
        "basketball": "basketball",
        "nba": "basketball",
        "hoops": "basketball",
    }
    
    # Status keywords → canonical status
    STATUS_KEYWORDS: Dict[str, str] = {
        "settled": "SETTLED",
        "pending": "PENDING",
        "void": "VOID",
        "voided": "VOID",
        "rejected": "REJECTED",
        "cancelled": "REJECTED",
    }
    
    # Incident keywords → canonical incident
    INCIDENT_KEYWORDS: Dict[str, str] = {
        "latency_spike": "LATENCY_SPIKE",
        "latency spike": "LATENCY_SPIKE",
        "spike": "LATENCY_SPIKE",
        "feed_outage": "FEED_OUTAGE",
        "feed outage": "FEED_OUTAGE",
        "outage": "FEED_OUTAGE",
        "market_suspended": "MARKET_SUSPENDED",
        "market suspended": "MARKET_SUSPENDED",
        "suspended": "MARKET_SUSPENDED",
        "manual_review": "MANUAL_REVIEW",
        "manual review": "MANUAL_REVIEW",
        "review": "MANUAL_REVIEW",
        "none": "NONE",
        "no incident": "NONE",
    }
    
    # Aggregation keywords
    AGGREGATION_KEYWORDS: Dict[str, AggregationType] = {
        "how many": AggregationType.COUNT,
        "count": AggregationType.COUNT,
        "number of": AggregationType.COUNT,
        "total stake": AggregationType.SUM,
        "sum of": AggregationType.SUM,
        "total amount": AggregationType.SUM,
        "average stake": AggregationType.AVG,
        "avg stake": AggregationType.AVG,
        "mean stake": AggregationType.AVG,
        "average delay": AggregationType.AVG,
        "avg delay": AggregationType.AVG,
        "mean delay": AggregationType.AVG,
        # Existence queries (treated as count)
        "are there any": AggregationType.COUNT,
        "are there": AggregationType.COUNT,
        "is there any": AggregationType.COUNT,
        "is there a": AggregationType.COUNT,
        "do we have": AggregationType.COUNT,
        "does it have": AggregationType.COUNT,
        "any": AggregationType.COUNT,  # "Any rejected bets?"
    }
    
    # Top/Bottom N indicators
    TOP_N_KEYWORDS = {"top", "highest", "largest", "biggest", "best", "most"}
    BOTTOM_N_KEYWORDS = {"bottom", "lowest", "smallest", "worst", "least"}
    
    # General aggregate query indicators
    GENERAL_AGGREGATE_KEYWORDS = {
        "overview", "summary", "statistics", "stats", "all bets",
        "overall", "entire", "whole", "everything", "total"
    }
    
    # Semantic indicator words (suggest we need embedding search)
    SEMANTIC_INDICATORS = {
        "suspicious", "problematic", "risky", "unusual", "strange",
        "similar", "like", "related", "about", "concerning",
        "issues", "problems", "errors", "anomalies", "outliers",
        "interesting", "notable", "significant", "important", "relevant",
        "weird", "odd", "questionable", "curious", "remarkable",
    }
    
    # ==========================================================================
    # Main Parsing Method
    # ==========================================================================
    
    def parse(self, query: str) -> ParsedQuery:
        """
        Parse a natural language query into structured components.
        
        Args:
            query: Natural language query string
            
        Returns:
            ParsedQuery object with extracted components
        """
        # Initialize result
        parsed = ParsedQuery(original_query=query)
        query_lower = query.lower()
        remaining_text = query_lower
        
        # 1. Extract entity IDs (highest priority)
        parsed.bet_ids, remaining_text = self._extract_bet_ids(query, remaining_text)
        parsed.customer_ids, remaining_text = self._extract_customer_ids(query, remaining_text)
        
        # 2. Extract filters
        parsed.filters, remaining_text = self._extract_filters(remaining_text)
        
        # 3. Extract sorting
        sort_info, remaining_text = self._extract_sorting(remaining_text)
        if sort_info:
            parsed.sort_by, parsed.sort_order = sort_info
        
        # 4. Extract limit
        parsed.limit, remaining_text = self._extract_limit(remaining_text)
        
        # 5. Extract aggregation
        parsed.aggregation, parsed.aggregation_column, remaining_text = self._extract_aggregation(remaining_text)
        
        # 6. Detect top/bottom N pattern
        if self._has_top_n_pattern(query_lower):
            if parsed.aggregation == AggregationType.NONE:
                # Determine if top or bottom
                if any(kw in query_lower for kw in self.BOTTOM_N_KEYWORDS):
                    parsed.aggregation = AggregationType.BOTTOM_N
                else:
                    parsed.aggregation = AggregationType.TOP_N
                
                # Default limit if not specified
                if parsed.limit is None:
                    parsed.limit = 5
                
                # Infer column from remaining text if not set
                if parsed.sort_by is None:
                    parsed.sort_by = self._infer_sort_column(query_lower)
        
        # 7. Check for general aggregate queries
        if self._is_general_aggregate(query_lower):
            if parsed.aggregation == AggregationType.NONE:
                parsed.aggregation = AggregationType.COUNT
        
        # 8. Check for invalid entity references (e.g., "customer F029")
        # This prevents falling through to semantic search for clearly invalid IDs
        parsed.invalid_entity_reference = self._detect_invalid_entity_reference(query_lower, parsed)
        
        # 9. Check for incomplete ID queries (e.g., "give me a bet with id" without specifying the ID)
        # This prevents falling through to semantic search when user clearly wants an ID-based lookup
        if not parsed.invalid_entity_reference:
            parsed.incomplete_id_query = self._detect_incomplete_id_query(query_lower, parsed)
        
        # 10. Extract semantic terms from remaining text (only if no invalid entity reference or incomplete query)
        if not parsed.invalid_entity_reference and not parsed.incomplete_id_query:
            parsed.semantic_terms = self._extract_semantic_terms(remaining_text)
        
        # 11. Calculate parse confidence
        parsed.parse_confidence = self._calculate_confidence(parsed)
        
        return parsed
    
    def _detect_invalid_entity_reference(self, query: str, parsed: ParsedQuery) -> Optional[str]:
        """
        Detect if user tried to reference an entity with an invalid ID format.
        
        Returns the invalid reference string if detected, None otherwise.
        """
        # If we already found valid IDs, no problem
        if parsed.bet_ids or parsed.customer_ids:
            return None
        
        # Check for "customer X" where X doesn't match C### pattern
        customer_attempt = re.search(r'customers?\s+([a-z]?\d+)', query)
        if customer_attempt:
            attempted_id = customer_attempt.group(1)
            # Valid customer IDs start with 'c' or are just numbers
            if not re.match(r'^c?\d+$', attempted_id, re.IGNORECASE):
                return f"customer {attempted_id}"
        
        # Check for patterns like "customer F029" (letter prefix that's not C)
        invalid_customer = re.search(r'customers?\s+([a-eg-z]\d+)', query, re.IGNORECASE)
        if invalid_customer:
            return f"customer {invalid_customer.group(1)}"
        
        # Check for "bet X" where X doesn't match B#### pattern
        bet_attempt = re.search(r'bets?\s+([a-z]?\d+)', query)
        if bet_attempt:
            attempted_id = bet_attempt.group(1)
            # Valid bet IDs start with 'b' or are just numbers
            if not re.match(r'^b?\d+$', attempted_id, re.IGNORECASE):
                return f"bet {attempted_id}"
        
        # Check for patterns like "bet X123" (letter prefix that's not B)
        invalid_bet = re.search(r'bets?\s+([a-ac-z]\d+)', query, re.IGNORECASE)
        if invalid_bet:
            return f"bet {invalid_bet.group(1)}"
        
        return None
    
    def _detect_incomplete_id_query(self, query: str, parsed: ParsedQuery) -> Optional[str]:
        """
        Detect if user is asking for a bet/customer by ID but didn't provide the actual ID.
        
        Examples that should be detected:
        - "give me a bet with id"
        - "show me bet with id"
        - "get me some bet with id"
        - "find customer with id"
        - "show the bet id"
        
        Returns "bet" or "customer" if detected, None otherwise.
        """
        # If we already found valid IDs, the query is complete
        if parsed.bet_ids or parsed.customer_ids:
            return None
        
        # Check bet patterns (using pre-compiled class constants)
        for pattern in self.INCOMPLETE_BET_PATTERNS:
            if pattern.search(query):
                return "bet"
        
        # Check customer patterns (using pre-compiled class constants)
        for pattern in self.INCOMPLETE_CUSTOMER_PATTERNS:
            if pattern.search(query):
                return "customer"
        
        return None
    
    # ==========================================================================
    # Extraction Methods
    # ==========================================================================
    
    def _extract_bet_ids(self, original: str, remaining: str) -> Tuple[List[str], str]:
        """Extract and normalize bet IDs."""
        bet_ids = []
        
        # Pattern: B0042, B42, etc.
        for match in self.BET_ID_PATTERN.finditer(original):
            num = match.group(1).lstrip('0') or '0'
            bet_ids.append(f"B{num.zfill(4)}")
            remaining = remaining.replace(match.group(0).lower(), ' ')
        
        # Pattern: "bet 42", "bets 1, 2, 3"
        for match in self.BET_WORD_PATTERN.finditer(original):
            num = match.group(1).lstrip('0') or '0'
            bid = f"B{num.zfill(4)}"
            if bid not in bet_ids:
                bet_ids.append(bid)
            remaining = remaining.replace(match.group(0).lower(), ' ')
        
        return bet_ids, remaining
    
    def _extract_customer_ids(self, original: str, remaining: str) -> Tuple[List[str], str]:
        """Extract and normalize customer IDs."""
        customer_ids = []
        
        # Pattern: C029, C29, etc.
        for match in self.CUSTOMER_ID_PATTERN.finditer(original):
            num = match.group(1).lstrip('0') or '0'
            customer_ids.append(f"C{num.zfill(3)}")
            remaining = remaining.replace(match.group(0).lower(), ' ')
        
        # Pattern: "customer 29"
        for match in self.CUSTOMER_WORD_PATTERN.finditer(original):
            num = match.group(1).lstrip('0') or '0'
            cid = f"C{num.zfill(3)}"
            if cid not in customer_ids:
                customer_ids.append(cid)
            remaining = remaining.replace(match.group(0).lower(), ' ')
        
        return customer_ids, remaining
    
    def _extract_filters(self, text: str) -> Tuple[Dict[str, Any], str]:
        """Extract structured filters from text."""
        filters = {}
        remaining = text
        
        # Sport filter
        for keyword, sport in self.SPORT_KEYWORDS.items():
            if keyword in remaining:
                filters["sport"] = sport
                remaining = remaining.replace(keyword, ' ')
                break
        
        # Status filter
        for keyword, status in self.STATUS_KEYWORDS.items():
            if keyword in remaining:
                filters["status"] = status
                remaining = remaining.replace(keyword, ' ')
                break
        
        # Incident filter
        for keyword, incident in self.INCIDENT_KEYWORDS.items():
            if keyword in remaining:
                filters["incident_tag"] = incident
                remaining = remaining.replace(keyword, ' ')
                break
        
        # Numeric range filters (e.g., "over £50", "delay > 1000ms")
        stake_range = self._extract_stake_range(remaining)
        if stake_range:
            filters.update(stake_range)
        
        delay_range = self._extract_delay_range(remaining)
        if delay_range:
            filters.update(delay_range)
        
        return filters, remaining
    
    def _extract_stake_range(self, text: str) -> Dict[str, float]:
        """Extract stake range filters."""
        filters = {}
        
        # "over £50", "more than 50", "above £100"
        # But NOT "delay > 500ms" - exclude if followed by 'ms' or preceded by delay/latency keywords
        over_match = re.search(r'(?:over|above|more than|greater than|>=?)\s*£(\d+(?:\.\d+)?)', text)
        if over_match:
            filters["min_stake"] = float(over_match.group(1))
        else:
            # Try without £ but make sure it's not a delay pattern
            over_match = re.search(r'(?<!delay\s)(?<!latency\s)(?:over|above|more than|greater than)\s+(\d+(?:\.\d+)?)(?!ms)', text)
            if over_match and 'delay' not in text.lower() and 'latency' not in text.lower():
                filters["min_stake"] = float(over_match.group(1))
        
        # "under £50", "less than 50", "below £100"
        under_match = re.search(r'(?:under|below|less than|<=?)\s*£(\d+(?:\.\d+)?)', text)
        if under_match:
            filters["max_stake"] = float(under_match.group(1))
        else:
            # Try without £ but make sure it's not a delay pattern
            under_match = re.search(r'(?<!delay\s)(?<!latency\s)(?:under|below|less than)\s+(\d+(?:\.\d+)?)(?!ms)', text)
            if under_match and 'delay' not in text.lower() and 'latency' not in text.lower():
                filters["max_stake"] = float(under_match.group(1))
        
        return filters
    
    def _extract_delay_range(self, text: str) -> Dict[str, int]:
        """Extract delay range filters."""
        filters = {}
        
        # Patterns for "delay > 500ms", "delay over 1000", "latency > 500"
        # Also matches "had delay > 500ms"
        over_patterns = [
            r'delay\s*(?:>|>=|over|above|greater than)\s*(\d+)',
            r'latency\s*(?:>|>=|over|above|greater than)\s*(\d+)',
            r'(?:>|>=)\s*(\d+)\s*ms',
        ]
        
        for pattern in over_patterns:
            over_match = re.search(pattern, text, re.IGNORECASE)
            if over_match:
                filters["min_delay"] = int(over_match.group(1))
                break
        
        # Patterns for "delay < 100ms", "delay under 100"
        under_patterns = [
            r'delay\s*(?:<|<=|under|below|less than)\s*(\d+)',
            r'latency\s*(?:<|<=|under|below|less than)\s*(\d+)',
            r'(?:<|<=)\s*(\d+)\s*ms',
        ]
        
        for pattern in under_patterns:
            under_match = re.search(pattern, text, re.IGNORECASE)
            if under_match:
                filters["max_delay"] = int(under_match.group(1))
                break
        
        return filters
    
    def _extract_sorting(self, text: str) -> Tuple[Optional[Tuple[str, str]], str]:
        """Extract sorting information."""
        remaining = text
        
        # Check explicit sort keywords
        for keyword, (column, order) in self.SORT_KEYWORDS.items():
            if keyword in remaining:
                remaining = remaining.replace(keyword, ' ')
                return (column, order), remaining
        
        # Check "by X" pattern
        by_match = re.search(r'\bby\s+(stake|amount|delay|latency)', remaining)
        if by_match:
            column = self.COLUMN_SYNONYMS.get(by_match.group(1), by_match.group(1))
            # Default to descending unless "lowest" etc. appears
            order = "asc" if any(kw in remaining for kw in self.BOTTOM_N_KEYWORDS) else "desc"
            remaining = remaining.replace(by_match.group(0), ' ')
            return (column, order), remaining
        
        return None, remaining
    
    def _extract_limit(self, text: str) -> Tuple[Optional[int], str]:
        """Extract limit/count."""
        remaining = text
        
        # "top 5", "first 10", "5 bets"
        limit_match = re.search(r'\b(?:top|first|last|bottom)?\s*(\d+)\s*(?:bets?|records?|results?)?', remaining)
        if limit_match:
            limit = int(limit_match.group(1))
            if 1 <= limit <= 100:  # Sanity check
                remaining = remaining.replace(limit_match.group(0), ' ')
                return limit, remaining
        
        return None, remaining
    
    def _extract_aggregation(self, text: str) -> Tuple[AggregationType, Optional[str], str]:
        """Extract aggregation type and column."""
        remaining = text
        
        for keyword, agg_type in self.AGGREGATION_KEYWORDS.items():
            if keyword in remaining:
                remaining = remaining.replace(keyword, ' ')
                
                # Determine column
                column = None
                if "stake" in keyword or "amount" in keyword:
                    column = "stake_gbp"
                elif "delay" in keyword or "latency" in keyword:
                    column = "price_delay_ms"
                
                return agg_type, column, remaining
        
        return AggregationType.NONE, None, remaining
    
    def _has_top_n_pattern(self, text: str) -> bool:
        """Check if query has a top/bottom N pattern for structured ranking."""
        has_top = any(kw in text for kw in self.TOP_N_KEYWORDS)
        has_bottom = any(kw in text for kw in self.BOTTOM_N_KEYWORDS)
        has_column = any(kw in text for kw in self.COLUMN_SYNONYMS.keys())
        
        # Check if top/bottom keyword is followed by a semantic word (not a ranking query)
        # e.g., "most interesting", "most suspicious" = semantic, not top_n
        if has_top or has_bottom:
            semantic_after_top = re.search(
                r'\b(most|highest|largest|biggest|best|lowest|smallest|worst)\s+(' + 
                '|'.join(self.SEMANTIC_INDICATORS) + r')',
                text,
                re.IGNORECASE
            )
            if semantic_after_top:
                return False  # This is a semantic query, not a ranking
        
        return (has_top or has_bottom) and has_column
    
    def _infer_sort_column(self, text: str) -> Optional[str]:
        """Infer which column to sort by from context."""
        # Check for column synonyms in text
        for keyword, column in self.COLUMN_SYNONYMS.items():
            if keyword in text:
                return column
        return None
    
    def _is_general_aggregate(self, text: str) -> bool:
        """Check if query is asking for general aggregates."""
        # Use word boundary matching to avoid false positives like "football bets" matching "all bets"
        for kw in self.GENERAL_AGGREGATE_KEYWORDS:
            # For multi-word keywords, check exact phrase
            if ' ' in kw:
                if re.search(r'\b' + re.escape(kw) + r'\b', text):
                    return True
            else:
                # For single words, use word boundary
                if re.search(r'\b' + re.escape(kw) + r'\b', text):
                    return True
        return False
    
    def _extract_semantic_terms(self, text: str) -> List[str]:
        """Extract terms that require semantic search."""
        semantic_terms = []
        
        # Clean up remaining text
        text = ' '.join(text.split())  # Normalize whitespace
        
        # Common words to ignore
        stop_words = {
            'bets', 'bet', 'show', 'find', 'get', 'list', 'the', 'all', 'with', 'for',
            'me', 'please', 'give', 'what', 'which', 'where', 'when', 'how', 'who',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'must', 'can', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'of', 'by', 'from', 'bets?', 'records', 'record', 'data'
        }
        
        # Check for semantic indicator words
        for indicator in self.SEMANTIC_INDICATORS:
            if indicator in text:
                semantic_terms.append(indicator)
        
        # Extended stop words including short common words
        short_stop_words = stop_words | {'vs', 'am', 'pm', 'uk', 'us', 'if', 'so', 'no', 'up', 'as'}
        
        # If there's substantial remaining text, it might need semantic search
        remaining_words = [w for w in text.split() 
                         if (len(w) > 3 or (len(w) >= 2 and len(w) <= 4 and w.isalpha()))
                         and w.lower() not in short_stop_words]
        
        # Only add remaining words if they look meaningful
        if remaining_words and not semantic_terms:
            # Filter out things that look like IDs or numbers
            meaningful_words = [w for w in remaining_words 
                               if not re.match(r'^[a-z]?\d+$', w)]
            semantic_terms.extend(meaningful_words[:5])  # Limit to 5 terms
        
        return semantic_terms
    
    def _calculate_confidence(self, parsed: ParsedQuery) -> float:
        """Calculate confidence score for parsing."""
        confidence = 1.0
        
        # Lower confidence if we have semantic terms (couldn't fully parse)
        if parsed.semantic_terms:
            confidence -= 0.2 * len(parsed.semantic_terms)
        
        # Higher confidence if we have specific IDs
        if parsed.bet_ids or parsed.customer_ids:
            confidence = max(confidence, 0.9)
        
        # Higher confidence for explicit filters
        if parsed.filters:
            confidence = max(confidence, 0.8)
        
        return max(0.1, min(1.0, confidence))


# Singleton instance
_parser: Optional[QueryParser] = None


def get_query_parser() -> QueryParser:
    """Get the singleton QueryParser instance."""
    global _parser
    if _parser is None:
        _parser = QueryParser()
    return _parser
