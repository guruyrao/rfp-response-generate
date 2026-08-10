<#
.SYNOPSIS
    Convert a Markdown file to a consulting-grade corporate PDF.

.DESCRIPTION
    Full pipeline: enhance.py (inject diagrams + covers) -> Pandoc (HTML+TOC)
    -> headless Chromium (final PDF with header/footer/page numbers).

    Features:
      * Branded cover page
      * Table of Contents (3-level, dotted leaders, hyperlinked)
      * Section-cover pages between chapters
      * Executive Summary front-matter with KPIs, value cards, callouts
      * 19 Mermaid diagrams injected in relevant sections
      * Compliance badges + infographics
      * Alphabetical Index (2-column A-Z, hyperlinked)
      * Page-numbered header/footer on every page
      * Syntax-highlighted code blocks (Kate theme)
      * Zebra-striped tables with repeating headers

.PARAMETER InputMd      Path to the source .md file (required)
.PARAMETER OutputPdf    Destination .pdf path (defaults to input path with .pdf)
.PARAMETER Title        Document title shown on cover / metadata
.PARAMETER Subtitle     Optional subtitle under the title
.PARAMETER Client       Client name (e.g. "TUI")
.PARAMETER Author       Author / company (e.g. "ATMECS Inc.")
.PARAMETER Version      Document version
.PARAMETER ReleaseDate  Release date shown on cover
.PARAMETER DiagramMode  How diagrams are generated:
                          'catalog' (default) = use the 19 hard-coded
                                                ATMECS diagrams; text
                                                inside them is fixed.
                          'llm'     = ask an LLM to author a diagram
                                      per section from your actual
                                      Markdown content (uses llm-config.json).
                          'none'    = do not inject any diagrams.
.PARAMETER LlmProvider  When -DiagramMode llm: overrides `provider` in
                        llm-config.json. One of:
                          openai | azure | anthropic | bedrock | ollama | github
.PARAMETER LlmModel     When -DiagramMode llm: overrides `model` in
                        llm-config.json (e.g. "Claude-3.5-Sonnet",
                        "gpt-4o-mini", "qwen2.5:32b").
.PARAMETER LlmConfig    Path to a custom LLM config file (defaults to
                        .\llm-config.json alongside this script).
.PARAMETER ExecSummary  Whether to prepend the pre-authored ATMECS
                        executive summary (KPI strip, value cards,
                        compliance grid, callouts):
                          'catalog' (default) = include it (ATMECS/TUI RFP)
                          'none'   = skip it (recommended for other RFPs)
.PARAMETER SkipEnhance  Re-use existing build/enhanced.md (skip Python step)

.EXAMPLE
    # Original ATMECS/TUI RFP (unchanged behavior)
    .\Convert-MdToPdf.ps1 -InputMd "C:\docs\proposal.md" `
        -Title "Managed IT Services" -Client "TUI" `
        -Author "ATMECS Inc." -Version "1.0" `
        -ReleaseDate "08 August, 2026"

.EXAMPLE
    # Any RFP, diagrams authored by an LLM from your Markdown content
    .\Convert-MdToPdf.ps1 -InputMd "C:\docs\any-rfp.md" `
        -Title "Cloud Modernization" -Client "Contoso" `
        -Author "My Co." -Version "1.0" `
        -DiagramMode llm `
        -LlmProvider github -LlmModel "Claude-3.5-Sonnet" `
        -ExecSummary none
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$InputMd,

    [string]$OutputPdf,

    [string]$Title       = "Managed IT Services Proposal",
    [string]$Subtitle    = "Response Document",
    [string]$Client      = "Client",
    [string]$Author      = "ATMECS Inc.",
    [string]$Version     = "1.0",
    [string]$ReleaseDate = (Get-Date -Format "dd MMMM, yyyy"),

    [ValidateSet('catalog','llm','none')]
    [string]$DiagramMode = 'catalog',

    [ValidateSet('openai','azure','anthropic','bedrock','ollama','github')]
    [string]$LlmProvider,

    [string]$LlmModel,
    [string]$LlmConfig,

    [ValidateSet('catalog','none')]
    [string]$ExecSummary = 'catalog',

    [switch]$SkipEnhance
)

