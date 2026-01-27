#!/usr/bin/env python3
"""Debug script to trace where the bet_id error occurs."""

import traceback
import sys

def main():
    print("Step 1: Importing modules...")
    try:
        from src.database import Database
        from src.rag import RAGAssistant
        from src.config import DATABASE_PATH
        print("  ✓ Imports successful")
    except Exception as e:
        print(f"  ✗ Import error: {e}")
        traceback.print_exc()
        return
    
    print("\nStep 2: Creating database connection...")
    try:
        db = Database(DATABASE_PATH)
        print(f"  ✓ Database created at {DATABASE_PATH}")
    except Exception as e:
        print(f"  ✗ Database error: {e}")
        traceback.print_exc()
        return
    
    print("\nStep 3: Loading embeddings...")
    try:
        db.load_embeddings_to_memory()
        print(f"  ✓ Loaded {db._vector_store.size()} embeddings")
    except Exception as e:
        print(f"  ✗ Embedding load error: {e}")
        traceback.print_exc()
        return
    
    print("\nStep 4: Creating RAG assistant...")
    try:
        assistant = RAGAssistant(db)
        print("  ✓ RAG assistant created")
    except Exception as e:
        print(f"  ✗ RAG assistant error: {e}")
        traceback.print_exc()
        return
    
    query = "What is the total stake for all SETTLED bets?"
    print(f"\nStep 5: Testing retrieval for: '{query}'")
    
    try:
        results, count = assistant._retrieve_for_query(query, top_k=10)
        print(f"  ✓ Retrieved {count} results")
        for i, r in enumerate(results[:3]):
            print(f"    - {r.bet.bet_id}: {r.bet.status}")
    except Exception as e:
        print(f"  ✗ Retrieval error: {e}")
        traceback.print_exc()
        return
    
    print("\nStep 6: Computing SQL aggregations...")
    try:
        stats_context = assistant._compute_sql_aggregations(query)
        if stats_context:
            print(f"  ✓ Stats context:\n{stats_context[:200]}...")
        else:
            print("  ✓ No stats context (might be normal)")
    except Exception as e:
        print(f"  ✗ SQL aggregation error: {e}")
        traceback.print_exc()
        return
    
    print("\nStep 7: Formatting row context...")
    try:
        row_context = assistant._format_row_context(results, 10)
        print(f"  ✓ Row context length: {len(row_context)} chars")
    except Exception as e:
        print(f"  ✗ Row context error: {e}")
        traceback.print_exc()
        return
    
    print("\nStep 8: Building full context...")
    try:
        context = assistant._build_full_context(row_context, stats_context, count, 10)
        print(f"  ✓ Full context length: {len(context)} chars")
    except Exception as e:
        print(f"  ✗ Full context error: {e}")
        traceback.print_exc()
        return
    
    print("\nStep 9: Generating answer (LLM call)...")
    try:
        answer = assistant._generate_answer(query, context)
        print(f"  ✓ Answer: {answer[:100]}...")
    except Exception as e:
        print(f"  ✗ LLM error: {e}")
        traceback.print_exc()
        return
    
    print("\nStep 10: Extracting citations...")
    try:
        citations = assistant._extract_citations(answer, results)
        print(f"  ✓ Citations: {citations}")
    except Exception as e:
        print(f"  ✗ Citation error: {e}")
        traceback.print_exc()
        return
    
    print("\n✓ All steps completed successfully!")

if __name__ == "__main__":
    main()
