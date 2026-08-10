"""
enhance.py — Consulting-grade proposal enhancer.

Reads a raw Markdown RFP response and produces:
  1. build/enhanced.md      Cleaned + restructured Markdown with diagram
                            placeholders and executive-summary section injected.
  2. build/diagrams/*.svg   Pre-rendered Mermaid diagrams (via mmdc).

The generated .md still uses standard Markdown so Pandoc consumes it
downstream. Diagrams are embedded as <img> tags pointing at file:// URIs.

Usage:
    python enhance.py <input.md> <build_dir>
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import subprocess
import shutil
from pathlib import Path

from diagrams import MERMAID, INJECTION_RULES
from infographics import (
    KPI_STRIP, VALUE_CARDS, COMPLIANCE_MATRIX,
    section_cover_svg, callout,
)

# llm_diagrammer is loaded lazily (only when --diagrams=llm) so that
# users of the catalog mode do not need to have the LLM config in place.


MMDC = os.environ.get(
    "MMDC",
    r"C:\Users\grao\AppData\Roaming\npm\mmdc.cmd",
)


# ---------------------------------------------------------------------------
# Mermaid rendering
# ---------------------------------------------------------------------------

def render_mermaid_to_svg(key: str, source: str, out_dir: Path) -> Path:
    """Render a single Mermaid source string to an SVG file. Returns path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    mmd_file = out_dir / f"{key}.mmd"
    svg_file = out_dir / f"{key}.svg"
    mmd_file.write_text(source.strip(), encoding="utf-8")
    print(f"  [mmdc] rendering {key} ...", flush=True)
    try:
        subprocess.run(
            [MMDC, "-i", str(mmd_file), "-o", str(svg_file),
             "-b", "transparent", "-t", "default", "-w", "1400"],
            check=True, capture_output=True, text=True, timeout=120,
        )
    except subprocess.CalledProcessError as e:
        print(f"    !! mmdc failed: {e.stderr}", flush=True)
        return None
    return svg_file if svg_file.exists() else None


def render_all_diagrams(out_dir: Path) -> dict[str, Path]:
    """Render every Mermaid diagram in the library. Returns {key: svg_path}."""
    paths: dict[str, Path] = {}
    for key, (title, source) in MERMAID.items():
        p = render_mermaid_to_svg(key, source, out_dir)
        if p:
            paths[key] = p
    return paths


# ---------------------------------------------------------------------------
# Markdown parsing helpers
# ---------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def parse_headings(md_lines: list[str]) -> list[dict]:
    """Return list of {level, text, line_idx} for each heading."""
    out = []
    in_fence = False
    for i, ln in enumerate(md_lines):
        if ln.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(ln)
        if m:
            out.append({
                "level": len(m.group(1)),
                "text":  m.group(2).strip(),
                "line":  i,
            })
    return out


def heading_matches(text: str, tokens: list[str]) -> bool:
    t = text.lower()
    return all(tok.lower() in t for tok in tokens)


# ---------------------------------------------------------------------------
# Diagram-injection engine
# ---------------------------------------------------------------------------

def build_injection_map(headings: list[dict], svg_paths: dict[str, Path]) -> dict[int, list[str]]:
    """
    Walk INJECTION_RULES top-to-bottom.
    For each rule, find the first still-unused heading whose text matches
    and inject the diagram after it. Returns {heading_line_index: [md_blocks]}.
    """
    used_headings: set[int] = set()
    injections: dict[int, list[str]] = {}

    for rule in INJECTION_RULES:
        key      = rule["key"]
        tokens   = rule["match_all"]
        levels   = set(rule.get("any_of_h", [1, 2, 3, 4]))
        if key not in svg_paths:
            print(f"  [skip] {key}: SVG not available", flush=True)
            continue

        chosen = None
        for h in headings:
            if h["line"] in used_headings:
                continue
            if h["level"] not in levels:
                continue
            if heading_matches(h["text"], tokens):
                chosen = h
                break

        if chosen is None:
            print(f"  [miss] {key}: no matching heading for {tokens}", flush=True)
            continue

        title  = MERMAID[key][0]
        svg    = svg_paths[key].resolve().as_uri()
        block  = (
            f'\n\n<figure class="diagram">\n'
            f'  <img src="{svg}" alt="{title}"/>\n'
            f'  <figcaption>Figure &mdash; {title}</figcaption>\n'
            f'</figure>\n\n'
        )
        injections.setdefault(chosen["line"], []).append(block)
        used_headings.add(chosen["line"])
        print(f"  [inj ] {key:32s} -> L{chosen['line']+1}: {chosen['text'][:60]}", flush=True)

    return injections


