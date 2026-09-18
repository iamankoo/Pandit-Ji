# Pandit Ji — Architecture Diagrams

Referenced from `docs/ARCHITECTURE.md`. All diagrams are Mermaid so they render natively on GitHub and in most editors. These are architecture-level diagrams (Phase 2 deliverable) — they do not imply any of the depicted components are implemented yet.

## System overview

```mermaid
flowchart TD
    subgraph Clients
        MOB[Flutter Mobile App]
        WEB[Web App]
        ADM[Admin App]
    end

    MOB --> GW
    WEB --> GW
    ADM --> GW

    GW[API Gateway]--> SRV[FastAPI Composition Root]

    SRV --> AGENT[agent — Agent Orchestrator]
    SRV --> ASTRO[astro-engine]
    SRV --> RULE[rule-engine]
    SRV --> KNOW[knowledge]

    AGENT --> ASTRO
    AGENT --> RULE
    AGENT --> KNOW
    AGENT --> AIINF[AI Reasoner / Inference Service]
    AGENT --> VER[verification]

    VER --> AGENT

    ASTRO --> DB[(PostgreSQL)]
    RULE --> DB
    KNOW --> DB
    KNOW --> VEC[(pgvector)]
    AGENT --> CACHE[(Redis)]
    AGENT --> MEM[(Memory / Conversation store)]
```

## A. Normal astrology question (chat path)

```mermaid
sequenceDiagram
    participant U as User
    participant G as API Gateway
    participant A as agent (Orchestrator)
    participant AS as astro-engine
    participant R as rule-engine
    participant K as knowledge
    participant AI as AI Reasoner
    participant V as verification

    U->>G: "Will my career improve next year?"
    G->>A: routed request (authenticated, rate-limited)
    A->>A: intent detection -> domain = career
    A->>A: plan required evidence (D1, D10, 10th lord, Dasha, transits)
    A->>AS: ChartRequest / DashaRequest / TransitRequest
    AS-->>A: structured facts
    A->>R: evaluate rules against facts
    R-->>A: triggered yogas/doshas + evidence
    A->>K: retrieve phrasing/remedy context (RAG)
    K-->>A: knowledge snippets (narration-only)
    A->>AI: evidence bundle + user question + conversation memory
    AI-->>A: draft narrative response
    A->>V: draft response + evidence bundle
    V-->>A: PASS or REGENERATE (+ reasons)
    A-->>G: final response (+ agent_trace)
    G-->>U: response
```

## B. Calculation authority

```mermaid
flowchart LR
    IN[Input: birth data + calculation_config] --> ENG[astro-engine]
    ENG --> RES[Deterministic Result]
    RES --> STORE[(Stored as computed_charts / dasha_periods / etc.)]
    RES --> EVID[Passed as Evidence to agent]
    EVID --> NAR[AI Narration]
    NAR -.->|never writes back into| STORE
```

The dotted line is intentional: the AI narration layer has no write path into any deterministic-fact table. Facts flow one direction only.

## C. Verification

```mermaid
flowchart TD
    EV[Evidence Bundle] --> GEN[Generated Answer]
    EV --> VER[Verifier]
    GEN --> VER
    VER --> CHECK{Claims traceable to evidence?<br/>No contradictions?<br/>No unsupported certainty?}
    CHECK -->|PASS| OUT[Response released]
    CHECK -->|FAIL| REGEN[Regenerate / strip claim / add caveat]
    REGEN --> GEN
```

## D. Async background job

```mermaid
flowchart LR
    API[API request] -->|enqueue| Q[(Queue)]
    Q --> W[Worker]
    W --> SVC[Target service<br/>e.g. knowledge ingestion,<br/>report generation, backtesting]
    SVC --> DB[(Database)]
    SVC --> NOTIFY[Notification / result available]
```

## E. Production observability

```mermaid
flowchart LR
    C[Client] --> G[API Gateway]
    G --> S[Services<br/>astro-engine / rule-engine / agent / knowledge / verification]
    S --> L[Structured Logs]
    S --> M[Metrics]
    S --> T[Traces]
    L --> MON[Monitoring / Alerting]
    M --> MON
    T --> MON
```
