# CentrAlign AI — system architecture

The operator separates user intent, execution and verification. The browser presents requests and decisions. FastAPI establishes the caller's identity and records work. A durable worker performs agent execution. The canonical adapter turns typed operations into ERPNext calls.

![System map](assets/centralign-architecture.svg)

## Component boundaries

| Component | Owns | Does not own |
| --- | --- | --- |
| React workspace | Chat, request queues, approval controls, progress and evidence views | Model keys, ERP credentials or authorization decisions |
| Keycloak | OIDC identity, signed tokens, roles and department claims | ERP accounting permissions |
| FastAPI | JWT validation, role checks, HTTP interfaces and job creation | Background job execution inside a request |
| PostgreSQL | Jobs, events, conversations, decisions, lifecycle and write claims | ERP accounting as a second system of record |
| Worker | Queue consumption, heartbeat, process deadline and durable events | Unlimited concurrency or automatic replay of uncertain writes |
| Per-job runner | Agent reasoning, context and permitted tool execution | A shared mutable agent instance across jobs |
| ERP adapter | Canonical schemas, per-user HTTP credentials and ERP operations | Escalating to a broad service account when credentials are missing |
| ERPNext | Procurement records, accounting rules and ERP permissions | The model's narrative of whether work succeeded |

The deployed database configuration uses PostgreSQL. SQLite is used for local tests. Keycloak stores its identity data in a separate database on the same PostgreSQL service. ERPNext uses MariaDB, Redis and site volumes.

## A procurement job, end to end

```mermaid
sequenceDiagram
    actor User
    participant UI as React workspace
    participant API as FastAPI
    participant SQL as PostgreSQL
    participant Worker
    participant Run as Job subprocess
    participant LLM as Model provider
    participant Tool as ERP tool and write checks
    participant ERP as ERPNext
    User->>UI: Start workflow for a requisition
    UI->>API: POST /api/agents/workflow/runs + bearer token
    API->>API: Verify identity and role
    API->>SQL: Persist owner-scoped job
    API-->>UI: 202 + job_id
    Worker->>SQL: Claim queued job
    Worker->>Run: Start isolated runner with verified identity
    loop Reason, act and observe
        Run->>LLM: Context and permitted tool definitions
        LLM-->>Run: Next operation or structured result
        Run->>Tool: Typed operation
        Tool->>ERP: Read as the acting user
        ERP-->>Tool: Authoritative records
        Tool-->>Run: Observation
        Run-->>Worker: Progress event
        Worker->>SQL: Persist event and heartbeat
    end
    Note over Run,ERP: Exceptions pause at a human approval gate.
    Run->>Tool: Create PO from approved snapshot
    Tool->>Tool: Validate state, unchanged lines and write claim
    Tool->>ERP: Create purchase order
    Tool->>ERP: Read back supplier, quantities and prices
    ERP-->>Tool: Verified PO record
    Tool-->>Run: Confirmed evidence
    Worker->>SQL: Store final result and job status
    UI->>API: Poll /api/agents/runs/{job_id}/events
    API-->>UI: Progress, result and ERP identifier
    UI-->>User: Completed outcome or blocking condition
```

The diagram shows the background workflow. Chat currently runs synchronously through the API. Agents use a local typed dispatcher for ERP access; direct user actions and invoice processing can use the mounted canonical HTTP API. This implementation does not require an MCP gateway.

## Approval and write boundary

```mermaid
flowchart TD
    A[Requisition analysis] --> B{Low risk and eligible amount?}
    B -->|Yes| C[Save approved item and price snapshot]
    B -->|No| D[Human reviews exception]
    D -->|Approve| C
    D -->|Reject| E[Record rejection]
    C --> F[PO stage requests a write]
    F --> G{Current requisition matches snapshot?}
    G -->|No| X[Block and request fresh approval]
    G -->|Yes| H{Write already attempted?}
    H -->|Yes| Y[Inspect ERP before retry]
    H -->|No| I[Persist write claim]
    I --> J[Create through per-user ERP credentials]
    J --> K[Read back ERP record]
    K --> L{Supplier and lines match?}
    L -->|Yes| M[Persist confirmed order evidence]
    L -->|No or unknown| Y
```

Approval snapshots cover item identifiers, quantities and approved unit prices. They are not a full enterprise policy engine or an atomic ERP version lock. The PO boundary accepts all approved items once, with unchanged quantities and prices no higher than approved rates. Amounts above 50000 require the application admin role in addition to ERP permissions.

## Failure and recovery

```mermaid
stateDiagram-v2
    [*] --> Queued
    Queued --> Running: worker claims job
    Running --> Completed: final result recorded
    Running --> Failed: known execution failure
    Running --> Interrupted: process lost or deadline reached
    Interrupted --> Reconciled: admin checks ERP and records evidence
    Completed --> [*]
    Failed --> [*]
    Reconciled --> [*]
```

A completed job can contain an `AWAITING_APPROVAL` workflow result; that means the analysis job ended, not that a PO was created. A later approved resume starts another job. The UI must distinguish job state from the business outcome.

An interrupted job retains its document lock. Admin reconciliation releases that job lock only. Permanent ERP write claims remain until the uncertain ERP outcome is resolved. The worker never blindly replays an ambiguous write.

## Invoice and payment path

```mermaid
flowchart LR
    PDF[PDF or image] --> OCR[Text extraction or OCR]
    OCR --> LLM[Structured field extraction]
    LLM --> P[Saved proposal]
    P --> H[Owner reviews original and extracted values]
    H -->|Explicit confirmation| I[Create and read back ERP invoice]
    I --> M[Compare invoice, PO and accepted receipts]
    M --> A[Payment analysis]
    A --> C[Human confirms payment]
    C --> G[Balance, quantities and amount checks]
    G --> ERP[Create ERP payment entry]
```

Extraction confidence is not calibrated, so extracted values always require human review. Payment checks use authoritative ERP records rather than client-supplied analysis. The accounting transaction is recorded in ERPNext; no external bank transfer integration is implemented.

## Deployment boundary

Netlify serves static frontend assets. Requests go directly to a separate HTTPS API; browser polling avoids coupling job duration to a frontend request. Docker Compose defines FastAPI, a single worker, identity, ERP services and persistent data. The optional Caddy profile terminates public HTTPS for API and identity hostnames.

See [deployment](NETLIFY_DEPLOYMENT.md), [implementation evidence](IMPLEMENTATION.md) and [validation status](STATUS.md).

## Quote-backed execution demonstrated locally

The verified path uses the model for supplier selection and requisition assessment,
then pauses for explicit human approval. The approved quote binds supplier, rates,
terms and delivery date. A typed executor creates that exact PO without another
model request, and the write boundary independently reads the ERP record back.
This reduces provider exposure after the commercial decision is already fixed.
The model-planned PO path remains available for cases without a quote snapshot.
See [the local evidence](evidence/2026-10-26-procurement.json).
