#!/usr/bin/env python3
"""Test embedding dimension validation."""

# run simply with `python tests/test_dimension_validation.py`

import tempfile
from pathlib import Path
import warnings
# Add src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database

def test_dimension_validation():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        
        # Test 1: First ingestion - no validation needed
        print("Test 1: First ingestion (no stored config)")
        assert db.get_embedding_config() is None
        db.validate_embedding_config("any-model", 999)  # Should not raise
        print("  ✓ Passed")
        
        # Store config
        db.set_embedding_config("text-embedding-3-small", 1536)
        
        # Test 2: Same config - should pass
        print("\nTest 2: Same model and dimension")
        db.validate_embedding_config("text-embedding-3-small", 1536)
        print("  ✓ Passed")
        
        # Test 3: Different model, same dimension - should warn
        print("\nTest 3: Different model, same dimension")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            db.validate_embedding_config("different-model", 1536)
            assert len(w) == 1
            assert "model changed" in str(w[0].message).lower()
        print("  ✓ Passed (warning issued)")
        
        # Test 4: Different dimension - should FAIL
        print("\nTest 4: Different dimension (should fail)")
        try:
            db.validate_embedding_config("any-model", 768)
            print("  ✗ Should have raised ValueError!")
            return False
        except ValueError as e:
            assert "dimension mismatch" in str(e).lower()
            print("  ✓ Passed (ValueError raised)")
        
        print("\n" + "="*50)
        print("ALL TESTS PASSED!")
        print("="*50)
        return True

if __name__ == "__main__":
    test_dimension_validation()