"""
diagrams.py — Library of Mermaid diagrams for the RFP proposal.

Each entry maps a diagram key to (title, mermaid_source).
The enhancer will render these to SVG via mmdc and inject them
after headings whose text matches the section_map keywords.
"""

# ---------------------------------------------------------------------------
# Mermaid diagrams
# ---------------------------------------------------------------------------

MERMAID = {

    # ================= EXECUTIVE SUMMARY =================
    "value_proposition": ("ATMECS Value Proposition to TUI", """
flowchart LR
    classDef core fill:#0b3d91,stroke:#0b3d91,color:#fff,stroke-width:2px,font-weight:bold
    classDef pillar fill:#e0edff,stroke:#1259c3,color:#0b3d91,stroke-width:2px
    C((ATMECS<br/>Managed<br/>IT Services)):::core
    P1[Cost<br/>Optimization<br/>25-35%]:::pillar
    P2[24x7<br/>Global<br/>Support]:::pillar
    P3[Cloud &<br/>DevOps<br/>Excellence]:::pillar
    P4[Security &<br/>Compliance<br/>ISO / Cyber Ess+]:::pillar
    P5[Talent &<br/>Scale<br/>1500+ Experts]:::pillar
    P6[Continuous<br/>Innovation<br/>AI / Automation]:::pillar
    P1 --- C
    P2 --- C
    P3 --- C
    P4 --- C
    P5 --- C
    P6 --- C
"""),

    "differentiator_wheel": ("ATMECS Key Differentiators", """
flowchart TB
    classDef diff fill:#1259c3,stroke:#0b3d91,color:#fff,stroke-width:1px
    classDef center fill:#0b3d91,stroke:#0b3d91,color:#fff,stroke-width:2px,font-weight:bold
    T((TUI<br/>Success)):::center
    D1[Domain Depth<br/>Travel &<br/>Hospitality]:::diff
    D2[Outcome-Based<br/>Delivery Model]:::diff
    D3[Global 24x7<br/>NOC / SOC]:::diff
    D4[Automation-First<br/>Approach]:::diff
    D5[Rapid Onboarding<br/>8-week Transition]:::diff
    D6[Flexible<br/>Commercials]:::diff
    D7[Executive<br/>Governance]:::diff
    D8[Innovation<br/>Partnership]:::diff
    D1 --> T
    D2 --> T
    D3 --> T
    D4 --> T
    D5 --> T
    D6 --> T
    D7 --> T
    D8 --> T
"""),

    "partnership_model": ("ATMECS + TUI Partnership Model", """
flowchart LR
    classDef tui fill:#c9deff,stroke:#0b3d91,color:#0b3d91,stroke-width:2px
    classDef atmecs fill:#0b3d91,stroke:#0b3d91,color:#fff,stroke-width:2px
    classDef shared fill:#fef3c7,stroke:#b45309,color:#78350f,stroke-width:2px
    subgraph TUI[" TUI "]
        T1[Business<br/>Outcomes]:::tui
        T2[Strategic<br/>Direction]:::tui
    end
    subgraph SHARED[" Joint Governance "]
        S1[Steering<br/>Committee]:::shared
        S2[SLAs & KPIs]:::shared
        S3[Innovation<br/>Roadmap]:::shared
    end
    subgraph ATMECS[" ATMECS "]
        A1[Delivery<br/>Execution]:::atmecs
        A2[Talent &<br/>Technology]:::atmecs
    end
    TUI --> SHARED
    SHARED --> ATMECS
    ATMECS -->|Value Delivered| TUI
"""),

    # ================= CLOUD SERVICES =================
    "cloud_services_framework": ("ATMECS Cloud Services Framework", """
flowchart TB
    classDef layer1 fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold
    classDef layer2 fill:#1259c3,stroke:#0b3d91,color:#fff
    classDef layer3 fill:#e0edff,stroke:#1259c3,color:#0b3d91
    classDef found fill:#334155,stroke:#0f172a,color:#fff,font-weight:bold

    L1[Cloud Strategy &amp; Advisory]:::layer1
    L2A[Assessment]:::layer2
    L2B[Migration]:::layer2
    L2C[Modernization]:::layer2
    L2D[Managed Ops]:::layer2
    L3A[Discovery<br/>Planning]:::layer3
    L3B[Lift &amp; Shift<br/>Re-platform<br/>Re-architect]:::layer3
    L3C[Containers<br/>Serverless<br/>Microservices]:::layer3
    L3D[FinOps<br/>SecOps<br/>Observability]:::layer3
    F[Foundation - AWS - Azure - GCP - Hybrid - Multi-Cloud]:::found

    L1 --> L2A --> L3A
    L1 --> L2B --> L3B
    L1 --> L2C --> L3C
    L1 --> L2D --> L3D
    L3A --> F
    L3B --> F
    L3C --> F
    L3D --> F
"""),

    "cloud_migration_lifecycle": ("Cloud Migration Lifecycle", """
flowchart LR
    classDef phase fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold,stroke-width:2px
    classDef act fill:#e0edff,stroke:#1259c3,color:#0b3d91
    classDef out fill:#dcfce7,stroke:#16a34a,color:#14532d

    P1[1. DISCOVER]:::phase
    P2[2. DESIGN]:::phase
    P3[3. BUILD]:::phase
    P4[4. MIGRATE]:::phase
    P5[5. OPERATE]:::phase

    P1 --> P2 --> P3 --> P4 --> P5

    A1[App Inventory<br/>Dependency Map<br/>TCO Model]:::act
    A2[Target Architecture<br/>Landing Zone<br/>Security Baseline]:::act
    A3[IaC / Terraform<br/>CI/CD Pipelines<br/>Automation]:::act
    A4[Waves &amp; Cutover<br/>Data Sync<br/>Validation]:::act
    A5[24x7 Monitoring<br/>FinOps<br/>Continuous Improve]:::act

    P1 --- A1
    P2 --- A2
    P3 --- A3
    P4 --- A4
    P5 --- A5
"""),

    "cloud_operating_model": ("Cloud Operating Model", """
flowchart TB
    classDef gov fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold
    classDef svc fill:#1259c3,stroke:#0b3d91,color:#fff
    classDef ops fill:#e0edff,stroke:#1259c3,color:#0b3d91
    classDef plat fill:#334155,stroke:#0f172a,color:#fff

    G[Cloud Governance &amp; FinOps]:::gov
    S1[Cloud Center<br/>of Excellence]:::svc
    S2[Platform<br/>Engineering]:::svc
    S3[Application<br/>Teams]:::svc
    O1[Standards<br/>Guardrails]:::ops
    O2[Reusable<br/>Blueprints]:::ops
    O3[Consumption<br/>Self-Service]:::ops
    P[Multi-Cloud Platform - AWS - Azure - GCP]:::plat
    G --> S1 --> O1
    G --> S2 --> O2
    G --> S3 --> O3
    O1 --> P
    O2 --> P
    O3 --> P
"""),

    # ================= TRANSFORMATION =================
    "transformation_lifecycle": ("Application Transformation Lifecycle", """
flowchart LR
    classDef step fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold,stroke-width:2px
    classDef desc fill:#e0edff,stroke:#1259c3,color:#0b3d91

    S1[1. DISCOVER]:::step
    S2[2. EVALUATE]:::step
    S3[3. TRANSFORM]:::step
    S4[4. MEASURE]:::step
    S1 --> S2 --> S3 --> S4

    D1["&bull; Portfolio scan<br/>&bull; Business fit<br/>&bull; Tech health"]:::desc
    D2["&bull; 6R strategy<br/>&bull; TCO / ROI<br/>&bull; Risk profile"]:::desc
    D3["&bull; Re-platform<br/>&bull; Refactor<br/>&bull; Rebuild"]:::desc
    D4["&bull; KPIs / SLOs<br/>&bull; Cost savings<br/>&bull; User NPS"]:::desc
    S1 --- D1
    S2 --- D2
    S3 --- D3
    S4 --- D4
"""),

    # ================= DEVOPS =================
    "cicd_pipeline": ("CI/CD Pipeline — Code to Production", """
flowchart LR
    classDef stage fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold,stroke-width:2px
    classDef tool fill:#e0edff,stroke:#1259c3,color:#0b3d91

    C[CODE]:::stage
    B[BUILD]:::stage
    T[TEST]:::stage
    R[RELEASE]:::stage
    D[DEPLOY]:::stage
    O[OPERATE]:::stage
    C --> B --> T --> R --> D --> O
    O -.feedback.-> C

    C1[Git / GitHub<br/>Branch Policy<br/>PR Reviews]:::tool
    B1[Maven / Gradle<br/>npm / Docker<br/>Artifacts]:::tool
    T1[JUnit / Jest<br/>SonarQube<br/>Security Scan]:::tool
    R1[Semantic Ver<br/>Release Notes<br/>Approvals]:::tool
    D1[Terraform<br/>Kubernetes<br/>Blue/Green]:::tool
    O1[Prometheus<br/>ELK / Grafana<br/>PagerDuty]:::tool
    C --- C1
    B --- B1
    T --- T1
    R --- R1
    D --- D1
    O --- O1
"""),

    "devops_toolchain": ("DevOps Toolchain Architecture", """
flowchart TB
    classDef cat fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold
    classDef tool fill:#e0edff,stroke:#1259c3,color:#0b3d91

    C1[Source Control]:::cat --> T1[GitHub<br/>GitLab<br/>Bitbucket]:::tool
    C2[CI / Build]:::cat --> T2[Jenkins<br/>GitHub Actions<br/>Azure DevOps]:::tool
    C3[Artifact Mgmt]:::cat --> T3[Nexus<br/>JFrog Artifactory<br/>ACR / ECR]:::tool
    C4[Quality &amp; Security]:::cat --> T4[SonarQube<br/>Snyk<br/>Checkmarx]:::tool
    C5[IaC / Config]:::cat --> T5[Terraform<br/>Ansible<br/>Helm]:::tool
    C6[Orchestration]:::cat --> T6[Kubernetes<br/>ECS<br/>AKS / GKE / EKS]:::tool
    C7[Observability]:::cat --> T7[Prometheus<br/>Grafana<br/>Datadog / New Relic]:::tool
    C8[Incident Mgmt]:::cat --> T8[PagerDuty<br/>ServiceNow<br/>Jira Service Mgmt]:::tool
"""),

    # ================= GOVERNANCE =================
    "governance_structure": ("Executive & Operational Governance Structure", """
flowchart TB
    classDef exec fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold,stroke-width:2px
    classDef mgmt fill:#1259c3,stroke:#0b3d91,color:#fff,stroke-width:1px
    classDef ops fill:#e0edff,stroke:#1259c3,color:#0b3d91

    ESC[Executive Steering Committee<br/>Quarterly &bull; TUI CIO + ATMECS EVP]:::exec
    SLC[Service Leadership Committee<br/>Monthly &bull; Delivery Heads]:::mgmt
    ORB[Operations Review Board<br/>Weekly &bull; Service Owners]:::mgmt

    T1[Change<br/>Advisory<br/>Board]:::ops
    T2[Incident<br/>Review]:::ops
    T3[Capacity &amp;<br/>Performance]:::ops
    T4[Security &amp;<br/>Compliance]:::ops
    T5[Financial<br/>Governance]:::ops

    ESC --> SLC --> ORB
    ORB --> T1
    ORB --> T2
    ORB --> T3
    ORB --> T4
    ORB --> T5
"""),

    "escalation_matrix": ("Escalation Hierarchy & Response Times", """
flowchart LR
    classDef l1 fill:#dcfce7,stroke:#16a34a,color:#14532d,font-weight:bold
    classDef l2 fill:#fef3c7,stroke:#d97706,color:#78350f,font-weight:bold
    classDef l3 fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,font-weight:bold
    classDef l4 fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold

    L1[Level 1<br/>Service Desk<br/>&lt; 15 min ack]:::l1
    L2[Level 2<br/>Domain Specialist<br/>&lt; 30 min engage]:::l2
    L3[Level 3<br/>Delivery Manager<br/>&lt; 60 min mobilize]:::l3
    L4[Level 4<br/>Executive Sponsor<br/>&lt; 2 hr response]:::l4

    L1 -->|Sev 3-4| L2
    L2 -->|Sev 2| L3
    L3 -->|Sev 1 / P1| L4
"""),

    # ================= SECURITY =================
    "security_layers": ("Defence-in-Depth Security Control Layers", """
flowchart TB
    classDef layer fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold
    classDef ctrl fill:#e0edff,stroke:#1259c3,color:#0b3d91

    L1[Governance, Risk &amp; Compliance]:::layer
    L2[Identity &amp; Access Management]:::layer
    L3[Network &amp; Perimeter Security]:::layer
    L4[Endpoint &amp; Device Security]:::layer
    L5[Application &amp; Data Security]:::layer
    L6[Monitoring, Detection &amp; Response]:::layer

    L1 --> L2 --> L3 --> L4 --> L5 --> L6

    L1 --- C1[ISO 27001<br/>Cyber Ess+<br/>GDPR / DPA]:::ctrl
    L2 --- C2[SSO / MFA<br/>PAM<br/>Zero Trust]:::ctrl
    L3 --- C3[NGFW<br/>WAF / DDoS<br/>Segmentation]:::ctrl
    L4 --- C4[EDR / XDR<br/>MDM<br/>Patch Mgmt]:::ctrl
    L5 --- C5[SAST/DAST<br/>DLP<br/>Encryption]:::ctrl
    L6 --- C6[24x7 SOC<br/>SIEM / SOAR<br/>Threat Intel]:::ctrl
"""),

    "incident_response": ("Cybersecurity Incident Response Workflow", """
flowchart LR
    classDef phase fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold,stroke-width:2px
    classDef act fill:#e0edff,stroke:#1259c3,color:#0b3d91

    P1[1. DETECT]:::phase
    P2[2. TRIAGE]:::phase
    P3[3. CONTAIN]:::phase
    P4[4. ERADICATE]:::phase
    P5[5. RECOVER]:::phase
    P6[6. LEARN]:::phase
    P1 --> P2 --> P3 --> P4 --> P5 --> P6

    A1[SIEM alerts<br/>User reports<br/>Threat intel]:::act
    A2[Severity class<br/>Impact assess<br/>Notify stake]:::act
    A3[Isolate hosts<br/>Block IoCs<br/>Preserve evid]:::act
    A4[Remove threat<br/>Patch / harden<br/>Root cause]:::act
    A5[Restore ops<br/>Validate<br/>Monitor]:::act
    A6[Post-mortem<br/>Update runbooks<br/>Training]:::act
    P1 --- A1
    P2 --- A2
    P3 --- A3
    P4 --- A4
    P5 --- A5
    P6 --- A6
"""),

    # ================= TALENT =================
    "recruitment_funnel": ("Talent Acquisition Funnel", """
flowchart TB
    classDef stage fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold
    classDef metric fill:#e0edff,stroke:#1259c3,color:#0b3d91

    S1[Sourcing<br/>1000+ candidates]:::stage
    S2[Screening &amp; Assessment<br/>~200 pass]:::stage
    S3[Technical &amp; Cultural Interviews<br/>~60 shortlist]:::stage
    S4[Client Panel &amp; Offer<br/>~20 selected]:::stage
    S5[Onboarding &amp; Deployment<br/>~15 productive]:::stage
    S1 --> S2 --> S3 --> S4 --> S5

    M1[Job boards<br/>Referrals<br/>Talent pools]:::metric
    M2[Skills tests<br/>Coding<br/>Comms]:::metric
    M3[Domain + culture<br/>Multi-panel]:::metric
    M4[Client interview<br/>Reference check<br/>BGV]:::metric
    M5[8-week ramp<br/>Buddy program<br/>KPIs]:::metric
    S1 --- M1
    S2 --- M2
    S3 --- M3
    S4 --- M4
    S5 --- M5
"""),

    "onboarding_timeline": ("8-Week Onboarding & Transition Plan", """
gantt
    dateFormat  YYYY-MM-DD
    title       ATMECS-TUI Transition Plan
    axisFormat  W%V
    section Week 1-2 Discovery
    Stakeholder alignment       :done,    d1, 2026-01-06, 7d
    Knowledge capture           :done,    d2, 2026-01-06, 14d
    section Week 3-4 Setup
    Team mobilization           :active,  s1, 2026-01-20, 14d
    Tooling &amp; access             :active,  s2, 2026-01-20, 14d
    section Week 5-6 Shadow
    Shadow existing team        :         sh1, 2026-02-03, 14d
    Reverse KT sessions         :         sh2, 2026-02-03, 14d
    section Week 7-8 Steady State
    Cutover to ATMECS ops       :         co1, 2026-02-17, 7d
    Hypercare &amp; stabilization   :         co2, 2026-02-24, 7d
"""),

    # ================= SLA / REPORTING =================
    "sla_framework": ("SLA & Service Reporting Framework", """
flowchart TB
    classDef cat fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold
    classDef m fill:#e0edff,stroke:#1259c3,color:#0b3d91

    CAT1[Availability]:::cat --> M1[Uptime 99.9%<br/>Incident MTTR<br/>Change success]:::m
    CAT2[Performance]:::cat --> M2[Response time<br/>Throughput<br/>Capacity headroom]:::m
    CAT3[Quality]:::cat --> M3[Defect density<br/>First-call resolve<br/>User satisfaction]:::m
    CAT4[Security]:::cat --> M4[Patch compliance<br/>Vuln closure SLA<br/>Audit findings]:::m
    CAT5[Financial]:::cat --> M5[Cost per unit<br/>Budget variance<br/>Savings realized]:::m
"""),

    # ================= NETWORK / MONITORING =================
    "monitoring_architecture": ("24x7 Proactive Monitoring Architecture", """
flowchart LR
    classDef src fill:#e0edff,stroke:#1259c3,color:#0b3d91
    classDef mid fill:#1259c3,stroke:#0b3d91,color:#fff,font-weight:bold
    classDef out fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold

    S1[Servers<br/>Windows / Linux]:::src
    S2[Network<br/>Routers / Switches]:::src
    S3[Cloud<br/>AWS / Azure / GCP]:::src
    S4[Applications<br/>APM traces]:::src
    S5[Endpoints<br/>Laptops / EUC]:::src

    AGG[Telemetry Ingestion<br/>Metrics &middot; Logs &middot; Traces]:::mid
    S1 --> AGG
    S2 --> AGG
    S3 --> AGG
    S4 --> AGG
    S5 --> AGG

    AGG --> DASH[Unified Dashboards<br/>Grafana / Kibana]:::out
    AGG --> AI[AIOps Correlation<br/>Anomaly Detection]:::out
    AI --> NOC[24x7 NOC / SOC<br/>Incident Response]:::out
    DASH --> NOC
"""),

    # ================= COMPANY OVERVIEW =================
    "global_footprint": ("ATMECS Global Delivery Footprint", """
flowchart LR
    classDef hq fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold
    classDef reg fill:#1259c3,stroke:#0b3d91,color:#fff
    classDef del fill:#e0edff,stroke:#1259c3,color:#0b3d91

    HQ[Headquarters<br/>Fremont, USA]:::hq

    R1[Americas Hub<br/>USA &amp; LATAM]:::reg
    R2[EMEA Hub<br/>UK / Germany]:::reg
    R3[APAC Hub<br/>India / Singapore]:::reg

    D1[Fremont - Austin<br/>New York - Toronto]:::del
    D2[London - Frankfurt<br/>Dublin]:::del
    D3[Hyderabad - Bangalore<br/>Chennai - Singapore]:::del

    HQ --> R1 --> D1
    HQ --> R2 --> D2
    HQ --> R3 --> D3
"""),

    "service_portfolio": ("ATMECS Service Portfolio", """
flowchart TB
    classDef top fill:#0b3d91,stroke:#0b3d91,color:#fff,font-weight:bold
    classDef svc fill:#1259c3,stroke:#0b3d91,color:#fff
    classDef sub fill:#e0edff,stroke:#1259c3,color:#0b3d91

    T[ATMECS Service Portfolio]:::top

    S1[Product Engineering]:::svc
    S2[Cloud &amp; Infrastructure]:::svc
    S3[Enterprise Analytics]:::svc
    S4[Automation &amp; AI]:::svc
    S5[Next-Gen Products]:::svc

    T --> S1 --> P1[Full-stack Dev<br/>SaaS Platforms<br/>Mobile]:::sub
    T --> S2 --> P2[Cloud Migration<br/>DevOps / SRE<br/>Managed Services]:::sub
    T --> S3 --> P3[Data Engineering<br/>BI / Dashboards<br/>Data Science]:::sub
    T --> S4 --> P4[RPA<br/>ML / AI<br/>Intelligent Ops]:::sub
    T --> S5 --> P5[IoT<br/>AR / VR<br/>Blockchain]:::sub
"""),
}


