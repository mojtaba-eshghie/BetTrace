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
            top_k: Maximum number of bets to retrieve
            include_aggregations: Whether to include aggregate stats in context
            
        Returns:
            RAGResponse with answer, citations, and metadata
        """
        # Step 1: Retrieve relevant bets
        results = self._retrieve_for_query(query, top_k)
        
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
        
        # Step 2: Format context
        context = self._format_context(results, query, include_aggregations)
        
        # Step 3: Generate answer
        answer = self._generate_answer(query, context)
        
        # Step 4: Extract citations
        citations = self._extract_citations(answer, results)
        
        # Step 5: Check if evidence was sufficient
        sufficient = not any(phrase in answer.lower() for phrase in [
            "i need", "please provide", "not enough information",
            "couldn't find", "no records", "insufficient"
        ])
        
        return RAGResponse(
            answer=answer,
            citations=citations,
            retrieved_bets=[r.bet for r in results],
            query=query,
            sufficient_evidence=sufficient
        )
    
    def _retrieve_for_query(
        self, 
        query: str, 
        top_k: int
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant bets based on query analysis.
        
        Uses smart retrieval that auto-detects query intent.
        """
        # Use the smart retriever which handles:
        # - Bet ID extraction (B0042)
        # - Customer ID extraction (C068)
        # - Incident tag detection (LATENCY_SPIKE)
        # - Status detection (REJECTED)
        # - Latency queries (highest delay)
        # - Semantic search for general queries
        
        results = self.retriever.retrieve(query, top_k=top_k)
        
        # For aggregation queries, we might need more context
        query_lower = query.lower()
        
        # If asking about "most impacted" customers, get full incident data
        if "most" in query_lower and ("impact" in query_lower or "affect" in query_lower):
            incident = self.retriever._extract_incident_tag(query)
            if incident:
                # Get all bets with this incident for proper aggregation
                results = self.retriever.filter_by_incident(incident)
        
        # If asking about "highest" or "top" delays
        if ("highest" in query_lower or "top" in query_lower) and self.retriever._is_latency_query(query):
            limit = self.retriever._extract_number(query) or 5
            results = self.retriever.get_top_by_delay(limit)
        
        return results
    
    def _format_context(
        self, 
        results: List[RetrievalResult],
        query: str,
        include_aggregations: bool
    ) -> str:
        """Format retrieved bets as context for the LLM."""
        
        lines = ["=== RETRIEVED BET RECORDS ===\n"]
        
        for i, result in enumerate(results, 1):
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
        
        # Add aggregations for certain query types
        if include_aggregations and len(results) > 1:
            lines.append("=== SUMMARY STATISTICS ===")
            
            bets = [r.bet for r in results]
            
            # Status breakdown
            statuses = {}
            for bet in bets:
                statuses[bet.status] = statuses.get(bet.status, 0) + 1
            lines.append(f"Status breakdown: {statuses}")
            
            # Incident breakdown
            incidents = {}
            for bet in bets:
                incidents[bet.incident_tag] = incidents.get(bet.incident_tag, 0) + 1
            lines.append(f"Incident breakdown: {incidents}")
            
            # Customer breakdown (for incident queries)
            customers = {}
            for bet in bets:
                customers[bet.customer_id] = customers.get(bet.customer_id, 0) + 1
            if len(customers) < len(bets):  # Only show if there are repeat customers
                lines.append(f"Customers affected: {len(customers)} unique")
                # Show top affected customers
                sorted_customers = sorted(customers.items(), key=lambda x: x[1], reverse=True)
                top_customers = sorted_customers[:5]
                lines.append(f"Most affected customers: {top_customers}")
            
            # Delay statistics
            delays = [bet.price_delay_ms for bet in bets]
            lines.append(f"Delay range: {min(delays)}ms - {max(delays)}ms")
            lines.append(f"Average delay: {sum(delays)/len(delays):.0f}ms")
            
            # Total stake
            total_stake = sum(bet.stake_gbp for bet in bets)
            lines.append(f"Total stake: £{total_stake:.2f}")
            lines.append("")
        
        return "\n".join(lines)
    
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
        # This is a safety net - extract key info from context
        import re
        
        # Extract bet IDs from context
        bet_ids = re.findall(r'Bet ID: (B\d{4})', context)
        
        if not bet_ids:
            return "I found relevant records but couldn't generate a summary. Please try rephrasing your question."
        
        return f"I found {len(bet_ids)} relevant bet(s): {', '.join(bet_ids)}. Please review the context above for details.\n\nEvidence: {', '.join(bet_ids)}"
    
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
