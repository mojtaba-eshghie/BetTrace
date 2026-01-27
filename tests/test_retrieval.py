"""
Tests for the Sportsbook RAG Assistant.

Run with: pytest tests/ -v
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Bet, RetrievalResult, QueryContext
from src.database import Database
from src.retrieval import Retriever


# ==================== FIXTURES ====================

@pytest.fixture
def sample_bets():
    """Create sample bet data for testing."""
    return [
        Bet(
            bet_id="B0001",
            customer_id="C001",
            sport="football",
            event_name="Team A vs Team B",
            market="Match Winner",
            selection="Team A",
            stake_gbp=10.0,
            status="SETTLED",
            incident_tag="NONE",
            price_delay_ms=100
        ),
        Bet(
            bet_id="B0002",
            customer_id="C001",
            sport="tennis",
            event_name="Player X vs Player Y",
            market="Set 1 Winner",
            selection="Player X",
            stake_gbp=20.0,
            status="PENDING",
            incident_tag="LATENCY_SPIKE",
            price_delay_ms=2500
        ),
        Bet(
            bet_id="B0003",
            customer_id="C002",
            sport="basketball",
            event_name="Lakers vs Celtics",
            market="Moneyline",
            selection="Lakers",
            stake_gbp=50.0,
            status="REJECTED",
            incident_tag="MARKET_SUSPENDED",
            price_delay_ms=500
        ),
    ]


@pytest.fixture
def test_db(tmp_path, sample_bets):
    """Create a test database with sample data."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    
    # Insert sample bets without embeddings
    db.insert_bets_batch(sample_bets, embeddings=None)
    
    return db


@pytest.fixture
def retriever(test_db):
    """Create a retriever with the test database."""
    return Retriever(test_db)


# ==================== MODEL TESTS ====================

class TestBetModel:
    """Tests for the Bet model."""
    
    def test_bet_creation(self):
        """Test creating a Bet from dict."""
        data = {
            "bet_id": "B0042",
            "customer_id": "C029",
            "sport": "football",
            "event_name": "PSG vs Marseille",
            "market": "BTTS",
            "selection": "Yes",
            "stake_gbp": 10,
            "status": "SETTLED",
            "incident_tag": "NONE",
            "price_delay_ms": 214
        }
        bet = Bet.from_dict(data)
        
        assert bet.bet_id == "B0042"
        assert bet.customer_id == "C029"
        assert bet.stake_gbp == 10.0
    
    def test_bet_to_document(self):
        """Test document generation for embedding."""
        bet = Bet(
            bet_id="B0001",
            customer_id="C001",
            sport="football",
            event_name="Team A vs Team B",
            market="Match Winner",
            selection="Team A",
            stake_gbp=10.0,
            status="REJECTED",
            incident_tag="MARKET_SUSPENDED",
            price_delay_ms=600
        )
        
        doc = bet.to_document()
        
        assert "B0001" in doc
        assert "C001" in doc
        assert "football" in doc
        assert "REJECTED" in doc
        assert "MARKET_SUSPENDED" in doc
        assert "600ms" in doc  # High latency should be mentioned
    
    def test_bet_to_summary(self):
        """Test summary generation."""
        bet = Bet(
            bet_id="B0001",
            customer_id="C001",
            sport="football",
            event_name="Team A vs Team B",
            market="Match Winner",
            selection="Team A",
            stake_gbp=10.0,
            status="SETTLED",
            incident_tag="NONE",
            price_delay_ms=100
        )
        
        summary = bet.to_summary()
        
        assert "[B0001]" in summary
        assert "FOOTBALL" in summary


# ==================== DATABASE TESTS ====================

