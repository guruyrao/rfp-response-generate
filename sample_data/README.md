# Sample Data for rfp-response-generate

Ready-to-run sample inputs so the skill works out-of-the-box. Copy these into the local `C:\rag\` layout (or point the scripts at this folder via command args).

## Contents

```
sample_data/
├── compliance.md                  -> C:\rag\compliance.md
├── source/
│   └── sample_rfp.md              -> C:\rag\source\ (Agent 1 input RFP)
├── knowledge/
│   ├── past_performance_acmecorp.md   -> C:\rag\knowledge\ (Agent 2 indexes)
│   └── qa_coaching_platform_spec.md   -> C:\rag\knowledge\
└── templates/
    └── response_template.md       -> C:\rag\templates\ (Agent 3 output format)
```

## Setup for a new machine

1. Install Python 3.10+: `pip install chromadb pymupdf`
2. Install & start Ollama, then: `ollama pull nomic-embed-text` (embeddings stay local)
3. Provide an LLM API key:
   - Groq (default): `$env:LLM_PROVIDER = "groq"; $env:GROQ_API_KEY = "gsk_..."` or put it in `~/.local/share/opencode/auth.json`
   - DeepSeek: `$env:LLM_PROVIDER = "deepseek"; $env:DEEPSEEK_API_KEY = "sk-..."`
   - Offline: `$env:LLM_PROVIDER = "ollama"` (needs local LLM, e.g. `ollama pull deepseek-r1:7b`)
4. Create the folder layout and copy the sample files (see map above):
   ```
   C:\rag\{source, knowledge, chunks, chroma_db, templates, output, feedback}
   ```
5. Run the pipeline:
   ```
   py scripts/extract_requirements.py sample_data\source\sample_rfp.md
   py scripts/knowledge_store.py sample_data\knowledge
   py scripts/generate_response.py
   py scripts/review_compliance.py --feedback "..."
   ```
   Or end-to-end:
   ```
   py scripts/run_all.py sample_data\source\sample_rfp.md
   ```

## Notes

- `C:\rag\chroma_db\` is created automatically by ChromaDB — do not ship it.
- The RFP is synthetic ("Call Centre Agent Performance Platform"); the knowledge docs are fictional past projects. Replace both with real inputs.
