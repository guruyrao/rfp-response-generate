"""Agent 2 — ContextRetriever: build the knowledge index in ChromaDB.

Usage:
  py scripts/knowledge_store.py                # index C:\rag\knowledge\ (default)
  py scripts/knowledge_store.py <dir>          # index a whole folder
  py scripts/knowledge_store.py <file>         # index a single doc (pdf/md/txt)
"""
import os
import sys

import rag

RAG_ROOT = os.environ.get("RAG_ROOT", r"C:\rag")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target = args[0] if args else os.path.join(RAG_ROOT, "knowledge")

    if os.path.isdir(target):
        print(f"[Agent 2] Indexing knowledge from folder: {target}")
    elif os.path.isfile(target):
        print(f"[Agent 2] Indexing single document: {target}")
    else:
        print(f"ERROR: knowledge path not found: {target}", file=sys.stderr)
        sys.exit(1)

    print(f"[Agent 2] Embedding model: {os.environ.get('EMBED_MODEL', 'nomic-embed-text')}")
    rag.index_knowledge(target)
    print(f"[Agent 2] ChromaDB collection '{rag.COLLECTION}' has {rag.collection_count()} chunks")


if __name__ == "__main__":
    main()
