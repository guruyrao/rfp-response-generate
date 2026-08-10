# Markdown → Consulting-Grade PDF Toolkit

A reusable pipeline that turns any large Markdown file into a professionally
formatted, executive-ready PDF suitable for RFP responses, proposals, and
technical whitepapers.

## What you get

- Branded **cover page** with client / version / date
- Auto-generated **Table of Contents** (3-level, hyperlinked)
- **Section cover pages** between chapters (blue gradient with SVG geometry)
- **Executive front-matter** injected before your content:
  - KPI strip (25+ Years, 1500+ pros, 24×7, 30% savings, 99.9% SLA, 8-week onboarding)
  - 6-card value proposition grid
  - 3 pre-built exec Mermaid diagrams (value proposition, differentiator wheel, partnership model)
  - Highlight callout box
  - Compliance badges grid (ISO 27001, Cyber Ess+, GDPR, SOC 2 …)
- **19 Mermaid diagrams** auto-injected at keyword-matched headings
- **Alphabetical Index** at the end (2-column A-Z, hyperlinked)
- Every page has header + footer + **Page X of Y**
- Zebra-striped tables with repeating headers on page breaks
- Kate-themed syntax highlighting for code blocks
- Callouts (info / success / warn / highlight)

## Prerequisites (one-time setup)

Already installed on this machine — verify with the commands below.
If you're setting up a new machine, run these:

```powershell
# 1. Node.js 18+   (check: node --version)
winget install --id OpenJS.NodeJS

# 2. Python 3.9+   (check: python --version)
winget install --id Python.Python.3.12

# 3. Pandoc 3.0+   (check: pandoc --version)
winget install --id JohnMacFarlane.Pandoc

# 4. Mermaid CLI (renders diagrams; ships its own Chromium)
npm install -g @mermaid-js/mermaid-cli
```

**No wkhtmltopdf, no MiKTeX** — the Chromium that ships with `mermaid-cli`
is reused for the final PDF render.

## Usage

### Quick one-liner

```powershell
cd d:\Agantic-Platfom-MCP\work-dir\md-to-pdf
.\Convert-MdToPdf.ps1 -InputMd "C:\path\to\your.md"
```

### With full metadata (recommended)

```powershell
.\Convert-MdToPdf.ps1 `
    -InputMd     "C:\path\to\proposal.md" `
    -OutputPdf   "C:\path\to\proposal.pdf" `
    -Title       "Managed IT Services" `
    -Subtitle    "Response Document" `
    -Client      "Contoso Corp" `
    -Author      "ATMECS Inc." `
    -Version     "1.0" `
    -ReleaseDate "08 August, 2026"
```

### Re-render fast (skip diagram rendering)

If you only tweaked the CSS or cover metadata and want to re-render without
re-running the Python enhancement step:

```powershell
.\Convert-MdToPdf.ps1 -InputMd "C:\path\to\your.md" -SkipEnhance
```

## Pipeline

```
input.md
    │
    ▼
enhance.py   ◄──  diagrams.py     (19 Mermaid definitions)
    │        ◄──  infographics.py (KPI strip, cards, callouts, section covers)
    │        ◄──  mermaid-cli     (renders Mermaid → SVG)
    ▼
build/enhanced.md      + build/diagrams/*.svg
    │
    ▼
Pandoc      ──►  build/body.html   (TOC + syntax highlight)
    │
    ▼
PowerShell wraps body with cover + corporate.css
    │
    ▼
build/full.html
    │
    ▼
html2pdf.js  ◄──  Chromium (from ~/.cache/puppeteer/)
    │        ◄──  pptr-header.html / pptr-footer.html
    ▼
   final.pdf
```

## Files in this toolkit

| File | Purpose | Edit for |
|---|---|---|
| [Convert-MdToPdf.ps1](Convert-MdToPdf.ps1) | Orchestrator (call this) | Default metadata |
| [enhance.py](enhance.py) | Injects diagrams + exec front-matter + index | Front-matter copy |
| [diagrams.py](diagrams.py) | 19 Mermaid diagrams + injection rules | Add / edit diagrams |
| [infographics.py](infographics.py) | KPI strip, value cards, compliance grid, callouts | KPI numbers, compliance list |
| [llm_diagrammer.py](llm_diagrammer.py) | LLM-driven diagram generator (6 providers) | Provider dispatch, guardrails |
| [llm-config.json](llm-config.json) | LLM provider + guardrail configuration | Provider, model, thresholds |
| [corporate.css](corporate.css) | ~600 lines of styling | Colors, fonts, spacing |
| [body-only.html](body-only.html) | Pandoc HTML template (TOC + body) | Rarely |
| [html2pdf.js](html2pdf.js) | Chromium PDF renderer | Rarely |
| [pptr-header.html](pptr-header.html) | Puppeteer page-header template | Header layout |
| [pptr-footer.html](pptr-footer.html) | Puppeteer page-footer template | Footer layout |
| build/ | Intermediate artifacts (safe to delete) | — |

