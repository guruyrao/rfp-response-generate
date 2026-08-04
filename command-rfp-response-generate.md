---
description: Generate an RFP response using the local 4-agent RAG pipeline (extract requirements, index knowledge, draft response, compliance review). All local via Ollama + ChromaDB. Usage: /rfp-response-generate <agent> [path]
agent: build
---

You are executing the rfp-response-generate skill. Load the skill context, then run the requested agent.

## Context to load first

1. `.opencode/skills/rfp-response-generate/SKILL.md` — what the skill is and the agent map
2. `.opencode/skills/rfp-response-generate/agent.md` — your role, conventions
3. `.opencode/skills/rfp-response-generate/skills/ingest.md` or `retrieve.md` — if the agent uses them
4. `.opencode/skills/rfp-response-generate/scripts/` — the deterministic scripts

## Arguments

- Agent name: `$1` — one of: `extract_requirements`, `knowledge_store`, `generate_response`, `review_compliance`, `query_kb`, `all`
- Optional path: `$2` (RFP file for agent 1/3, knowledge dir for agent 2, draft for agent 4)
- Remaining input: `$ARGUMENTS` (e.g. `--feedback "..."`)

## Agent execution

Run the matching script with `py -3.10` under `scripts/`:

| Agent (`$1`) | Script | Extra arg |
|---|---|---|
| `extract_requirements` | `extract_requirements.py` | `$2` = RFP pdf/md/txt (default: first file in `C:\rag\source\`) |
| `knowledge_store` | `knowledge_store.py` | `$2` = knowledge folder **or a single pdf/md/txt** (default: `C:\rag\knowledge\`) |
| `generate_response` | `generate_response.py` | `$2` = requirements json (default: latest in `C:\rag\chunks\`) |
| `review_compliance` | `review_compliance.py` | `$2` = draft md (default: latest in `C:\rag\output\`); pass `--feedback "..."` via `$ARGUMENTS` |
| `all` | `run_all.py` | `$2` = RFP pdf (optional) |
| `query_kb` | `query_kb.py` | `$2` = question; test retrieval from the knowledge base only (no pipeline) |

Example:
```
/rfp-response-generate extract_requirements sample_data\source\sample_rfp.md
/rfp-response-generate knowledge_store sample_data\knowledge
/rfp-response-generate knowledge_store sample_data\knowledge\qa_coaching_platform_spec.md
/rfp-response-generate query_kb "automated coaching workflows"
/rfp-response-generate generate_response
/rfp-response-generate review_compliance --feedback "Add pricing section per reviewer comment"
/rfp-response-generate all sample_data\source\sample_rfp.md
```
Path prefixes are relative to the skill folder (`.opencode/skills/rfp-response-generate/`).

## Environment

- LLM: default Groq (`llama-3.3-70b-versatile`) — fast, no local GPU needed. Override with `$env:LLM_PROVIDER` (`deepseek`, `ollama`). API keys auto-load from `~/.local/share/opencode/auth.json` (or set `$env:GROQ_API_KEY` / `$env:DEEPSEEK_API_KEY`).
- Embeddings: `nomic-embed-text` on local Ollama (must be running for Agent 2/3).
- Everything else local: `C:\rag\chroma_db\` (ChromaDB), `C:\rag\output\` (drafts), `C:\rag\feedback\` (review log)

## After running

Report: which agent ran, the output file path(s), and any next step (e.g. run Agent 4 again, or review the draft manually).
