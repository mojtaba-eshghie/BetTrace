"""
RAG (Retrieval-Augmented Generation) module for the Sportsbook Assistant.

Combines retrieval with LLM generation to produce grounded, cited answers.

Key Design: LLMs do NOT do math!
- All calculations are performed by SafeCalculator (SQL-based)
- LLM receives pre-computed facts in COMPUTED FACTS section
- LLM's job is ONLY to narrate and explain, never to calculate
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI

from .config import OPENAI_API_KEY, LLM_MODEL, validate_config
from .models import Bet, RetrievalResult
from .retrieval import Retriever
from .database import Database
from .calculator import SafeCalculator, CalculationRequest, CalculationType


# System prompt for the RAG assistant
SYSTEM_PROMPT = """You are an internal operations assistant for a sports betting company. Your role is to answer questions about bet records accurately using ONLY the provided data and pre-computed statistics.

CRITICAL RULES:
1. For aggregate questions (counts, totals, averages, summaries), answer DIRECTLY from COMPUTED FACTS.
2. DO NOT list individual bets when answering aggregate questions - just state the computed answer.
3. Only describe individual bet records when asked about specific bets or when providing examples.
4. Be CONCISE. A question like "How many bets?" should be answered with "There are 100 bets." not a list.

⚠️ ARITHMETIC PROHIBITION:
- You MUST NOT perform any arithmetic yourself
- You MUST NOT count items by enumerating them
- All numeric facts come from COMPUTED FACTS - quote them exactly
- If a computation is not provided, say "This requires computation"

RESPONSE FORMAT FOR AGGREGATE QUESTIONS:
- State the answer from COMPUTED FACTS in ONE sentence
- Optionally add breakdown details if relevant
- End with "Evidence: [bet_ids]" (just list a few sample IDs)

RESPONSE FORMAT FOR SPECIFIC BET QUESTIONS:
- Describe the specific bet(s) requested
- End with "Evidence: [bet_ids]"