$ErrorActionPreference = 'Stop'

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$cssPath    = Join-Path $scriptDir 'corporate.css'
$bodyTpl    = Join-Path $scriptDir 'body-only.html'
$enhancer   = Join-Path $scriptDir 'enhance.py'

if (-not (Test-Path $InputMd))  { throw "Input file not found: $InputMd" }
if (-not $OutputPdf) {
    $OutputPdf = [System.IO.Path]::ChangeExtension($InputMd, '.pdf')
}

$workDir = Join-Path $scriptDir 'build'
if (-not (Test-Path $workDir)) { New-Item -ItemType Directory -Path $workDir | Out-Null }

$enhancedMd = Join-Path $workDir 'enhanced.md'
$bodyHtml   = Join-Path $workDir 'body.html'
$fullHtml   = Join-Path $workDir 'full.html'

# ---- Step 1: Enhance markdown (inject diagrams, exec summary, section covers)
if (-not $SkipEnhance) {
    Write-Host "==> [1/3] Enhancing Markdown (mode: diagrams=$DiagramMode  exec=$ExecSummary) ..." -ForegroundColor Cyan

    # ---- Build the effective LLM config (base config + optional overrides)
    $effectiveLlmConfig = ""
    if ($DiagramMode -eq 'llm') {
        if ($LlmConfig) {
            $baseCfgPath = $LlmConfig
        } else {
            $baseCfgPath = Join-Path $scriptDir 'llm-config.json'
        }
        if (-not (Test-Path $baseCfgPath)) {
            throw "LLM config not found: $baseCfgPath"
        }
        $baseCfg = Get-Content $baseCfgPath -Raw | ConvertFrom-Json
        if ($LlmProvider) { $baseCfg.provider = $LlmProvider }
        if ($LlmModel)    { $baseCfg.model    = $LlmModel }
        $effectiveLlmConfig = Join-Path $workDir 'llm-config.effective.json'
        $baseCfg | ConvertTo-Json -Depth 12 | Set-Content -Path $effectiveLlmConfig -Encoding UTF8
        Write-Host "    LLM provider: $($baseCfg.provider)   model: $($baseCfg.model)" -ForegroundColor DarkGray
    }

    Push-Location $scriptDir
    try {
        $enhanceArgs = @(
            'enhance.py', $InputMd, $workDir,
            '--client',       $Client,
            '--author',       $Author,
            '--title',        $Title,
            '--diagrams',     $DiagramMode,
            '--exec-summary', $ExecSummary
        )
        if ($effectiveLlmConfig) {
            $enhanceArgs += @('--llm-config', $effectiveLlmConfig)
        }
        & python @enhanceArgs
        if ($LASTEXITCODE -ne 0) { throw "enhance.py failed with exit code $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "==> [1/3] Skipping enhancement (using existing enhanced.md)" -ForegroundColor Yellow
}

if (-not (Test-Path $enhancedMd)) { throw "Enhanced Markdown not found: $enhancedMd" }

# ---- Step 2: Convert enhanced Markdown to HTML fragment
Write-Host "==> [2/3] Converting Markdown to HTML fragment ..." -ForegroundColor Cyan

& pandoc `
    --from=gfm+raw_html `
    --to=html5 `
    --toc `
    --toc-depth=3 `
    --syntax-highlighting=kate `
    --template="$bodyTpl" `
    --wrap=preserve `
    --output="$bodyHtml" `
    "$enhancedMd"

if ($LASTEXITCODE -ne 0) { throw "pandoc failed with exit code $LASTEXITCODE" }

# ---- Step 3: Build final HTML + render PDF
Write-Host "==> [3/3] Building final HTML + rendering PDF ..." -ForegroundColor Cyan

Add-Type -AssemblyName System.Web
$cssContent  = Get-Content $cssPath -Raw
$bodyContent = Get-Content $bodyHtml -Raw

function HtmlEnc([string]$s) {
    if ($null -eq $s) { return '' }
    return [System.Web.HttpUtility]::HtmlEncode($s)
}

$eTitle   = HtmlEnc $Title
$eSub     = HtmlEnc $Subtitle
$eClient  = HtmlEnc $Client
$eAuthor  = HtmlEnc $Author
$eVersion = HtmlEnc $Version
$eDate    = HtmlEnc $ReleaseDate

$cover = @'
<section id="cover">
  <div class="brand-bar">__AUTHOR__ &nbsp;|&nbsp; Confidential Proposal</div>
  <div class="doc-type">Response to Request for Proposal</div>
  <div class="doc-title">__TITLE__</div>
  <div class="doc-subtitle">__SUB__</div>
  <div class="meta">
    <div><span class="label">Prepared for</span>__CLIENT__</div>
    <div><span class="label">Prepared by</span>__AUTHOR__</div>
    <div><span class="label">Version</span>__VERSION__</div>
    <div><span class="label">Release Date</span>__DATE__</div>
  </div>
  <div class="confidential">Confidential &ndash; Do not distribute without written consent</div>
</section>
'@
$cover = $cover.Replace('__AUTHOR__',$eAuthor).Replace('__TITLE__',$eTitle).Replace('__SUB__',$eSub).Replace('__CLIENT__',$eClient).Replace('__VERSION__',$eVersion).Replace('__DATE__',$eDate)

$fullDoc = @'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>__TITLE__</title>
<style>
__CSS__
</style>
</head>
<body>
__COVER__
__BODY__
</body>
</html>
'@
$fullDoc = $fullDoc.Replace('__TITLE__',$eTitle).Replace('__CSS__',$cssContent).Replace('__COVER__',$cover).Replace('__BODY__',$bodyContent)

Set-Content -Path $fullHtml -Value $fullDoc -Encoding UTF8

# ---- Generate per-run header/footer with dynamic client/version
$pptrHeaderTpl = Join-Path $scriptDir 'pptr-header.html'
$pptrFooterTpl = Join-Path $scriptDir 'pptr-footer.html'
$pptrHeader    = Join-Path $workDir  'pptr-header.html'
$pptrFooter    = Join-Path $workDir  'pptr-footer.html'

(Get-Content $pptrHeaderTpl -Raw).Replace('__CLIENT__',$eClient).Replace('__TITLE__',$eTitle).Replace('__AUTHOR__',$eAuthor) | Set-Content $pptrHeader -Encoding UTF8
(Get-Content $pptrFooterTpl -Raw).Replace('__CLIENT__',$eClient).Replace('__TITLE__',$eTitle).Replace('__VERSION__',$eVersion).Replace('__AUTHOR__',$eAuthor) | Set-Content $pptrFooter -Encoding UTF8

$html2pdf = Join-Path $scriptDir 'html2pdf.js'

Write-Host "==> Rendering PDF via headless Chromium (Puppeteer) ..." -ForegroundColor Cyan

$prevEAP = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    & node $html2pdf $fullHtml $OutputPdf --header $pptrHeader --footer $pptrFooter 2>&1 | ForEach-Object { Write-Host $_ }
} finally {
    $ErrorActionPreference = $prevEAP
}

if (-not (Test-Path $OutputPdf)) {
    throw "PDF render failed - output not produced"
}

$pdfInfo = Get-Item $OutputPdf
Write-Host ""
Write-Host "==> SUCCESS" -ForegroundColor Green
Write-Host "    Output : $OutputPdf"
Write-Host "    Size   : $([math]::Round($pdfInfo.Length/1KB,1)) KB"
