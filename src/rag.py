"""
RAG (Retrieval-Augmented Generation) module for the Sportsbook Assistant.

Combines retrieval with LLM generation to produce grounded, cited answers.
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI

from .config import OPENAI_API_KEY, LLM_MODEL, validate_config
from .models import Bet, RetrievalResult
from .retrieval import Retriever
from .database import Database


# System prompt for the RAG assistant
SYSTEM_PROMPT = """You are an internal operations assistant for a sports betting company. Your role is to answer questions about bet records accurately and concisely.

CRITICAL RULES:
1. ONLY use information from the provided bet records. Never make up or assume data.
2. ALWAYS cite the bet_id(s) that support your answer.
3. If the provided records don't contain enough information to answer, say so clearly and suggest what additional information is needed (e.g., "I need the bet_id" or "I need the customer_id").
4. Be concise but thorough. Focus on the operational insights.
5. When explaining why something happened (e.g., rejection), look at the incident_tag and status fields.
6. For latency issues, note the price_delay_ms values and compare to normal (~200ms average).

RESPONSE FORMAT:
- Provide a clear, direct answer first
- Include relevant details from the bet records
- End with "Evidence: [bet_ids]" listing all bet IDs used

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
    3. Format context from retrieved records
    4. Generate answer using LLM with grounding instructions
    5. Extract citations and return structured response
    """
    
    def __init__(self, db: Optional[Database] = None):
        """Initialize the RAG assistant."""
        self.db = db or Database()
        self.db.load_embeddings_to_memory()
        self.retriever = Retriever(self.db)
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
        
        # Step 3: Format row context (limited to top_k for readability)
        row_context = self._format_row_context(results, top_k)
        
        # Step 4: Combine contexts
        context = self._build_full_context(row_context, stats_context, all_results_count, top_k)
        
        # Step 5: Generate answer
        answer = self._generate_answer(query, context)
        
        # Step 6: Extract citations
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
        
        # Check for specific bet ID - return exact match
        bet_id_match = self.retriever._extract_bet_id(query)
        if bet_id_match:
            result = self.retriever.get_bet(bet_id_match)
            if result:
                return [result], 1
            return [], 0
        
        # Check for customer ID - return ALL customer bets (no truncation)
        customer_id_match = self.retriever._extract_customer_id(query)
        if customer_id_match:
            results = self.retriever.get_customer_bets(customer_id_match)
            return results, len(results)  # Return all for customer queries
        
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
        
        # Default: semantic search (this is where top_k matters)
        results = self.retriever.retrieve(query, top_k=top_k)
        return results, len(results)
    
    def _compute_sql_aggregations(self, query: str) -> Optional[str]:
        """
        Compute aggregations via SQL based on query type.
        
        This ensures aggregations are ALWAYS computed on the full dataset,
        not just the top_k rows shown to the LLM.
        """
        query_lower = query.lower()
        lines = []
        
        # Customer-specific aggregations
        customer_id = self.retriever._extract_customer_id(query)
        if customer_id:
            stats = self.db.get_customer_stats(customer_id)
            if stats:
                lines.append("=== COMPLETE CUSTOMER STATISTICS (from database) ===")
                lines.append(f"Customer: {stats['customer_id']}")
                lines.append(f"Total Bets: {stats['total_bets']}")
                lines.append(f"Total Stake: £{stats['total_stake']:.2f}")
                lines.append(f"Average Stake: £{stats['avg_stake']:.2f}")
                lines.append(f"Average Delay: {stats['avg_delay']:.0f}ms")
                lines.append(f"Delay Range: {stats['min_delay']}ms - {stats['max_delay']}ms")
                lines.append(f"Status Breakdown: {stats['status_breakdown']}")
                lines.append(f"Incident Breakdown: {stats['incident_breakdown']}")
                lines.append(f"Sport Breakdown: {stats['sport_breakdown']}")
                lines.append("")
                return "\n".join(lines)
        
        # Incident-specific aggregations
        incident_tag = self.retriever._extract_incident_tag(query)
        if incident_tag:
            stats = self.db.get_incident_stats(incident_tag)
            if stats:
                lines.append("=== COMPLETE INCIDENT STATISTICS (from database) ===")
                lines.append(f"Incident Type: {stats['incident_tag']}")
                lines.append(f"Total Bets Affected: {stats['total_bets']}")
                lines.append(f"Unique Customers Affected: {stats['unique_customers']}")
                lines.append(f"Total Stake at Risk: £{stats['total_stake']:.2f}")
                lines.append(f"Average Stake: £{stats['avg_stake']:.2f}")
                lines.append(f"Average Delay: {stats['avg_delay']:.0f}ms")
                lines.append(f"Delay Range: {stats['min_delay']}ms - {stats['max_delay']}ms")
                lines.append(f"Status Breakdown: {stats['status_breakdown']}")
                lines.append("")
                lines.append("Customers Ranked by Impact:")
                for i, cust in enumerate(stats['customers_affected'], 1):
                    lines.append(f"  {i}. {cust['customer_id']}: {cust['bet_count']} bet(s), max delay {cust['max_delay']}ms")
                lines.append("")
                return "\n".join(lines)
        
        # Status-specific aggregations
        status = self.retriever._extract_status(query)
        if status:
            stats = self.db.get_status_stats(status)
            if stats:
                lines.append("=== COMPLETE STATUS STATISTICS (from database) ===")
                lines.append(f"Status: {stats['status']}")
                lines.append(f"Total Bets: {stats['total_bets']}")
                lines.append(f"Unique Customers: {stats['unique_customers']}")
                lines.append(f"Total Stake: £{stats['total_stake']:.2f}")
                lines.append(f"Average Stake: £{stats['avg_stake']:.2f}")
                lines.append(f"Average Delay: {stats['avg_delay']:.0f}ms")
                lines.append(f"Incident Breakdown: {stats['incident_breakdown']}")
                lines.append("")
                return "\n".join(lines)
        
        # Top delay aggregations
        if ("highest" in query_lower or "top" in query_lower) and self.retriever._is_latency_query(query):
            limit = self.retriever._extract_number(query) or 5
            stats = self.db.get_top_delay_stats(limit)
            if stats:
                lines.append(f"=== TOP {limit} DELAY STATISTICS (from database) ===")
                lines.append(f"Total Stake: £{stats['total_stake']:.2f}")
                lines.append(f"Delay Range: {stats['min_delay']}ms - {stats['max_delay']}ms")
                lines.append(f"Average Delay: {stats['avg_delay']:.0f}ms")
                lines.append(f"Incident Breakdown: {stats['incident_breakdown']}")
                lines.append(f"Status Breakdown: {stats['status_breakdown']}")
                lines.append("")
                return "\n".join(lines)
        
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
    
    def _build_full_context(
        self, 
        row_context: str, 
        stats_context: Optional[str],
        total_count: int,
        shown_count: int
    ) -> str:
        """Combine row context and stats context with clear separation."""
        parts = []
        
        # Add stats context first (this is the authoritative data)
        if stats_context:
            parts.append(stats_context)
            parts.append("IMPORTANT: Use the statistics above for any counts, totals, or averages.")
            parts.append("The bet records below are for evidence/citation purposes.\n")
        
        # Note if we're showing a subset
        if total_count > shown_count:
            parts.append(f"Note: Showing {shown_count} of {total_count} matching records.\n")
        
        # Add row context
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
        """Generate an answer using the LLM."""
        
        user_message = f"""Question: {query}

