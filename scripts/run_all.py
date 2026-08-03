"""Orchestrator — run all 4 agents end-to-end, mirroring the repo design.

Usage:
  py scripts/run_all.py [rfp.pdf]
"""
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(BASE_DIR, "scripts")


def run(script, *args):
    cmd = [sys.executable, os.path.join(SCRIPTS, script)] + list(args)
    print(f"\n=== RUN: {' '.join(os.path.basename(a) for a in [script] + list(args))} ===")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"FAILED: {script} (exit {r.returncode})", file=sys.stderr)
        sys.exit(r.returncode)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rfp = args[0] if args else None

    run("extract_requirements.py", *( [rfp] if rfp else [] ))
    run("knowledge_store.py")
    run("generate_response.py", *( [rfp] if rfp else [] ))
    run("review_compliance.py", "all")

    print("\n[Orchestrator] All 4 agents completed. See C:\\rag\\output\\ for the response.")


if __name__ == "__main__":
    main()
