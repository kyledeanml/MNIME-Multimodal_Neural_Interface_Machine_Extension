import os
import argparse
import sys
import shutil

# Force UTF-8 stdout if needed
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Ensure progress bars and telemetry are disabled globally to avoid messy console
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

try:
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    print("[ERROR] Missing required langchain packages.")
    print("Please run: pip install langchain-huggingface langchain-community langchain-text-splitters faiss-cpu")
    sys.exit(1)

def get_embedding_model_path():
    """Locate the bundled embedding model in MNIME."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.abspath(os.path.join(script_dir, "..", "models", "bge-small-en-v1.5"))
    if not os.path.exists(model_path):
        print(f"[WARNING] Local embedding model not found at {model_path}.")
        print("Falling back to downloading 'BAAI/bge-small-en-v1.5' from HuggingFace.")
        return "BAAI/bge-small-en-v1.5"
    return model_path

def ingest_to_memory(cache_path: str, new_texts: list[str], sources: list[str]):
    """Ingests new documents into the persistent memory cache."""
    print("\n--- INGESTING MEMORIES ---")
    
    # 1. Initialize Embeddings
    print("[1/4] Initializing Embedding Model...")
    model_path = get_embedding_model_path()
    embeddings = HuggingFaceEmbeddings(
        model_name=model_path,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    # 2. Chunk the new texts
    print(f"[2/4] Chunking {len(new_texts)} documents...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    
    new_docs = []
    for text, source in zip(new_texts, sources):
        chunks = splitter.split_text(text)
        for chunk in chunks:
            new_docs.append(Document(page_content=chunk, metadata={"source": source}))
            
    if not new_docs:
        print("[ERROR] No readable text to ingest.")
        return

    # 3. Load existing memory or create new
    print("[3/4] Accessing Global Memory Cache...")
    if os.path.exists(cache_path) and os.path.exists(os.path.join(cache_path, "index.faiss")):
        print("      Found existing memory! Loading and appending...")
        vectorstore = FAISS.load_local(cache_path, embeddings, allow_dangerous_deserialization=True)
        vectorstore.add_documents(new_docs)
    else:
        print("      No existing index found. Initializing new persistent vector store...")
        vectorstore = FAISS.from_documents(new_docs, embeddings)

    # 4. Save to disk
    print(f"[4/4] Saving updated memory to disk at: {cache_path}")
    vectorstore.save_local(cache_path)
    print("[OK] Memory Ingestion Complete.")

def recall_from_memory(cache_path: str, query: str):
    """Retrieves relevant information from the persistent memory cache."""
    print(f"\n--- RECALLING MEMORY FOR: '{query}' ---")
    
    if not os.path.exists(cache_path) or not os.path.exists(os.path.join(cache_path, "index.faiss")):
        print(f"[ERROR] No memory cache found at {cache_path}. Ingest something first!")
        return

    print("[1/3] Initializing Embedding Model...")
    model_path = get_embedding_model_path()
    embeddings = HuggingFaceEmbeddings(
        model_name=model_path,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    print("[2/3] Loading Global Memory Cache from disk...")
    vectorstore = FAISS.load_local(cache_path, embeddings, allow_dangerous_deserialization=True)
    
    print("[3/3] Searching memories...")
    results = vectorstore.similarity_search(query, k=3)
    
    print("\n[RESULTS]")
    for i, res in enumerate(results):
        print(f"--- Memory Node {i+1} (Source: {res.metadata.get('source', 'Unknown')}) ---")
        print(res.page_content.strip())
        print("-" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone test for Global Persistent Memory Cache.")
    parser.add_argument("--cache", type=str, default="global_memory_cache", help="Path to the persistent FAISS cache folder")
    parser.add_argument("--demo", action="store_true", help="Run a full automated demo of ingestion and recall")
    parser.add_argument("--ingest", type=str, help="Ingest a specific string into memory")
    parser.add_argument("--query", type=str, help="Query the memory cache")
    parser.add_argument("--clear", action="store_true", help="Clear the existing memory cache")
    
    args = parser.parse_args()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_abs_path = os.path.abspath(os.path.join(script_dir, args.cache))
    
    if args.clear:
        if os.path.exists(cache_abs_path):
            shutil.rmtree(cache_abs_path)
            print(f"[OK] Cleared memory cache at {cache_abs_path}")
        else:
            print("[OK] Memory cache already empty.")
        sys.exit(0)
        
    if args.demo:
        print("==================================================")
        print(">>> INITIALIZATION: PERSISTENT GLOBAL VECTOR STORE")
        print("==================================================")
        
        # Clear for clean demo
        if os.path.exists(cache_abs_path):
            shutil.rmtree(cache_abs_path)
            
        # 1. Ingest Day 1
        ingest_to_memory(
            cache_path=cache_abs_path,
            new_texts=["The user's favorite programming language is Python.", "The secret project is codenamed 'Titanium'."],
            sources=["Conversation_Day_1", "Project_Notes"]
        )
        
        # 2. Ingest Day 2 (Appending)
        ingest_to_memory(
            cache_path=cache_abs_path,
            new_texts=["The Titanium project is scheduled to launch in December.", "The user prefers dark mode interfaces."],
            sources=["Conversation_Day_2", "UI_Preferences"]
        )
        
        # 3. Recall
        recall_from_memory(cache_path=cache_abs_path, query="What is the codename for the secret project?")
        recall_from_memory(cache_path=cache_abs_path, query="What UI theme does the user like?")
        sys.exit(0)

    if args.ingest:
        ingest_to_memory(cache_abs_path, [args.ingest], ["Manual_Entry"])
        
    if args.query:
        recall_from_memory(cache_abs_path, args.query)
        
    if not any([args.demo, args.ingest, args.query, args.clear]):
        parser.print_help()
