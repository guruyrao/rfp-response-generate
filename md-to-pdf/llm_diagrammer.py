"""
llm_diagrammer.py
-----------------
Runtime, LLM-driven diagram generator for the MD -> PDF toolkit.

For every H2/H3 section of the source Markdown that is long enough to be
worth diagramming, an LLM is asked to author a Mermaid diagram that
represents ONLY the facts stated in that section (or to return SKIP).

The Mermaid text is then rendered to SVG by `mmdc` and spliced into
`enhanced.md` as an <figure> block, exactly like the catalog-based path.

Providers supported (selectable via llm-config.json):

    openai     OpenAI public API
    azure      Azure OpenAI (deployment-based)
    anthropic  Anthropic public API
    bedrock    AWS Bedrock (requires boto3)
    ollama     Local Ollama server
    github     GitHub Models (OpenAI-compatible; token = GITHUB_TOKEN
               or GitHub Copilot personal access token). Gives access to
               Claude, GPT-4o, Llama 3.1, Phi-3, etc.

The module is dependency-free EXCEPT when provider = "bedrock", where
boto3 is imported on demand.

Anti-hallucination guardrails (all applied before a diagram is accepted):

  1. Response must be either the literal token "SKIP" or a single
     ```mermaid ... ``` fenced block. Anything else is discarded.
  2. Every NUMBER appearing in a diagram node label must appear
     verbatim in the source section text.
  3. Every capitalized STANDALONE proper-noun-looking token (>= 3 chars,
     not a stop word) must appear in the source section text.
  4. mmdc must succeed in rendering the Mermaid. If it fails, ONE retry
     is attempted with the parser error appended to the prompt.

Caching: SHA256(section_text + heading + provider + model + prompt_version)
is used as the cache key; results are stored under build/llm-cache/.
Re-running the pipeline on the same section with the same model is free.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Callable

PROMPT_VERSION = "v1"

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config(path: Path) -> dict:
    """Load the llm-config.json file and return the parsed dict."""
    if not path.exists():
        raise FileNotFoundError(f"LLM config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def resolve_env(config: dict, provider: str, key_name: str) -> str | None:
    """Resolve an environment-variable name from provider config."""
    prov_cfg = config.get("providers", {}).get(provider, {})
    env_name = prov_cfg.get(key_name)
    if not env_name:
        return None
    return os.environ.get(env_name)


# ---------------------------------------------------------------------------
# Section splitting
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def split_into_sections(md_lines: list[str],
                        levels: tuple[int, ...] = (2, 3),
                        min_words: int = 60,
                        max_chars: int = 8000) -> list[dict]:
    """
    Walk the Markdown once, returning a list of sections at the requested
    heading levels. Each section's body extends up to (but not including)
    the next heading of ANY level.

    Sections shorter than `min_words` words are skipped so we do not
    call the LLM for tiny intros. Long sections are truncated to
    `max_chars` characters (LLM sees a truncated view, with a marker).
    """
    heading_positions: list[tuple[int, int, str]] = []
    in_fence = False
    for i, ln in enumerate(md_lines):
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING_RE.match(ln)
        if m:
            heading_positions.append((i, len(m.group(1)), m.group(2).strip()))

    sections: list[dict] = []
    for idx, (line_no, level, text) in enumerate(heading_positions):
        if level not in levels:
            continue

        next_line = len(md_lines)
        if idx + 1 < len(heading_positions):
            next_line = heading_positions[idx + 1][0]

        body_lines = md_lines[line_no + 1:next_line]
        body = "\n".join(body_lines).strip()

        # Drop leading empty/HTML-only lines (e.g. previously injected figures)
        body_stripped = re.sub(r"<figure[\s\S]*?</figure>", "", body).strip()

        word_count = len(re.findall(r"\w+", body_stripped))
        if word_count < min_words:
            continue

        truncated = False
        if len(body_stripped) > max_chars:
            body_stripped = body_stripped[:max_chars]
            truncated = True

        sections.append({
            "heading":       text,
            "level":         level,
            "line":          line_no,
            "body":          body_stripped,
            "truncated":     truncated,
            "word_count":    word_count,
        })

    return sections


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You author diagrams for professional consulting and \
technical documents.

Your job: given ONE section of a document, decide if a diagram would help
the reader, and if so return a Mermaid diagram that faithfully represents
ONLY what the section says.

You MUST return EXACTLY ONE of these two things and NOTHING else:

  (A) the single literal token:  SKIP
  (B) a single fenced Mermaid code block, starting with ```mermaid and
      ending with ```

Rules for option (B):

  1. The diagram must reflect ONLY facts stated in the section. Do NOT
     invent numbers, dates, durations, brand names, tool names, team
     sizes, percentages, or capabilities.
  2. Every node label must be a short phrase drawn from the section text
     (verbatim or trivially rephrased). Node labels must be <= 30 chars.
  3. Use ONE of these Mermaid diagram types (whichever fits best):
        flowchart LR   or   flowchart TB
        sequenceDiagram
        stateDiagram-v2
        timeline
        gantt
  4. Keep the diagram compact: maximum 12 nodes. If the section is very
     complex, pick the single most important structure to show.
  5. Use this exact color palette by adding classDefs at the top:
        classDef primary fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold
        classDef accent  fill:#1259c3,stroke:#0b3d91,color:#fff
        classDef bg      fill:#e0edff,stroke:#1259c3,color:#0b3d91
     Assign :::primary to the root/central node, :::accent to major
     pillars, :::bg to leaves.
  6. Use <br/> for line breaks inside a node.
  7. Do NOT use pipe characters | inside node labels.
  8. Return SKIP if the section is pure prose (no process, structure,
     timeline, roles, phases, workflow, or comparison to depict).
  9. Do NOT include any commentary, explanation, title, or heading
     around the mermaid block. Return the block only.
"""