# ---------------------------------------------------------------------------
# Section keyword → diagram key mapping
# The enhancer will inject the diagram AFTER the first heading whose text
# contains ALL of the "match_all" tokens (case-insensitive).
# "after_line" is a hint from analysis; not required.
# "used" flag ensures each diagram is injected only once.
# ---------------------------------------------------------------------------

INJECTION_RULES = [
    # Executive summary block — appended to a synthetic exec section
    # (handled directly by enhancer, not by rule)

    # Cloud
    {"key": "cloud_services_framework",  "match_all": ["cloud", "services"], "any_of_h": [2]},
    {"key": "cloud_migration_lifecycle", "match_all": ["transition", "approach"], "any_of_h": [2]},
    {"key": "cloud_operating_model",     "match_all": ["delivery", "model"], "any_of_h": [2]},

    # Transformation
    {"key": "transformation_lifecycle",  "match_all": ["technical", "expertise"], "any_of_h": [2]},

    # DevOps / CI-CD
    {"key": "cicd_pipeline",             "match_all": ["technical", "architecture"], "any_of_h": [2]},
    {"key": "devops_toolchain",          "match_all": ["proposed", "solution"], "any_of_h": [2]},

    # Governance / Roles
    {"key": "governance_structure",      "match_all": ["roles", "responsibilities"], "any_of_h": [2]},
    {"key": "escalation_matrix",         "match_all": ["support", "response"], "any_of_h": [2]},

    # Security
    {"key": "security_layers",           "match_all": ["security", "compliance"], "any_of_h": [2]},
    {"key": "incident_response",         "match_all": ["incident", "management"], "any_of_h": [2]},

    # Talent
    {"key": "recruitment_funnel",        "match_all": ["expertise", "resources"], "any_of_h": [2]},
    {"key": "onboarding_timeline",       "match_all": ["onboarding"], "any_of_h": [1, 2, 3]},

    # SLA / Monitoring
    {"key": "sla_framework",             "match_all": ["quality", "assurance"], "any_of_h": [2]},
    {"key": "monitoring_architecture",   "match_all": ["monitoring"], "any_of_h": [2]},

    # Company
    {"key": "global_footprint",          "match_all": ["corporate", "information"], "any_of_h": [2]},
    {"key": "service_portfolio",         "match_all": ["service"], "any_of_h": [2, 3]},
]
