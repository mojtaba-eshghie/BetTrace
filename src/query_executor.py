"""
Unified Query Executor for the Sportsbook RAG Assistant.

Executes ParsedQuery objects using the appropriate strategy:
- Pure SQL for structured queries
- Pure embedding search for semantic queries
- Hybrid (SQL filter + embedding rank) for mixed queries

This module bridges the QueryParser output with the retrieval and
calculator infrastructure.
"""

from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

from .query_parser import ParsedQuery, QueryType, AggregationType, get_query_parser
from .models import Bet, RetrievalResult
from .database import Database
from .retrieval import Retriever
from .calculator import SafeCalculator, CalculationRequest, CalculationType


@dataclass
class ExecutionResult:
    """Result of query execution."""
    results: List[RetrievalResult]      # Retrieved bet records
    total_count: int                     # Total matching records (may exceed len(results))
    stats_context: Optional[str]         # Pre-computed statistics for LLM context
    parsed_query: ParsedQuery            # The parsed query (for debugging/logging)
    execution_path: str                  # Which path was used: "sql", "semantic", "hybrid"


class QueryExecutor:
    """
    Executes parsed queries using the optimal strategy.
    
    Supports:
    - Entity lookups (bet IDs, customer IDs)
    - Filtered queries (sport, status, incident, etc.)
    - Aggregations (count, sum, avg)
    - Top/Bottom N rankings
    - Semantic search
    - Hybrid search (filter + semantic)
    """
    
    def __init__(self, db: Database, retriever: Retriever, calculator: SafeCalculator):
        """
        Initialize the executor with required dependencies.
        
        Args:
            db: Database instance for direct queries
            retriever: Retriever for semantic/hybrid search
            calculator: SafeCalculator for aggregations
        """
        self.db = db
        self.retriever = retriever
        self.calculator = calculator
        self.parser = get_query_parser()
    
    def execute(self, query: str, top_k: int = 10) -> ExecutionResult:
        """
        Execute a natural language query.
        
        Args:
            query: Natural language query string
            top_k: Maximum results to return
            
        Returns:
            ExecutionResult with results, stats, and metadata
        """
        # Parse the query
        parsed = self.parser.parse(query)


        # print("+++++++ Parsed Query +++++++")
        # print(parsed.query_type)
        # print("++++++++++++++++++++++++++++")
        
        # Route to appropriate handler based on query type
        if parsed.query_type == QueryType.ENTITY_LOOKUP:
            return self._execute_entity_lookup(parsed, top_k)
        
        elif parsed.query_type == QueryType.TOP_N:
            return self._execute_top_n(parsed, top_k)
        
        elif parsed.query_type == QueryType.AGGREGATE:
            return self._execute_aggregate(parsed, top_k)
        
        elif parsed.query_type == QueryType.FILTERED:
            return self._execute_filtered(parsed, top_k)
        
        elif parsed.query_type == QueryType.HYBRID:
            return self._execute_hybrid(parsed, top_k)
        
        else:  # QueryType.SEMANTIC
            return self._execute_semantic(parsed, top_k)
    
    # ==========================================================================
    # Execution Strategies
    # ==========================================================================
    
    def _execute_entity_lookup(self, parsed: ParsedQuery, top_k: int) -> ExecutionResult:
        """Execute direct entity lookup by IDs."""
        
        # Handle invalid entity references (e.g., "customer F029")
        if parsed.invalid_entity_reference:
            return ExecutionResult(
                results=[],
                total_count=0,
                stats_context=None,
                parsed_query=parsed,
                execution_path="invalid_entity"
            )
        
        results = []
        
        # Look up bet IDs
        for bet_id in parsed.bet_ids:
            bet = self.db.get_by_bet_id(bet_id)
            if bet:
                results.append(RetrievalResult(bet=bet, score=1.0, match_type="exact"))
        
        # Look up customer IDs
        for customer_id in parsed.customer_ids:
            customer_bets = self.db.get_by_customer_id(customer_id)
            for bet in customer_bets:
                results.append(RetrievalResult(bet=bet, score=1.0, match_type="customer"))
        
        # Compute stats if we have results
        stats_context = None
        if results:
            if parsed.customer_ids:
                stats_context = self._compute_customer_stats(parsed.customer_ids, results)
            elif parsed.bet_ids:
                stats_context = self._compute_bet_stats(results)
        
        return ExecutionResult(
            results=results[:top_k],
            total_count=len(results),
            stats_context=stats_context,
            parsed_query=parsed,
            execution_path="sql_lookup"
        )
    
    def _execute_top_n(self, parsed: ParsedQuery, top_k: int) -> ExecutionResult:
        """Execute top/bottom N ranking query."""
        limit = parsed.limit or 5
        column = parsed.sort_by or "stake_gbp"  # Default to stake
        desc = parsed.sort_order == "desc" or parsed.aggregation == AggregationType.TOP_N
        
        # Build filters for calculator
        calc_filters = self._build_calc_filters(parsed.filters)
        
        # Execute via calculator
        calc_result = self.calculator.execute(CalculationRequest(
            calc_type=CalculationType.TOP_N if desc else CalculationType.BOTTOM_N,
            column=column,
            filters=calc_filters,
            limit=limit
        ))
        
        # Convert to RetrievalResults
        results = []
        for record in calc_result.value:
            bet = self.db.get_by_bet_id(record['bet_id'])
            if bet:
                results.append(RetrievalResult(
                    bet=bet,
                    score=1.0,
                    match_type=f"top_n_{column}"
                ))
        
        # Compute stats context
        stats_context = self._compute_top_n_stats(parsed, calc_result.value, column, desc)
        
        return ExecutionResult(
            results=results,
            total_count=len(results),
            stats_context=stats_context,
            parsed_query=parsed,
            execution_path="sql_top_n"
        )
    
    def _execute_aggregate(self, parsed: ParsedQuery, top_k: int) -> ExecutionResult:
        """Execute aggregation query (count, sum, avg)."""
        calc_filters = self._build_calc_filters(parsed.filters)
        db_filters = self._build_db_filters(parsed)
        
        # Get sample results for citation
        if db_filters:
            sample_bets = self.db.advanced_filter(**db_filters, limit=top_k)
        else:
            sample_bets = self.db.get_all_bets()[:top_k]
        
        results = [
            RetrievalResult(bet=bet, score=1.0, match_type="aggregate_sample")
            for bet in sample_bets
        ]
        
        # Compute total count
        count_result = self.calculator.count_bets(**calc_filters) if calc_filters else self.calculator.count_bets()
        total_count = count_result.value
        
        # Compute stats context
        stats_context = self._compute_aggregate_stats(parsed, calc_filters)
        
        return ExecutionResult(
            results=results,
            total_count=total_count,
            stats_context=stats_context,
            parsed_query=parsed,
            execution_path="sql_aggregate"
        )
    
    def _execute_filtered(self, parsed: ParsedQuery, top_k: int) -> ExecutionResult:
        """Execute filtered query (SQL WHERE only)."""
        # Build database filters
        db_filters = self._build_db_filters(parsed)
        
        # Execute filter
        bets = self.db.advanced_filter(**db_filters, limit=top_k * 2)  # Get extra for ranking
        
        # Apply sorting if specified
        if parsed.sort_by:
            reverse = parsed.sort_order == "desc"
            bets = sorted(bets, key=lambda b: getattr(b, parsed.sort_by, 0), reverse=reverse)
        
        results = [
            RetrievalResult(bet=bet, score=1.0, match_type="filtered")
            for bet in bets[:top_k]
        ]
        
        # Get total count
        all_bets = self.db.advanced_filter(**db_filters)
        total_count = len(all_bets)
        
        # Compute stats
        calc_filters = self._build_calc_filters(parsed.filters)
        stats_context = self._compute_filter_stats(parsed, calc_filters)
        
        return ExecutionResult(
            results=results,
            total_count=total_count,
            stats_context=stats_context,
            parsed_query=parsed,
            execution_path="sql_filtered"
        )
    
    def _execute_hybrid(self, parsed: ParsedQuery, top_k: int) -> ExecutionResult:
        """Execute hybrid query (SQL filter + semantic ranking)."""
        # First: SQL filter to narrow candidates
        db_filters = self._build_db_filters(parsed)
        candidates = self.db.advanced_filter(**db_filters)
        
        if not candidates:
            return ExecutionResult(
                results=[],
                total_count=0,
                stats_context=None,
                parsed_query=parsed,
                execution_path="hybrid_empty"
            )
        
        # Second: Try semantic ranking of candidates if we have semantic terms
        results = []
        if parsed.semantic_terms and hasattr(self.retriever, 'semantic_search'):
            # Build a semantic query from the terms
            semantic_query = ' '.join(parsed.semantic_terms)
            try:
                # Get semantic results
                semantic_results = self.retriever.semantic_search(semantic_query, top_k=top_k * 2)
                # Filter to only candidates
                candidate_ids = {b.bet_id for b in candidates}
                results = [r for r in semantic_results if r.bet.bet_id in candidate_ids][:top_k]
            except Exception:
                # Semantic search failed, fall back to filtered results
                pass
        
        # If semantic ranking didn't work, use filtered results directly
        if not results:
            results = [
                RetrievalResult(bet=bet, match_type="filtered_fallback")
                for bet in candidates[:top_k]
            ]
        
        # Compute stats
        calc_filters = self._build_calc_filters(parsed.filters)
        stats_context = self._compute_filter_stats(parsed, calc_filters)
        
        return ExecutionResult(
            results=results,
            total_count=len(candidates),
            stats_context=stats_context,
            parsed_query=parsed,
            execution_path="hybrid"
        )
    
    def _execute_semantic(self, parsed: ParsedQuery, top_k: int) -> ExecutionResult:
        """
        Execute semantic search using team-level embeddings.
        
        Detects if query is looking for a team/player name and uses team-only
        search for best results (no document embedding noise).
        """
        query = parsed.original_query
        
        # Detect if this is a team/player name search
        # Indicators: short meaningful terms, asking about specific team
        team_search = self._is_team_search(parsed)
        
        try:
            # Use lower threshold for team searches (want max recall)
            threshold = 0.7 if team_search else None  # None = use default
            
            results = self.retriever.semantic_search(
                query, 
                top_k=top_k,
                threshold=threshold,
                use_dual_embeddings=True,
                team_only=team_search  # Pure team search if detected
            )
        except Exception as e:
            # Semantic search failed (no API key, etc.)
            results = []
        
        return ExecutionResult(
            results=results,
            total_count=len(results),
            stats_context=None,
            parsed_query=parsed,
            execution_path="semantic_team_only" if team_search else ("semantic_team" if results else "semantic_empty")
        )
    
    def _is_team_search(self, parsed: ParsedQuery) -> bool:
        """
        Detect if query is looking for a specific team/player name.
        
        Returns True if:
        - Query has short, meaningful search terms (likely team/player names)
        - Query uses patterns like "involving X", "X bets", "bets on X"
        """
        # Common filler words to ignore
        filler_words = {
            'all', 'bets', 'bet', 'involving', 'involves', 'with', 'for',
            'on', 'the', 'a', 'an', 'that', 'which', 'find', 'show', 'get',
            'list', 'event', 'events', 'team', 'teams', 'game', 'games',
            'match', 'matches', 'player', 'players'
        }
        
        # Extract meaningful terms from semantic_terms
        meaningful = [
            t.lower().rstrip('.?,!') 
            for t in parsed.semantic_terms 
            if t.lower().rstrip('.?,!') not in filler_words and len(t) >= 2
        ]
        
        # If we have 1-3 short meaningful terms, likely a team/player search
        if 1 <= len(meaningful) <= 3:
            # Check if terms look like names (capitalized words, short words)
            return True
        
        # Check for patterns in original query
        query_lower = parsed.original_query.lower()
        team_patterns = [
            'involving ', 'bets on ', 'bets for ', 'games with ',
            ' vs ', ' versus ', 'match against '
        ]
        for pattern in team_patterns:
            if pattern in query_lower:
                return True
        
        return False
    
    # ==========================================================================
    # Filter Building Helpers
    # ==========================================================================
    
    def _build_calc_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Convert parsed filters to calculator format."""
        if not filters:
            return {}
        
        calc_filters = {}
        
        # Direct mappings
        if "sport" in filters:
            calc_filters["sport"] = filters["sport"]
        if "status" in filters:
            calc_filters["status"] = filters["status"]
        if "incident_tag" in filters:
            calc_filters["incident_tag"] = filters["incident_tag"]
        
        # Range filters need special handling for calculator
        if "min_stake" in filters:
            calc_filters["stake_gbp"] = calc_filters.get("stake_gbp", {})
            calc_filters["stake_gbp"]["gte"] = filters["min_stake"]
        if "max_stake" in filters:
            calc_filters["stake_gbp"] = calc_filters.get("stake_gbp", {})
            calc_filters["stake_gbp"]["lte"] = filters["max_stake"]
        if "min_delay" in filters:
            calc_filters["price_delay_ms"] = calc_filters.get("price_delay_ms", {})
            calc_filters["price_delay_ms"]["gte"] = filters["min_delay"]
        if "max_delay" in filters:
            calc_filters["price_delay_ms"] = calc_filters.get("price_delay_ms", {})
            calc_filters["price_delay_ms"]["lte"] = filters["max_delay"]
        
        return calc_filters
    
    def _build_db_filters(self, parsed: ParsedQuery) -> Dict[str, Any]:
        """Convert parsed query to database filter format."""
        db_filters = {}
        
        filters = parsed.filters
        
        if "sport" in filters:
            db_filters["sports"] = [filters["sport"]]
        if "status" in filters:
            db_filters["statuses"] = [filters["status"]]
        if "incident_tag" in filters:
            db_filters["incident_tags"] = [filters["incident_tag"]]
        if "min_stake" in filters:
            db_filters["min_stake"] = filters["min_stake"]
        if "max_stake" in filters:
            db_filters["max_stake"] = filters["max_stake"]
        if "min_delay" in filters:
            db_filters["min_delay"] = filters["min_delay"]
        if "max_delay" in filters:
            db_filters["max_delay"] = filters["max_delay"]
        
        return db_filters
    
    # ==========================================================================
    # Stats Context Building
    # ==========================================================================
    
    def _compute_customer_stats(self, customer_ids: List[str], results: List[RetrievalResult]) -> str:
        """Compute statistics for customer lookup."""
        # print(f"***** We are here 1 *****")
        lines = ["=" * 60]
        lines.append("COMPUTED FACTS (pre-calculated, DO NOT recalculate)")
        lines.append("=" * 60)
        lines.append(f"Customer(s): {', '.join(customer_ids)}")
        lines.append("")
        
        bets = [r.bet for r in results]
        total_stake = sum(b.stake_gbp for b in bets)
        avg_stake = total_stake / len(bets) if bets else 0
        avg_delay = sum(b.price_delay_ms for b in bets) / len(bets) if bets else 0
        max_delay = max((b.price_delay_ms for b in bets), default=0)
        
        status_counts = {}
        for b in bets:
            status_counts[b.status] = status_counts.get(b.status, 0) + 1
        
        lines.append(f"• Total Bets: {len(bets)}")
        lines.append(f"• Total Stake: £{total_stake:.2f}")
        lines.append(f"• Average Stake: £{avg_stake:.2f}")
        lines.append(f"• Average Delay: {avg_delay:.0f}ms")
        lines.append(f"• Maximum Delay: {max_delay}ms")
        lines.append(f"• Status Breakdown: {status_counts}")
        lines.append("")
        lines.append("⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _compute_bet_stats(self, results: List[RetrievalResult]) -> str:
        """Compute statistics for bet lookup."""
        # print(f"***** We are here 2 *****")
        lines = ["=" * 60]
        lines.append("COMPUTED FACTS (pre-calculated, DO NOT recalculate)")
        lines.append("=" * 60)
        
        for r in results:
            bet = r.bet
            lines.append(f"Bet {bet.bet_id}:")
            lines.append(f"  • Customer: {bet.customer_id}")
            lines.append(f"  • Sport: {bet.sport}")
            lines.append(f"  • Event: {bet.event_name}")
            lines.append(f"  • Market: {bet.market} → {bet.selection}")
            lines.append(f"  • Stake: £{bet.stake_gbp:.2f}")
            lines.append(f"  • Status: {bet.status}")
            lines.append(f"  • Incident: {bet.incident_tag}")
            lines.append(f"  • Delay: {bet.price_delay_ms}ms")
            lines.append("")
        
        lines.append("⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _compute_top_n_stats(
        self, 
        parsed: ParsedQuery, 
        records: List[Dict], 
        column: str,
        desc: bool
    ) -> str:
        """Compute statistics for top/bottom N query."""
        # print(f"***** We are here 3 *****")
        lines = ["=" * 60]
        lines.append("COMPUTED FACTS (pre-calculated, DO NOT recalculate)")
        lines.append("=" * 60)
        
        order_word = "Top" if desc else "Bottom"
        column_name = "Stake" if column == "stake_gbp" else "Delay"
        n = len(records)
        
        lines.append(f"{order_word} {n} Bets by {column_name}")
        
        # Add filter context if present
        if parsed.filters:
            filter_parts = []
            if "sport" in parsed.filters:
                filter_parts.append(f"Sport: {parsed.filters['sport']}")
            if "status" in parsed.filters:
                filter_parts.append(f"Status: {parsed.filters['status']}")
            if "incident_tag" in parsed.filters:
                filter_parts.append(f"Incident: {parsed.filters['incident_tag']}")
            if filter_parts:
                lines.append(f"Filters: {', '.join(filter_parts)}")
        
        lines.append("")
        
        # Summary stats
        total_stake = sum(r['stake_gbp'] for r in records)
        avg_delay = sum(r['price_delay_ms'] for r in records) / len(records) if records else 0
        
        lines.append(f"• Total Stake of {order_word} {n}: £{total_stake:.2f}")
        lines.append(f"• Average Delay of {order_word} {n}: {avg_delay:.0f}ms")
        lines.append("")
        
        # Rankings
        lines.append(f"Rankings (by {column_name.lower()}, {'highest' if desc else 'lowest'} first):")
        for i, record in enumerate(records, 1):
            if column == "stake_gbp":
                lines.append(f"  {i}. {record['bet_id']}: £{record['stake_gbp']:.2f} "
                           f"({record['price_delay_ms']}ms, {record['status']}, {record['incident_tag']})")
            else:
                lines.append(f"  {i}. {record['bet_id']}: {record['price_delay_ms']}ms "
                           f"(£{record['stake_gbp']:.2f}, {record['status']}, {record['incident_tag']})")
        
        lines.append("")
        lines.append("⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _compute_aggregate_stats(self, parsed: ParsedQuery, calc_filters: Dict) -> str:
        """Compute statistics for aggregate query."""
        # print(f"***** We are here 4 *****")
        lines = ["=" * 60]
        lines.append("COMPUTED FACTS (pre-calculated, DO NOT recalculate)")
        lines.append("=" * 60)
        
        # Add filter context
        if parsed.filters:
            filter_parts = []
            if "sport" in parsed.filters:
                filter_parts.append(f"Sport: {parsed.filters['sport']}")
            if "status" in parsed.filters:
                filter_parts.append(f"Status: {parsed.filters['status']}")
            if "incident_tag" in parsed.filters:
                filter_parts.append(f"Incident: {parsed.filters['incident_tag']}")
            if "min_delay" in parsed.filters:
                filter_parts.append(f"Min Delay: {parsed.filters['min_delay']}ms")
            if "max_delay" in parsed.filters:
                filter_parts.append(f"Max Delay: {parsed.filters['max_delay']}ms")
            if "min_stake" in parsed.filters:
                filter_parts.append(f"Min Stake: £{parsed.filters['min_stake']}")
            if "max_stake" in parsed.filters:
                filter_parts.append(f"Max Stake: £{parsed.filters['max_stake']}")
            if filter_parts:
                lines.append(f"Filters: {', '.join(filter_parts)}")
        else:
            lines.append("Scope: All Bets")
        lines.append("")
        
        # Compute aggregates with null safety
        count = self.calculator.count_bets(**calc_filters) if calc_filters else self.calculator.count_bets()
        total_stake = self.calculator.sum_stake(**calc_filters) if calc_filters else self.calculator.sum_stake()
        avg_stake = self.calculator.execute(CalculationRequest(
            calc_type=CalculationType.AVG, column="stake_gbp", filters=calc_filters or None
        ))
        customers = self.calculator.customers_affected(**calc_filters) if calc_filters else self.calculator.customers_affected()
        avg_delay = self.calculator.avg_delay(**calc_filters) if calc_filters else self.calculator.avg_delay()
        
        # Format with null safety
        lines.append(f"• Total Bets: {count.value if count.value is not None else 0}")
        lines.append(f"• Total Stake: £{total_stake.value:.2f}" if total_stake.value is not None else "• Total Stake: £0.00")
        lines.append(f"• Average Stake: £{avg_stake.value:.2f}" if avg_stake.value is not None else "• Average Stake: N/A")
        lines.append(f"• Unique Customers: {customers.value if customers.value is not None else 0}")
        lines.append(f"• Average Delay: {avg_delay.value:.0f}ms" if avg_delay.value is not None else "• Average Delay: N/A")
        lines.append("")
        
        # Status breakdown (only if we have filters that don't already filter by status)
        if "status" not in parsed.filters:
            status_breakdown = self.calculator.group_by_status()
            if status_breakdown.value:
                lines.append("Status Breakdown:")
                for status, data in status_breakdown.value.items():
                    lines.append(f"  • {status}: {data['count']} bets, £{data['total']:.2f}")
                lines.append("")
        
        lines.append("⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _compute_filter_stats(self, parsed: ParsedQuery, calc_filters: Dict) -> str:
        """Compute statistics for filtered query."""
        # Same as aggregate stats but with filter context
        return self._compute_aggregate_stats(parsed, calc_filters)


def create_executor(db: Database) -> QueryExecutor:
    """Factory function to create a QueryExecutor with all dependencies."""
    retriever = Retriever(db)
    calculator = SafeCalculator(db.db_path)
    return QueryExecutor(db, retriever, calculator)
