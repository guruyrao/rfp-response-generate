"""Test/query the knowledge base without running the pipeline.

Usage:
  py scripts/query_kb.py "your question"              # retrieval only (raw chunks)
  py scripts/query_kb.py "your question" --ask        # LLM answer grounded in the KB
  py scripts/query_kb.py "your question" --top-k 5
"""
import os
import sys

import rag
from ollama_client import chat_retry, embed

RAG_ROOT = os.environ.get("RAG_ROOT", r"C:\rag")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANSWER_PROMPT = os.path.join(BASE_DIR, "prompts", "answer_question.md")


def load(path, default=""):
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return default


def main():
    args = sys.argv[1:]
    query = None
    top_k = 3
    ask = False
    i = 0
    while i < len(args):
        if args[i] == "--top-k" and i + 1 < len(args):
            top_k = int(args[i + 1])
            i += 2
        elif args[i] == "--ask":
            ask = True
            i += 1
        elif args[i].startswith("--"):
            i += 1
        else:
            query = args[i]
            i += 1

    if not query:
        print('Usage: py scripts/query_kb.py "question" [--ask] [--top-k N]', file=sys.stderr)
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

    if not ask:
        print(f"[KB] Top {len(results)} matches:")
        for i, r in enumerate(results, 1):
            src = (r.get("metadata") or {}).get("source", "?")
            print(f"\n--- {i}. [{src}] distance={r['distance']:.3f} ---")
            print(r["text"][:400])
        return

    context_parts = []
    for i, r in enumerate(results, 1):
        src = (r.get("metadata") or {}).get("source", "?")
        context_parts.append(f"[Source: {src}]\n{r['text']}")
    context = "\n\n---\n\n".join(context_parts)

    system = load(ANSWER_PROMPT)
    user = (
        f"Context from knowledge base:\n\n{context}\n\n"
        f"Question: {query}\n\nAnswer based only on the context above."
    )
    print(f"[KB] Asking LLM (grounded in top {len(results)} chunks)...")
    try:
        answer = chat_retry(system, user, format_json=False)
        print("\n=== ANSWER ===")
        print(answer.strip())
        print("\n=== SOURCES ===")
        seen = set()
        for r in results:
            src = (r.get("metadata") or {}).get("source", "?")
            if src not in seen:
                print(f"- {src}")
                seen.add(src)
    except Exception as e:
        print(f"[KB] LLM answer failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
