---
name: rfp-response-generate
description: Generate RFP responses using a 4-agent RAG pipeline (extract requirements, index knowledge, draft from past work, review for compliance). Fast cloud LLM (Groq default) + local ChromaDB. Use when the user invokes /rfp-response-generate.
---

# Skill: rfp-response-generate

RFP response generator. Reads an RFP, extracts requirements, retrieves past work from a knowledge base (RAG), drafts a response following the organization template, and iterates through a compliance review. LLM calls use a fast cloud API; embeddings + vector store are local.

## Invocation

| Command | Agent | What it does |
|---------|-------|--------------|
| `/rfp-response-generate extract_requirements [rfp.pdf]` | 1 — DocumentProcessor | Read RFP, chunk it, extract structured requirements + categories → JSON |
| `/rfp-response-generate knowledge_store [knowledge_dir]` | 2 — ContextRetriever | Walk knowledge folder, chunk, embed (Ollama `nomic-embed-text`), upsert into ChromaDB |
| `/rfp-response-generate generate_response [rfp.pdf]` | 3 — ProposalDrafter | Requirements + RAG-retrieved past work + org template → DRAFT response (Markdown) |
| `/rfp-response-generate review_compliance [draft.md]` | 4 — ComplianceOfficer | Review draft against `compliance.md` + user feedback → new version; iterate until approved |
| `/rfp-response-generate all [rfp.pdf]` | Orchestrator | Run all 4 agents end-to-end |

## Prerequisites

- **LLM** (cloud, fast): default Groq `llama-3.3-70b-versatile`. Alternatives: DeepSeek `deepseek-v4-flash` (`LLM_PROVIDER=deepseek`) or local Ollama `deepseek-r1:7b` (`LLM_PROVIDER=ollama`). API keys auto-load from `~/.local/share/opencode/auth.json`.
- **Ollama** running locally for embeddings: `nomic-embed-text` (`ollama pull nomic-embed-text`)
- **Python 3.10+** with `chromadb`, `pymupdf` installed
- **ChromaDB** — embedded, in-process, stores in `C:\rag\chroma_db\`

## Folder Layout

```
C:\rag\
  source\         <- raw RFP files (PDF, md, txt)
  knowledge\      <- past RFP responses, specs, case studies (Agent 2 indexes these)
  chunks\         <- processed chunks + extracted requirements (jsonl/json)
  chroma_db\      <- vector index (auto-created by Chroma)
  templates\      <- response_template.md (org format Agent 3 must follow)
  compliance.md   <- compliance criteria Agent 4 reviews against
  output\         <- generated response drafts (v1, v2, ...)
  feedback\       <- review feedback log
  skills\         <- ingest.md, retrieve.md (agent guidance)
```

Sample inputs for testing ship in `sample_data/` (see `sample_data/README.md`).

## Architecture

```
RFP (source\) ──Agent 1──> requirements.json
                              │
knowledge\ ──Agent 2──> chroma_db (RAG)      template\response_template.md
                              │                       │
                              └────Agent 3───────────┘  RAG retrieve past work
                                       │
                                   DRAFT response (output\v1.md)
                                       │
compliance.md + user feedback ──Agent 4──> reviewed → v2 → ... → APPROVED
```

## Data Flow

1. **Agent 1** reads the RFP, chunks by section, calls the LLM per chunk to extract requirements with categories → `chunks\{rfp}_requirements.json`
2. **Agent 2** walks `knowledge\`, chunks docs, embeds with `nomic-embed-text`, upserts to ChromaDB collection `knowledge`
3. **Agent 3** loads the requirements JSON + org template, retrieves similar past work per requirement from ChromaDB, drafts each section → `output\{rfp}_response_v1.md`
4. **Agent 4** reads `compliance.md` + optional user feedback, reviews the draft, produces feedback, regenerates `v2`; loop repeats until compliance passes or user accepts

## Conventions

- All LLM chat calls go through `scripts/ollama_client.py` (provider selectable via `LLM_PROVIDER`: `groq` default, `deepseek`, or `ollama`)
- Embeddings use the Ollama `/api/embed` endpoint with the **`input`** field (not `prompt`)
- ChromaDB is embedded (PersistentClient at `C:\rag\chroma_db\`), single-user
- Output is Markdown (review/edit friendly); versioned in `output\`
- Always report which agent ran and the output file path