{context}

Please answer the question based ONLY on the bet records above. Remember to cite bet_ids and end with "Evidence: [bet_ids]"."""
        
        response = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            # Note: gpt-5-nano only supports default temperature (1)
            # and uses max_completion_tokens instead of max_tokens
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
        
        # Extract bet IDs from context (these are the displayed ones)
        bet_ids = re.findall(r'Bet ID: (B\d{4})', context)
        
        if not bet_ids and not stats_lines:
            return "I found relevant records but couldn't generate a summary. Please try rephrasing your question."
        
        # Build a proper fallback response
        answer_parts = []
        
        # Include stats if we found them
        if stats_lines:
            answer_parts.append("Based on the database statistics:\n")
            for line in stats_lines[:10]:  # First 10 stats lines
                answer_parts.append(f"• {line}")
            answer_parts.append("")
        
        # Include bet count - use stats count if available (authoritative)
        actual_count = total_bets_from_stats or len(bet_ids)
        
        if bet_ids:
            if actual_count <= 10:
                answer_parts.append(f"This covers {actual_count} bet(s): {', '.join(bet_ids)}")
            else:
                answer_parts.append(f"This covers {actual_count} bet(s). Sample: {', '.join(bet_ids[:10])}")
            answer_parts.append(f"\nEvidence: {', '.join(bet_ids)}")
        
        return "\n".join(answer_parts)
    
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
