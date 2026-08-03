"""Agent 3 — ProposalDrafter: build a draft RFP response.

For each requirement in the Agent 1 output, retrieve similar past work from the
ChromaDB knowledge index (RAG), draft a section with the LLM following the org
template, and assemble a Markdown response document.

Usage:
  py scripts/generate_response.py [requirements.json] [--out output/{name}_response_v1.md]
"""
import json
import os
import re
import sys

import rag
from ollama_client import chat_retry, embed, embed_many

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFT_PROMPT = os.path.join(BASE_DIR, "prompts", "draft_section.md")
RAG_ROOT = os.environ.get("RAG_ROOT", r"C:\rag")


def load_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def find_requirements(arg):
    if arg and os.path.isfile(arg):
        return arg
    chunks_dir = os.path.join(RAG_ROOT, "chunks")
    if os.path.isdir(chunks_dir):
        candidates = [os.path.join(chunks_dir, n) for n in sorted(os.listdir(chunks_dir))
                      if n.endswith("_requirements.json")]
        if candidates:
            return candidates[-1]
    return None


def load_template():
    tpl_path = os.path.join(RAG_ROOT, "templates", "response_template.md")
    if os.path.isfile(tpl_path):
        with open(tpl_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def main():
    args = [a for a in sys.argv[1:]]
    req_path = None
    out = None
    i = 0
    while i < len(args):
        if args[i] == "--out" and i + 1 < len(args):
            out = args[i + 1]
            i += 2
        elif args[i].startswith("--"):
            i += 1
        else:
            req_path = args[i]
            i += 1

    req_path = find_requirements(req_path)
    if not req_path or not os.path.isfile(req_path):
        print("ERROR: requirements JSON not found. Run Agent 1 (extract_requirements) first.", file=sys.stderr)
        sys.exit(1)

    with open(req_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    base = data.get("source", os.path.splitext(os.path.basename(req_path))[0].replace("_requirements", ""))
    criteria = data.get("criteria", [])
    print(f"[Agent 3] {len(criteria)} requirements from {req_path}")

    template = load_template()
    if not template:
        print("[Agent 3] WARNING: no templates/response_template.md found; using default structure", file=sys.stderr)
        template = "# {rfp_title}\n\n## 1. Executive Summary\n\n## 2. Requirements Response\n\n## 3. Compliance\n"

    draft_prompt = load_prompt(DRAFT_PROMPT)

    client = rag.get_client()
    collection = rag.get_collection(client)

    sections = []
    results_dir = os.path.join(os.path.dirname(req_path), "agent3_sections")
    os.makedirs(results_dir, exist_ok=True)

    for idx, crit in enumerate(criteria, 1):
        text = crit.get("criterion_text", "").strip()
        if not text:
            continue
        cp = os.path.join(results_dir, f"section_{idx:02d}.md")
        if os.path.exists(cp):
            with open(cp, "r", encoding="utf-8") as f:
                sections.append(f.read())
            print(f"  [{idx}/{len(criteria)}] section {idx} (cached)")
            continue

        retrieved = rag.retrieve(text, embed, top_k=3, collection=collection)
        retrieved_context = "\n\n".join(
            f"--- SOURCE: {r['metadata'].get('source', '?')} ---\n{r['text']}"
            for r in retrieved
        ) if retrieved else "No relevant past work found in the knowledge base."

        user_prompt = (
            draft_prompt.replace("{criterion_text}", text)
            .replace("{category}", crit.get("category", ""))
            .replace("{priority}", crit.get("priority", ""))
            .replace("{templates}", template)
            .replace("{retrieved_context}", retrieved_context)
        )

        print(f"  [{idx}/{len(criteria)}] drafting section for: {text[:60]}...")
        try:
            section = chat_retry(draft_prompt, user_prompt, format_json=False)
        except Exception as e:
            print(f"  [{idx}/{len(criteria)}] FAILED: {e}")
            section = f"**{text}**\n\n> Draft failed — review required.\n"
        section = section.strip()
        with open(cp, "w", encoding="utf-8") as f:
            f.write(section)
        sections.append(section)

    rfp_title = base.replace("_", " ").replace("-", " ").title()

    # Assemble into template shape. If the template has numbered headings, fill under Requirements Response.
    header = re.sub(r"\{rfp_title\}", rfp_title, template)

    body = []
    for idx, crit in enumerate(criteria, 1):
        text = crit.get("criterion_text", "").strip()
        if not text:
            continue
        sec = sections[len(body)]
        body.append(f"### {idx}. {text}\n\n{sec}")
    filled = header
    if "## 2. Requirements Response" in filled:
        filled = filled.replace(
            "## 2. Requirements Response",
            "## 2. Requirements Response\n\n" + "\n\n".join(body),
            1,
        )
    else:
        filled = filled + "\n\n## Requirements Response\n\n" + "\n\n".join(body)

    if not out:
        out = os.path.join(RAG_ROOT, "output", f"{base}_response_v1.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(filled.rstrip() + "\n")

    print(f"[Agent 3] Draft saved -> {out}")


if __name__ == "__main__":
    main()