FIELD MEANINGS:
- status: SETTLED (completed), PENDING (in progress), REJECTED (not accepted), VOID (cancelled)  
- incident_tag: NONE (normal), LATENCY_SPIKE (high delay), FEED_OUTAGE (data feed issue), MARKET_SUSPENDED (market closed), MANUAL_REVIEW (flagged for review)
- price_delay_ms: Latency in milliseconds. Normal is ~200ms. Above 1000ms indicates issues."""


@dataclass
class RAGResponse:
    """Response from the RAG system."""
    answer: str
    citations: List[str]  # List of bet_ids used
    retrieved_bets: List[Bet]  # The bets that were retrieved
    query: str
    sufficient_evidence: bool = True
    stats_context: Optional[str] = None  # Pre-computed SQL statistics


class RAGAssistant:
    """
    RAG Assistant that combines retrieval with LLM generation.
    
    Workflow:
    1. Analyze the query to determine retrieval strategy
    2. Retrieve relevant bet records
    3. COMPUTE all needed facts via SafeCalculator (SQL-based, deterministic)
    4. Format context with COMPUTED FACTS section
    5. Generate answer using LLM (narration only, no arithmetic)
    6. Extract citations and return structured response
    
    Key Principle: LLMs cannot do math reliably, so we:
    - Pre-compute ALL numeric values (totals, counts, averages, rankings)
    - Present them as immutable COMPUTED FACTS
    - LLM's job is ONLY to explain and format these facts
    """
    
    def __init__(self, db: Optional[Database] = None):
        """Initialize the RAG assistant."""
        self.db = db or Database()
        self.db.load_embeddings_to_memory()
        self.retriever = Retriever(self.db)
        self.calculator = SafeCalculator(self.db.db_path)
        self._client: Optional[OpenAI] = None
    
    @property
    def client(self) -> OpenAI:
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            validate_config()
            self._client = OpenAI(api_key=OPENAI_API_KEY)
        return self._client
    
    def ask(
        self, 
        query: str, 
        top_k: int = 10,
        include_aggregations: bool = True
    ) -> RAGResponse:
        """
        Answer a question using RAG.
        
        Args:
            query: The user's question
            top_k: Maximum number of bet ROWS to show (aggregations always use full data)
            include_aggregations: Whether to include aggregate stats in context
            
        Returns:
            RAGResponse with answer, citations, and metadata
        """
        # For aggregate queries, show fewer bet records to avoid confusing the LLM
        if self._is_general_aggregate_query(query):
            top_k = min(top_k, 3)  # Only show 3 records for citation purposes
        
        # Step 1: Retrieve relevant bets (for row-level context)
        results, all_results_count = self._retrieve_for_query(query, top_k)
        
        if not results:
            return RAGResponse(
                answer="I couldn't find any relevant bet records for your query. "
                       "Please provide a specific bet_id (e.g., B0042) or customer_id (e.g., C068) "
                       "to look up, or ask about specific incidents like LATENCY_SPIKE or MARKET_SUSPENDED.",
                citations=[],
                retrieved_bets=[],
                query=query,
                sufficient_evidence=False
            )
        
        # Step 2: Compute SQL-based aggregations (ALWAYS on full dataset, not just top_k)
        stats_context = self._compute_sql_aggregations(query)
        
        # Step 3: Format context based on query type
        is_aggregate = self._is_general_aggregate_query(query)
        
        if is_aggregate and stats_context:
            # For aggregate queries: ONLY show computed facts, no bet records
            # This prevents the LLM from listing individual bets
            context = self._build_aggregate_context(stats_context, results, all_results_count)
        else:
            # For specific queries: show bet records for detail
            row_context = self._format_row_context(results, top_k)
            context = self._build_full_context(row_context, stats_context, all_results_count, top_k)
        
        # Step 4: Generate answer
        answer = self._generate_answer(query, context)
        
        # Step 6: Extract and enforce citations
        citations = self._extract_citations(answer, results)
        answer = self._enforce_citations(answer, citations, results)
        
        # Re-extract citations in case we added them
        if not citations and results:
            citations = self._extract_citations(answer, results)
        
        # Step 7: Check if evidence was sufficient
        sufficient = not any(phrase in answer.lower() for phrase in [
            "i need", "please provide", "not enough information",
            "couldn't find", "no records", "insufficient"
        ])
        
        return RAGResponse(
            answer=answer,
            citations=citations,
            retrieved_bets=[r.bet for r in results],
            query=query,
            sufficient_evidence=sufficient,
            stats_context=stats_context
        )
    
    def _retrieve_for_query(
        self, 
        query: str, 
        top_k: int
    ) -> Tuple[List[RetrievalResult], int]:
        """
        Retrieve relevant bets based on query analysis.
        
        Returns:
            Tuple of (results, total_matching_count)
            - results: Limited to top_k for context
            - total_matching_count: Full count for accurate reporting
        """
        query_lower = query.lower()
        
        # Check for MULTIPLE bet IDs - return all matches
        all_bet_ids = self.retriever._extract_all_bet_ids(query)
        if all_bet_ids:
            results = []
            for bid in all_bet_ids:
                result = self.retriever.get_bet(bid)
                if result:
                    results.append(result)
            if results:
                return results, len(results)
            # User asked for specific bet IDs but none found - return empty, don't fall back
            return [], 0
        
        # Check for MULTIPLE customer IDs - return all their bets
        all_customer_ids = self.retriever._extract_all_customer_ids(query)
        if all_customer_ids:
            results = []
            for cid in all_customer_ids:
                customer_results = self.retriever.get_customer_bets(cid)
                results.extend(customer_results)
            if results:
                return results, len(results)
            # User asked for specific customers but none found - return empty, don't fall back
            return [], 0
        
        # Check if user INTENDED to query a customer/bet but we couldn't parse the ID
        # This prevents falling back to semantic search for queries like "customer F029"
        if self._has_entity_intent_but_no_match(query):
            return [], 0
        
        # Check for incident tag - return ALL matching bets
        incident_match = self.retriever._extract_incident_tag(query)
        if incident_match:
            results = self.retriever.filter_by_incident(incident_match)
            return results, len(results)  # Return all for incident queries
        
        # Check for status - return ALL matching bets
        status_match = self.retriever._extract_status(query)
        if status_match:
            results = self.retriever.filter_by_status(status_match)
            return results, len(results)
        
        # Check for top/highest delay queries
        if ("highest" in query_lower or "top" in query_lower) and self.retriever._is_latency_query(query):
            limit = self.retriever._extract_number(query) or 5
            results = self.retriever.get_top_by_delay(limit)
            return results, len(results)
        
        # Check for general aggregate queries - return sample bets for citation
        if self._is_general_aggregate_query(query):
            # For general queries, return a sample of all bets
            # The actual answer comes from COMPUTED FACTS, these are just for citation
            all_bets = self.db.get_all_bets()
            total_count = len(all_bets)
            results = [
                RetrievalResult(bet=bet, match_type="sample")
                for bet in all_bets[:top_k]
            ]
            return results, total_count
        
        # Default: semantic search (this is where top_k matters)
        results = self.retriever.retrieve(query, top_k=top_k)
        return results, len(results)
    
    def _compute_sql_aggregations(self, query: str) -> Optional[str]:
        """
        Compute aggregations via SafeCalculator based on query type.
        
        This ensures:
        1. All math is done deterministically in SQL
        2. LLM receives pre-computed facts (never calculates itself)
        3. Results are formatted clearly as COMPUTED FACTS
        
        The LLM should ONLY report these values, never recalculate them.
        """
        query_lower = query.lower()
        lines = []
        
        # Customer-specific calculations
        customer_id = self.retriever._extract_customer_id(query)
        if customer_id:
            lines.append("=" * 60)
            lines.append("COMPUTED FACTS (pre-calculated, DO NOT recalculate)")
            lines.append("=" * 60)
            lines.append(f"Customer: {customer_id}")
            lines.append("")
            
            # Execute calculations
            count = self.calculator.count_bets(customer_id=customer_id)
            total_stake = self.calculator.sum_stake(customer_id=customer_id)
            avg_stake = self.calculator.execute(CalculationRequest(
                calc_type=CalculationType.AVG, column="stake_gbp",
                filters={"customer_id": customer_id}
            ))
            avg_delay = self.calculator.avg_delay(customer_id=customer_id)
            max_delay = self.calculator.execute(CalculationRequest(
                calc_type=CalculationType.MAX, column="price_delay_ms",
                filters={"customer_id": customer_id}
            ))
            status_breakdown = self.calculator.execute(CalculationRequest(
                calc_type=CalculationType.GROUP_BY, column="bet_id",
                filters={"customer_id": customer_id}, group_by="status"
            ))
            
            lines.append(f"• Total Bets: {count.value}")
            lines.append(f"• Total Stake: £{total_stake.value}")
            lines.append(f"• Average Stake: £{avg_stake.value:.2f}" if avg_stake.value else "• Average Stake: N/A")
            lines.append(f"• Average Delay: {avg_delay.value:.0f}ms" if avg_delay.value else "• Average Delay: N/A")
            lines.append(f"• Maximum Delay: {max_delay.value}ms" if max_delay.value else "• Maximum Delay: N/A")
            lines.append(f"• Status Breakdown: {status_breakdown.value}")
            lines.append("")
            lines.append("⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE")
            lines.append("=" * 60)
            return "\n".join(lines)
        
        # Incident-specific calculations
        incident_tag = self.retriever._extract_incident_tag(query)
        if incident_tag:
            lines.append("=" * 60)
            lines.append("COMPUTED FACTS (pre-calculated, DO NOT recalculate)")
            lines.append("=" * 60)
            lines.append(f"Incident Type: {incident_tag}")
            lines.append("")
            
            count = self.calculator.count_bets(incident_tag=incident_tag)
            customers = self.calculator.customers_affected(incident_tag=incident_tag)
            total_stake = self.calculator.sum_stake(incident_tag=incident_tag)
            avg_delay = self.calculator.avg_delay(incident_tag=incident_tag)
            max_delay = self.calculator.execute(CalculationRequest(
                calc_type=CalculationType.MAX, column="price_delay_ms",
                filters={"incident_tag": incident_tag}
            ))
            
            lines.append(f"• Total Bets Affected: {count.value}")
            lines.append(f"• Unique Customers Affected: {customers.value}")
            lines.append(f"• Total Stake at Risk: £{total_stake.value}")
            lines.append(f"• Average Delay: {avg_delay.value:.0f}ms" if avg_delay.value else "• Average Delay: N/A")
            lines.append(f"• Maximum Delay: {max_delay.value}ms" if max_delay.value else "• Maximum Delay: N/A")
            lines.append("")
            lines.append("⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE")
            lines.append("=" * 60)
            return "\n".join(lines)
        
        # Status-specific calculations
        status = self.retriever._extract_status(query)
        if status:
            lines.append("=" * 60)
            lines.append("COMPUTED FACTS (pre-calculated, DO NOT recalculate)")
            lines.append("=" * 60)
            lines.append(f"Status: {status}")
            lines.append("")
            
            count = self.calculator.count_bets(status=status)
            customers = self.calculator.customers_affected(status=status)
            total_stake = self.calculator.sum_stake(status=status)
            avg_stake = self.calculator.execute(CalculationRequest(
                calc_type=CalculationType.AVG, column="stake_gbp",
                filters={"status": status}
            ))
            avg_delay = self.calculator.avg_delay(status=status)
            incident_breakdown = self.calculator.execute(CalculationRequest(
                calc_type=CalculationType.GROUP_BY, column="bet_id",
                filters={"status": status}, group_by="incident_tag"
            ))
            
            lines.append(f"• Total Bets: {count.value}")
            lines.append(f"• Unique Customers: {customers.value}")
            lines.append(f"• Total Stake: £{total_stake.value}")
            lines.append(f"• Average Stake: £{avg_stake.value:.2f}" if avg_stake.value else "• Average Stake: N/A")
            lines.append(f"• Average Delay: {avg_delay.value:.0f}ms" if avg_delay.value else "• Average Delay: N/A")
            lines.append(f"• Incident Breakdown: {incident_breakdown.value}")
            lines.append("")
            lines.append("⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE")
            lines.append("=" * 60)
            return "\n".join(lines)
        
        # Top delay calculations
        if ("highest" in query_lower or "top" in query_lower) and self.retriever._is_latency_query(query):
            limit = self.retriever._extract_number(query) or 5
            
            lines.append("=" * 60)
            lines.append("COMPUTED FACTS (pre-calculated, DO NOT recalculate)")
            lines.append("=" * 60)
            lines.append(f"Top {limit} Bets by Delay")
            lines.append("")
            
            top_results = self.calculator.top_by_delay(n=limit)
            total_stake = self.calculator.execute(CalculationRequest(
                calc_type=CalculationType.SUM, column="stake_gbp",
                filters={"price_delay_ms": {"gte": 1000}}
            ))
            
            lines.append(f"• High-Latency Bet Count (>1000ms): {len([r for r in top_results.value if r['price_delay_ms'] >= 1000])}")
            lines.append(f"• Total Stake in Top {limit}: £{sum(r['stake_gbp'] for r in top_results.value)}")
            lines.append("")
            lines.append("Rankings (by delay, highest first):")
            for i, bet in enumerate(top_results.value, 1):
                lines.append(f"  {i}. {bet['bet_id']}: {bet['price_delay_ms']}ms (£{bet['stake_gbp']}, {bet['incident_tag']})")
            lines.append("")
            lines.append("⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE")
            lines.append("=" * 60)
            return "\n".join(lines)
        
        # Sport-specific calculations
        sport_match = self._extract_sport(query)
        if sport_match:
            lines.append("=" * 60)
            lines.append("COMPUTED FACTS (pre-calculated, DO NOT recalculate)")
            lines.append("=" * 60)
            lines.append(f"Sport: {sport_match}")
            lines.append("")
            
            count = self.calculator.count_bets(sport=sport_match)
            total_stake = self.calculator.sum_stake(sport=sport_match)
            customers = self.calculator.customers_affected(sport=sport_match)
            status_breakdown = self.calculator.execute(CalculationRequest(
                calc_type=CalculationType.GROUP_BY, column="bet_id",
                filters={"sport": sport_match}, group_by="status"
            ))
            
            lines.append(f"• Total Bets: {count.value}")
            lines.append(f"• Total Stake: £{total_stake.value}")
            lines.append(f"• Unique Customers: {customers.value}")
            lines.append(f"• Status Breakdown: {status_breakdown.value}")
            lines.append("")
            lines.append("⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE")
            lines.append("=" * 60)
            return "\n".join(lines)
        
        # General aggregate queries (no specific filter)
        # Matches: "how many bets", "total stake", "all bets", "overall", etc.
        if self._is_general_aggregate_query(query):
            lines.append("=" * 60)
            lines.append("COMPUTED FACTS (pre-calculated, DO NOT recalculate)")
            lines.append("=" * 60)
            lines.append("Overall Statistics (All Bets)")
            lines.append("")
            
            total_count = self.calculator.count_bets()
            total_stake = self.calculator.sum_stake()
            avg_stake = self.calculator.execute(CalculationRequest(
                calc_type=CalculationType.AVG, column="stake_gbp"
            ))
            customers = self.calculator.customers_affected()
            avg_delay = self.calculator.avg_delay()
            status_breakdown = self.calculator.group_by_status()
            incident_breakdown = self.calculator.group_by_incident()
            
            lines.append(f"• Total Bets: {total_count.value}")
            lines.append(f"• Total Stake: £{total_stake.value}")
            lines.append(f"• Average Stake: £{avg_stake.value:.2f}" if avg_stake.value else "• Average Stake: N/A")
            lines.append(f"• Unique Customers: {customers.value}")
            lines.append(f"• Average Delay: {avg_delay.value:.0f}ms" if avg_delay.value else "• Average Delay: N/A")
            lines.append("")
            lines.append("Status Breakdown:")
            for status, data in status_breakdown.value.items():
                lines.append(f"  • {status}: {data['count']} bets, £{data['total']} total")
            lines.append("")
            lines.append("Incident Breakdown:")
            for incident, data in incident_breakdown.value.items():
                lines.append(f"  • {incident}: {data['count']} bets")
            lines.append("")
            lines.append("⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE")
            lines.append("=" * 60)
            return "\n".join(lines)
        
        return None
    
    def _is_general_aggregate_query(self, query: str) -> bool:
        """
        Detect if a query is asking for general aggregate statistics.
        
        Examples:
        - "How many bets are there?"
        - "What is the total stake?"
        - "Give me an overview of all bets"
        - "Summary of the data"
        """
        query_lower = query.lower()
        
        # Keywords indicating aggregate queries
        aggregate_keywords = [
            "how many", "total", "all bets", "overall", "summary",
            "overview", "count", "sum", "average", "statistics",
            "how much", "entire", "whole", "everything"
        ]
        
        return any(keyword in query_lower for keyword in aggregate_keywords)
    
    def _has_entity_intent_but_no_match(self, query: str) -> bool:
        """
        Detect if user intended to query a specific customer/bet but we couldn't parse it.
        
        This prevents falling back to semantic search for queries like:
        - "customer F029" (invalid prefix)
        - "bet X123" (invalid format)
        - "show me customer abc" (non-numeric ID)
        
        Returns True if we should NOT fall back to semantic search.
        """
        query_lower = query.lower()
        
        # User said "customer" but we didn't extract any customer IDs
        if "customer" in query_lower:
            # Check if there's something that looks like an ID attempt after "customer"
            import re
            # Match "customer" followed by something that looks like an ID attempt
            # (letter + digits, or just digits, or alphanumeric)
            if re.search(r'customer\s+[a-z]?\d+', query_lower):
                return True
            if re.search(r'customer\s+\w+\d+', query_lower):
                return True
        
        # User said "bet" but we didn't extract any bet IDs  
        if "bet " in query_lower or "bets " in query_lower:
            import re
            # Match "bet" followed by something that looks like an ID attempt
            if re.search(r'bets?\s+[a-z]?\d+', query_lower):
                return True
            if re.search(r'bets?\s+\w+\d+', query_lower):
                return True
        
        return False
    
    def _extract_sport(self, query: str) -> Optional[str]:
        """Extract sport name from query."""
        query_lower = query.lower()
        sports = {
            "football": "football",
            "soccer": "football",
            "tennis": "tennis",
            "basketball": "basketball",
            "nba": "basketball"
        }
        for keyword, sport in sports.items():
            if keyword in query_lower:
                return sport
        return None
    
    def _format_row_context(self, results: List[RetrievalResult], max_rows: int) -> str:
        """Format individual bet rows for context (limited to max_rows)."""
        lines = ["=== BET RECORDS (for evidence/citations) ===\n"]
        
        display_results = results[:max_rows]
        
        for i, result in enumerate(display_results, 1):
            bet = result.bet
            lines.append(f"Record {i}:")
            lines.append(f"  Bet ID: {bet.bet_id}")
            lines.append(f"  Customer: {bet.customer_id}")
            lines.append(f"  Sport: {bet.sport}")
            lines.append(f"  Event: {bet.event_name}")
            lines.append(f"  Market: {bet.market}")
            lines.append(f"  Selection: {bet.selection}")
            lines.append(f"  Stake: £{bet.stake_gbp}")
            lines.append(f"  Status: {bet.status}")
            lines.append(f"  Incident: {bet.incident_tag}")
            lines.append(f"  Price Delay: {bet.price_delay_ms}ms")
            lines.append("")
        
        return "\n".join(lines)
    
    def _build_aggregate_context(
        self,
        stats_context: str,
        results: List[RetrievalResult],
        total_count: int
    ) -> str:
        """
        Build context for aggregate queries - ONLY computed facts, no bet records.
        
        This prevents the LLM from listing individual bets when asked for totals/summaries.
        The LLM only sees:
        1. The computed statistics
        2. A list of bet IDs for citation (no details)
        """
        parts = []
        
        # Add computed facts (this is the ONLY data the LLM should use)
        parts.append(stats_context)
        parts.append("")
        parts.append("─" * 60)
        parts.append("ANSWER FORMAT FOR THIS AGGREGATE QUESTION:")
        parts.append("• State the totals from COMPUTED FACTS above (1-3 sentences)")
        parts.append("• DO NOT describe individual bets")
        parts.append("• End with: Evidence: [sample bet IDs from list below]")
        parts.append("─" * 60)
        parts.append("")
        
        # Only provide bet IDs for citation - NO DETAILS
        parts.append(f"Available bet IDs for citation ({total_count} total):")
        bet_ids = [r.bet.bet_id for r in results[:10]]  # Just first 10 IDs
        parts.append(", ".join(bet_ids))
        if total_count > 10:
            parts.append(f"... and {total_count - 10} more")
        
        return "\n".join(parts)
    
    def _build_full_context(
        self, 
        row_context: str, 
        stats_context: Optional[str],
        total_count: int,
        shown_count: int
    ) -> str:
        """
        Combine computed facts and row context for the LLM.
        
        Structure:
        1. COMPUTED FACTS (pre-calculated values the LLM must use)
        2. BET RECORDS (for evidence/citations only)
        
        The LLM should NEVER recalculate anything from the bet records.
        """
        parts = []
        
        # Add computed facts first (this is authoritative)
        if stats_context:
            parts.append(stats_context)
            parts.append("")
            parts.append("─" * 60)
            parts.append("YOUR ANSWER MUST USE THE COMPUTED FACTS ABOVE.")
            parts.append("For aggregate questions: state the computed total, nothing more.")
            parts.append("DO NOT list or describe individual bets for aggregate questions.")
            parts.append("The bet records below are ONLY for the 'Evidence:' citation.")
            parts.append("─" * 60)
            parts.append("")
        
        # Note if we're showing a subset
        if total_count > shown_count:
            parts.append(f"(Sample of {shown_count} from {total_count} total records - for citation only)\n")
        
        # Add row context (minimal for aggregate queries)
        parts.append(row_context)
        
        return "\n".join(parts)
    
    # Keep old method for backwards compatibility but mark deprecated
    def _format_context(
        self, 
        results: List[RetrievalResult],
        query: str,
        include_aggregations: bool
    ) -> str:
        """DEPRECATED: Use _format_row_context + _compute_sql_aggregations instead."""
        return self._format_row_context(results, len(results))
    
    def _generate_answer(self, query: str, context: str) -> str:
        """
        Generate an answer using the LLM.
        
        The LLM receives pre-computed facts and must NOT do any arithmetic.
        Its job is ONLY to:
        1. Report the computed values exactly as given
        2. Add context/explanation from individual bet records
        3. Cite relevant bet_ids
        """
        
        # Detect if this is an aggregate question
        query_lower = query.lower()
        is_aggregate = any(kw in query_lower for kw in [
            "how many", "total", "count", "sum", "average", "overview", "summary"
        ])
        
        if is_aggregate:
            instruction = """INSTRUCTIONS:
