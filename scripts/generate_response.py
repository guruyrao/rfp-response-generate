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
    """Return the org template content used as the format reference.

    Prefers a PDF template in templates/ (the ATMECS response PDF if present),
    falling back to response_template.md, then a minimal default skeleton. The
    returned text is passed to the LLM as {templates} so each drafted section
    follows the template's structure/tone/format. Env TEMPLATE_FILE overrides.
    """
    templates_dir = os.path.join(RAG_ROOT, "templates")
    override = os.environ.get("TEMPLATE_FILE")
    if override and os.path.isfile(override):
        return _read_template(override)
    if os.path.isdir(templates_dir):
        if os.path.isfile(os.path.join(templates_dir, "ATMECS-TUI Cloud Engineering - RFP Response - v1.0.pdf")):
            pdf_path = os.path.join(templates_dir, "ATMECS-TUI Cloud Engineering - RFP Response - v1.0.pdf")
            return _read_template(pdf_path)
        for name in sorted(os.listdir(templates_dir)):
            if name.lower().endswith(".pdf") and os.path.isfile(os.path.join(templates_dir, name)):
                return _read_template(os.path.join(templates_dir, name))
        md_path = os.path.join(templates_dir, "response_template.md")
        if os.path.isfile(md_path):
            return _read_template(md_path)
    # default skeleton if no template found
    return "# {rfp_title}\n\n## 1. Executive Summary\n\n## 2. Requirements Response\n\n## 3. Compliance\n"


def _read_template(path):
    import rag as _rag
    try:
        return _rag.extract_text(path)
    except Exception:
        return ""


def clean_template_for_llm(template_text, cap=12000):
    """Compact the (possibly large PDF) template into a structure summary for the
    per-criterion drafting prompt, so the LLM matches format/tone without a
    90k-token payload per call. Returns top-level numbered section titles only
    (e.g. "1. Executive Summary") plus a short body excerpt.
    """
    import re as _re
    heads = [m.strip() for m in _re.findall(r"^\d+\.\s+[A-Za-z][A-Za-z &'/\-():,]+$", template_text, _re.MULTILINE)]
    head_str = "TEMPLATE TOP-LEVEL SECTIONS (match this structure/format):\n" + "\n".join(heads[:40])
    if len(template_text) <= cap:
        return head_str + "\n\n" + template_text
    head_str += "\n\nTEMPLATE EXCERPT (tone/format reference):\n" + template_text[:cap - len(head_str) - 300]
    return head_str


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
        print("[Agent 3] WARNING: no template found in templates/ ; using default structure", file=sys.stderr)
        template = "# {rfp_title}\n\n## 1. Executive Summary\n\n## 2. Requirements Response\n\n## 3. Compliance\n"

    # Template is shown to the LLM as the format/tone reference. For a large PDF
    # template, pass a structure summary so we don't burn 90k tokens per call.
    template_for_llm = clean_template_for_llm(template)

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
            .replace("{templates}", template_for_llm)
            .replace("{retrieved_context}", retrieved_context)
        )

        print(f"  [{idx}/{len(criteria)}] drafting section for: {text[:60]}...")
        try:
            section = chat_retry(draft_prompt, user_prompt, format_json=False)
        except Exception as e:
            print(f"  [{idx}/{len(criteria)}] FAILED: {e}")
            section = f"**{text}**\n\n> Draft failed — review required.\n"
        section = section.strip()
        # strip leading template-subsection headings the LLM may echo (e.g. "### 2.3.5. Title")
        section = re.sub(r"^\s*###\s*\d+(?:\.\d+)*\.?\s+[^\n]*\n+", "", section).strip()
        with open(cp, "w", encoding="utf-8") as f:
            f.write(section)
        sections.append(section)

    rfp_title = base.replace("_", " ").replace("-", " ").title()

    # Assemble: use the template skeleton (the ATMECS PDF structure, cleaned) as
    # the document body, and insert each drafted requirement under the most
    # relevant numbered section. Unmatched requirements fall into a
    # "Requirements Response" section so nothing is lost.
    header = re.sub(r"\{rfp_title\}", rfp_title, template)
    body_parts = []
    for idx, crit in enumerate(criteria, 1):
        text = crit.get("criterion_text", "").strip()
        if not text:
            continue
        sec = sections[len(body_parts)]
        body_parts.append(f"### {idx}. {text}\n\n{sec}")

    assembled = insert_requirements_into_template(header, criteria, body_parts, rfp_title)

    if not out:
        out = os.path.join(RAG_ROOT, "output", f"{base}_response_v1.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(assembled.rstrip() + "\n")

    print(f"[Agent 3] Draft saved -> {out}")


# Map criterion category -> template section (top-level "N. Title") keywords.
SECTION_KEYWORDS = {
    "pricing": "Pricing",
    "commercial": "Pricing",
    "integration": "Roles and Responsibilities",
    "security": "Governance",
    "compliance": "Governance",
    "talent": "Talent Acquisition & Retention",
    "support": "Roles and Responsibilities",
    "technical": "Cloud Services",
}


def insert_requirements_into_template(template_text, criteria, body_parts, rfp_title):
    """Append drafted requirement sections as a structured REQUIREMENTS RESPONSE
    appendix to the template skeleton.

    We do not perform fragile in-place anchor replacement on the template (PDF
    text contains a table of contents where section-number anchors first match
    TOC lines, corrupting the document). Instead, the template's full structure
    and tone are preserved verbatim, and a consolidated, well-ordered
    "Requirements Response" section is appended at the end — grouped by the
    template section each requirement maps to (so a reviewer sees, e.g., the
    security requirements under a "Governance" group).
    """
    import re as _re

    outline = _re.findall(r"(\d+(?:\.\d+)?)\.?\s+([A-Za-z][A-Za-z &'/\-():,]+)\n", template_text)
    section_titles = [name.strip() for _num, name in outline]

    def map_section(crit):
        cat = (crit.get("category") or "").lower()
        ctext = (crit.get("criterion_text", "")).lower()
        for kw, dst in SECTION_KEYWORDS.items():
            if kw in cat or kw in ctext:
                # confirm the template actually has this section
                if any(dst.lower() in t.lower() for t in section_titles):
                    return dst
        return None

    groups = {}
    unmapped = []
    for crit, part in zip(criteria, body_parts):
        dst = map_section(crit)
        if dst:
            groups.setdefault(dst, []).append(part)
        else:
            unmapped.append(part)

    out = template_text.replace("{rfp_title}", rfp_title) if False else template_text
    out = out.rstrip()

    parts = []
    # keep template section order when grouping
    for title in section_titles:
        if title in groups:
            parts.append(f"\n### {title}\n")
            for g in groups[title]:
                parts.append(g)
            parts.append("")
    if unmapped:
        parts.append("\n### General / Unmapped Requirements\n")
        for u in unmapped:
            parts.append(u)
            parts.append("")

    if parts:
        out = out + "\n\n## REQUIREMENTS RESPONSE\n\n" + "\n".join(parts).rstrip() + "\n"
    return out


if __name__ == "__main__":
    main()