## Customization guide

### Change brand color

Search-and-replace `#0b3d91` in [corporate.css](corporate.css) with your hex.
The two accent shades `#1259c3` and `#e0edff` should also be adjusted to
stay in the same family. Also update the header/footer templates.

### Change KPI numbers

Edit `KPI_STRIP` in [infographics.py](infographics.py).

### Add or remove a diagram

1. Add a new entry to the `MERMAID` dict in [diagrams.py](diagrams.py):
   ```python
   "my_diagram": ("My Diagram Caption", """
   flowchart LR
       A --> B --> C
   """),
   ```
2. Add an injection rule in the same file:
   ```python
   {"key": "my_diagram", "match_all": ["some", "keywords"], "any_of_h": [2, 3]},
   ```
   The enhancer will inject the SVG after the first heading whose text
   contains all listed keywords.

### Change compliance badges

Edit `COMPLIANCE_MATRIX` in [infographics.py](infographics.py).

### Change page size / margins

- Page size: edit `@page { size: A4 }` in [corporate.css](corporate.css)
- Margins: edit the `margin` object in [html2pdf.js](html2pdf.js) and the
  `@page { margin: ... }` rule in the CSS

### Change syntax-highlighting theme

Edit `--syntax-highlighting=kate` in [Convert-MdToPdf.ps1](Convert-MdToPdf.ps1).
Pandoc built-in themes: `kate`, `pygments`, `tango`, `espresso`, `zenburn`,
`haddock`, `breezedark`, `monochrome`.

### Change TOC depth

Edit `--toc-depth=3` in [Convert-MdToPdf.ps1](Convert-MdToPdf.ps1) (values 1–6).

## Troubleshooting

| Problem | Fix |
|---|---|
| `pandoc: not recognized` | Restart your terminal after installing Pandoc (PATH refresh) |
| `mmdc: not recognized` | Run `npm install -g @mermaid-js/mermaid-cli` |
| `Chromium not found` | Set `$env:CHROME_PATH = "C:\path\to\chrome.exe"` or reinstall mermaid-cli |
| PDF is locked / can't overwrite | Close the previously-opened PDF in Acrobat/Edge |
| Mermaid diagram fails to render | Avoid `|` and unescaped HTML entities inside `[...]` labels; use `-` or `&middot;` alternatives |
| No diagram injected | Check `enhance.py` output — `[miss]` lines mean no heading matched the rule keywords |

## Reusability across projects

The whole toolkit is self-contained in this folder. To use it in another
Markdown project, just call the script with a different `-InputMd` path.
No changes to the toolkit are needed unless you want a different brand look.

If you copy the folder somewhere else, only these two things need to be
present on the machine:

1. **Node global mermaid-cli** (`npm install -g @mermaid-js/mermaid-cli`)
2. **Pandoc** on PATH

Everything else (Chromium, puppeteer-core) is discovered automatically.

---

## Diagram Modes: catalog vs LLM vs none

Diagrams can be generated three different ways. Pick per-run with `-DiagramMode`.

| Mode | What it does | When to use |
|---|---|---|
| `catalog` (default) | Uses the 19 hard-coded ATMECS diagrams in [diagrams.py](diagrams.py). Content is FIXED regardless of your Markdown. | The original ATMECS/TUI RFP where those diagrams were designed for. |
| `llm` | Asks a configurable LLM to author a Mermaid diagram for each H2/H3 section, based on the actual text of that section. | Any other document / any other client — diagrams reflect YOUR content. |
| `none` | Injects no diagrams at all. | Reports where you want only prose, tables, and code. |

The executive front-matter (KPI strip, value cards, ATMECS callouts, compliance
grid) is controlled separately with `-ExecSummary`:

| `-ExecSummary` | Effect |
|---|---|
| `catalog` (default) | Prepends the hard-coded ATMECS exec block. |
| `none` | Skips it entirely. Only your Markdown + cover + TOC + index. |

For a generic RFP for a non-ATMECS client, use `-DiagramMode llm -ExecSummary none`.

### LLM Mode: how it works

For every H2/H3 section that has at least 60 words:

