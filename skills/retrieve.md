# Skill: retrieve — RAG retrieval for drafting (Agent 3)

Purpose: for each RFP requirement, retrieve the most relevant past work from the ChromaDB knowledge index so the drafted response is grounded in real, prior company output — not invented.

## Retrieval

- Query: the requirement text (optionally expanded with its keywords).
- Endpoint: `scripts/ollama_client.py` embed via `/api/embed` (`input` field), then ChromaDB `query()` on collection `knowledge`.
- Default: top-k = 3 chunks, cosine similarity.

## Grounding Rules (critical — prevents hallucination)

1. Agent 3 must base every capability claim, metric, and past-project reference on retrieved chunks or the organization template.
2. If no relevant chunk is retrieved, the section must explicitly state the requirement is unaddressed in the knowledge base rather than inventing content.
3. Always cite the source in the draft (e.g., "per our past response: {filename}").

## Usage

Pass the Chroma collection and requirement to `scripts/generate_response.py`; it retrieves internally. This file documents the retrieval contract for reference.
