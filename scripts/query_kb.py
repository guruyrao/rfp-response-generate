"""Test/query the knowledge base without running the pipeline.

Usage:
  py scripts/query_kb.py "your question"
  py scripts/query_kb.py "your question" --top-k 5
"""
import os
import sys

import rag
from ollama_client import embed

RAG_ROOT = os.environ.get("RAG_ROOT", r"C:\rag")


def main():
    args = sys.argv[1:]
    query = None
    top_k = 3
    i = 0
    while i < len(args):
        if args[i] == "--top-k" and i + 1 < len(args):
            top_k = int(args[i + 1])
            i += 2
        elif args[i].startswith("--"):
            i += 1
        else:
            query = args[i]
            i += 1

    if not query:
        print("Usage: py scripts/query_kb.py \"question\" [--top-k N]", file=sys.stderr)
        sys.exit(1)

    client = rag.get_client()
    collection = rag.get_collection(client)
    total = collection.count()
    print(f"[KB] collection '{rag.COLLECTION}' has {total} chunks")
    if total == 0:
        print("[KB] Knowledge base is empty. Run: /rfp-response-generate knowledge_store", file=sys.stderr)
        sys.exit(1)

    print(f"[KB] Query: {query}")
    results = rag.retrieve(query, embed, top_k=top_k, collection=collection)
    print(f"[KB] Top {len(results)} matches:")
    for i, r in enumerate(results, 1):
        src = (r.get("metadata") or {}).get("source", "?")
        print(f"\n--- {i}. [{src}] distance={r['distance']:.3f} ---")
        print(r["text"][:400])


if __name__ == "__main__":
    main()
