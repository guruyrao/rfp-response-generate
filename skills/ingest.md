# Skill: ingest — Index knowledge into ChromaDB (Agent 2)

Purpose: turn raw knowledge documents (past RFP responses, case studies, specs, product docs) into a searchable vector index so Agent 3 can retrieve relevant past work.

## Source

- Default folder: `C:\rag\knowledge\`
- Override: pass a folder path as the command argument
- Accepted file types: `.pdf`, `.md`, `.txt`

## Pipeline

1. **Walk** the folder recursively for supported files.
2. **Extract text** per file:
   - PDF → PyMuPDF (`fitz`)
   - md/txt → raw read
3. **Chunk** each document by sections (headers first, then paragraph blocks with a soft size cap ~800 tokens with overlap).
4. **Embed** each chunk with `nomic-embed-text` (via `scripts/ollama_client.py`, `/api/embed` with `input`).
5. **Upsert** into ChromaDB collection `knowledge` at `C:\rag\chroma_db\`, storing:
   - `id` = stable hash of (source file + chunk index) for re-indexing
   - `document` = chunk text
   - `metadata` = `{source: filename, section: header, chunk: index}`
6. **Dedupe**: same id upsert replaces the old vector — re-running is safe.

## Notes

- Embeddings stay local (no cloud).
- ChromaDB is embedded/in-process; single-user.
- Report count of documents indexed and total chunks.
