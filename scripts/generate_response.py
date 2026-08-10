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
ADD_INSTRUCTIONS = os.path.join(BASE_DIR, "prompts", "additional_instructions.md")
RAG_ROOT = os.environ.get("RAG_ROOT", r"C:\rag")


def load_prompt(path):
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_additional_instructions():
    """Load the extra RFP response instructions (if provided) as drafting rules."""
    return load_prompt(ADD_INSTRUCTIONS).strip()


def find_requirements(arg):
    """Return the requirements JSON strictly for the requested RFP.

    If arg is a path to a *_requirements.json, use exactly that file. If arg is
    a source RFP (pdf/md/txt), derive its requirements JSON by base name. Never
    fall back to an arbitrary *_requirements.json from chunks/ (that can pull in
    a different RFP's requirements, e.g. sample_rfp_requirements.json).
    """
    if arg:
        p = os.path.abspath(arg)
        if not os.path.isfile(p):
            return None
        lower = p.lower()
        if lower.endswith("_requirements.json"):
            return p
        base = os.path.splitext(os.path.basename(p))[0]
        cand = os.path.join(RAG_ROOT, "chunks", f"{base}_requirements.json")
        if os.path.isfile(cand):
            return cand
        return None
    # No arg: only use the requirements file whose base matches the current RFP
    # source dir if there is exactly one; otherwise refuse (avoid mixing).
    chunks_dir = os.path.join(RAG_ROOT, "chunks")
    if os.path.isdir(chunks_dir):
        cands = sorted(
            os.path.join(chunks_dir, n) for n in os.listdir(chunks_dir)
            if n.endswith("_requirements.json")
        )
        if len(cands) == 1:
            return cands[0]
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


def short_title(text, max_words=3):
    """Derive a short 2-3 word heading from a long criterion text.

    Drops leading stop/filler words and focuses on the requirement subject so
    headings stay short (e.g. "Automated Coaching & Upskilling Workflows must be
    available, including Asynchronous Training Delivery." -> "Automated Coaching
    Upskilling"). Empty results fall back to the first max_words words.
    """
    if not text:
        return ""
    t = re.sub(r"\s+", " ", text.strip())
    stop = {"the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with", "&",
            "must", "should", "shall", "will", "can", "could", "including", "include",
            "be", "is", "are", "provide", "provided", "ensure", "ensure,"}
    tokens = [w.strip(".,;:!?()[]{}'\u201c\u201d\u2018\u2019-")
              for w in re.split(r"[\s&]+", t)]
    meaningful = [w for w in tokens if w and w.lower() not in stop]
    if not meaningful:
        meaningful = tokens
    pick = meaningful[:max_words]
    # drop leading determiners that are not meaningful subjects
    while pick and pick[0].lower() in {"the", "a", "an", "and", "or", "to", "for", "including"}:
        pick = pick[1:]
    title = " ".join(pick)
    title = re.sub(r"^(Including|Include|All|Any|The|A|An|Be|Is|Are|To|Provide|Seamless)\s+", "", title)
    title = title.strip()
    if len(title.split()) >= 2:
        # keep original word casing (acronyms, proper nouns), don't .title() re-mangle
        pass
    return title.title() if title else (t[:max_words * 8].title() if t else "")


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
    add_instr = load_additional_instructions()
    if add_instr:
        draft_prompt = draft_prompt + "\n\n# ADDITIONAL INSTRUCTIONS (MANDATORY)\n" + add_instr

    client = rag.get_client()
    collection = rag.get_collection(client)

    sections = []
    coverage = []  # (criterion_text, section_label, status) for the compliance matrix
    # Per-RFP results dir so sections never mix across different RFPs.
    results_dir = os.path.join(os.path.dirname(req_path), f"agent3_chunks_{base}_requirements")
    os.makedirs(results_dir, exist_ok=True)

    for idx, crit in enumerate(criteria, 1):
        text = crit.get("criterion_text", "").strip()
        if not text:
            continue
        cp = os.path.join(results_dir, f"section_{idx:02d}.md")
        if os.path.exists(cp):
            with open(cp, "r", encoding="utf-8") as f:
                section = f.read()
            sections.append(section)
            coverage.append((text, map_section_label(crit), "draft"))
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
        status = "covered" if retrieved else "gap"
        coverage.append((text, map_section_label(crit), status))

    rfp_title = base.replace("_", " ").replace("-", " ").title()

    # Assemble: use the template skeleton (the ATMECS PDF structure, cleaned) as
    # the document body, and insert each drafted requirement under the most
    # relevant numbered section. Unmatched requirements fall into a
    # "Requirements Response" section so nothing is lost.
    header = re.sub(r"\{rfp_title\}", rfp_title, template)
    body_parts = []
    seq = 0
    for idx, crit in enumerate(criteria, 1):
        text = crit.get("criterion_text", "").strip()
        if not text:
            continue
        seq += 1
        sec = sections[len(body_parts)]
        heading = short_title(text)
        body_parts.append(f"### {seq}. {heading}\n\n*{text}*\n\n{sec}")

    assembled = insert_requirements_into_template(header, criteria, body_parts, rfp_title)

    # Instruction #9: RFP Compliance Coverage matrix.
    matrix = build_compliance_matrix(criteria, coverage)
    assembled = assembled.rstrip() + "\n\n---\n\n## REQUIREMENTS RESPONSE -- Compliance Coverage Matrix\n\n" + matrix + "\n"

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


def map_section_label(crit):
    """Return the template section label a criterion maps to (or 'General')."""
    cat = (crit.get("category") or "").lower()
    ctext = (crit.get("criterion_text") or "").lower()
    for kw, dst in SECTION_KEYWORDS.items():
        if kw in cat or kw in ctext:
            return dst
    return "General / Unmapped"


def build_compliance_matrix(criteria, coverage):
    """RFP Compliance Coverage matrix (instruction #9)."""
    lines = [
        "| RFP Requirement | Addressed Section | Status |",
        "|---|---|---|",
    ]
    for crit, cov in zip(criteria, coverage):
        text = (crit.get("criterion_text") or "").strip()[:80]
        sec_label = cov[1] if len(cov) > 1 else map_section_label(crit)
        status = cov[2] if len(cov) > 2 else "draft"
        if status == "gap":
            mark = "[GAP] Uncovered"
        elif status in ("covered", "draft", "cached"):
            mark = "[OK] Covered"
        else:
            mark = "[PARTIAL] Review"
        lines.append(f"| {text} | {sec_label} | {mark} |")
    return "\n".join(lines)


def insert_requirements_into_template(template_text, criteria, body_parts, rfp_title):
    """Append drafted requirement sections as a structured REQUIREMENTS RESPONSE
    appendix to the template skeleton.

    Requirements are already rendered in strict sequential order (### 1. .. ### N.)
    by the caller, so we keep that order verbatim instead of re-grouping them
    under template subsections (which previously made numbering look non-sequential
    when template headings were interleaved). The template structure/tone is
    preserved at the top as the document body.
    """
    out = template_text.replace("{rfp_title}", rfp_title)
    out = out.rstrip()

    appendix = "\n\n## REQUIREMENTS RESPONSE\n\n" + "\n\n".join(body_parts).rstrip() + "\n"
    return out + appendix


if __name__ == "__main__":
    main()