1. The section body is sent to the configured LLM with a strict prompt.
2. The LLM returns either the literal token `SKIP` or a single ` ```mermaid ` block.
3. Response is validated:
   - Must be `SKIP` or a valid Mermaid fenced block.
   - Every **number** and every **capitalized proper-noun-looking token** in the diagram must appear in the source section text. Otherwise the diagram is **rejected** as hallucinated.
4. The Mermaid is rendered to SVG via `mmdc`. If `mmdc` reports a syntax error, ONE retry is attempted with the error appended to the prompt.
5. On success, an `<figure>` block is spliced into `enhanced.md` right after the section heading.
6. The result is **cached** by `SHA256(section_text + provider + model + prompt_version)`. Re-running the pipeline on the same document costs nothing.

Cache location: `build/llm-cache/*.json`. Delete individual files to regenerate a specific diagram.

### Supported LLM providers

All are configured in [llm-config.json](llm-config.json). Switch by editing `provider` in the file OR by passing `-LlmProvider` at the command line.

| `-LlmProvider` | Endpoint | Auth (env var) | Example model |
|---|---|---|---|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `azure` | your Azure OpenAI resource | `AZURE_OPENAI_KEY` + `AZURE_OPENAI_ENDPOINT` | your deployment name |
| `anthropic` | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` |
| `bedrock` | AWS Bedrock (requires `pip install boto3`) | standard AWS creds | `anthropic.claude-3-5-sonnet-20241022-v2:0` |
| `ollama` | `http://localhost:11434` (local) | — | `qwen2.5:32b`, `llama3.1:70b` |
| `github` | `https://models.inference.ai.azure.com` | `GITHUB_TOKEN` (PAT with `models:read`) | `Claude-3.5-Sonnet`, `gpt-4o-mini`, `Meta-Llama-3.1-70B-Instruct` |

The `github` provider gives you Claude, GPT-4o, and Llama through a single OpenAI-compatible endpoint using a GitHub personal access token. This is the recommended path for GitHub Copilot users who want to use Claude for diagram generation.

### LLM mode quick starts

**Using GitHub Copilot / GitHub Models with Claude:**

```powershell
# 1. Set your GitHub token once per shell (or add to your PowerShell profile)
$env:GITHUB_TOKEN = "ghp_your_token_with_models_read_scope"

# 2. Run the pipeline with LLM diagrams
.\Convert-MdToPdf.ps1 `
    -InputMd  "C:\docs\any-rfp.md" `
    -Title    "Cloud Modernization" `
    -Client   "Contoso" `
    -Author   "My Company" `
    -Version  "1.0" `
    -DiagramMode  llm `
    -LlmProvider  github `
    -LlmModel     "Claude-3.5-Sonnet" `
    -ExecSummary  none
```

**Using OpenAI directly:**

```powershell
$env:OPENAI_API_KEY = "sk-..."
.\Convert-MdToPdf.ps1 -InputMd "C:\docs\proposal.md" `
    -DiagramMode llm -LlmProvider openai -LlmModel gpt-4o-mini `
    -ExecSummary none
```

**Using Anthropic Claude directly:**

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
.\Convert-MdToPdf.ps1 -InputMd "C:\docs\proposal.md" `
    -DiagramMode llm -LlmProvider anthropic `
    -LlmModel "claude-3-5-sonnet-latest" -ExecSummary none
```

**Using AWS Bedrock (Claude):**

```powershell
pip install boto3         # once
# Configure AWS creds (aws configure, env vars, or IAM role)
.\Convert-MdToPdf.ps1 -InputMd "C:\docs\proposal.md" `
    -DiagramMode llm -LlmProvider bedrock `
    -LlmModel "anthropic.claude-3-5-sonnet-20241022-v2:0" -ExecSummary none
```

**Fully offline (local Ollama):**

```powershell
# Once: install and pull a model that can write Mermaid well
winget install Ollama.Ollama
ollama pull qwen2.5:32b

.\Convert-MdToPdf.ps1 -InputMd "C:\docs\proposal.md" `
    -DiagramMode llm -LlmProvider ollama -LlmModel "qwen2.5:32b" `
    -ExecSummary none
```

### LLM anti-hallucination guarantees

The generated diagrams are validated BEFORE they are placed into the PDF:

- **Numbers in labels** (e.g. `12 weeks`, `99.9%`, `3 phases`) must appear in the source section text. If the LLM invents `24 weeks` when your text said `12`, the diagram is discarded.
- **Proper-noun tokens** in labels (e.g. `Kubernetes`, `Contoso`, `Kafka`) must appear in the source section. Prevents brand-name leakage from prior conversations.
- **Mermaid syntax errors** trigger ONE automatic retry with the parser error passed back to the model.
- **SKIP responses** are cached so prose-only sections aren't re-queried.

The console log labels each result: `OK`, `LLM SKIP`, `cache HIT`, `REJECTED`, `BAD FORMAT`, `RENDER FAIL`, `LLM ERROR`.

### Configuring LLM behavior

Edit [llm-config.json](llm-config.json) to change:

- `provider`, `model` — default provider and model
- `temperature`, `max_tokens_per_call`, `timeout_seconds`
- `max_sections` — safety cap on sections diagrammed per run
- `providers.<name>` — per-provider endpoints, auth env vars, candidate models
- `diagrams.section_levels` — which heading levels get diagrams (default H2 + H3)
- `diagrams.min_section_words` — skip sections smaller than this
- `diagrams.max_section_chars` — truncate very long sections before sending

### Cost estimate

For a 600 KB RFP (~80 candidate sections) with `gpt-4o-mini`: **~$0.10–0.40 per full run**. First run bills all sections; subsequent runs are cached and free unless you change the section text.

For local Ollama on a 24 GB GPU: **free**, ~5–10 minutes total.

