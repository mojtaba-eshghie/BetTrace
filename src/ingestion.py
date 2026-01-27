"""
Data ingestion module for the Sportsbook RAG Assistant.

Handles:
- Loading bet data from CSV files
- Generating embeddings via EmbeddingService (shared, cached, with retry)
- Storing data in the hybrid database
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Optional

from .config import (
    CSV_PATH, 
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
)
from .models import Bet
from .database import Database
from .embedding_service import get_embedding_service


class Ingestion:
    """
    Handles data ingestion from CSV files into the hybrid database.
    """
    
    def __init__(self, db: Optional[Database] = None):
        """Initialize the ingestion module."""
        self.db = db or Database()
        self._embedding_service = None
    
    @property
    def embedding_service(self):
        """Get the shared embedding service (lazy initialization)."""
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    def load_csv(self, csv_path: Optional[Path] = None) -> List[Bet]:
        """
        Load bet data from a CSV file.
        
        Args:
            csv_path: Path to the CSV file. Defaults to configured path.
            
        Returns:
            List of Bet objects
        """
        path = csv_path or CSV_PATH
        
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")
        
        df = pd.read_csv(path)
        
        # Validate required columns
        required_columns = {
            "bet_id", "customer_id", "sport", "event_name", "market",
            "selection", "stake_gbp", "status", "incident_tag", "price_delay_ms"
        }
        missing = required_columns - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # Convert to Bet objects
        bets = [Bet.from_dict(row.to_dict()) for _, row in df.iterrows()]
        
        print(f"✓ Loaded {len(bets)} bets from {path}")
        return bets
    
    def generate_embeddings(
        self, 
        texts: List[str], 
        batch_size: int = 100
    ) -> np.ndarray:
        """
        Generate embeddings for a list of texts using the shared EmbeddingService.
        
        The EmbeddingService provides:
        - Caching (avoids re-embedding identical texts)
        - Retry with exponential backoff (handles rate limits and transient errors)
        - Shared OpenAI client (single connection pool)
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts per API call
            
        Returns:
            NumPy array of embeddings (shape: [len(texts), EMBEDDING_DIMENSIONS])
        """
        # Delegate to the shared embedding service
        return self.embedding_service.embed_batch(
            texts=texts,
            batch_size=batch_size,
            use_cache=True,
            show_progress=True
        )
    
    def ingest(
        self, 
        csv_path: Optional[Path] = None,
        generate_embeddings: bool = True,
        clear_existing: bool = True
    ) -> int:
        """
        Full ingestion pipeline: load CSV, generate embeddings, store in database.
        
        Args:
            csv_path: Path to the CSV file
            generate_embeddings: Whether to generate embeddings (requires API key)
            clear_existing: Whether to clear existing data before ingesting
            
        Returns:
            Number of bets ingested
            
        Raises:
            ValueError: If embedding dimensions don't match stored config
        """
        print("\n" + "="*60)
        print("SPORTSBOOK RAG - DATA INGESTION")
        print("="*60)
        
        # Step 0: Validate embedding config if not clearing
        if not clear_existing and generate_embeddings:
            stored_config = self.db.get_embedding_config()
            if stored_config:
                print(f"\n[0/4] Validating embedding config...")
                self.db.validate_embedding_config(EMBEDDING_MODEL, EMBEDDING_DIMENSIONS)
                print(f"✓ Config matches (model: {EMBEDDING_MODEL}, dim: {EMBEDDING_DIMENSIONS})")
        
        # Step 1: Load CSV
        print("\n[1/4] Loading CSV data...")
        bets = self.load_csv(csv_path)
        
        # Step 2: Clear existing data if requested
        if clear_existing:
            print("\n[2/4] Clearing existing database...")
            self.db.clear()
            print("✓ Database cleared")
        
        # Step 3: Generate embeddings
        embeddings = None
        team1_embeddings = None
        team2_embeddings = None
        if generate_embeddings:
            print("\n[3/4] Generating embeddings...")
            
            # Full document embeddings (for broad semantic search)
            documents = [bet.to_document() for bet in bets]
            embeddings = self.generate_embeddings(documents)
            print(f"✓ Generated {len(embeddings)} document embeddings (dim={embeddings.shape[1]})")
            
            # Parse event names into individual teams
            from .models import parse_event_teams, phonetic_normalize
            team_pairs = [parse_event_teams(bet.event_name) for bet in bets]
            team1_names = [t[0] for t in team_pairs]
            team2_names = [t[1] for t in team_pairs]
            
            # PHONETIC NORMALIZATION: Embed phonetic versions for typo tolerance
            # "Rapters" → "RPTRS" → embed("RPTRS")
            # "Raptors" → "RPTRS" → embed("RPTRS")  ← Same embedding!
            team1_phonetic = [phonetic_normalize(t) for t in team1_names]
            team2_phonetic = [phonetic_normalize(t) for t in team2_names]
            
            # Team1 embeddings (phonetic version)
            team1_embeddings = self.generate_embeddings(team1_phonetic)
            print(f"✓ Generated {len(team1_embeddings)} team1 phonetic embeddings")
            
            # Team2 embeddings (phonetic version, may be empty for some events)
            non_empty_indices = [i for i, t in enumerate(team2_phonetic) if t]
            if non_empty_indices:
                non_empty_team2 = [team2_phonetic[i] for i in non_empty_indices]
                non_empty_team2_emb = self.generate_embeddings(non_empty_team2)
                
                # Create full array with zeros for empty team2
                team2_embeddings = np.zeros_like(team1_embeddings)
                for idx, emb in zip(non_empty_indices, non_empty_team2_emb):
                    team2_embeddings[idx] = emb
                print(f"✓ Generated {len(non_empty_indices)} team2 phonetic embeddings")
            else:
                team2_embeddings = None
                print("✓ No team2 embeddings needed (single-participant events)")
            
            # Store embedding config for future validation
            self.db.set_embedding_config(EMBEDDING_MODEL, embeddings.shape[1])
            print(f"✓ Stored embedding config (model: {EMBEDDING_MODEL}, dim: {embeddings.shape[1]})")
        else:
            print("\n[3/4] Skipping embedding generation")
        
        # Step 4: Store in database
        print("\n[4/4] Storing in database...")
        self.db.insert_bets_batch(bets, embeddings, team1_embeddings, team2_embeddings)
        print(f"✓ Stored {len(bets)} bets in database")
        
        # Load embeddings into memory for fast search
        if embeddings is not None:
            self.db.load_embeddings_to_memory()
            print("✓ Loaded embeddings into memory")
        
        print("\n" + "="*60)
        print(f"INGESTION COMPLETE: {len(bets)} bets processed")
        print("="*60 + "\n")
        
        return len(bets)
    
    def get_stats(self) -> dict:
        """Get statistics about the ingested data."""
        return {
            "total_bets": self.db.get_bet_count(),
            "by_status": self.db.count_by_status(),
            "by_incident": self.db.count_by_incident(),
            "by_sport": self.db.get_stats_by_sport(),
            "unique_customers": len(self.db.get_unique_customers())
        }


def run_ingestion(
    csv_path: Optional[str] = None,
    db_path: Optional[str] = None,
    skip_embeddings: bool = False
) -> Database:
    """
    Convenience function to run the full ingestion pipeline.
    
    Args:
        csv_path: Path to CSV file (uses default if None)
        db_path: Path to database file (uses default if None)
        skip_embeddings: Set to True to skip embedding generation
        
    Returns:
        Initialized Database instance
    """
    db = Database(Path(db_path) if db_path else None)
    ingestion = Ingestion(db)
    ingestion.ingest(
        csv_path=Path(csv_path) if csv_path else None,
        generate_embeddings=not skip_embeddings
    )
    return db