class TestDatabase:
    """Tests for the Database class."""
    
    def test_stored_document_retrieved(self, test_db, sample_bets):
        """Test that stored document is retrieved from database."""
        bet = test_db.get_by_bet_id("B0001")
        assert bet is not None
        assert bet.stored_document is not None
        # to_document() should return the stored version
        assert bet.to_document() == bet.stored_document
    
    def test_insert_and_retrieve(self, test_db, sample_bets):
        """Test inserting and retrieving bets."""
        bet = test_db.get_by_bet_id("B0001")
        assert bet is not None
        assert bet.bet_id == "B0001"
        assert bet.customer_id == "C001"
    
    def test_get_by_customer(self, test_db):
        """Test retrieving bets by customer ID."""
        bets = test_db.get_by_customer_id("C001")
        assert len(bets) == 2
        assert all(b.customer_id == "C001" for b in bets)
    
    def test_filter_by_status(self, test_db):
        """Test filtering by status."""
        rejected = test_db.filter_by_status("REJECTED")
        assert len(rejected) == 1
        assert rejected[0].bet_id == "B0003"
    
    def test_filter_by_incident(self, test_db):
        """Test filtering by incident tag."""
        latency = test_db.filter_by_incident("LATENCY_SPIKE")
        assert len(latency) == 1
        assert latency[0].bet_id == "B0002"
    
    def test_filter_by_sport(self, test_db):
        """Test filtering by sport."""
        football = test_db.filter_by_sport("football")
        assert len(football) == 1
        assert football[0].sport == "football"
    
    def test_advanced_filter(self, test_db):
        """Test advanced multi-criteria filtering."""
        results = test_db.advanced_filter(
            customer_ids=["C001"],
            incident_tags=["LATENCY_SPIKE"]
        )
        assert len(results) == 1
        assert results[0].bet_id == "B0002"
    
    def test_get_top_by_delay(self, test_db):
        """Test getting top bets by delay."""
        top = test_db.get_top_by_delay(2)
        assert len(top) == 2
        assert top[0].price_delay_ms >= top[1].price_delay_ms
    
    def test_aggregations(self, test_db):
        """Test aggregation queries."""
        status_counts = test_db.count_by_status()
        assert status_counts["SETTLED"] == 1
        assert status_counts["PENDING"] == 1
        assert status_counts["REJECTED"] == 1
        
        incident_counts = test_db.count_by_incident()
        assert incident_counts["NONE"] == 1
        assert incident_counts["LATENCY_SPIKE"] == 1
    
    def test_text_search(self, test_db):
        """Test basic text search."""
        results = test_db.text_search("Lakers")
        assert len(results) == 1
        assert "Lakers" in results[0].event_name


# ==================== RETRIEVER TESTS ====================

class TestRetriever:
    """Tests for the Retriever class."""
    
    def test_get_bet_exact(self, retriever):
        """Test exact bet lookup."""
        result = retriever.get_bet("B0001")
        assert result is not None
        assert result.bet.bet_id == "B0001"
        assert result.match_type == "exact"
    
    def test_get_bet_normalized(self, retriever):
        """Test bet lookup with normalized ID."""
        result = retriever.get_bet("1")  # Should normalize to B0001
        assert result is not None
        assert result.bet.bet_id == "B0001"
    
    def test_get_customer_bets(self, retriever):
        """Test customer bet lookup."""
        results = retriever.get_customer_bets("C001")
        assert len(results) == 2
        assert all(r.bet.customer_id == "C001" for r in results)
    
    def test_filter_by_incident(self, retriever):
        """Test incident filtering."""
        results = retriever.filter_by_incident("MARKET_SUSPENDED")
        assert len(results) == 1
        assert results[0].bet.status == "REJECTED"
    
    def test_get_top_by_delay(self, retriever):
        """Test delay ranking."""
        results = retriever.get_top_by_delay(2)
        assert len(results) == 2
        assert results[0].bet.price_delay_ms >= results[1].bet.price_delay_ms
    
    def test_incident_summary(self, retriever):
        """Test incident summary generation."""
        summary = retriever.get_incident_summary("LATENCY_SPIKE")
        assert summary["count"] == 1
        assert summary["customers_affected"] == 1
        assert "B0002" in summary["bet_ids"]
    
    def test_extract_bet_id(self, retriever):
        """Test bet ID extraction from text."""
        assert retriever._extract_bet_id("bet B0042") == "B0042"
        assert retriever._extract_bet_id("bet B42") == "B0042"
        assert retriever._extract_bet_id("What about B0001?") == "B0001"
    
    def test_extract_customer_id(self, retriever):
        """Test customer ID extraction from text."""
        assert retriever._extract_customer_id("customer C029") == "C029"
        assert retriever._extract_customer_id("Show C29 bets") == "C029"
    
    def test_extract_incident_tag(self, retriever):
        """Test incident tag extraction from text."""
        assert retriever._extract_incident_tag("LATENCY_SPIKE issues") == "LATENCY_SPIKE"
        assert retriever._extract_incident_tag("high latency") == "LATENCY_SPIKE"
        assert retriever._extract_incident_tag("feed outage") == "FEED_OUTAGE"


# ==================== INTEGRATION TESTS ====================

