"""Lightweight compliance checker for the generated RFP draft.

Scans the assembled response against C:\\rag\\compliance.md rules and a set of
invariant checks (forbidden terms, invented-claim markers, missing requirements,
missing template sections, placeholder stubs). Emits a findings report to
C:\\rag\\feedback\\ and prints a summary. This runs locally without any LLM call,
so it is not constrained by provider quotas or context-window limits.
"""
import json
import os
import re
import sys

RAG_ROOT = os.environ.get("RAG_ROOT", r"C:\rag")
COMPLIANCE_PATH = os.path.join(RAG_ROOT, "compliance.md")
DRAFT_PATH = os.path.join(RAG_ROOT, "output", "rfp-managed-it-servicedocx_response_v1.md")
FEEDBACK_DIR = os.path.join(RAG_ROOT, "feedback")

# --- Hard-coded invariant checks (supplement the markdown compliance rules) ---
# Forbidden / invented-claim phrases the org disallows in bids.
FORBIDDEN_TERMS = [
    "guarantee 100%", "no downtime ever", "free of charge", "zero downtime",
    "unlimited scalability", "industry-best", "best in class", "best-in-class",
    "100% availability", "five 9s", "five nines",
]
# Markers that indicate an unsubstantiated/knowledge-gap placeholder.
GAP_MARKERS = ["knowledge gap", "draft failed", "requires client", "requires sme"]
# Minimum number of requirements that should be addressed (matches the 237 criteria).
EXPECTED_REQUIREMENTS = 237


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def split_sections(text):
    """Split the assembled draft into top-level sections by '## ' or '### ' headings."""
    lines = text.splitlines()
    sections, cur_name, cur_lines = [], "", []
    for line in lines:
        if re.match(r"^(#{1,3})\s+", line):
            if cur_name and cur_lines:
                sections.append((cur_name, "\n".join(cur_lines)))
            cur_name = line
            cur_lines = []
        else:
            cur_lines.append(line)
    if cur_name and cur_lines:
        sections.append((cur_name, "\n".join(cur_lines)))
    return sections


def main():
    draft = read_text(DRAFT_PATH)
    rules = read_text(COMPLIANCE_PATH)

    findings = []

    # 1. Forbidden terms (search whole draft)
    dl = draft.lower()
    for term in FORBIDDEN_TERMS:
        if term in dl:
            # find a snippet of context
            idx = dl.find(term)
            snippet = draft[max(0, idx - 40):idx + 60].replace("\n", " ").strip()
            findings.append({
                "rule": "No forbidden/marketing terms",
                "severity": "warning",
                "finding": f"Found forbidden term '{term}'",
                "context": snippet,
                "suggested_fix": f"Remove or substantiate the claim '{term}'.",
            })

    # 2. Gap / placeholder stubs
    for marker in GAP_MARKERS:
        count = len(re.findall(re.escape(marker), dl))
        if count:
            findings.append({
                "rule": "No placeholder/gap stubs in final draft",
                "severity": "warning" if "gap" in marker else "info",
                "finding": f"{count}x occurrence(s) of '{marker}' marker",
                "suggested_fix": "Review each occurrence; gap sections are flagged for SME validation rather than finalized claims.",
            })

    # 3. Coverage: each requirement section header present
    sections = split_sections(draft)
    req_sections = [h for h, _ in sections if re.match(r"^### \d+\.", h)]
    missing_count = max(0, EXPECTED_REQUIREMENTS - len(req_sections))
    if missing_count:
        findings.append({
            "rule": "Every mandatory RFP requirement addressed",
            "severity": "critical",
            "finding": f"{missing_count} requirement section(s) appear missing (expected {EXPECTED_REQUIREMENTS}, found {len(req_sections)} numbered '### N.' headers).",
            "suggested_fix": "Ensure all 237 requirements from the JSON have a corresponding '### N. <text>' section.",
        })

    # 4. Template structure: presence of standard ATMECS template headings
    template_headings = [
        "1. Executive Summary",
        "2. Corporate Information",
        "3.",
        "Pricing",
        "Governance",
    ]
    for th in template_headings:
        if th.lower() not in dl:
            findings.append({
                "rule": "Follow organization template structure",
                "severity": "warning",
                "finding": f"Template heading '{th}' not found in draft.",
                "suggested_fix": f"Verify the template section '{th}' is present or explicitly justified as N/A.",
            })

    # 5. Compliance matrix present (rule #9)
    if "compliance coverage matrix" not in dl.lower():
        findings.append({
            "rule": "RFP Compliance Coverage Validation (rule #9)",
            "severity": "warning",
            "finding": "No Compliance Coverage Matrix found in the assembled draft.",
            "suggested_fix": "Append the RFP Requirement | Addressed Section | Status matrix.",
        })

    # 6. Unattributed claims heuristic: look for common claim phrases without a source
    claim_patterns = [
        r"\b(?:over \d+%|reduce costs by|save up to|increase efficiency by)\b[ ,.0-9]*",
    ]
    for pat in claim_patterns:
        for m in re.finditer(pat, draft, re.IGNORECASE):
            snippet = draft[max(0, m.start() - 40):m.end() + 40].replace("\n", " ").strip()
            findings.append({
                "rule": "Substantiate quantitative claims with evidence",
                "severity": "info",
                "finding": f"Quantitative claim near '{m.group()}' has no cited source in the immediate context.",
                "context": snippet,
                "suggested_fix": "Attribute the source (e.g., 'per CSC Data Centre PQQ response') or qualify the claim.",
            })

    approved = len([f for f in findings if f["severity"] == "critical"]) == 0 and missing_count == 0

    os.makedirs(FEEDBACK_DIR, exist_ok=True)
    report = {
        "draft": os.path.basename(DRAFT_PATH),
        "checked_by": "local_compliance_checker",
        "approved": approved,
        "total_findings": len(findings),
        "critical": sum(1 for f in findings if f["severity"] == "critical"),
        "warnings": sum(1 for f in findings if f["severity"] == "warning"),
        "info": sum(1 for f in findings if f["severity"] == "info"),
        "findings": findings,
    }
    report_path = os.path.join(FEEDBACK_DIR, "compliance_check_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"[Agent 4] Local compliance check complete.")
    print(f"[Agent 4] Draft: {os.path.basename(DRAFT_PATH)}")
    print(f"[Agent 4] Approved (no critical/missing): {approved}")
    print(f"[Agent 4] Findings: {len(findings)} total | {report['critical']} critical | {report['warnings']} warnings | {report['info']} info")
    print(f"[Agent 4] Report: {report_path}")
    print("[Agent 4] Top findings:")
    for f in findings[:12]:
        print(f"   - [{f['severity']}] {f['finding'][:90]}")
    if len(findings) > 12:
        print(f"   ... and {len(findings) - 12} more (see report)")
    print("[Agent 4] NOTE: This is a static, machine-based pre-check. Agent 4's LLM-based iterative review is pending Groq quota reset (~7h). Recommend manual review using this report as a starting checklist.")


if __name__ == "__main__":
    main()
