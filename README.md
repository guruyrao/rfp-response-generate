# rfp-response-generate

A 4-agent RFP response generator skill for opencode: extract requirements from an RFP, index a company knowledge base (RAG), draft a response from past work following an org template, and iterate through a compliance review.

- **LLM**: fast cloud API by default — Groq (`llama-3.3-70b-versatile`), or DeepSeek (`deepseek-v4-flash`), or local Ollama. Switch via `LLM_PROVIDER`.
- **Embeddings + vector store**: local — Ollama `nomic-embed-text` + embedded ChromaDB.
- **No secrets in repo**: API keys load from `~/.local/share/opencode/auth.json` or env vars.

## Install

1. Copy the repo contents into your project:
   - `.opencode/skills/rfp-response-generate/` (this repo's root)
   - `.opencode/command/rfp-response-generate.md`
2. `pip install chromadb pymupdf`
3. `ollama pull nomic-embed-text` (Ollama must be running)
4. Provide an LLM key (env var or `auth.json`): `GROQ_API_KEY` or `DEEPSEEK_API_KEY`
5. Create the runtime layout: `C:\rag\{source, knowledge, chunks, chroma_db, templates, output, feedback}`

## Usage

```
/rfp-response-generate extract_requirements sample_data\source\sample_rfp.md
/rfp-response-generate knowledge_store sample_data\knowledge
/rfp-response-generate generate_response
/rfp-response-generate review_compliance --feedback "Add pricing section"
/rfp-response-generate all sample_data\source\sample_rfp.md
```

## Architecture

| Agent | Script | Role |
|---|---|---|
| 1 — DocumentProcessor | `scripts/extract_requirements.py` | RFP → chunked → structured requirements JSON |
| 2 — ContextRetriever | `scripts/knowledge_store.py` | knowledge folder → ChromaDB index |
| 3 — ProposalDrafter | `scripts/generate_response.py` | requirements + RAG + template → draft (Markdown) |
| 4 — ComplianceOfficer | `scripts/review_compliance.py` | draft vs compliance.md + feedback → next version, iterate |

See `sample_data/README.md` for full setup and run instructions.