class TestIntegration:
    """Integration tests for the full pipeline."""
    
    def test_smart_retrieve_bet_id(self, retriever):
        """Test smart retrieval with bet ID."""
        results = retriever.retrieve("Why was bet B0003 rejected?")
        assert len(results) == 1
        assert results[0].bet.bet_id == "B0003"
    
    def test_smart_retrieve_customer(self, retriever):
        """Test smart retrieval with customer ID."""
        results = retriever.retrieve("Show bets for customer C001")
        assert len(results) == 2
    
    def test_smart_retrieve_incident(self, retriever):
        """Test smart retrieval with incident."""
        results = retriever.retrieve("Which bets had LATENCY_SPIKE?")
        assert len(results) == 1
        assert results[0].bet.incident_tag == "LATENCY_SPIKE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ==================== RAG TESTS ====================

class TestRAGFormatting:
    """Tests for RAG context formatting and citation extraction."""
    
    def test_context_formatting(self, test_db, sample_bets):
        """Test that context is properly formatted for LLM."""
        from src.rag import RAGAssistant
        
        assistant = RAGAssistant(test_db)
        results = [
            RetrievalResult(bet=sample_bets[0]),
            RetrievalResult(bet=sample_bets[1])
        ]
        
        context = assistant._format_context(results, "test query", include_aggregations=True)
        
        # Check that bet IDs are present
        assert "B0001" in context
        assert "B0002" in context
        
        # Check that key fields are present
        assert "Status:" in context
        assert "Incident:" in context
        assert "Price Delay:" in context
    
    def test_citation_extraction(self, test_db, sample_bets):
        """Test that citations are correctly extracted from answers."""
        from src.rag import RAGAssistant
        
        assistant = RAGAssistant(test_db)
        results = [
            RetrievalResult(bet=sample_bets[0]),
            RetrievalResult(bet=sample_bets[1])
        ]
        
        # Simulate an answer with citations
        answer = "The bet B0001 was settled. Evidence: B0001, B0002"
        citations = assistant._extract_citations(answer, results)
        
        assert "B0001" in citations
        assert "B0002" in citations
    
    def test_citation_filters_invalid_ids(self, test_db, sample_bets):
        """Test that only valid bet IDs are included in citations."""
        from src.rag import RAGAssistant
        
        assistant = RAGAssistant(test_db)
        results = [
            RetrievalResult(bet=sample_bets[0])  # Only B0001
        ]
        
        # Answer mentions B0001 (valid) and B9999 (not in results)
        answer = "See B0001 and B9999 for details."
        citations = assistant._extract_citations(answer, results)
        
        assert "B0001" in citations
        assert "B9999" not in citations  # Should be filtered out


# =============================================================================
# Calculator Tests
# =============================================================================

class TestCalculator:
    """Tests for the SafeCalculator module."""
# Fixed calculator tests based on sample_bets fixture:
# B0001: C001, SETTLED, £10, 100ms, NONE
# B0002: C001, PENDING, £20, 2500ms, LATENCY_SPIKE
# B0003: C002, REJECTED, £50, 500ms, MARKET_SUSPENDED

class TestCalculator:
    """Tests for the SafeCalculator module."""
    
    def test_count_all_bets(self, test_db):
        from src.calculator import SafeCalculator
        calc = SafeCalculator(test_db.db_path)
        
        result = calc.count_bets()
        assert result.value == 3  # 3 bets in sample_bets
    
    def test_sum_stake_filtered(self, test_db):
        from src.calculator import SafeCalculator
        calc = SafeCalculator(test_db.db_path)
        
        result = calc.sum_stake(status="SETTLED")
        # Only B0001 is SETTLED with £10
        assert float(result.value) == 10.0
    
    def test_sum_all_stake(self, test_db):
        from src.calculator import SafeCalculator
        calc = SafeCalculator(test_db.db_path)
        
        result = calc.sum_stake()
        # £10 + £20 + £50 = £80
        assert float(result.value) == 80.0
    
    def test_avg_delay(self, test_db):
        from src.calculator import SafeCalculator
        calc = SafeCalculator(test_db.db_path)
        
        result = calc.avg_delay()
        # Average of 100, 2500, 500 = 1033.33
        assert abs(result.value - 1033.33) < 1
    
    def test_customers_affected(self, test_db):
        from src.calculator import SafeCalculator
        calc = SafeCalculator(test_db.db_path)
        
        result = calc.customers_affected(status="SETTLED")
        # Only C001 has SETTLED bet
        assert result.value == 1
    
    def test_all_customers(self, test_db):
        from src.calculator import SafeCalculator
        calc = SafeCalculator(test_db.db_path)
        
        result = calc.customers_affected()
        # C001 and C002
        assert result.value == 2
    
    def test_top_by_delay(self, test_db):
        from src.calculator import SafeCalculator
        calc = SafeCalculator(test_db.db_path)
        
        result = calc.top_by_delay(n=2)
        assert len(result.value) == 2
        # B0002 has highest delay (2500ms)
        assert result.value[0]["bet_id"] == "B0002"
        assert result.value[0]["price_delay_ms"] == 2500
    
    def test_group_by_status(self, test_db):
        from src.calculator import SafeCalculator
        calc = SafeCalculator(test_db.db_path)
        
        result = calc.group_by_status()
        # 1 SETTLED, 1 REJECTED, 1 PENDING
        assert result.value["SETTLED"]["count"] == 1
        assert result.value["REJECTED"]["count"] == 1
        assert result.value["PENDING"]["count"] == 1
    
    def test_invalid_column_rejected(self, test_db):
        from src.calculator import SafeCalculator, CalculationRequest, CalculationType
        calc = SafeCalculator(test_db.db_path)
        
        # Try to use an invalid column
        with pytest.raises(ValueError, match="not allowed"):
            calc.execute(CalculationRequest(
                calc_type=CalculationType.SUM,
                column="malicious_column"
            ))
    
    def test_range_filter(self, test_db):
        from src.calculator import SafeCalculator, CalculationRequest, CalculationType
        calc = SafeCalculator(test_db.db_path)
        
        # Count bets with delay > 1000ms
        result = calc.execute(CalculationRequest(
            calc_type=CalculationType.COUNT,
            column="*",
            filters={"price_delay_ms": {"gt": 1000}}
        ))
        # Only B0002 (2500ms)
        assert result.value == 1


