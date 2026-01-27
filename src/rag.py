"""
RAG (Retrieval-Augmented Generation) module for the Sportsbook Assistant.

Combines retrieval with LLM generation to produce grounded, cited answers.

Architecture:
    Query → QueryParser → ParsedQuery → QueryExecutor → ExecutionResult → LLM → Answer

Key Design: LLMs do NOT do math!
- All calculations are performed by SafeCalculator (SQL-based)
- LLM receives pre-computed facts in COMPUTED FACTS section
- LLM's job is ONLY to narrate and explain, never to calculate
"""

import re
from typing import List, Optional
from dataclasses import dataclass
from openai import OpenAI

from .config import OPENAI_API_KEY, LLM_MODEL, validate_config
from .models import Bet, RetrievalResult
from .database import Database
from .retrieval import Retriever
from .calculator import SafeCalculator
from .query_parser import ParsedQuery, QueryType, AggregationType, get_query_parser
from .query_executor import QueryExecutor, ExecutionResult


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
    parsed_query: Optional[ParsedQuery] = None  # For debugging
    execution_path: Optional[str] = None  # For debugging


class RAGAssistant:
    """
    RAG Assistant using the unified query pipeline.
    
    Workflow:
    1. Parse query into structured components (QueryParser)
    2. Execute query using optimal strategy (QueryExecutor)
    3. Format context with COMPUTED FACTS
    4. Generate answer using LLM (narration only, no arithmetic)
    5. Extract and enforce citations
    
    Key Principle: LLMs cannot do math reliably, so we:
    - Pre-compute ALL numeric values via SQL
    - Present them as immutable COMPUTED FACTS
    - LLM's job is ONLY to explain and format these facts
    """
    
    def __init__(self, db: Optional[Database] = None):
        """Initialize the RAG assistant."""
        self.db = db or Database()
        self.db.load_embeddings_to_memory()
        self.retriever = Retriever(self.db)
        self.calculator = SafeCalculator(self.db.db_path)
        self.parser = get_query_parser()
        self.executor = QueryExecutor(self.db, self.retriever, self.calculator)
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
        Answer a question using the unified RAG pipeline.
        
        Args:
            query: The user's question
            top_k: Maximum number of bet records to include in context
            include_aggregations: Whether to include aggregate stats
            
        Returns:
            RAGResponse with answer, citations, and metadata
        """
        # Step 1: Execute query through unified pipeline
        exec_result = self.executor.execute(query, top_k)
        
        # Step 2: Handle empty results
        if not exec_result.results:
            return self._handle_empty_results(query, exec_result)
        
        # Step 3: Build context for LLM
        context = self._build_context(exec_result, top_k)
        
        # Step 4: Generate answer
        answer = self._generate_answer(query, context, exec_result.parsed_query)
        
        # Step 5: Extract and enforce citations
        citations = self._extract_citations(answer, exec_result.results)
        answer = self._enforce_citations(answer, citations, exec_result.results)
        
        # Re-extract citations after enforcement
        if not citations and exec_result.results:
            citations = self._extract_citations(answer, exec_result.results)
        
        # Step 6: Determine if evidence was sufficient
        sufficient = not any(phrase in answer.lower() for phrase in [
            "i need", "please provide", "not enough information",
            "couldn't find", "no records", "insufficient"
        ])
        
        return RAGResponse(
            answer=answer,
            citations=citations,
            retrieved_bets=[r.bet for r in exec_result.results],
            query=query,
            sufficient_evidence=sufficient,
            stats_context=exec_result.stats_context,
            parsed_query=exec_result.parsed_query,
            execution_path=exec_result.execution_path
        )
    
    def _handle_empty_results(self, query: str, exec_result: ExecutionResult) -> RAGResponse:
        """Handle case where no results were found."""
        parsed = exec_result.parsed_query
        
        # Provide helpful error message based on what was attempted
        if parsed.invalid_entity_reference:
            msg = (f"Invalid ID format: '{parsed.invalid_entity_reference}'. "
                   f"Customer IDs should be like C029, and bet IDs should be like B0042.")
        elif parsed.bet_ids:
            msg = f"No bets found with ID(s): {', '.join(parsed.bet_ids)}. Please check the bet ID format (e.g., B0042)."
        elif parsed.customer_ids:
            msg = f"No bets found for customer(s): {', '.join(parsed.customer_ids)}. Please check the customer ID format (e.g., C029)."
        elif parsed.filters:
            filter_desc = ", ".join(f"{k}={v}" for k, v in parsed.filters.items())
            msg = f"No bets found matching filters: {filter_desc}."
        else:
            msg = ("I couldn't find any relevant bet records for your query. "
                   "Please provide a specific bet_id (e.g., B0042) or customer_id (e.g., C068), "
                   "or ask about specific criteria like sport, status, or incident type.")
        
        return RAGResponse(
            answer=msg,
            citations=[],
            retrieved_bets=[],
            query=query,
            sufficient_evidence=False,
            parsed_query=parsed,
            execution_path=exec_result.execution_path
        )
    
    def _build_context(self, exec_result: ExecutionResult, top_k: int) -> str:
        """Build context for LLM from execution results."""
        parts = []
        parsed = exec_result.parsed_query
        
        # Add stats context if available
        if exec_result.stats_context:
            parts.append(exec_result.stats_context)
            parts.append("")
            parts.append("─" * 60)
            parts.append("YOUR ANSWER MUST USE THE COMPUTED FACTS ABOVE.")
            
            # Different instructions based on query type
            if parsed.query_type in (QueryType.AGGREGATE, QueryType.TOP_N):
                parts.append("For this query: state the computed values directly.")
                parts.append("DO NOT list or enumerate individual bets.")
                parts.append("The bet records below are ONLY for the 'Evidence:' citation.")
            else:
                parts.append("Use the computed facts for any totals/averages.")
                parts.append("You may describe individual bets as needed.")
            
            parts.append("─" * 60)
            parts.append("")
        
        # Add sample/limited results notice
        total = exec_result.total_count
        shown = len(exec_result.results)
        if total > shown:
            parts.append(f"(Showing {shown} of {total} matching records)\n")
        
        # Add bet records
        parts.append(self._format_bet_records(exec_result.results, top_k))
        
        return "\n".join(parts)
    
    def _format_bet_records(self, results: List[RetrievalResult], max_rows: int) -> str:
        """Format bet records for context."""
        if not results:
            return ""
        
        lines = ["=== BET RECORDS (for evidence/citations) ===\n"]
        
        for i, result in enumerate(results[:max_rows], 1):
            bet = result.bet
            lines.append(f"Record {i}:")
            lines.append(f"  Bet ID: {bet.bet_id}")
            lines.append(f"  Customer: {bet.customer_id}")
            lines.append(f"  Sport: {bet.sport}")
            lines.append(f"  Event: {bet.event_name}")
            lines.append(f"  Market: {bet.market}")
            lines.append(f"  Selection: {bet.selection}")
            lines.append(f"  Stake: £{bet.stake_gbp:.2f}")
            lines.append(f"  Status: {bet.status}")
            lines.append(f"  Incident: {bet.incident_tag}")
            lines.append(f"  Price Delay: {bet.price_delay_ms}ms")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_answer(self, query: str, context: str, parsed: ParsedQuery) -> str:
        """Generate an answer using the LLM."""
        
        # Determine instruction based on query type
        if parsed.query_type in (QueryType.AGGREGATE, QueryType.TOP_N):
            instruction = """INSTRUCTIONS:
