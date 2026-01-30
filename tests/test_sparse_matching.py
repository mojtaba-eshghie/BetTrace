"""
Tests for the sparse team matching functionality.

Tests the SparseTeamMatcher class and its integration with the
retrieval layer.
"""

import pytest
import os
from typing import List, Set, Dict

# Ensure sparse mode is used for these tests
os.environ['TEAM_MATCHING_METHOD'] = 'sparse'


class TestSparseTeamMatcher:
    """Tests for the SparseTeamMatcher class."""
    
    def test_basic_matching(self):
        """Test basic edit distance matching."""
        from src.sparse_matcher import SparseTeamMatcher
        
        matcher = SparseTeamMatcher(threshold=70)
        matcher.build_index(['Lakers', 'Celtics', 'Raptors', 'Warriors'])
        
        # Exact match
        matches = matcher.find_matches('Lakers')
        assert len(matches) == 1
        assert matches[0].team_name == 'Lakers'
        assert matches[0].score == 100.0
        assert matches[0].method == 'exact'
    
    def test_typo_matching(self):
        """Test matching with typos."""
        from src.sparse_matcher import SparseTeamMatcher
        
        matcher = SparseTeamMatcher(threshold=70)
        matcher.build_index(['Lakers', 'Celtics', 'Raptors', 'Warriors'])
        
        # Typo - should match "Lakers"
        matches = matcher.find_matches('Lakkers')
        assert len(matches) >= 1
        assert matches[0].team_name == 'Lakers'
        assert matches[0].score > 85  # Should be ~92.3%
        assert matches[0].method == 'edit_distance'
    
    def test_threshold_filtering(self):
        """Test that threshold properly filters results."""
        from src.sparse_matcher import SparseTeamMatcher
        
        matcher = SparseTeamMatcher(threshold=95)
        matcher.build_index(['Lakers', 'Celtics', 'Raptors'])
        
        # "Lakkers" has ~92.3% similarity, below 95% threshold
        matches = matcher.find_matches('Lakkers')
        assert len(matches) == 0
        
        # With lower threshold, should match
        matches = matcher.find_matches('Lakkers', threshold=90)
        assert len(matches) >= 1
    
    def test_bet_id_mapping(self):
        """Test finding bet IDs for queries."""
        from src.sparse_matcher import SparseTeamMatcher
        
        matcher = SparseTeamMatcher(threshold=70)
        team_to_bets = {
            'Lakers': {'B0001', 'B0002'},
            'Celtics': {'B0001', 'B0003'},
        }
        matcher.build_index(['Lakers', 'Celtics'], team_to_bets)
        
        # Search for Lakers typo
        results = matcher.find_bet_ids_for_query('Lakkers')
        bet_ids = [r[0] for r in results]
        
        assert 'B0001' in bet_ids
        assert 'B0002' in bet_ids
    
    def test_edit_distance(self):
        """Test raw edit distance calculation."""
        from src.sparse_matcher import SparseTeamMatcher
        
        matcher = SparseTeamMatcher()
        
        # 1 edit (substitution)
        assert matcher.get_edit_distance('Raptors', 'Rapters') == 1
        
        # 1 edit (insertion)
        assert matcher.get_edit_distance('Thunder', 'Thunderr') == 1
        
        # 2 edits
        assert matcher.get_edit_distance('Thundr', 'Thunderr') == 2
    
    def test_similarity_score(self):
        """Test similarity score calculation."""
        from src.sparse_matcher import SparseTeamMatcher
        
        matcher = SparseTeamMatcher()
        
        # Similar strings
        sim = matcher.get_similarity('Raptors', 'Rapters')
        assert 85 < sim < 90  # Should be ~85.7%
        
        sim = matcher.get_similarity('Thunder', 'Thunderr')
        assert 90 < sim < 95  # Should be ~93.3%
        
        # Exact match
        assert matcher.get_similarity('Lakers', 'Lakers') == 100.0
    
    def test_explain_match(self):
        """Test match explanation."""
        from src.sparse_matcher import SparseTeamMatcher
        
        matcher = SparseTeamMatcher()
        
        # Exact match
        explanation = matcher.explain_match('Lakers', 'Lakers')
        assert 'Exact match' in explanation
        
        # Edit distance match
        explanation = matcher.explain_match('Lakkers', 'Lakers')
        assert 'Edit distance' in explanation
        assert 'Levenshtein distance: 1' in explanation
    
    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        from src.sparse_matcher import SparseTeamMatcher
        
        matcher = SparseTeamMatcher(threshold=70)
        matcher.build_index(['Lakers', 'CELTICS', 'raptors'])
        
        # All should match regardless of case
        matches = matcher.find_matches('LAKERS')
        assert len(matches) >= 1
        assert matches[0].score == 100.0
        
        matches = matcher.find_matches('celtics')
        assert len(matches) >= 1
        assert matches[0].score == 100.0
    
    def test_empty_index(self):
        """Test behavior with empty index."""
        from src.sparse_matcher import SparseTeamMatcher
        
        matcher = SparseTeamMatcher()
        
        # Empty index should return empty results
        matches = matcher.find_matches('Lakers')
        assert matches == []
    
    def test_singleton_pattern(self):
        """Test singleton getter and resetter."""
        from src.sparse_matcher import get_sparse_matcher, reset_sparse_matcher
        
        m1 = get_sparse_matcher()
        m2 = get_sparse_matcher()
        assert m1 is m2
        
        reset_sparse_matcher()
        m3 = get_sparse_matcher()
        assert m1 is not m3


