# trace_callgraph.py
from pycallgraph2 import PyCallGraph
from pycallgraph2.output import GraphvizOutput

with PyCallGraph(output=GraphvizOutput(output_file='callgraph.png')):
    # Run your code
    from src.database import Database
    from src.rag import RAGAssistant
    from src.config import DATABASE_PATH
    
    db = Database(DATABASE_PATH)
    db.load_embeddings_to_memory()
    assistant = RAGAssistant(db)
    assistant.ask("Why was bet B0004 rejected?")