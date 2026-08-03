"""Agent 2 — ContextRetriever: build the knowledge index in ChromaDB.

Usage:
  py scripts/knowledge_store.py [knowledge_dir]
"""
import os
import sys

import rag

RAG_ROOT = os.environ.get("RAG_ROOT", r"C:\rag")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    folder = args[0] if args else os.path.join(RAG_ROOT, "knowledge")
    if not os.path.isdir(folder):
        print(f"ERROR: knowledge folder not found: {folder}", file=sys.stderr)
        sys.exit(1)

    print(f"[Agent 2] Indexing knowledge from: {folder}")
    print(f"[Agent 2] Embedding model: {os.environ.get('EMBED_MODEL', 'nomic-embed-text')}")
    rag.index_knowledge(folder)
    print(f"[Agent 2] ChromaDB collection '{rag.COLLECTION}' has {rag.collection_count()} chunks")


if __name__ == "__main__":
    main()