1. Answer the question DIRECTLY using the COMPUTED FACTS values
2. Keep your answer CONCISE (1-3 sentences for simple questions)
3. DO NOT list individual bets - just state the computed totals/rankings
4. End with "Evidence: [bet_ids]" listing a few sample bet IDs

Example good answer: "There are 100 bets with a total stake of £2,765.00."
Example bad answer: "Here are the bets: B0001 has £10..." (DO NOT DO THIS)"""
        else:
            instruction = """INSTRUCTIONS:
1. Answer the question using the bet records provided
2. If COMPUTED FACTS are available, include those values
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
            max_completion_tokens=1000
        )
        
        answer = response.choices[0].message.content
        
        if not answer or not answer.strip():
            return self._generate_fallback_answer(query, context, parsed)
        
        return answer.strip()
    
    def _generate_fallback_answer(self, query: str, context: str, parsed: ParsedQuery) -> str:
        """Generate a fallback answer when LLM returns empty."""
        # Try to extract key info from context
        if "Total Bets:" in context:
            match = re.search(r'Total Bets:\s*(\d+)', context)
            if match:
                return f"There are {match.group(1)} bets matching your query."
        
        return "I found relevant records but couldn't generate a detailed answer. Please try rephrasing your question."
    
    def _extract_citations(self, answer: str, results: List[RetrievalResult]) -> List[str]:
        """Extract bet_id citations from the answer."""
        valid_ids = {r.bet.bet_id for r in results}
        found_ids = re.findall(r'\bB\d{4}\b', answer)
        
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
        """Ensure the answer includes citations."""
        if not results:
            return answer
        
        # Check if answer already has proper Evidence line
        has_evidence = bool(re.search(r'Evidence:\s*\[?[^\]]+\]?', answer, re.IGNORECASE))
        result_ids = [r.bet.bet_id for r in results]
        
        if extracted_citations and has_evidence:
            return answer
        
        # Determine citations to use
        citation_ids = extracted_citations if extracted_citations else result_ids[:5]
        
        # Remove malformed Evidence line and append proper one
        answer = re.sub(r'\n*Evidence:.*$', '', answer, flags=re.IGNORECASE | re.MULTILINE).strip()
        return answer + f"\n\nEvidence: [{', '.join(citation_ids)}]"
    
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
                
                # Debug info
                if response.parsed_query:
                    print(f"🔍 Query type: {response.parsed_query.query_type.value}")
                    print(f"🛤️ Execution path: {response.execution_path}")
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()


def create_rag_assistant(db: Optional[Database] = None) -> RAGAssistant:
    """Factory function to create a RAG assistant."""
    return RAGAssistant(db)