class TestSparseMatcherIntegration:
    """Integration tests with Database and Retriever."""
    
    @pytest.fixture
    def db_with_sparse(self, tmp_path):
        """Create a test database with sparse matching enabled."""
        import os
        os.environ['TEAM_MATCHING_METHOD'] = 'sparse'
        
        from src.database import Database
        from src.models import Bet
        from decimal import Decimal
        
        db = Database(tmp_path / "test.db")
        
        # Insert test bets with misspelled team names (matching real data)
        test_bets = [
            Bet(
                bet_id="B0001",
                customer_id="C001",
                sport="basketball",
                event_name="Bulls vs Rapters",  # Misspelled "Raptors"
                market="Moneyline",
                selection="Bulls",
                stake_gbp=Decimal("10"),
                status="SETTLED",
                incident_tag="NONE",
                price_delay_ms=100
            ),
            Bet(
                bet_id="B0002",
                customer_id="C001",
                sport="basketball",
                event_name="Lakkers vs Celtcs",  # Misspelled both
                market="Moneyline",
                selection="Lakkers",
                stake_gbp=Decimal("20"),
                status="SETTLED",
                incident_tag="NONE",
                price_delay_ms=150
            ),
            Bet(
                bet_id="B0003",
                customer_id="C002",
                sport="basketball",
                event_name="Clippers vs Thunderr",  # Extra 'r'
                market="Moneyline",
                selection="Clippers",
                stake_gbp=Decimal("30"),
                status="SETTLED",
                incident_tag="NONE",
                price_delay_ms=200
            ),
        ]
        
        db.insert_bets_batch(test_bets)
        db.load_embeddings_to_memory()
        
        return db
    
    def test_database_sparse_search(self, db_with_sparse):
        """Test sparse search at database level."""
        db = db_with_sparse
        
        # Search for correctly spelled "Raptors" - should find "Rapters"
        results = db.sparse_search_teams('Raptors')
        assert len(results) >= 1
        
        bet_ids = [r[0] for r in results]
        assert 'B0001' in bet_ids
    
    def test_database_sparse_search_misspelled_query(self, db_with_sparse):
        """Test sparse search with misspelled query."""
        db = db_with_sparse
        
        # Search for "Lakrs" - should find "Lakkers"
        results = db.sparse_search_teams('Lakrs', threshold=70)
        assert len(results) >= 1
        
        bet_ids = [r[0] for r in results]
        assert 'B0002' in bet_ids
    
    def test_retriever_sparse_mode(self, db_with_sparse):
        """Test retriever uses sparse mode when configured."""
        from src.retrieval import Retriever
        
        retriever = Retriever(db_with_sparse)
        
        # This should use sparse matching (no API call)
        results = retriever.semantic_search(
            'bets involving Lakers', 
            top_k=5, 
            team_only=True
        )
        
        assert len(results) >= 1
        # Check match type indicates sparse
        assert results[0].match_type == 'sparse_team'
    
    def test_retriever_finds_misspelled_teams(self, db_with_sparse):
        """Test retriever finds teams with typos."""
        from src.retrieval import Retriever
        
        retriever = Retriever(db_with_sparse)
        
        # Search for "Thunder" - should find "Thunderr"
        results = retriever.semantic_search(
            'Thunder bets',
            top_k=5,
            team_only=True
        )
        
        assert len(results) >= 1
        assert any(r.bet.bet_id == 'B0003' for r in results)


class TestConfigSwitching:
    """Tests for switching between sparse and embedding modes."""
    
    def test_sparse_mode_no_api_calls(self, tmp_path):
        """Test that sparse mode doesn't require API calls."""
        import os
        os.environ['TEAM_MATCHING_METHOD'] = 'sparse'
        # Ensure no API key is set
        os.environ.pop('OPENAI_API_KEY', None)
        
        from src.database import Database
        from src.retrieval import Retriever
        from src.models import Bet
        from decimal import Decimal
        
        db = Database(tmp_path / "test.db")
        bet = Bet(
            bet_id="B0001",
            customer_id="C001",
            sport="basketball",
            event_name="Lakers vs Celtics",
            market="Moneyline",
            selection="Lakers",
            stake_gbp=Decimal("10"),
            status="SETTLED",
            incident_tag="NONE",
            price_delay_ms=100
        )
        db.insert_bets_batch([bet])
        db.load_embeddings_to_memory()
        
        retriever = Retriever(db)
        
        # This should NOT raise an error (no API call needed)
        results = retriever.semantic_search(
            'Lakers',
            top_k=5,
            team_only=True
        )
        
        assert len(results) >= 1


class TestSparseMatcherPerformance:
    """Performance-related tests."""
    
    def test_large_index(self):
        """Test sparse matcher with larger index."""
        from src.sparse_matcher import SparseTeamMatcher
        
        # Create 1000 fake team names
        teams = [f"Team{i:04d}" for i in range(1000)]
        
        matcher = SparseTeamMatcher(threshold=70)
        matcher.build_index(teams)
        
        assert matcher.team_count == 1000
        
        # Search should still be fast
        import time
        start = time.time()
        for _ in range(100):
            matcher.find_matches('Team0500')
        elapsed = time.time() - start
        
        # 100 searches should take < 1 second
        assert elapsed < 1.0, f"Sparse search too slow: {elapsed:.2f}s for 100 queries"
