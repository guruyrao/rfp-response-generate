"""Agent 4 — ComplianceOfficer: review the draft against compliance rules and
reviewer feedback, then regenerate the next version. Iterate until approved.

Usage:
  py scripts/review_compliance.py [draft.md] [--feedback "text"] [--out output/{name}_response_v2.md]
  py scripts/review_compliance.py all        # review the latest draft in output\ and auto-iterate
"""
import json
import os
import re
import sys

from ollama_client import chat_retry

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEW_PROMPT = os.path.join(BASE_DIR, "prompts", "review_compliance.md")
REVISE_PROMPT = os.path.join(BASE_DIR, "prompts", "revise_response.md")
RAG_ROOT = os.environ.get("RAG_ROOT", r"C:\rag")


def load(path, default=""):
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return default


def load_compliance():
    path = os.path.join(RAG_ROOT, "compliance.md")
    rules = load(path)
    if not rules:
        rules = "- All claims must be grounded in the knowledge base (no invented capabilities).\n- No forbidden terms: 'guarantee 100%', 'no downtime ever', 'free of charge'.\n- Every mandatory RFP requirement must be addressed.\n- Responses must follow the organization template format.\n"
    return rules


def next_version(out_dir, base, current):
    """v1 -> v2 -> v3 ... by scanning output dir."""
    m = re.match(r"(.+?)_response_v(\d+)\.md$", current)
    if m:
        prefix = m.group(1)
        n = int(m.group(2)) + 1
    else:
        prefix = os.path.splitext(current)[0]
        n = 2
    return os.path.join(out_dir, f"{prefix}_response_v{n}.md")


def find_latest_draft(out_dir):
    if not os.path.isdir(out_dir):
        return None
    drafts = sorted(
        [os.path.join(out_dir, n) for n in os.listdir(out_dir) if n.endswith(".md")],
        key=os.path.getmtime,
    )
    return drafts[-1] if drafts else None


def main():
    args = sys.argv[1:]
    draft = None
    feedback = ""
    out = None
    i = 0
    while i < len(args):
        if args[i] == "--feedback" and i + 1 < len(args):
            feedback = args[i + 1]
            i += 2
        elif args[i] == "--out" and i + 1 < len(args):
            out = args[i + 1]
            i += 2
        elif args[i].startswith("--"):
            i += 1
        else:
            draft = args[i]
            i += 1

    out_dir = os.path.join(RAG_ROOT, "output")
    if not draft or draft == "all":
        draft = find_latest_draft(out_dir)
    if not draft or not os.path.isfile(draft):
        print("ERROR: draft response not found. Run Agent 3 (generate_response) first.", file=sys.stderr)
        sys.exit(1)

    compliance = load_compliance()
    review_prompt = load(REVIEW_PROMPT)
    revise_prompt = load(REVISE_PROMPT)

    prev_feedback = feedback.strip()
    history_path = os.path.join(RAG_ROOT, "feedback", "feedback_history.jsonl")
    os.makedirs(os.path.dirname(history_path), exist_ok=True)

    current_draft = draft
    iterations = 0
    max_iterations = int(os.environ.get("MAX_REVIEW_ITERATIONS", "5"))

    while iterations < max_iterations:
        iterations += 1
        print(f"[Agent 4] Review iteration {iterations} on: {current_draft}")
        draft_text = load(current_draft)

        user_prompt = (
            review_prompt.replace("{compliance_rules}", compliance)
            .replace("{user_feedback}", prev_feedback or "No reviewer feedback yet.")
            .replace("{draft}", draft_text)
        )
        try:
            review = chat_retry(review_prompt, user_prompt)
        except Exception as e:
            print(f"[Agent 4] Review failed: {e}", file=sys.stderr)
            sys.exit(1)

        approved = bool(review.get("approved"))
        violations = review.get("violations", [])
        missing = review.get("missing", [])
        summary = review.get("summary", "")
        actions = review.get("actions", [])

        # Log to feedback history
        with open(history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "iteration": iterations,
                "draft": os.path.basename(current_draft),
                "approved": approved,
                "violations": violations,
                "missing": missing,
                "summary": summary,
                "actions": actions,
            }, ensure_ascii=False) + "\n")

        print(f"[Agent 4] Approved: {approved}")
        if violations:
            print(f"[Agent 4] Violations: {len(violations)}")
            for v in violations[:10]:
                print(f"   - [{v.get('severity', 'info')}] {v.get('finding', '')}")
        if missing:
            print(f"[Agent 4] Missing requirements: {', '.join(missing[:10])}")
        if summary:
            print(f"[Agent 4] Summary: {summary[:200]}")

        if approved:
            print(f"[Agent 4] COMPLIANT. Final: {current_draft}")
            return

        # Build feedback for revision
        fb_lines = ["Compliance feedback from reviewer:"]
        for v in violations:
            fb_lines.append(f"- {v.get('finding', '')} -> {v.get('suggested_fix', '')}")
        for m in missing:
            fb_lines.append(f"- Missing: {m}")
        for a in actions:
            fb_lines.append(f"- Action: {a}")
        if prev_feedback:
            fb_lines.append(f"- Earlier reviewer feedback: {prev_feedback}")
        new_feedback = "\n".join(fb_lines)

        if not out:
            out = next_version(out_dir, None, current_draft)

        print(f"[Agent 4] Regenerating -> {out}")
        try:
            revise_user = (
                revise_prompt.replace("{previous_draft}", draft_text)
                .replace("{feedback}", new_feedback)
            )
            new_text = chat_retry(revise_prompt, revise_user, format_json=False)
        except Exception as e:
            print(f"[Agent 4] Revision failed: {e}", file=sys.stderr)
            sys.exit(1)

        with open(out, "w", encoding="utf-8") as f:
            f.write(new_text.strip().rstrip() + "\n")

        prev_feedback = new_feedback
        current_draft = out
        out = None  # compute next next_version fresh

    print("[Agent 4] Max iterations reached without approval. Review the latest draft manually.")
    print(f"[Agent 4] Latest draft: {current_draft}")


if __name__ == "__main__":
    main()
