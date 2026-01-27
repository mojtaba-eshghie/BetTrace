#!/usr/bin/env python3
"""Minimal debug script to identify the bet_id error."""

import sqlite3
import traceback
from pathlib import Path

def main():
    db_path = Path("data/bets.db")
    
    print(f"Testing database at: {db_path}")
    print(f"Database exists: {db_path.exists()}")
    
    if not db_path.exists():
        print("\nERROR: Database doesn't exist. Run 'python main.py ingest' first.")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check schema
    print("\n=== Bets Table Schema ===")
    cursor.execute("PRAGMA table_info(bets)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col['name']}: {col['type']}")
    
    print("\n=== Embeddings Table Schema ===")
    cursor.execute("PRAGMA table_info(embeddings)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col['name']}: {col['type']}")
    
    # Test query
    print("\n=== Testing Query ===")
    cursor.execute("SELECT * FROM bets WHERE status = 'SETTLED' LIMIT 3")
    rows = cursor.fetchall()
    
    print(f"Found {len(rows)} rows")
    for row in rows:
        print(f"\nRow keys: {row.keys()}")
        try:
            print(f"  bet_id: {row['bet_id']}")
            print(f"  customer_id: {row['customer_id']}")
            print(f"  status: {row['status']}")
        except KeyError as e:
            print(f"  KeyError: {e}")
            print(f"  Available keys: {list(row.keys())}")
    
    conn.close()
    print("\n=== Done ===")

if __name__ == "__main__":
    main()