# =============================================================================
# Embedding Dimension Validation Tests
# =============================================================================

class TestEmbeddingValidation:
    """Tests for embedding dimension validation."""
    
    def test_metadata_storage(self, test_db):
        """Test that embedding metadata can be stored and retrieved."""
        test_db.set_embedding_config("test-model", 768)
        
        config = test_db.get_embedding_config()
        assert config is not None
        assert config["model"] == "test-model"
        assert config["dimension"] == 768
        assert "created_at" in config
    
    def test_validation_passes_when_matching(self, test_db):
        """Test validation passes when dimensions match."""
        test_db.set_embedding_config("text-embedding-3-small", 1536)
        
        # Should not raise
        test_db.validate_embedding_config("text-embedding-3-small", 1536)
    
    def test_validation_fails_on_dimension_mismatch(self, test_db):
        """Test validation fails when dimensions don't match."""
        test_db.set_embedding_config("text-embedding-3-small", 1536)
        
        with pytest.raises(ValueError, match="dimension mismatch"):
            test_db.validate_embedding_config("different-model", 768)
    
    def test_validation_warns_on_model_change(self, test_db):
        """Test validation warns but doesn't fail when only model changes."""
        import warnings
        
        test_db.set_embedding_config("old-model", 1536)
        
        # Should warn but not raise
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            test_db.validate_embedding_config("new-model", 1536)
            
            # Check that a warning was issued
            assert len(w) == 1
            assert "model changed" in str(w[0].message).lower()
    
    def test_no_validation_on_first_ingestion(self, test_db):
        """Test that validation passes when no config is stored yet."""


# =============================================================================
# Citation Enforcement Tests
# =============================================================================

class TestCitationEnforcement:
    """Tests for citation enforcement in RAG responses."""
    
    def test_keeps_proper_evidence_line(self, test_db, sample_bets):
        from src.rag import RAGAssistant
        from src.models import RetrievalResult
        
        assistant = RAGAssistant(test_db)
        
        # Use sample_bets fixture
        mock_results = [RetrievalResult(bet=sample_bets[0], match_type="test")]
        
        answer = "There are 100 bets.\n\nEvidence: [B0001, B0002]"
        result = assistant._enforce_citations(answer, ["B0001", "B0002"], mock_results)
        
        assert result == answer  # Should be unchanged
    
    def test_adds_evidence_when_missing(self, test_db, sample_bets):
        from src.rag import RAGAssistant
        from src.models import RetrievalResult
        
        assistant = RAGAssistant(test_db)
        mock_results = [RetrievalResult(bet=sample_bets[0], match_type="test")]
        
        # Answer mentions bet ID but no Evidence line
        answer = "The bet B0001 shows a stake of £10."
        result = assistant._enforce_citations(answer, ["B0001"], mock_results)
        
        assert "Evidence: [B0001]" in result
    
    def test_uses_fallback_when_no_citations(self, test_db, sample_bets):
        from src.rag import RAGAssistant
        from src.models import RetrievalResult
        
        assistant = RAGAssistant(test_db)
        mock_results = [RetrievalResult(bet=sample_bets[0], match_type="test")]
        
        # Answer with NO citations at all
        answer = "The total stake is £2765."
        result = assistant._enforce_citations(answer, [], mock_results)
        
        assert "Evidence: [B0001]" in result
    
    def test_no_change_when_no_results(self, test_db):
        from src.rag import RAGAssistant
        
        assistant = RAGAssistant(test_db)
        
        answer = "No data found."
        result = assistant._enforce_citations(answer, [], [])
        
        assert result == answer
    
    def test_replaces_malformed_evidence(self, test_db, sample_bets):
        from src.rag import RAGAssistant
        from src.models import RetrievalResult
        
        assistant = RAGAssistant(test_db)
        mock_results = [RetrievalResult(bet=sample_bets[0], match_type="test")]
        
        answer = "There are 100 bets.\nEvidence: malformed"
        result = assistant._enforce_citations(answer, [], mock_results)
        
        assert "Evidence: [B0001]" in result
        assert "malformed" not in result