1. Answer the question DIRECTLY using the COMPUTED FACTS values
2. Keep your answer CONCISE (1-3 sentences for simple questions)
3. DO NOT list individual bets - just state the computed totals
4. End with "Evidence: [bet_ids]" listing a few sample bet IDs

Example good answer: "There are 100 bets with a total stake of £2,765.00."
Example bad answer: "Here are the bets: B0001 has £10..." (DO NOT DO THIS)"""
        else:
            instruction = """INSTRUCTIONS:
1. Answer the question using the bet records provided
2. If COMPUTED FACTS are relevant, include those values
3. End with "Evidence: [bet_ids]" citing relevant bets"""
        
        user_message = f"""Question: {query}

{context}

{instruction}"""
        
        response = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            # Note: GPT-5 models only support temperature=1 (default)
            max_completion_tokens=1000
        )
        
        answer = response.choices[0].message.content
        
        # Handle empty responses
        if not answer or not answer.strip():
            # Fallback: generate a basic answer from the context
            return self._generate_fallback_answer(query, context)
        
        return answer.strip()
    
    def _generate_fallback_answer(self, query: str, context: str) -> str:
        """Generate a fallback answer when LLM returns empty response."""
        import re
        
        # Extract stats from context if present
        stats_lines = []
        total_bets_from_stats = None
        
        if "COMPLETE" in context and "STATISTICS" in context:
            # Parse the stats section
            in_stats = False
            for line in context.split('\n'):
                if "COMPLETE" in line and "STATISTICS" in line:
                    in_stats = True
                    continue
                if in_stats:
                    if line.startswith("===") or line.startswith("IMPORTANT"):
                        break
                    if line.strip():
                        stats_lines.append(line.strip())
                        # Extract total bets count
                        if "Total Bets:" in line:
                            match = re.search(r'Total Bets:\s*(\d+)', line)
                            if match:
                                total_bets_from_stats = int(match.group(1))
        
        # Extract bet records from context
        bet_records = self._parse_bet_records_from_context(context)
        # Filter to only records that have bet_id (defensive check)
        bet_records = [b for b in bet_records if 'bet_id' in b]
        bet_ids = [b['bet_id'] for b in bet_records]
        
        if not bet_ids and not stats_lines:
            return "I found relevant records but couldn't generate a summary. Please try rephrasing your question."
        
        # Build a proper fallback response
        answer_parts = []
        
        # If we have stats, show them
        if stats_lines:
            answer_parts.append("Based on the database statistics:\n")
            for line in stats_lines[:10]:
                answer_parts.append(f"• {line}")
            answer_parts.append("")
            
            actual_count = total_bets_from_stats or len(bet_ids)
            if bet_ids:
                if actual_count <= 10:
                    answer_parts.append(f"This covers {actual_count} bet(s): {', '.join(bet_ids)}")
                else:
                    answer_parts.append(f"This covers {actual_count} bet(s). Sample: {', '.join(bet_ids[:10])}")
        
        # If no stats but we have bet records, generate a comparison/summary
        elif bet_records:
            if len(bet_records) == 1:
                b = bet_records[0]
                answer_parts.append(f"**{b.get('bet_id', 'Unknown')}**: {b.get('customer', 'Unknown')} placed a £{b.get('stake', '?')} {b.get('market', '')} bet on {b.get('event', 'Unknown')}.")
                answer_parts.append(f"• Status: {b.get('status', 'Unknown')}")
                answer_parts.append(f"• Incident: {b.get('incident', 'NONE')}")
                answer_parts.append(f"• Delay: {b.get('delay', '?')}ms")
            else:
                # Multiple bets - generate comparison
                answer_parts.append(f"Comparison of {len(bet_records)} bets:\n")
                for b in bet_records:
                    answer_parts.append(f"**{b.get('bet_id', 'Unknown')}** ({b.get('customer', '?')}):")
                    answer_parts.append(f"  • Event: {b.get('event', 'Unknown')}")
                    answer_parts.append(f"  • Stake: £{b.get('stake', '?')}, Market: {b.get('market', '?')}")
                    answer_parts.append(f"  • Status: {b.get('status', '?')}, Incident: {b.get('incident', 'NONE')}")
                    answer_parts.append(f"  • Delay: {b.get('delay', '?')}ms")
                    answer_parts.append("")
        
        if bet_ids:
            answer_parts.append(f"\nEvidence: {', '.join(bet_ids)}")
        
        return "\n".join(answer_parts)
    
    def _parse_bet_records_from_context(self, context: str) -> List[dict]:
        """Parse bet records from the context string."""
        import re
        records = []
        current_record = None  # Start with None instead of empty dict
        
        for line in context.split('\n'):
            line = line.strip()
            if line.startswith('Bet ID:'):
                # Save previous record if exists
                if current_record and 'bet_id' in current_record:
                    records.append(current_record)
                # Start new record
                current_record = {'bet_id': line.split(':', 1)[1].strip()}
            elif current_record is not None:  # Only process if we have a record started
                if line.startswith('Customer:'):
                    current_record['customer'] = line.split(':', 1)[1].strip()
                elif line.startswith('Event:'):
                    current_record['event'] = line.split(':', 1)[1].strip()
                elif line.startswith('Market:'):
                    current_record['market'] = line.split(':', 1)[1].strip()
                elif line.startswith('Stake:'):
                    stake_str = line.split(':', 1)[1].strip().replace('£', '')
                    current_record['stake'] = stake_str
                elif line.startswith('Status:'):
                    current_record['status'] = line.split(':', 1)[1].strip()
                elif line.startswith('Incident:'):
                    current_record['incident'] = line.split(':', 1)[1].strip()
                elif line.startswith('Price Delay:'):
                    delay_str = line.split(':', 1)[1].strip().replace('ms', '')
                    current_record['delay'] = delay_str
        
        # Don't forget the last record
        if current_record and 'bet_id' in current_record:
            records.append(current_record)
        
        return records
    
    def _extract_citations(
        self, 
        answer: str, 
        results: List[RetrievalResult]
    ) -> List[str]:
        """Extract bet_id citations from the answer."""
        
        # Get all valid bet IDs from results
        valid_ids = {r.bet.bet_id for r in results}
        
        # Find all B#### patterns in the answer
        import re
        found_ids = re.findall(r'\bB\d{4}\b', answer)
        
        # Filter to only valid IDs and preserve order while deduplicating
        citations = []
        seen = set()
        for bid in found_ids:
            if bid in valid_ids and bid not in seen:
                citations.append(bid)
                seen.add(bid)
        
        return citations
    
    def _enforce_citations(
        self,
        answer: str,
        extracted_citations: List[str],
        results: List[RetrievalResult]
    ) -> str:
        """
        Enforce that the answer includes citations.
        
        Rules:
        1. If LLM included "Evidence: ..." with valid citations → keep as-is
        2. If LLM forgot citations but we have results → append Evidence line
        3. If citations are in answer but not in Evidence format → append Evidence line
        
        This ensures citations are ALWAYS present when we have retrieved results.
        """
        import re
        
        if not results:
            return answer
        
        # Check if answer already has a proper Evidence line
        evidence_pattern = r'Evidence:\s*\[?([^\]]+)\]?'
        has_evidence_line = bool(re.search(evidence_pattern, answer, re.IGNORECASE))
        
        # Get bet IDs from results for fallback
        result_ids = [r.bet.bet_id for r in results]
        
        if extracted_citations and has_evidence_line:
            # LLM did its job - keep the answer as-is
            return answer
        
        # Determine which citations to use
        if extracted_citations:
            # LLM mentioned bet IDs in the answer but maybe not in Evidence format
            citation_ids = extracted_citations
        else:
            # LLM forgot to cite - use the retrieved bet IDs
            # Limit to first 5 to keep it readable
            citation_ids = result_ids[:5]
        
        # Remove any malformed Evidence line and append a proper one
        answer = re.sub(r'\n*Evidence:.*$', '', answer, flags=re.IGNORECASE | re.MULTILINE).strip()
        
        # Append proper Evidence line
        evidence_line = f"\n\nEvidence: [{', '.join(citation_ids)}]"
        return answer + evidence_line
    
    def interactive_session(self):
        """Run an interactive Q&A session."""
        print("\n" + "="*60)
        print("SPORTSBOOK RAG ASSISTANT")
        print("="*60)
        print("Ask questions about bet records. Type 'quit' to exit.\n")
        
        while True:
            try:
                query = input("\n🎯 Your question: ").strip()
                
                if query.lower() in ('quit', 'exit', 'q'):
                    print("\nGoodbye!")
                    break
                
                if not query:
                    continue
                
                print("\n⏳ Thinking...\n")
                response = self.ask(query)
                
                print("📋 Answer:")
                print("-" * 40)
                print(response.answer)
                print("-" * 40)
                
                if response.citations:
                    print(f"\n📎 Citations: {', '.join(response.citations)}")
                
                print(f"📊 Retrieved {len(response.retrieved_bets)} bet(s)")
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")


def create_rag_assistant(db: Optional[Database] = None) -> RAGAssistant:
    """Factory function to create a RAG assistant."""
    return RAGAssistant(db)
