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
1. For simple aggregate questions (just counts, totals), answer DIRECTLY from COMPUTED FACTS.
2. When the user asks for analysis, explanation, summary, or details - PROVIDE THEM using the bet records.
3. Follow the INSTRUCTIONS in each message - they tell you exactly what to do.
4. Be CONCISE for simple questions, DETAILED for analysis requests.

⚠️ ARITHMETIC PROHIBITION:
- You MUST NOT perform any arithmetic yourself
- You MUST NOT count items by enumerating them
- All numeric facts come from COMPUTED FACTS - quote them exactly
- If a computation is not provided, say "This requires computation"

RESPONSE FORMAT:
- For simple counts: "There are X bets with total stake of £Y."
- For analysis requests: Start with summary stats, then describe individual bets with patterns/anomalies.
- Always end with "Evidence: [bet_ids]"

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
        if parsed.incomplete_id_query:
            # User asked for a bet/customer by ID but didn't provide the ID
            if parsed.incomplete_id_query == "bet":
                msg = ("Please specify which bet ID you'd like to see. "
                       "Bet IDs are in the format B0042. "
                       "For example, try: 'Give me bet B0042' or 'Show me details for bet B0095'.")
            else:  # customer
                msg = ("Please specify which customer ID you'd like to see. "
                       "Customer IDs are in the format C068. "
                       "For example, try: 'Give me customer C068' or 'Show me bets for customer C103'.")
        elif parsed.invalid_entity_reference:
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
            
            # Check if query has semantic/analysis intent
            analysis_keywords = ['summarize', 'analyze', 'explain', 'describe', 
                                'what happened', 'why', 'interesting', 'notable',
                                'tell me about', 'details', 'breakdown']
            has_analysis_intent = any(kw in parsed.original_query.lower() for kw in analysis_keywords)
            
            # Different instructions based on query type and intent
            # Pure count/sum aggregates without analysis intent: just state the numbers
            # TOP_N queries or anything with analysis intent: allow individual bet analysis
            if parsed.query_type == QueryType.AGGREGATE and not has_analysis_intent:
                parts.append("For this query: state the computed values directly.")
                parts.append("DO NOT list or enumerate individual bets.")
                parts.append("The bet records below are ONLY for the 'Evidence:' citation.")
            else:
                parts.append("Use the computed facts for any totals/averages.")
                parts.append("You may describe and analyze individual bets as needed.")
                if has_analysis_intent:
                    parts.append("The user wants analysis - explain what you observe in the data.")
            
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
        
        # Check if query has analysis/summary intent
        analysis_keywords = ['summarize', 'analyze', 'explain', 'describe', 
                            'what happened', 'why', 'interesting', 'notable',
                            'tell me about', 'details', 'breakdown', 'highlight',
                            'severely', 'affected', 'list them']
        has_analysis_intent = any(kw in parsed.original_query.lower() for kw in analysis_keywords)
        
        # Determine instruction based on query type AND intent
        if parsed.query_type in (QueryType.AGGREGATE, QueryType.TOP_N) and not has_analysis_intent:
            # Pure aggregate - just state numbers
            instruction = """INSTRUCTIONS:
1. Answer the question DIRECTLY using the COMPUTED FACTS values
2. Keep your answer CONCISE (1-3 sentences for simple questions)
3. DO NOT list individual bets - just state the computed totals/rankings
4. End with "Evidence: [bet_ids]" listing a few sample bet IDs

Example good answer: "There are 100 bets with a total stake of £2,765.00."
Example bad answer: "Here are the bets: B0001 has £10..." (DO NOT DO THIS)"""
        elif has_analysis_intent:
            # User wants analysis/summary/explanation
            instruction = """⚠️ ANALYSIS REQUIRED - DO NOT give a simple count!

INSTRUCTIONS:
1. Start with summary from COMPUTED FACTS (totals, averages)
2. Then LIST and DESCRIBE each bet record showing:
   - Bet ID, Customer ID, Event name
   - Status, Incident type, Delay (highlight if high)
   - Any patterns or notable observations
3. Conclude with key insights

EXAMPLE FORMAT for "List bets voided due to FEED_OUTAGE":
"There were 4 bets voided due to FEED_OUTAGE with a total stake of £95.00:

- B0028 (Customer C022): Zverev vs Tsitsipas, tennis. Delay: 495ms.
- B0050 (Customer C106): Man Utd vs Newcastle, football. Delay: 1073ms - notably high.
- B0066 (Customer C033): Warriors vs Suns, basketball. Delay: 1078ms - also elevated.
- B0094 (Customer C011): Medvedev vs Runee, tennis. Delay: 1194ms - highest of the group.

All 4 bets were cancelled due to data feed issues. The delays ranged from 495ms to 1194ms.

Evidence: [B0028, B0050, B0066, B0094]"

NOW provide a similar detailed response for the user's question."""
        else:
            instruction = """INSTRUCTIONS:
1. Answer the question using the bet records provided
2. If COMPUTED FACTS are available, include those values
3. Describe relevant details from the bet records
4. End with "Evidence: [bet_ids]" citing relevant bets"""
        
        user_message = f"""Question: {query}

{context}

{instruction}"""
        
        response = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            max_completion_tokens=2000  # Increased for detailed analysis
        )
        
        answer = response.choices[0].message.content
        
        if not answer or not answer.strip():
            return self._generate_fallback_answer(query, context, parsed)
        
        return answer.strip()
    
    def _generate_fallback_answer(self, query: str, context: str, parsed: ParsedQuery) -> str:
        """Generate a fallback answer when LLM returns empty."""
        # Try to extract key info from context for a more helpful response
        lines = []
        
        # Extract total bets
        if "Total Bets:" in context:
            match = re.search(r'Total Bets:\s*(\d+)', context)
            if match:
                lines.append(f"Found {match.group(1)} matching bets.")
        
        # Extract total stake
        if "Total Stake:" in context:
            match = re.search(r'Total Stake:\s*£([\d,\.]+)', context)
            if match:
                lines.append(f"Total stake: £{match.group(1)}.")
        
        # Extract average delay
        if "Average Delay:" in context:
            match = re.search(r'Average Delay:\s*(\d+)ms', context)
            if match:
                lines.append(f"Average delay: {match.group(1)}ms.")
        
        # Extract rankings if present
        rankings = re.findall(r'\d+\.\s+(B\d{4}):\s*(\d+)ms.*?([A-Z_]+)\)', context)
        if rankings:
            lines.append("\nTop delays:")
            for bet_id, delay, incident in rankings[:5]:
                lines.append(f"  - {bet_id}: {delay}ms ({incident})")
        
        # Extract bet IDs for evidence
        bet_ids = re.findall(r'\bB\d{4}\b', context)
        if bet_ids:
            unique_ids = list(dict.fromkeys(bet_ids))[:10]  # Preserve order, limit to 10
            lines.append(f"\nEvidence: [{', '.join(unique_ids)}]")
        
        if lines:
            return "\n".join(lines)
        
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
        """Ensure the answer includes complete citations."""
        if not results:
            return answer
        
        result_ids = [r.bet.bet_id for r in results]
        
        # Check if answer already has proper Evidence line
        has_evidence = bool(re.search(r'Evidence:\s*\[?[^\]]+\]?', answer, re.IGNORECASE))
        
        # For small result sets (≤ 10), always cite ALL results, not just what LLM chose
        # This ensures accuracy: if we say "5 bets" we should cite all 5
        if len(result_ids) <= 10:
            # Remove any existing Evidence line and append complete one
            answer = re.sub(r'\n*Evidence:.*$', '', answer, flags=re.IGNORECASE | re.MULTILINE).strip()
            return answer + f"\n\nEvidence: [{', '.join(result_ids)}]"
        
        # For larger result sets, use what LLM cited or first 5
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
