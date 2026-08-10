"""
infographics.py — Hand-crafted SVG infographics.

These are SVGs returned as strings and embedded inline in the HTML.
They complement the Mermaid diagrams for high-impact executive visuals.
"""

# ---- KPI strip for cover / exec page -------------------------------------
KPI_STRIP = """
<div class="kpi-strip">
  <div class="kpi"><div class="kpi-num">25+</div><div class="kpi-lbl">Years of<br/>Excellence</div></div>
  <div class="kpi"><div class="kpi-num">1500+</div><div class="kpi-lbl">IT<br/>Professionals</div></div>
  <div class="kpi"><div class="kpi-num">24x7</div><div class="kpi-lbl">Global<br/>Coverage</div></div>
  <div class="kpi"><div class="kpi-num">30%</div><div class="kpi-lbl">Avg. Cost<br/>Savings</div></div>
  <div class="kpi"><div class="kpi-num">99.9%</div><div class="kpi-lbl">Service<br/>Availability</div></div>
  <div class="kpi"><div class="kpi-num">8 wk</div><div class="kpi-lbl">Rapid<br/>Onboarding</div></div>
</div>
"""

# ---- Value Proposition Cards (used in Executive Summary) ------------------
VALUE_CARDS = """
<div class="card-grid">
  <div class="card card-blue">
    <div class="card-icon">◆</div>
    <div class="card-title">Predictable Cost</div>
    <div class="card-body">Outcome-based commercials with committed 25-35% run-rate optimization over 3 years.</div>
  </div>
  <div class="card card-blue">
    <div class="card-icon">◆</div>
    <div class="card-title">Operational Excellence</div>
    <div class="card-body">ITIL-aligned service management with 24x7 NOC/SOC and SLA-backed response.</div>
  </div>
  <div class="card card-blue">
    <div class="card-icon">◆</div>
    <div class="card-title">Cloud & DevOps</div>
    <div class="card-body">Multi-cloud expertise across AWS, Azure, GCP with automation-first delivery.</div>
  </div>
  <div class="card card-blue">
    <div class="card-icon">◆</div>
    <div class="card-title">Security by Design</div>
    <div class="card-body">ISO 27001, Cyber Essentials Plus, GDPR compliant with continuous SOC monitoring.</div>
  </div>
  <div class="card card-blue">
    <div class="card-icon">◆</div>
    <div class="card-title">Elastic Talent</div>
    <div class="card-body">1500+ certified engineers across cloud, security, data, DevOps and support.</div>
  </div>
  <div class="card card-blue">
    <div class="card-icon">◆</div>
    <div class="card-title">Innovation Partner</div>
    <div class="card-body">Continuous adoption of AI, automation and modernization to keep TUI ahead.</div>
  </div>
</div>
"""

# ---- Section-cover backgrounds (large SVG hero per major section) --------
def section_cover_svg(title: str, subtitle: str, section_num: str) -> str:
    """Return a full-page section-cover HTML block with SVG geometric background."""
    return f"""
<section class="section-cover">
  <svg class="section-cover-bg" viewBox="0 0 800 1000" preserveAspectRatio="none">
    <defs>
      <linearGradient id="g_{section_num}" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#0b3d91"/>
        <stop offset="60%" stop-color="#1259c3"/>
        <stop offset="100%" stop-color="#1e88e5"/>
      </linearGradient>
    </defs>
    <rect width="800" height="1000" fill="url(#g_{section_num})"/>
    <circle cx="720" cy="120" r="200" fill="rgba(255,255,255,0.08)"/>
    <circle cx="80" cy="880" r="260" fill="rgba(255,255,255,0.06)"/>
    <polygon points="0,700 800,500 800,1000 0,1000" fill="rgba(255,255,255,0.05)"/>
  </svg>
  <div class="section-cover-content">
    <div class="section-num">SECTION {section_num}</div>
    <div class="section-title">{title}</div>
    <div class="section-sub">{subtitle}</div>
    <div class="section-rule"></div>
    <div class="section-brand">ATMECS &nbsp;|&nbsp; Managed IT Services Proposal</div>
  </div>
</section>
"""

# ---- Compliance Matrix hero (visual grid) ---------------------------------
COMPLIANCE_MATRIX = """
<div class="compliance-grid">
  <div class="cg-cell"><div class="cg-badge">ISO 27001</div><div class="cg-desc">Information Security Management</div></div>
  <div class="cg-cell"><div class="cg-badge">Cyber Ess+</div><div class="cg-desc">UK Cyber Essentials Plus</div></div>
  <div class="cg-cell"><div class="cg-badge">GDPR</div><div class="cg-desc">EU Data Protection</div></div>
  <div class="cg-cell"><div class="cg-badge">SOC 2</div><div class="cg-desc">Trust Service Criteria</div></div>
  <div class="cg-cell"><div class="cg-badge">ISO 9001</div><div class="cg-desc">Quality Management</div></div>
  <div class="cg-cell"><div class="cg-badge">ITIL v4</div><div class="cg-desc">Service Management Aligned</div></div>
  <div class="cg-cell"><div class="cg-badge">PCI DSS</div><div class="cg-desc">Payment Security Ready</div></div>
  <div class="cg-cell"><div class="cg-badge">NIST CSF</div><div class="cg-desc">Cybersecurity Framework</div></div>
</div>
"""

# ---- Callout box helper ---------------------------------------------------
def callout(kind: str, title: str, body: str) -> str:
    """kind: info | success | warn | highlight"""
    return f'<div class="callout callout-{kind}"><div class="callout-title">{title}</div><div class="callout-body">{body}</div></div>'
