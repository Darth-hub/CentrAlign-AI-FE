# Implementation map

This document connects visible product capabilities to the code that implements them.

| Area | Implemented work | Main files | Verification evidence |
| --- | --- | --- | --- |
| Identity | Signature, issuer, audience, expiry and role validation; short-lived internal tokens | `backend/services/auth.py`, `backend/security/routes.py` | Forged, expired, wrong-audience and unauthorized requests are rejected |
| State | SQL records, owner-scoped jobs, ordered events and write claims | `backend/services/database.py`, `backend/runtime/jobs.py` | Ownership, duplicate job and stale worker tests |
| Execution | A subprocess for each job; heartbeat, deadline and result persistence | `backend/runtime/worker.py`, `backend/runtime/runner.py` | Real subprocess success/failure and process-start failure tests |
| Reasoning | Explicit model provider selection; domain agents and workflow context | `backend/providers/`, `backend/agents/`, `backend/agentcore_app.py` | Missing or unsupported providers fail explicitly |
| Tools | Typed ERP dispatch, read-only analysis stages and restricted arithmetic | `backend/runtime/tools.py` | Analysis writes and arbitrary code expressions are blocked |
| Procurement writes | Approved snapshots, quantity/price checks, one PO attempt per requisition and read-back | `backend/services/write_policy.py` | Changed snapshots, duplicate attempts and invented completion IDs are rejected |
| Documents | Private generated storage keys, PDF/OCR extraction and saved invoice proposals | `backend/services/storage.py`, `backend/services/textract.py` | Storage path checks and review-before-write test |
| Human decisions | Approval, rejection, invoice confirmation and payment confirmation | `backend/api/decisions.py`, `backend/api/invoices.py` | Owner and role boundaries; extraction does not create an ERP invoice |
| ERP integration | Canonical models, per-user credential mapping, bounded HTTP calls and invoice/PO linkage | `backend/adapters/` | Invoice detail derives the linked PO from ERP line records |
| Frontend | OIDC sign-in, durable job polling, procurement views and architecture map | `frontend/src/` | Build and full browser integration remain pending |
| Deployment | Private configuration, Docker services, identity/ERP bootstrap and backups | `compose.yaml`, `deploy/`, `scripts/`, `netlify.toml` | Compose configuration and shell syntax checks |

## What runs autonomously

Within the procurement workflow, the agents retrieve records, select read operations, analyze suppliers and requisitions, inspect tool results and decide subsequent steps. The PO stage can execute an eligible approved purchase order. A process deadline bounds the run, and events record its progress.

Human actions remain explicit at escalation, rejection, invoice creation, payment creation and uncertain-write reconciliation. Model-reported risk and confidence remain advisory.

## Current constraints

- One complete PO per requisition; split awards and partial PO allocations require manual handling.
- Receipt returns, multiple-PO invoices and duplicate invoice item lines require manual matching.
- The available computer interface is the ERP HTTP API. Generic browser or desktop automation is not implemented.
- Conversation and workflow memory are stored in SQL; semantic company-memory extraction is not implemented.
- The arithmetic tool evaluates numeric expressions. Arbitrary Python execution is not exposed.
- The single worker limits concurrent agent jobs. Some lifecycle updates still replace whole records and need stronger concurrency controls before production use.
- Agent risk assessments and low-value approval rules do not provide formal policy proofs. A real organization needs its own deterministic policy and evaluation.
- Job and document retention, off-host backup and a restore drill remain operational work.

## Source navigation

[System architecture](ARCHITECTURE.md) · [Validation status](STATUS.md) · [Deployment](NETLIFY_DEPLOYMENT.md) · [Source origin](../UPSTREAM.md)
