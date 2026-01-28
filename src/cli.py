"""
CLI interface for the Sportsbook RAG Assistant.

Provides commands for:
- Data ingestion
- Querying bets
- Testing retrieval
"""

import click
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from .config import CSV_PATH, DATABASE_PATH
from .database import Database
from .ingestion import Ingestion
from .retrieval import Retriever, create_retriever
from .models import RetrievalResult, Bet
from .rag import RAGAssistant, create_rag_assistant


console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    Sportsbook RAG Assistant - Query sports betting data using natural language.
    """
    pass


@cli.command()
@click.option(
    "--csv", "-c",
    type=click.Path(exists=True),
    default=None,
    help="Path to the CSV file (default: data/bets.csv)"
)
@click.option(
    "--db", "-d",
    type=click.Path(),
    default=None,
    help="Path to the database file (default: data/bets.db)"
)
@click.option(
    "--skip-embeddings", "-s",
    is_flag=True,
    help="Skip embedding generation (for testing without API key)"
)
def ingest(csv: Optional[str], db: Optional[str], skip_embeddings: bool):
    """
    Ingest bet data from CSV into the database.
    
    This command loads the CSV file, generates embeddings using OpenAI,
    and stores everything in the hybrid database.
    """
    try:
        db_instance = Database(Path(db) if db else DATABASE_PATH)
        ingestion = Ingestion(db_instance)
        
        count = ingestion.ingest(
            csv_path=Path(csv) if csv else CSV_PATH,
            generate_embeddings=not skip_embeddings
        )
        
        # Show stats
        stats = ingestion.get_stats()
        
        console.print("\n[bold green]Ingestion Statistics:[/bold green]")
        console.print(f"  Total bets: {stats['total_bets']}")
        console.print(f"  Unique customers: {stats['unique_customers']}")
        console.print(f"  By status: {stats['by_status']}")
        console.print(f"  By incident: {stats['by_incident']}")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@cli.command()
@click.argument("query")
@click.option(
    "--top-k", "-k",
    default=100,
    help="Number of results to return (default: 100)"
)
@click.option(
    "--method", "-m",
    type=click.Choice(["auto", "semantic", "text", "exact"]),
    default="auto",
    help="Retrieval method (default: auto)"
)
@click.option(
    "--db", "-d",
    type=click.Path(exists=True),
    default=None,
    help="Path to the database file"
)
def search(query: str, top_k: int, method: str, db: Optional[str]):
    """
    Search for bets using natural language queries.
    
    Examples:
    
    \b
      sportsbook search "Why was bet B0004 rejected?"
      sportsbook search "Customer C068 bets"
      sportsbook search "LATENCY_SPIKE incidents"
      sportsbook search "high latency bets" --top-k 10
    """
    try:
        db_instance = Database(Path(db) if db else DATABASE_PATH)
        db_instance.load_embeddings_to_memory()
        retriever = Retriever(db_instance)
        
        console.print(f"\n[bold]Query:[/bold] {query}")
        console.print(f"[bold]Method:[/bold] {method}")
        console.print()
        
        # Execute search based on method
        if method == "semantic":
            results = retriever.semantic_search(query, top_k)
        elif method == "text":
            results = retriever.text_search(query, top_k)
        elif method == "exact":
            # Try bet ID first, then customer ID
            results = []
            bet_result = retriever.get_bet(query)
            if bet_result:
                results = [bet_result]
            else:
                results = retriever.get_customer_bets(query)
        else:  # auto
            results = retriever.retrieve(query, top_k=top_k)
        
        # Display results
        _display_results(results, query)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@cli.command()
@click.option(
    "--bet-id", "-b",
    help="Get a specific bet by ID"
)
@click.option(
    "--customer", "-c",
    help="Get all bets for a customer"
)
@click.option(
    "--status", "-s",
    type=click.Choice(["SETTLED", "PENDING", "VOID", "REJECTED"]),
    help="Filter by status"
)
@click.option(
    "--incident", "-i",
    type=click.Choice(["NONE", "LATENCY_SPIKE", "FEED_OUTAGE", "MARKET_SUSPENDED", "MANUAL_REVIEW"]),
    help="Filter by incident tag"
)
@click.option(
    "--sport",
    type=click.Choice(["football", "tennis", "basketball"]),
    help="Filter by sport"
)
@click.option(
    "--top-delay", "-t",
    type=int,
    default=None,
    help="Get top N bets by price delay"
)
@click.option(
    "--db", "-d",
    type=click.Path(exists=True),
    default=None,
    help="Path to the database file"
)
def filter(
    bet_id: Optional[str],
    customer: Optional[str],
    status: Optional[str],
    incident: Optional[str],
    sport: Optional[str],
    top_delay: Optional[int],
    db: Optional[str]
):
    """
    Filter bets using structured queries.
    
    Examples:
    
    \b
      sportsbook filter --bet-id B0042
      sportsbook filter --customer C068
      sportsbook filter --status REJECTED
      sportsbook filter --incident LATENCY_SPIKE
      sportsbook filter --top-delay 5
    """
    try:
        db_instance = Database(Path(db) if db else DATABASE_PATH)
        retriever = Retriever(db_instance)
        
        results = []
        query_desc = ""
        
        if bet_id:
            query_desc = f"Bet ID: {bet_id}"
            result = retriever.get_bet(bet_id)
            results = [result] if result else []
        elif customer:
            query_desc = f"Customer: {customer}"
            results = retriever.get_customer_bets(customer)
        elif status:
            query_desc = f"Status: {status}"
            results = retriever.filter_by_status(status)
        elif incident:
            query_desc = f"Incident: {incident}"
            results = retriever.filter_by_incident(incident)
        elif sport:
            query_desc = f"Sport: {sport}"
            results = retriever.filter_by_sport(sport)
        elif top_delay:
            query_desc = f"Top {top_delay} by delay"
            results = retriever.get_top_by_delay(top_delay)
        else:
            console.print("[yellow]No filter specified. Use --help to see options.[/yellow]")
            return
        
        console.print(f"\n[bold]Filter:[/bold] {query_desc}")
        _display_results(results, query_desc)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@cli.command()
@click.argument("incident_tag")
@click.option(
    "--db", "-d",
    type=click.Path(exists=True),
    default=None,
    help="Path to the database file"
)
def incident_report(incident_tag: str, db: Optional[str]):
    """
    Generate a report for a specific incident type.
    
    Examples:
    
    \b
      sportsbook incident-report LATENCY_SPIKE
      sportsbook incident-report MARKET_SUSPENDED
    """
    try:
        db_instance = Database(Path(db) if db else DATABASE_PATH)
        retriever = Retriever(db_instance)
        
        summary = retriever.get_incident_summary(incident_tag.upper())
        
        if summary["count"] == 0:
            console.print(f"[yellow]No bets found with incident tag: {incident_tag}[/yellow]")
            return
        
        # Display summary panel
        panel_content = f"""
