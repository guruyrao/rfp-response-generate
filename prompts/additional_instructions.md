# Additional Instructions for Agent 3 – generate_response

## 1. RFP Context Awareness (Mandatory)

When generating content using `sample_rfp_response_v1.md`, the template must not be treated as a static document.

### Instructions

- Analyze the RFP input document and identify:
  - Business objectives
  - Scope of work
  - Technical requirements
  - Staffing requirements
  - Delivery expectations
  - Compliance requirements
  - Industry/domain context

- Every generated section must be contextualized to the specific RFP.

- Avoid generic boilerplate responses where the RFP provides specific requirements.

### Example

For the **Executive Summary**:

❌ Do not generate:

> We are pleased to submit this proposal and have extensive experience delivering digital transformation projects.

✅ Generate:

> Based on the RFP requirement to establish a cloud-native customer platform with DevSecOps automation and managed support services, our proposed solution delivers...

The Executive Summary must explicitly reference the client's stated requirements, objectives, and outcomes.

---

## 2. Knowledge Store Semantic Discovery

Do not rely solely on exact keyword matches.

### Instructions

- Use semantic retrieval and LLM-based matching to identify relevant content from the knowledge store.
- Search using:
  - Similar business concepts
  - Technical synonyms
  - Industry terminology
  - Capability mappings

### Example

RFP asks:

> Staffing Model for Application Support

Knowledge store contains:

> Resource Management Framework

Agent should recognize the relevance and use that content.

---

## 3. Gap Detection – Never Invent Content

If no supporting evidence exists in the knowledge store:

### Instructions

- Do not fabricate experience, staffing numbers, certifications, methodologies, or delivery approaches.
- Mark the section as a knowledge gap.

Use the following format:

```markdown
⚠ KNOWLEDGE GAP IDENTIFIED

The RFP requests information regarding:
<Requirement>

No validated content was found in the knowledge store.

Recommendation:
Provide organization-approved content for inclusion in the knowledge repository.

[HIGHLIGHT THIS BLOCK IN YELLOW]
```

This enables continuous improvement of the knowledge center.

---

## 4. Categorize Content into Two Segments

Every RFP response should be classified into:

### A. General Purpose Sections

Reusable content that is largely common across projects.

Examples:

- Company Overview
- Corporate Information
- Service Offerings
- Certifications
- Security Standards
- Delivery Methodology
- Quality Management
- Governance Framework

Source:

- Populate primarily from knowledge store.
- Minimal RFP customization required.

### B. Project-Specific Sections

Content that must align with the requirements of the current RFP.

Examples:

- Executive Summary
- Proposed Solution
- Staffing Plan
- Transition Approach
- Delivery Model
- Innovation Strategy
- Technical Architecture
- Project Timeline
- Risk Management
- Service Levels

Source:

- Derived using:
  - RFP requirements
  - Retrieved knowledge assets
  - Semantic matching

Must be tailored to the specific client opportunity.

---

## 5. Dynamic Section Discovery

The template is not the complete source of truth.

### Instructions

If the RFP contains requirements not represented in the template:

- Automatically identify missing sections.
- Create additional response sections.
- Clearly indicate that the section was added because it was required by the RFP.

Example:

RFP requests:

- RPA Services
- Intelligent Automation
- AI Governance

Template does not contain these sections.

Agent should create:

```markdown
## Robotic Process Automation (RPA)

<RFP-aligned content>

## Intelligent Automation Framework

<RFP-aligned content>

## AI Governance and Controls

<RFP-aligned content>
```

Do not omit requirements merely because the template lacks a corresponding section.

---

## 6. Staffing Identification and Workforce Planning

When staffing requirements are mentioned or implied:

### Instructions

- Extract staffing requirements from the RFP.
- Identify roles required for delivery.
- Generate:
  - Resource structure
  - Reporting hierarchy
  - Role responsibilities
  - Team composition
  - Skills matrix

Even if specific staffing content is absent from the knowledge store.

The agent may infer reasonable role structures from the stated scope of work but must clearly distinguish:

```markdown
Validated Knowledge Store Content
```

from

```markdown
Recommended Staffing Structure (Generated Based on RFP Scope)
```

If exact staffing information is unavailable:

Highlight as:

```markdown
[REQUIRES CLIENT / SME VALIDATION]
```

---

## 7. Case Study Adaptation Framework

Do not perform direct copy/paste of case studies.

### Instructions

- Select the most relevant case studies using semantic similarity.
- Align outcomes, delivery approach, capabilities, and business value to the RFP.

### Technology Normalization

If:

Knowledge Store:

```text
Azure DevOps Pipeline Implementation
```

RFP:

```text
AWS CodePipeline
```

Agent should:

- Reuse delivery methodology
- Reuse automation approach
- Reuse business outcomes

while adapting wording to AWS requirements.

The case study should focus on:

- Delivery capability
- Automation experience
- CI/CD expertise
- Business outcomes

rather than platform-specific wording alone.

Add:

```markdown
Adapted from related delivery experience.
Platform technology adjusted to align with RFP requirements.
```

when necessary.

---

## 8. Visual and Diagram Generation

Where appropriate, generate visual assets to improve proposal quality.

Examples:

- Solution Architecture
- Delivery Model
- Governance Framework
- Resource Structure
- Transition Model
- Operating Model
- Service Management Framework

Rules:

- Use information retrieved from the knowledge store.
- Ensure visuals support the narrative.
- Do not generate unsupported architecture components.

---

## 9. RFP Compliance Coverage Validation

Before finalizing the response:

Agent must perform a compliance review.

Generate a matrix:

| RFP Requirement | Addressed Section | Status |
|----------------|-------------------|---------|
| Requirement X | Section 4.2 | ✅ Covered |
| Requirement Y | Section 6.1 | ⚠ Partial |
| Requirement Z | Missing | ❌ Gap |

No requirement should remain unassessed.

---

## 10. Research-Based Recommendations for Missing Content

If the RFP requests a capability that is not available in the knowledge store:

### Instructions

- Create a placeholder section.
- Highlight in yellow.
- Provide advisory guidance on what content should be added.

Format:

```markdown
⚠ KNOWLEDGE GAP

RFP Requirement:
Robotic Process Automation

Suggested Content Areas:
- Automation governance
- Bot lifecycle management
- RPA development standards
- Hyperautomation framework
- Monitoring and reporting

Reason:
No validated RPA content exists in the knowledge repository.
```

---

# Recommended Governing Principle

Add the following as a final instruction:

> **The RFP document is the primary source of truth. The template provides structure, and the knowledge store provides evidence. Content generation must be driven by RFP requirements, supported by validated knowledge-store content, and must never invent unsupported claims, experience, staffing details, certifications, or capabilities. Any unsupported requirement must be surfaced as a clearly highlighted gap with recommendations for knowledge-center enrichment.**
