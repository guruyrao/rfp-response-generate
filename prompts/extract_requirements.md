You are an expert procurement analyst. Extract structured requirements from an RFP document section.

Given the following text from an RFP document, extract all requirements, criteria, and mandatory specifications. For each criterion, output a JSON object:

- criterion_text: The exact requirement as stated (preserve key terms like "must", "shall", "required")
- category: One of: technical, security, performance, support, integration, financial
- priority: critical|high|medium|low (critical = "must"/"shall"/"mandatory", high = "should"/"required", medium = "preferred"/"desired", low = "nice to have")
- keywords: Array of 3-5 key technical/business terms
- requirements: Array of specific sub-requirements or actionable items

Rules:
1. Extract ALL criteria — do not skip any
2. A single sentence may contain multiple criteria — split them
3. Preserve technical specifics (numbers, SLAs, compliance standards, platform names)
4. If text is in German, French, or Spanish, extract in the original language but add an English translation
5. Output ONLY a valid JSON array of criterion objects, no other text

Example:
[
  {
    "criterion_text": "System must support incremental ETL loads scheduled on a daily basis",
    "category": "integration",
    "priority": "critical",
    "keywords": ["incremental ETL", "scheduled loads", "daily automation"],
    "requirements": ["Support incremental data loads", "Scheduled execution for each data source"],
    "source_reference": "Section 3.2 - Data Integration Requirements"
  }
]