# ---------------------------------------------------------------------------
# Executive front-matter (prepended before raw content)
# ---------------------------------------------------------------------------

def build_exec_frontmatter(svg_paths: dict[str, Path], meta: dict) -> str:
    client = meta.get("client", "our client")
    author = meta.get("author", "ATMECS Inc.")
    title  = meta.get("title",  "Managed IT Services")

    def svg_img(key: str, cap: str) -> str:
        if key not in svg_paths:
            return ""
        uri = svg_paths[key].resolve().as_uri()
        return (f'\n<figure class="diagram">\n'
                f'  <img src="{uri}" alt="{cap}"/>\n'
                f'  <figcaption>Figure &mdash; {cap}</figcaption>\n'
                f'</figure>\n')

    parts = []

    # ---- Section 1 cover
    parts.append(section_cover_svg(
        title    = "Executive Summary",
        subtitle = f"Our Value Proposition &amp; Partnership Vision for {client}",
        section_num = "01",
    ))

    parts.append("# Executive Summary\n")
    parts.append(
        f"{author} is pleased to submit this response to the {client} "
        f"Request for Proposal for {title}. We bring 25+ years of enterprise "
        "IT delivery, a proven managed-services operating model, and a "
        "1500-strong engineering base to become "
        f"{client}'s strategic partner for run, optimize and transform.\n"
    )

    parts.append(KPI_STRIP)

    parts.append(f"\n## Our Value Proposition to {client}\n")
    parts.append(
        "We combine outcome-based commercials, an automation-first delivery "
        "model, and 24x7 global coverage to deliver measurable business "
        "impact from day one.\n"
    )
    parts.append(VALUE_CARDS)

    parts.append(svg_img("value_proposition",   f"{author} Value Proposition to {client}"))
    parts.append(svg_img("differentiator_wheel",f"{author} Key Differentiators for {client}"))
    parts.append(svg_img("partnership_model",   f"{author} + {client} Partnership Model"))

    parts.append(callout(
        "highlight",
        f"Why {author} for {client}",
        "A partnership designed to deliver <b>25-35% run-rate savings</b>, "
        "<b>99.9% availability</b>, and a modernization roadmap that puts "
        f"{client} on a scalable cloud-first foundation within 12 months.",
    ))

    # ---- Section 2 cover
    parts.append(section_cover_svg(
        title    = "Company Overview",
        subtitle = f"About {author} &amp; Our Global Delivery Model",
        section_num = "02",
    ))
    parts.append("# Company Overview\n")
    parts.append(
        f"{author} is a technology services company headquartered in Fremont, "
        "California with a global delivery footprint across the Americas, "
        "EMEA and APAC. Our practices span product engineering, cloud &amp; "
        "infrastructure, analytics, automation and next-gen product "
        "development.\n"
    )
    parts.append(svg_img("global_footprint",  f"{author} Global Delivery Footprint"))
    parts.append(svg_img("service_portfolio", f"{author} Service Portfolio"))

    # ---- Section 3 cover
    parts.append(section_cover_svg(
        title    = "Managed IT Services Solution",
        subtitle = "Cloud, DevOps, Security &amp; Support &mdash; Fully Integrated",
        section_num = "03",
    ))
    parts.append("# Managed IT Services Solution\n")
    parts.append(
        f"Our proposed solution covers the full lifecycle of {client}'s IT estate "
        "&mdash; from strategy and cloud migration through DevOps automation, "
        "security operations and end-user support &mdash; delivered under a "
        "single accountable governance model.\n"
    )

    parts.append("\n## Compliance & Certifications at a Glance\n")
    parts.append(COMPLIANCE_MATRIX)

    parts.append("\n---\n\n")
    parts.append(section_cover_svg(
        title    = "Detailed RFP Response",
        subtitle = f"Point-by-Point Response to {client} Requirements",
        section_num = "04",
    ))
    parts.append("# Detailed RFP Response\n")
    parts.append(
        "The following sections provide our detailed response to each "
        f"requirement in the {client} RFP. Diagrams are embedded within the "
        "relevant sections to illustrate frameworks, workflows and "
        "governance models.\n\n"
    )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Content cleanup
# ---------------------------------------------------------------------------