def build_user_prompt(section: dict) -> str:
    """Build the user message for one section."""
    trunc_note = ""
    if section.get("truncated"):
        trunc_note = "\n\n(Note: the section body above was truncated for length.)"
    return (f"Section heading: {section['heading']}\n\n"
            f"Section text:\n\"\"\"\n{section['body']}\n\"\"\"{trunc_note}\n\n"
            "Return SKIP or a single ```mermaid block. Nothing else.")


def section_hash(section: dict, provider: str, model: str) -> str:
    """Stable cache key for a (section, model) pair."""
    payload = json.dumps({
        "heading":  section["heading"],
        "body":     section["body"],
        "provider": provider,
        "model":    model,
        "prompt":   PROMPT_VERSION,
    }, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


# ---------------------------------------------------------------------------
# Provider dispatch
# ---------------------------------------------------------------------------

def _http_post_json(url: str, body: dict, headers: dict, timeout: int) -> dict:
    """POST JSON, return parsed JSON. Raises on non-2xx."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err_body[:800]}")
    return json.loads(raw)


def _openai_compatible_chat(url: str, api_key: str, model: str,
                            system: str, user: str, extra: dict,
                            timeout: int) -> str:
    body = {
        "model":       model,
        "temperature": extra.get("temperature", 0.0),
        "max_tokens":  extra.get("max_tokens", 1500),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    for k, v in extra.get("extra_headers", {}).items():
        headers[k] = v
    resp = _http_post_json(url, body, headers, timeout)
    return resp["choices"][0]["message"]["content"]


def call_openai(cfg: dict, model: str, system: str, user: str,
                timeout: int, temperature: float, max_tokens: int) -> str:
    api_key = os.environ.get(cfg.get("api_key_env", "OPENAI_API_KEY"))
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")
    base = cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
    return _openai_compatible_chat(
        f"{base}/chat/completions", api_key, model, system, user,
        {"temperature": temperature, "max_tokens": max_tokens},
        timeout,
    )


def call_azure(cfg: dict, model: str, system: str, user: str,
               timeout: int, temperature: float, max_tokens: int) -> str:
    api_key  = os.environ.get(cfg.get("api_key_env", "AZURE_OPENAI_KEY"))
    endpoint = os.environ.get(cfg.get("base_url_env", "AZURE_OPENAI_ENDPOINT"))
    if not api_key or not endpoint:
        raise RuntimeError("AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT must be set")
    api_version = cfg.get("api_version", "2024-06-01")
    deployment  = model or cfg.get("deployment")
    url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    body = {
        "temperature": temperature,
        "max_tokens":  max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    }
    resp = _http_post_json(url, body, {"api-key": api_key}, timeout)
    return resp["choices"][0]["message"]["content"]


def call_anthropic(cfg: dict, model: str, system: str, user: str,
                   timeout: int, temperature: float, max_tokens: int) -> str:
    api_key = os.environ.get(cfg.get("api_key_env", "ANTHROPIC_API_KEY"))
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
    base = cfg.get("base_url", "https://api.anthropic.com/v1").rstrip("/")
    body = {
        "model":       model,
        "system":      system,
        "max_tokens":  max_tokens,
        "temperature": temperature,
        "messages": [
            {"role": "user", "content": user},
        ],
    }
    headers = {
        "x-api-key":         api_key,
        "anthropic-version": cfg.get("api_version", "2023-06-01"),
    }
    resp = _http_post_json(f"{base}/messages", body, headers, timeout)
    return resp["content"][0]["text"]


def call_bedrock(cfg: dict, model: str, system: str, user: str,
                 timeout: int, temperature: float, max_tokens: int) -> str:
    try:
        import boto3  # type: ignore
    except ImportError:
        raise RuntimeError("boto3 is required for the 'bedrock' provider. "
                           "Install it with:  pip install boto3")
    region = cfg.get("region", os.environ.get("AWS_REGION", "us-east-1"))
    client = boto3.client("bedrock-runtime", region_name=region)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens":  max_tokens,
        "temperature": temperature,
        "system":      system,
        "messages": [
            {"role": "user", "content": user},
        ],
    }
    resp = client.invoke_model(
        modelId     = model,
        contentType = "application/json",
        accept      = "application/json",
        body        = json.dumps(body).encode("utf-8"),
    )
    payload = json.loads(resp["body"].read())
    return payload["content"][0]["text"]


def call_ollama(cfg: dict, model: str, system: str, user: str,
                timeout: int, temperature: float, max_tokens: int) -> str:
    base = cfg.get("base_url", "http://localhost:11434").rstrip("/")
    body = {
        "model":   model,
        "stream":  False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    }
    resp = _http_post_json(f"{base}/api/chat", body, {}, timeout)
    return resp["message"]["content"]


def call_github(cfg: dict, model: str, system: str, user: str,
                timeout: int, temperature: float, max_tokens: int) -> str:
    api_key = os.environ.get(cfg.get("api_key_env", "GITHUB_TOKEN"))
    if not api_key:
        raise RuntimeError(
            "GITHUB_TOKEN environment variable not set. "
            "Create a GitHub PAT (or use $env:GITHUB_TOKEN=(gh auth token)) "
            "and grant it the 'models:read' scope."
        )
    base = cfg.get("base_url", "https://models.inference.ai.azure.com").rstrip("/")
    return _openai_compatible_chat(
        f"{base}/chat/completions", api_key, model, system, user,
        {"temperature": temperature, "max_tokens": max_tokens},
        timeout,
    )


PROVIDERS: dict[str, Callable] = {
    "openai":    call_openai,
    "azure":     call_azure,
    "anthropic": call_anthropic,
    "bedrock":   call_bedrock,
    "ollama":    call_ollama,
    "github":    call_github,
}


def call_llm(config: dict, system: str, user: str) -> str:
    """Dispatch to the configured provider and return the raw text response."""
    provider = config["provider"]
    if provider not in PROVIDERS:
        raise RuntimeError(f"Unknown LLM provider: {provider!r}. "
                           f"Choose one of: {sorted(PROVIDERS)}")
    prov_cfg = config.get("providers", {}).get(provider, {})
    model = (config.get("model")
             or prov_cfg.get("default_model")
             or prov_cfg.get("deployment"))
    if not model:
        raise RuntimeError(f"No model specified for provider {provider!r}")
    return PROVIDERS[provider](
        prov_cfg, model, system, user,
        timeout     = int(config.get("timeout_seconds", 90)),
        temperature = float(config.get("temperature", 0.0)),
        max_tokens  = int(config.get("max_tokens_per_call", 1500)),
    )


# ---------------------------------------------------------------------------
# Response parsing + validation
# ---------------------------------------------------------------------------

_MERMAID_FENCE = re.compile(
    r"```(?:mermaid)?\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def parse_response(raw: str) -> tuple[str, str | None]:
    """
    Returns (verdict, mermaid_source):
        verdict = "skip" | "diagram" | "invalid"
        mermaid_source = the Mermaid text, or None
    """
    txt = raw.strip()
    if txt.upper().startswith("SKIP") or txt.upper() == "SKIP":
        return "skip", None
    m = _MERMAID_FENCE.search(txt)
    if not m:
        return "invalid", None
    src = m.group(1).strip()
    if not src:
        return "invalid", None
    return "diagram", src


# ---- Grounding validator ---------------------------------------------------

_STOP_WORDS = {
    "The", "And", "For", "Our", "Their", "With", "From", "This", "That",
    "Into", "Onto", "Over", "Under", "Between", "Among", "Across", "Then",
    "Also", "Not", "Yes", "No",
}


def _extract_labels(mermaid: str) -> list[str]:
    """Extract the human-readable text of every node label."""
    labels: list[str] = []
    # flowchart node forms:  A[Label]  A(Label)  A((Label))  A{Label}  A>Label]
    for pat in (r"\[\[([^\]]+)\]\]",
                r"\(\(([^)]+)\)\)",
                r"\[([^\]]+)\]",
                r"\(([^)]+)\)",
                r"\{([^}]+)\}",
                r">\s*([^\]]+)\]"):
        labels.extend(re.findall(pat, mermaid))
    # sequenceDiagram / stateDiagram: `participant X as "Label"` or `: label`
    labels.extend(re.findall(r'as\s+"([^"]+)"', mermaid))
    labels.extend(re.findall(r"as\s+'([^']+)'", mermaid))
    # timeline / gantt: freeform label text after `title` or on lines with `:`
    labels.extend(re.findall(r"^\s*title\s+(.+)$", mermaid, re.MULTILINE))

    # Clean each label: drop HTML entities and <br/>
    cleaned: list[str] = []
    for lab in labels:
        s = re.sub(r"<br\s*/?>", " ", lab)
        s = re.sub(r"&[a-z]+;", " ", s)
        s = re.sub(r":::[\w-]+", "", s)  # strip class assignments
        s = s.strip()
        if s:
            cleaned.append(s)
    return cleaned


def validate_grounding(mermaid: str, section_text: str
                       ) -> tuple[bool, list[str]]:
    """
    Reject diagrams whose labels contain NUMBERS or PROPER NOUNS
    that do not appear in the source section text.

    Returns (ok, list_of_offending_tokens).
    """
    src_lower = section_text.lower()

    labels = _extract_labels(mermaid)
    offenses: list[str] = []
    for lab in labels:
        # 1. Numbers must appear in source
        for num in re.findall(r"\d+(?:\.\d+)?", lab):
            if num not in section_text:
                offenses.append(f"number {num!r} not in source")
        # 2. Standalone capitalized proper-noun-looking tokens must appear
        for tok in re.findall(r"\b([A-Z][A-Za-z0-9]{2,})\b", lab):
            if tok in _STOP_WORDS:
                continue
            if tok.lower() not in src_lower:
                offenses.append(f"proper-noun {tok!r} not in source")

    return (len(offenses) == 0), offenses


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _render_svg(mmdc: str, mermaid_src: str, key: str, out_dir: Path
                ) -> tuple[Path | None, str]:
    """
    Run `mmdc` on the Mermaid source. Returns (svg_path_or_None, stderr).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    mmd_file = out_dir / f"{key}.mmd"
    svg_file = out_dir / f"{key}.svg"
    mmd_file.write_text(mermaid_src, encoding="utf-8")
    try:
        subprocess.run(
            [mmdc, "-i", str(mmd_file), "-o", str(svg_file),
             "-b", "transparent", "-t", "default", "-w", "1400"],
            check=True, capture_output=True, text=True, timeout=120,
        )
    except subprocess.CalledProcessError as e:
        return None, (e.stderr or e.stdout or "").strip()[:1200]
    except subprocess.TimeoutExpired:
        return None, "mmdc timed out after 120s"
    return (svg_file if svg_file.exists() else None), ""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_llm_diagrams(md_lines: list[str],
                     build_dir: Path,
                     config: dict,
                     mmdc_bin: str,
                     verbose: bool = True) -> dict[int, list[str]]:
    """
    For each qualifying section:
      1. Look up cached diagram; if hit, render from cache.
      2. Otherwise call the LLM.
      3. Parse -> validate -> render. On mmdc failure, retry once.
      4. On success, splice a <figure> HTML block after the heading line.

    Returns {heading_line_index: [figure_html_block, ...]} suitable for
    the same injection loop enhance.py already uses.
    """
    diag_cfg = config.get("diagrams", {})
    cache_dir = build_dir / diag_cfg.get("cache_dir", "llm-cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    svg_dir = build_dir / "diagrams-llm"

    sections = split_into_sections(
        md_lines,
        levels    = tuple(diag_cfg.get("section_levels", [2, 3])),
        min_words = int(diag_cfg.get("min_section_words", 60)),
        max_chars = int(diag_cfg.get("max_section_chars", 8000)),
    )

    max_sections = int(config.get("max_sections", 200))
    if len(sections) > max_sections:
        if verbose:
            print(f"    [warn] capping sections at {max_sections} "
                  f"(found {len(sections)})")
        sections = sections[:max_sections]

    if verbose:
        print(f"    LLM provider = {config['provider']}   "
              f"model = {config.get('model') or '(provider default)'}")
        print(f"    Candidate sections: {len(sections)}")

    provider = config["provider"]
    model = (config.get("model")
             or config.get("providers", {}).get(provider, {}).get("default_model"))

    injections: dict[int, list[str]] = {}
    stats = {"cache_hit": 0, "generated": 0, "skipped": 0,
             "rejected": 0, "failed": 0}

    for idx, sec in enumerate(sections, 1):
        key_hash = section_hash(sec, provider, model or "")
        cache_file = cache_dir / f"{key_hash}.json"

        mermaid_src: str | None = None
        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                verdict = cached.get("verdict")
                mermaid_src = cached.get("mermaid")
                if verdict == "skip":
                    stats["cache_hit"] += 1
                    if verbose:
                        print(f"    [{idx:>3}/{len(sections)}] cache SKIP  "
                              f"L{sec['line']+1:>5}: {sec['heading'][:60]}")
                    continue
                if verdict == "diagram" and mermaid_src:
                    stats["cache_hit"] += 1
                    if verbose:
                        print(f"    [{idx:>3}/{len(sections)}] cache HIT   "
                              f"L{sec['line']+1:>5}: {sec['heading'][:60]}")
            except Exception:
                mermaid_src = None  # fall through to fresh call

        if mermaid_src is None and (not cache_file.exists()):
            # ---- Call LLM
            system = _SYSTEM_PROMPT
            user = build_user_prompt(sec)
            try:
                raw = call_llm(config, system, user)
            except Exception as e:
                stats["failed"] += 1
                if verbose:
                    print(f"    [{idx:>3}/{len(sections)}] LLM ERROR   "
                          f"{sec['heading'][:50]}  ->  {e}")
                continue

            verdict, mermaid_src = parse_response(raw)
            if verdict == "invalid":
                stats["failed"] += 1
                if verbose:
                    print(f"    [{idx:>3}/{len(sections)}] BAD FORMAT  "
                          f"{sec['heading'][:50]}")
                # cache the failure so we don't retry
                cache_file.write_text(json.dumps({
                    "verdict": "invalid", "heading": sec["heading"],
                }, indent=2), encoding="utf-8")
                continue
            if verdict == "skip":
                stats["skipped"] += 1
                cache_file.write_text(json.dumps({
                    "verdict": "skip", "heading": sec["heading"],
                }, indent=2), encoding="utf-8")
                if verbose:
                    print(f"    [{idx:>3}/{len(sections)}] LLM SKIP    "
                          f"L{sec['line']+1:>5}: {sec['heading'][:60]}")
                continue

            # ---- Grounding check
            ok, offenses = validate_grounding(mermaid_src, sec["body"])
            if not ok:
                stats["rejected"] += 1
                if verbose:
                    print(f"    [{idx:>3}/{len(sections)}] REJECTED    "
                          f"{sec['heading'][:50]}   {offenses[:3]}")
                cache_file.write_text(json.dumps({
                    "verdict":   "rejected",
                    "heading":   sec["heading"],
                    "offenses":  offenses,
                    "mermaid":   mermaid_src,
                }, indent=2), encoding="utf-8")
                continue

        # ---- Render via mmdc (with 1-shot retry on syntax error)
        svg_path, err = _render_svg(mmdc_bin, mermaid_src, key_hash, svg_dir)
        if svg_path is None and err and not cache_file.exists():
            # retry once with error appended
            if verbose:
                print(f"    [{idx:>3}/{len(sections)}] mmdc retry ({err[:80]}...)")
            retry_user = (build_user_prompt(sec)
                          + f"\n\nYour previous response produced this Mermaid "
                            f"parser error:\n{err}\nPlease correct it and "
                            "return a valid ```mermaid block only.")
            try:
                raw2 = call_llm(config, _SYSTEM_PROMPT, retry_user)
                v2, m2 = parse_response(raw2)
                if v2 == "diagram" and m2:
                    ok2, off2 = validate_grounding(m2, sec["body"])
                    if ok2:
                        mermaid_src = m2
                        svg_path, err = _render_svg(mmdc_bin, mermaid_src,
                                                    key_hash, svg_dir)
            except Exception:
                pass

        if svg_path is None:
            stats["failed"] += 1
            if verbose:
                print(f"    [{idx:>3}/{len(sections)}] RENDER FAIL {sec['heading'][:50]}")
            continue

        # ---- Success -> cache + queue injection
        cache_file.write_text(json.dumps({
            "verdict":   "diagram",
            "heading":   sec["heading"],
            "mermaid":   mermaid_src,
            "svg_file":  svg_path.name,
        }, indent=2), encoding="utf-8")

        title = sec["heading"].replace("&", "&amp;")
        uri = svg_path.resolve().as_uri()
        block = (
            f'\n\n<figure class="diagram">\n'
            f'  <img src="{uri}" alt="{title}"/>\n'
            f'  <figcaption>Figure &mdash; {title}</figcaption>\n'
            f'</figure>\n\n'
        )
        injections.setdefault(sec["line"], []).append(block)
        stats["generated"] += 1
        if verbose:
            print(f"    [{idx:>3}/{len(sections)}] OK          "
                  f"L{sec['line']+1:>5}: {sec['heading'][:60]}")

    if verbose:
        print(f"    LLM diagram summary: "
              f"generated={stats['generated']}  "
              f"cache_hit={stats['cache_hit']}  "
              f"skipped={stats['skipped']}  "
              f"rejected={stats['rejected']}  "
              f"failed={stats['failed']}")
    return injections
