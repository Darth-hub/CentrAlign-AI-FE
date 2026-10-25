# Procurement agents

The agent layer uses Strands with an explicitly configured model provider. Procurement orchestration is implemented in `backend/agentcore_app.py` and executed by the durable worker.

| Module | Responsibility |
| --- | --- |
| `chat_agent.py` | Natural-language intake and role-scoped ERP HTTP tools |
| `sourcing_agent.py` | Supplier evaluation and contract context |
| `requisition_agent.py` | Request analysis and risk recommendation |
| `po_management_agent.py` | Approved purchase-order generation |
| `receiving_agent.py` | Receipt and delivery analysis |
| `invoice_matching_agent.py` | Invoice/PO/receipt comparison |
| `payment_agent.py` | Payment timing and discount analysis |
| `p2p_workflow.py` | Structured-response extraction helpers |

Analysis tools are read-only. The workflow PO stage enables a guarded PO write, subject to the server's approval snapshot and ERP permissions. Standalone analysis is not authority to create a record. Invoice and payment creation are separate, explicit user actions.

See [architecture](../../docs/ARCHITECTURE.md) for the actual control flow and [implementation](../../docs/IMPLEMENTATION.md) for constraints and test evidence.