def clean_raw_content(md_lines: list[str]) -> list[str]:
    """
    Trim the broken auto-exported TOC (dot-leader lines) and cover
    boilerplate at the very top of the source document. Keeps everything
    from the first real H1/H2 onward.
    """
    # Find first heading line
    for i, ln in enumerate(md_lines):
        if HEADING_RE.match(ln):
            first_hi = i
            break
    else:
        return md_lines

    # Skip garbage dot-leader lines like "Executive Summary ......... 5"
    cleaned = md_lines[first_hi:]

    # Remove standalone "dot-leader" fragments (dots-only lines, tiny numeric lines)
    filtered = []
    for ln in cleaned:
        s = ln.strip()
        if not s:
            filtered.append(ln); continue
        if re.fullmatch(r"[.\s]{4,}", s):  # a line of just dots
            continue
        if re.fullmatch(r"\d{1,3}\.?", s):  # standalone tiny numbers
            continue
        filtered.append(ln)
    return filtered


# ---------------------------------------------------------------------------
# Alphabetical Index generation
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Match Pandoc's auto_identifiers slug: lowercase, spaces->dashes,
    strip punctuation. Good enough for anchoring index entries."""
    t = text.lower().strip()
    # remove markdown/HTML entities and punctuation except spaces & hyphens
    t = re.sub(r"&[a-z]+;", "", t)
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"\s+", "-", t)
    t = re.sub(r"-+", "-", t).strip("-")
    return t or "section"


# Filter out noise: super-generic repeated titles, tiny fragments, and things
# that are more like paragraph headings than index-worthy topics.
_INDEX_STOP = {
    "proposed solution", "roles and responsibilities", "pricing",
    "technical architecture", "case studies", "delivery model",
    "corporate information", "conclusion", "references",
    "critical assumptions dependencies and exclusions",
}


def build_index_markdown(headings: list[dict]) -> str:
    """
    Return an HTML block containing an alphabetical A-Z index of
    all H1/H2/H3 headings from the enhanced document.
    """
    # Collect uniqueue (text, slug) pairs from H1..H3
    seen: dict[str, str] = {}   # text_lower -> slug (first occurrence)
    for h in headings:
        if h["level"] > 3:
            continue
        text = h["text"].strip()
        # Drop numeric-only or trivially short headings
        if len(text) < 3:
            continue
        # Drop headings that are just numbers or single words like "1." or "Contents"
        if re.fullmatch(r"[\d.\s]+", text):
            continue
        key = text.lower()
        if key in _INDEX_STOP:
            # keep only first occurrence of these generic ones
            if key in seen:
                continue
        if key not in seen:
            seen[key] = slugify(text)

    # Group alphabetically by first letter
    from collections import defaultdict
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key, slug in seen.items():
        # Reconstruct display text from the original (first-seen) heading
        pass  # we'll rebuild by re-scanning
    # Rebuild display map preserving original capitalization
    display: dict[str, str] = {}
    for h in headings:
        if h["level"] > 3:
            continue
        text = h["text"].strip()
        key = text.lower()
        if key in seen and key not in display:
            display[key] = text

    for key, slug in seen.items():
        text = display.get(key, key)
        first = text[0].upper()
        if not first.isalpha():
            first = "#"
        groups[first].append((text, slug))

    # Sort within groups
    for k in groups:
        groups[k].sort(key=lambda t: t[0].lower())

    # Emit HTML
    parts = ['<section class="index-section">',
             '<h1 class="index-title">Index</h1>',
             '<div class="index-intro">Alphabetical listing of topics, '
             'frameworks and services covered in this response.</div>',
             '<div class="index-grid">']

    for letter in sorted(groups.keys(), key=lambda c: (c == "#", c)):
        entries = groups[letter]
        if not entries:
            continue
        parts.append('<div class="index-col">')
        parts.append(f'<div class="index-letter">{letter}</div>')
        parts.append('<ul class="index-list">')
        for text, slug in entries:
            safe = (text.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;"))
            parts.append(f'<li><a href="#{slug}">{safe}</a></li>')
        parts.append('</ul></div>')

    parts.append('</div></section>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Enhance a Markdown RFP with diagrams, exec summary, and index."
    )
    parser.add_argument("input_md",  help="Path to source .md file")
    parser.add_argument("build_dir", help="Output/build directory")
    parser.add_argument("--client", default="our client",     help="Client name")
    parser.add_argument("--author", default="ATMECS Inc.",    help="Author / company")
    parser.add_argument("--title",  default="Managed IT Services",
                        help="Proposal title (used in body copy)")
    parser.add_argument(
        "--diagrams",
        choices=["catalog", "llm", "none"],
        default="catalog",
        help=("Diagram source: "
              "'catalog' = the 19 hard-coded ATMECS diagrams (default, "
              "backward-compatible); "
              "'llm' = ask an LLM to author a diagram per section from your "
              "actual Markdown content; "
              "'none' = do not inject any diagrams."),
    )
    parser.add_argument(
        "--llm-config",
        default="llm-config.json",
        help="Path to the LLM configuration JSON (used when --diagrams=llm).",
    )
    parser.add_argument(
        "--exec-summary",
        choices=["catalog", "none"],
        default="catalog",
        help=("Executive front-matter mode: "
              "'catalog' = include the hard-coded KPI strip / value cards / "
              "compliance grid / callouts (default); "
              "'none' = skip all pre-authored ATMECS marketing content "
              "(recommended when reusing the toolkit for other RFPs)."),
    )
    args = parser.parse_args(argv[1:])

    src_path  = Path(args.input_md)
    build_dir = Path(args.build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    diag_dir = build_dir / "diagrams"

    meta = {"client": args.client, "author": args.author, "title": args.title}

    print(f"==> Enhancing {src_path.name}")
    print(f"    client={meta['client']!r}  author={meta['author']!r}")
    print(f"    diagrams={args.diagrams}  exec_summary={args.exec_summary}")
    md_text = src_path.read_text(encoding="utf-8", errors="replace")
    md_lines = md_text.splitlines()
    print(f"    source: {len(md_lines):,} lines, {len(md_text):,} chars")

    # ---- Catalog SVGs are only needed when we render exec front-matter
    #      figures or when --diagrams=catalog.
    svg_paths: dict[str, Path] = {}
    need_catalog_svgs = (args.diagrams == "catalog"
                         or args.exec_summary == "catalog")
    if need_catalog_svgs:
        print("==> Rendering Mermaid diagrams to SVG (catalog) ...")
        svg_paths = render_all_diagrams(diag_dir)
        print(f"    rendered {len(svg_paths)} / {len(MERMAID)} diagrams")

    print("==> Cleaning raw content (removing dot-leader TOC junk) ...")
    md_lines = clean_raw_content(md_lines)
    print(f"    cleaned: {len(md_lines):,} lines")

    print("==> Locating headings ...")
    headings = parse_headings(md_lines)
    print(f"    found {len(headings)} headings")

    # ---- Build injection map based on the selected diagram mode
    injections: dict[int, list[str]] = {}
    if args.diagrams == "catalog":
        print("==> Building injection map (catalog) ...")
        injections = build_injection_map(headings, svg_paths)
    elif args.diagrams == "llm":
        print("==> Generating diagrams via LLM (one per section) ...")
        try:
            import llm_diagrammer  # local module
        except ImportError as e:
            print(f"    !! Failed to import llm_diagrammer: {e}")
            return 2
        cfg_path = Path(args.llm_config)
        if not cfg_path.is_absolute():
            cfg_path = Path(__file__).parent / cfg_path
        try:
            llm_cfg = llm_diagrammer.load_config(cfg_path)
        except Exception as e:
            print(f"    !! Failed to load LLM config {cfg_path}: {e}")
            return 2
        injections = llm_diagrammer.run_llm_diagrams(
            md_lines, build_dir, llm_cfg, MMDC, verbose=True,
        )
    else:
        print("==> Diagram injection disabled (--diagrams=none)")

    print("==> Assembling enhanced markdown ...")
    out_lines: list[str] = []
    for i, ln in enumerate(md_lines):
        out_lines.append(ln)
        if i in injections:
            for block in injections[i]:
                out_lines.append(block)

    # ---- Executive front-matter (only in catalog mode)
    if args.exec_summary == "catalog":
        exec_front = build_exec_frontmatter(svg_paths, meta)
    else:
        exec_front = ""
        print("==> Executive front-matter disabled (--exec-summary=none)")

    # Build alphabetical index from ALL headings (source + injected exec sections)
    print("==> Building alphabetical Index ...")
    exec_head_lines = exec_front.splitlines()
    all_heads = parse_headings(exec_head_lines) + [
        {**h, "line": h["line"] + len(exec_head_lines)} for h in headings
    ]
    index_cover = section_cover_svg(
        title    = "Index",
        subtitle = "Alphabetical Topic Reference",
        section_num = "A",
    )
    index_block = build_index_markdown(all_heads)
    print(f"    indexed {sum(1 for _ in all_heads if _['level'] <= 3)} entries")

    enhanced_parts: list[str] = []
    if exec_front:
        enhanced_parts.append(exec_front + "\n\n")
    enhanced_parts.append("\n".join(out_lines) + "\n\n")
    enhanced_parts.append(index_cover + "\n\n")
    enhanced_parts.append(index_block + "\n")
    enhanced = "".join(enhanced_parts)

    out_md = build_dir / "enhanced.md"
    out_md.write_text(enhanced, encoding="utf-8")
    print(f"==> Wrote {out_md}  ({len(enhanced):,} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
