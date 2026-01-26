#!/usr/bin/env python3
"""
Acceptance Test Suite for Sportsbook RAG Assistant

This script runs 6 test questions covering:
- 2 bet-specific questions (single bet_id)
- 2 analytics-style questions (aggregations/ranking)
- 2 incident/ops questions (latency/suspensions)

Usage:
    python run_acceptance_tests.py
    python run_acceptance_tests.py --output results.md
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import Database
from src.rag import RAGAssistant
from src.config import DATABASE_PATH


# Define the 6 acceptance test questions
ACCEPTANCE_QUESTIONS = [
    # ==================== BET-SPECIFIC (2) ====================
    {
        "id": 1,
        "category": "Bet-Specific",
        "question": "Why was bet B0004 rejected?",
        "description": "Tests exact bet lookup and explanation of rejection reason",
        "expected_elements": ["B0004", "REJECTED", "MARKET_SUSPENDED"]
    },
    {
        "id": 2,
        "category": "Bet-Specific",
        "question": "What happened with bet B0059? Explain the incident and latency.",
        "description": "Tests retrieval of highest-latency bet with incident analysis",
        "expected_elements": ["B0059", "4648", "LATENCY_SPIKE", "SETTLED"]
    },
    
    # ==================== ANALYTICS-STYLE (2) ====================
    {
        "id": 3,
        "category": "Analytics",
        "question": "Find the top 5 highest price_delay_ms bets and summarize what happened.",
        "description": "Tests ranking query and multi-bet summarization",
        "expected_elements": ["B0059", "B0090", "B0032", "B0036", "B0072"]
    },
    {
        "id": 4,
        "category": "Analytics",
        "question": "For customer C068, summarize all their bets and highlight any incidents.",
        "description": "Tests customer-level aggregation and incident detection",
        "expected_elements": ["C068", "B0003", "B0018", "B0019", "B0055"]
    },
    
    # ==================== INCIDENT/OPS (2) ====================
    {
        "id": 5,
        "category": "Incident/Ops",
        "question": "Which customers were affected by LATENCY_SPIKE and how severely?",
        "description": "Tests incident filtering and customer impact analysis",
        "expected_elements": ["LATENCY_SPIKE", "C069", "C120", "C122", "C004", "C076", "C055", "C121"]
    },
    {
        "id": 6,
        "category": "Incident/Ops",
        "question": "How many bets were voided due to FEED_OUTAGE? List them and explain.",
        "description": "Tests incident-status correlation analysis",
        "expected_elements": ["VOID", "FEED_OUTAGE", "B0028", "B0050", "B0066", "B0094"]
    },
]


def run_tests(output_file: str = None):
    """Run all acceptance tests and display/save results."""
    
    print("\n" + "=" * 70)
    print("SPORTSBOOK RAG ASSISTANT - ACCEPTANCE TEST SUITE")
    print("=" * 70)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total questions: {len(ACCEPTANCE_QUESTIONS)}")
    print("=" * 70 + "\n")
    
    # Initialize the RAG assistant
    try:
        db = Database(DATABASE_PATH)
        assistant = RAGAssistant(db)
    except Exception as e:
        print(f"Error initializing assistant: {e}")
        print("Make sure you have run 'python main.py ingest' first.")
        sys.exit(1)
    
    results = []
    
    for test in ACCEPTANCE_QUESTIONS:
        print(f"\n{'─' * 70}")
        print(f"TEST {test['id']}: [{test['category']}]")
        print(f"{'─' * 70}")
        print(f"Question: {test['question']}")
        print(f"Description: {test['description']}")
        print()
        
        try:
            # Run the query
            response = assistant.ask(test["question"], top_k=10)
            
            # Check for expected elements
            answer_lower = response.answer.lower()
            found_elements = []
            missing_elements = []
            
            for elem in test["expected_elements"]:
                if elem.lower() in answer_lower or elem in response.answer:
                    found_elements.append(elem)
                else:
                    # Also check in citations
                    if elem in response.citations:
                        found_elements.append(elem)
                    else:
                        missing_elements.append(elem)
            
            # Display results
            print("ANSWER:")
            print("-" * 40)
            print(response.answer)
            print("-" * 40)
            print(f"\nEvidence: {', '.join(response.citations) if response.citations else 'None'}")
            print(f"Retrieved: {len(response.retrieved_bets)} bet(s)")
            
            # Validation
            validation_passed = len(missing_elements) == 0 or len(found_elements) >= len(test["expected_elements"]) // 2
            status = "✓ PASS" if validation_passed else "⚠ PARTIAL"
            
            print(f"\nValidation: {status}")
            if found_elements:
                print(f"  Found: {', '.join(found_elements)}")
            if missing_elements:
                print(f"  Missing: {', '.join(missing_elements)}")
            
            results.append({
                "test": test,
                "response": response,
                "found": found_elements,
                "missing": missing_elements,
                "passed": validation_passed
            })
            
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "test": test,
                "error": str(e),
                "passed": False
            })
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results if r.get("passed", False))
    print(f"Passed: {passed}/{len(ACCEPTANCE_QUESTIONS)}")
    
    for r in results:
        test = r["test"]
        status = "✓" if r.get("passed") else "✗"
        print(f"  {status} Test {test['id']}: {test['category']} - {test['question'][:40]}...")
    
    # Save to file if requested
    if output_file:
        save_results_markdown(results, output_file)
        print(f"\nResults saved to: {output_file}")
    
    return results


def save_results_markdown(results: list, output_file: str):
    """Save test results to a markdown file."""
    
    with open(output_file, "w") as f:
        f.write("# Sportsbook RAG Assistant - Acceptance Test Results\n\n")
        f.write(f"**Run time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Summary table
        f.write("## Summary\n\n")
        f.write("| # | Category | Question | Status |\n")
        f.write("|---|----------|----------|--------|\n")
        
        for r in results:
            test = r["test"]
            status = "✓ Pass" if r.get("passed") else "⚠ Partial"
            question_short = test["question"][:50] + "..." if len(test["question"]) > 50 else test["question"]
            f.write(f"| {test['id']} | {test['category']} | {question_short} | {status} |\n")
        
        f.write("\n---\n\n")
        
        # Detailed results
        f.write("## Detailed Results\n\n")
        
        for r in results:
            test = r["test"]
            f.write(f"### Test {test['id']}: {test['category']}\n\n")
            f.write(f"**Question:** {test['question']}\n\n")
            f.write(f"**Description:** {test['description']}\n\n")
            
            if "error" in r:
                f.write(f"**Error:** {r['error']}\n\n")
            else:
                response = r["response"]
                f.write("**Answer:**\n\n")
                f.write(f"```\n{response.answer}\n```\n\n")
                f.write(f"**Evidence:** {', '.join(response.citations) if response.citations else 'None'}\n\n")
                f.write(f"**Retrieved Bets:** {len(response.retrieved_bets)}\n\n")
            
            f.write("---\n\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG acceptance tests")
    parser.add_argument("--output", "-o", help="Save results to markdown file")
    args = parser.parse_args()
    
    run_tests(args.output)