[bold]Incident Type:[/bold] {summary['incident']}
[bold]Total Bets:[/bold] {summary['count']}
[bold]Customers Affected:[/bold] {summary['customers_affected']}
[bold]Total Stake:[/bold] £{summary['total_stake']:.2f}
[bold]Avg Stake:[/bold] £{summary['avg_stake']:.2f}
[bold]Avg Delay:[/bold] {summary['avg_delay_ms']:.0f}ms
[bold]Max Delay:[/bold] {summary['max_delay_ms']}ms
[bold]Status Breakdown:[/bold] {summary['status_breakdown']}
[bold]Bet IDs:[/bold] {', '.join(summary['bet_ids'])}
"""
        console.print(Panel(panel_content, title=f"Incident Report: {incident_tag.upper()}"))
        
        # Show affected customers
        customers = retriever.get_customers_affected_by_incident(incident_tag)
        if customers:
            console.print("\n[bold]Affected Customers:[/bold]")
            table = Table()
            table.add_column("Customer ID")
            table.add_column("Bet Count")
            table.add_column("Bet IDs")
            
            for customer_id, count, bets in customers:
                bet_ids = ", ".join(b.bet_id for b in bets)
                table.add_row(customer_id, str(count), bet_ids)
            
            console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@cli.command()
@click.option(
    "--db", "-d",
    type=click.Path(exists=True),
    default=None,
    help="Path to the database file"
)
def stats(db: Optional[str]):
    """
    Display database statistics.
    """
    try:
        db_instance = Database(Path(db) if db else DATABASE_PATH)
        
        console.print("\n[bold]Database Statistics[/bold]")
        console.print("=" * 40)
        
        # Basic counts
        total = db_instance.get_bet_count()
        console.print(f"Total bets: {total}")
        
        # Status breakdown
        console.print("\n[bold]By Status:[/bold]")
        for status, count in db_instance.count_by_status().items():
            console.print(f"  {status}: {count}")
        
        # Incident breakdown
        console.print("\n[bold]By Incident:[/bold]")
        for incident, count in db_instance.count_by_incident().items():
            console.print(f"  {incident}: {count}")
        
        # Sport breakdown
        console.print("\n[bold]By Sport:[/bold]")
        sport_stats = db_instance.get_stats_by_sport()
        table = Table()
        table.add_column("Sport")
        table.add_column("Bets")
        table.add_column("Total Stake")
        table.add_column("Avg Stake")
        table.add_column("Avg Delay (ms)")
        
        for s in sport_stats:
            table.add_row(
                s["sport"],
                str(s["bet_count"]),
                f"£{s['total_stake']:.2f}",
                f"£{s['avg_stake']:.2f}",
                f"{s['avg_delay']:.0f}"
            )
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@cli.command()
@click.argument("question")
@click.option(
    "--top-k", "-k",
    default=100,
    help="Maximum number of bets to retrieve (default: 100)"
)
@click.option(
    "--db", "-d",
    type=click.Path(exists=True),
    default=None,
    help="Path to the database file"
)
@click.option(
    "--show-context", "-c",
    is_flag=True,
    help="Show the retrieved bets used for context"
)
def ask(question: str, top_k: int, db: Optional[str], show_context: bool):
    """
    Ask a question about bet records using RAG.
    
    The assistant will retrieve relevant bets and generate a grounded
    answer with citations.
    
    Examples:
    
    \b
      sportsbook ask "Why was bet B0004 rejected?"
      sportsbook ask "Which customers were most impacted by LATENCY_SPIKE?"
      sportsbook ask "Find the highest price_delay_ms bets and summarize"
      sportsbook ask "For customer C068, summarize their bets and incidents"
    """
    try:
        db_instance = Database(Path(db) if db else DATABASE_PATH)
        assistant = RAGAssistant(db_instance)
        
        console.print(f"\n[bold]Question:[/bold] {question}\n")
        
        with console.status("[bold green]Thinking..."):
            response = assistant.ask(question, top_k=top_k)
        
        # Show retrieved context if requested
        if show_context:
            # Show SQL-computed statistics first
            if response.stats_context:
                console.print("[bold cyan]SQL Statistics (authoritative):[/bold cyan]")
                console.print(response.stats_context)
            
            # Show the bet records table
            if response.retrieved_bets:
                console.print(f"[bold]Retrieved Bets ({len(response.retrieved_bets)} shown):[/bold]")
                _display_bets_compact(response.retrieved_bets)
                console.print()
        
        # Display the answer
        console.print(Panel(
            response.answer,
            title="[bold green]Answer[/bold green]",
            border_style="green"
        ))
        
        # Show citations
        if response.citations:
            console.print(f"\n[bold]Evidence:[/bold] {', '.join(response.citations)}")
        
        # Show retrieval stats
        console.print(f"[dim]Retrieved {len(response.retrieved_bets)} bet(s) for context[/dim]")
        
        if not response.sufficient_evidence:
            console.print("\n[yellow]⚠ The answer may be incomplete due to insufficient evidence.[/yellow]")
        
    except Exception as e:
        import traceback
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()


@cli.command()
@click.option(
    "--db", "-d",
    type=click.Path(exists=True),
    default=None,
    help="Path to the database file"
)
def chat(db: Optional[str]):
    """
    Start an interactive chat session with the RAG assistant.
    
    Ask multiple questions in a conversational interface.
    Type 'quit' or 'exit' to end the session.
    """
    try:
        db_instance = Database(Path(db) if db else DATABASE_PATH)
        assistant = RAGAssistant(db_instance)
        
        console.print("\n" + "="*60)
        console.print("[bold][blue]BetTrace: A SPORTSBOOK RAG ASSISTANT[/blue][/bold]")
        console.print("="*60)
        console.print("Ask questions about bet records. Type 'quit' to exit.\n")
        console.print("Example questions:")
        console.print("  • Why was bet B0004 rejected?")
        console.print("  • Which customers were impacted by LATENCY_SPIKE?")
        console.print("  • Find the top 5 highest delay bets")
        console.print("  • Summarize bets for customer C068")
        console.print()
        
        while True:
            try:
                question = console.input("[bold cyan]You:[/bold cyan] ").strip()
                
                if question.lower() in ('quit', 'exit', 'q'):
                    console.print("\n[bold]Goodbye![/bold]")
                    break
                
                if not question:
                    continue
                
                with console.status("[bold green]Thinking..."):
                    response = assistant.ask(question)
                
                console.print(f"\n[bold green]Assistant:[/bold green]")
                console.print(response.answer)
                
                if response.citations:
                    console.print(f"\n[dim]Evidence: {', '.join(response.citations)}[/dim]")
                console.print()
                
            except KeyboardInterrupt:
                console.print("\n\n[bold]Goodbye![/bold]")
                break
                
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


def _display_bets_compact(bets: List[Bet]):
    """Display bets in a compact format."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Bet ID", style="cyan")
    table.add_column("Customer")
    table.add_column("Event")
    table.add_column("Status")
    table.add_column("Incident")
    table.add_column("Delay")
    
    for bet in bets:
        table.add_row(
            bet.bet_id,
            bet.customer_id,
            bet.event_name[:25] + "..." if len(bet.event_name) > 25 else bet.event_name,
            bet.status,
            bet.incident_tag,
            f"{bet.price_delay_ms}ms"
        )
    
    console.print(table)