# =============================================================================
# EmbeddingService Tests
# =============================================================================

class TestEmbeddingService:
    """Tests for the centralized EmbeddingService."""
    
    def test_singleton_pattern(self):
        """Test that get_embedding_service returns the same instance."""
        from src.embedding_service import get_embedding_service
        
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        
        assert service1 is service2, "Should return same singleton instance"
    
    def test_cache_stats(self):
        """Test cache statistics."""
        from src.embedding_service import EmbeddingService
        
        service = EmbeddingService()
        stats = service.cache_stats()
        
        assert "size" in stats
        assert "max_size" in stats
        assert stats["size"] == 0  # Fresh service has empty cache
        assert stats["max_size"] == EmbeddingService.CACHE_SIZE
    
    def test_clear_cache(self):
        """Test cache clearing."""
        from src.embedding_service import EmbeddingService
        
        service = EmbeddingService()
        # Manually add to cache
        service._cache["test_hash"] = "test_value"
        assert len(service._cache) == 1
        
        service.clear_cache()
        assert len(service._cache) == 0
    
    def test_text_hash_consistency(self):
        """Test that same text produces same hash."""
        from src.embedding_service import EmbeddingService
        
        service = EmbeddingService()
        
        text = "This is a test"
        hash1 = service._text_hash(text)
        hash2 = service._text_hash(text)
        
        assert hash1 == hash2, "Same text should produce same hash"
    
    def test_text_hash_uniqueness(self):
        """Test that different texts produce different hashes."""
        from src.embedding_service import EmbeddingService
        
        service = EmbeddingService()
        
        hash1 = service._text_hash("Text one")
        hash2 = service._text_hash("Text two")
        
        assert hash1 != hash2, "Different texts should produce different hashes"


# =============================================================================
# ID Normalization Tests
# =============================================================================

class TestIDNormalization:
    """Tests for bet ID and customer ID normalization."""
    
    def test_customer_id_extra_zeros(self, test_db):
        from src.retrieval import Retriever
        
        retriever = Retriever(test_db)
        
        # All of these should normalize to C029
        assert retriever._normalize_customer_id("C0029") == "C029"
        assert retriever._normalize_customer_id("C029") == "C029"
        assert retriever._normalize_customer_id("C29") == "C029"
        assert retriever._normalize_customer_id("29") == "C029"
        assert retriever._normalize_customer_id("c029") == "C029"
    
    def test_bet_id_extra_zeros(self, test_db):
        from src.retrieval import Retriever
        
        retriever = Retriever(test_db)
        
        # All of these should normalize to B0001
        assert retriever._normalize_bet_id("B00001") == "B0001"
        assert retriever._normalize_bet_id("B0001") == "B0001"
        assert retriever._normalize_bet_id("B001") == "B0001"
        assert retriever._normalize_bet_id("B1") == "B0001"
        assert retriever._normalize_bet_id("1") == "B0001"
        assert retriever._normalize_bet_id("b0001") == "B0001"
    
    def test_extract_customer_with_extra_zeros(self, test_db):
        from src.retrieval import Retriever
        
        retriever = Retriever(test_db)
        
        # C0029 should extract and normalize to C029
        ids = retriever._extract_all_customer_ids("Show customer C0029 bets")
        assert ids == ["C029"]
    
    def test_extract_bet_with_extra_zeros(self, test_db):
        from src.retrieval import Retriever
        
        retriever = Retriever(test_db)
        
        # B00001 should extract and normalize to B0001
        ids = retriever._extract_all_bet_ids("Show bet B00001")
        assert ids == ["B0001"]
