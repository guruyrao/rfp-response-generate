"""Agent 1 — DocumentProcessor: read RFP, chunk by section, extract structured requirements.

Usage:
  py scripts/extract_requirements.py [rfp.pdf] [--out chunks/{name}_requirements.json]
"""
import json
import os
import re
import sys
from collections import Counter

import rag
from ollama_client import chat_retry

PROMPT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts", "extract_requirements.md")
RAG_ROOT = os.environ.get("RAG_ROOT", r"C:\rag")

# Common all-caps words / acronyms that are NOT the customer organization.
_ACRONYM_STOP = {
    "IT", "ITSM", "ICT", "RFP", "PDF", "DOC", "SLA", "KPI", "OS", "LAN",
    "WAN", "VPN", "CPU", "RAM", "AI", "EU", "UK", "USA", "CCTV", "MSP",
    "MDM", "M365", "SaaS", "IaaS", "PaaS", "API", "HTTPS", "HTTP", "SQL",
    "ETL", "BI", "QA", "ITIL", "CISO", "CEO", "CTO", "CFO", "COO", "MS",
    "IBM", "AWS", "AZURE", "GCP", "VM", "VDI", "SSO", "MFA", "DLP", "EDR",
    "AV", "UEM", "SLA", "AR", "VR", "NOC", "SOC", "OEM", "TOGAF", "PRINCE",
    "GDPR", "ISO", "SOC2", "HIPAA", "NIST", "PCI",
}


def detect_customer_name(rfp_text, override=None):
    """Best-effort detection of the customer organization name from RFP text.

    Priority: explicit override (CUSTOMER_NAME env or CLI) > most frequent
    all-caps acronym / proper-noun phrase in the document. Returns None if no
    confident match. Used for the response header and to avoid past-customer
    names (e.g. "TUI") leaking into the output.
    """
    if override and override.strip():
        return override.strip()
    if not rfp_text:
        return None
    counts = Counter()
    # All-caps acronyms (e.g. ARIA) — strongest signal, repeated.
    for m in re.finditer(r"\b[A-Z]{2,}\b", rfp_text):
        w = m.group(0)
        if w in _ACRONYM_STOP:
            continue
        counts[w] += 1
    # Proper-noun phrases (e.g. "Advanced Research and Invention Agency").
    for m in re.finditer(r"\b(?:[A-Z][a-z]+(?:\s+(?:and|&|of)\s+[A-Z][a-z]+){1,3})\b", rfp_text):
        counts[m.group(0)] += 1
    if not counts:
        return None
    name, n = counts.most_common(1)[0]
    # Require repeated mentions to avoid picking up a one-off word.
    return name if n >= 3 else None


def load_prompt():
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def find_rfp(arg):
    if arg and os.path.isfile(arg):
        return os.path.abspath(arg)
    source_dir = os.path.join(RAG_ROOT, "source")
    if os.path.isdir(source_dir):
        for root, _d, names in os.walk(source_dir):
            for n in sorted(names):
                if n.lower().endswith((".pdf", ".md", ".txt")):
                    return os.path.join(root, n)
    return None


def normalize_criteria(parsed):
    """Accept a list of criteria, a {"criteria": [...]} wrapper, or a single
    criterion object (some LLMs return a bare object instead of an array)."""
    if isinstance(parsed, list):
        return [c for c in parsed if isinstance(c, dict) and c.get("criterion_text")]
    if isinstance(parsed, dict):
        for key in ("criteria", "requirements", "results", "items", "data"):
            val = parsed.get(key)
            if isinstance(val, list):
                cleaned = [c for c in val if isinstance(c, dict) and c.get("criterion_text")]
                if cleaned:
                    return cleaned
        if parsed.get("criterion_text"):
            return [parsed]
    return []


def main():
    args = sys.argv[1:]
    rfp = None
    out = None
    i = 0
    while i < len(args):
        if args[i] == "--out" and i + 1 < len(args):
            out = args[i + 1]
            i += 2
        elif args[i].startswith("--"):
            i += 1
        else:
            rfp = args[i]
            i += 1

    rfp = find_rfp(rfp)
    if not rfp:
        print("ERROR: no RFP file found. Pass a path or put one in C:\\rag\\source\\", file=sys.stderr)
        sys.exit(1)

    base = os.path.splitext(os.path.basename(rfp))[0]
    if not out:
        out = os.path.join(RAG_ROOT, "chunks", f"{base}_requirements.json")

    print(f"[Agent 1] Reading RFP: {rfp}")
    text = rag.extract_text(rfp)
    customer_name = detect_customer_name(
        text, override=os.environ.get("CUSTOMER_NAME")
    )
    if customer_name:
        print(f"[Agent 1] Customer organization detected: {customer_name}")
    else:
        print("[Agent 1] WARNING: could not detect customer organization name")
    chunks = rag.chunk_text(text)
    print(f"[Agent 1] {len(chunks)} chunks extracted")

    system_prompt = load_prompt()
    all_criteria = []

    # Per-RFP cache dir so chunks from one source never mix with another
    # (e.g. a prior sample_rfp run reusing chunk_01.json for a different RFP).
    results_dir = os.path.join(os.path.dirname(out), f"agent1_chunks_{base}_requirements")
    os.makedirs(results_dir, exist_ok=True)

    for i, chunk in enumerate(chunks, 1):
        cp = os.path.join(results_dir, f"chunk_{i:02d}.json")
        if os.path.exists(cp):
            with open(cp, "r", encoding="utf-8") as f:
                parsed = json.load(f)
            all_criteria.extend(parsed if isinstance(parsed, list) else parsed.get("criteria", []))
            print(f"  [{i}/{len(chunks)}] chunk {i} (cached)")
            continue

        print(f"  [{i}/{len(chunks)}] extracting criteria from chunk {i}...")
        try:
            parsed = chat_retry(system_prompt, chunk)
        except Exception as e:
            print(f"  [{i}/{len(chunks)}] FAILED: {e}")
            continue

        criteria = normalize_criteria(parsed)
        for c in criteria:
            c["source_reference"] = c.get("source_reference") or f"{base} chunk {i}"
            c["chunk"] = i

        with open(cp, "w", encoding="utf-8") as f:
            json.dump(criteria, f, indent=2, ensure_ascii=False)
        all_criteria.extend(criteria)
        print(f"  [{i}/{len(chunks)}] +{len(criteria)} criteria")

    # dedupe by criterion_text (normalized)
    seen = {}
    for c in all_criteria:
        key = c.get("criterion_text", "").strip().lower()
        if key and key not in seen:
            seen[key] = c
    unique = list(seen.values())

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"source": base, "customer_name": customer_name, "criteria": unique}, f, indent=2, ensure_ascii=False)

    print(f"[Agent 1] Done. {len(unique)} unique criteria -> {out}")


if __name__ == "__main__":
    main()