def _display_results(results: list[RetrievalResult], query: str):
    """Display retrieval results in a formatted table."""
    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return
    
    console.print(f"[green]Found {len(results)} result(s)[/green]\n")
    
    # Create results table
    table = Table(title="Retrieved Bets")
    table.add_column("Bet ID", style="cyan")
    table.add_column("Customer")
    table.add_column("Sport")
    table.add_column("Event")
    table.add_column("Market")
    table.add_column("Selection")
    table.add_column("Stake", justify="right")
    table.add_column("Status")
    table.add_column("Incident")
    table.add_column("Delay (ms)", justify="right")
    if any(r.score is not None for r in results):
        table.add_column("Score", justify="right")
    
    for result in results:
        bet = result.bet
        row = [
            bet.bet_id,
            bet.customer_id,
            bet.sport,
            bet.event_name[:20] + "..." if len(bet.event_name) > 20 else bet.event_name,
            bet.market,
            bet.selection,
            f"£{bet.stake_gbp:.0f}",
            bet.status,
            bet.incident_tag,
            str(bet.price_delay_ms)
        ]
        if any(r.score is not None for r in results):
            row.append(f"{result.score:.3f}" if result.score else "-")
        table.add_row(*row)
    
    console.print(table)
    
    # Show citation format
    bet_ids = [r.bet.bet_id for r in results]
    console.print(f"\n[bold]Evidence:[/bold] {', '.join(bet_ids)}")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
