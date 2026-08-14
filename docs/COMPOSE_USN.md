# Composing the USN — the API contract this operator targets

`sovereign-operator` is a **separate repo** that composes a Universal Sovereign Node **over HTTP only**.
It imports **zero** USN packages (grep `sovereign_agent` in `src/` → 0). The boundary is an
**API-contract pin**, not a code dependency.

## Version pin

> **operator v0.1.0 targets USN tag ≥ `44a9ff3`** (the tip that serves `GET /api/v1/status` with
> `grants[].renew_run` / `revoke_run` verbatim, the atrium chat + builtins, the gate path, and the
> capacity templates). See the USN repo `sovereign-agent-starter`.

Pull latest safely on iron (never track a moving branch):
```bash
git -C sovereign-agent-starter fetch --tags && git -C sovereign-agent-starter checkout <usn-tag>
git -C sovereign-operator       fetch --tags && git -C sovereign-operator       checkout <operator-tag>
# personal state in ~/.sovereign_operator/ survives untouched.
```

## Routes the operator consumes (all GET; drafts reference the POST routes as text only)

| tool | method the operator uses | route |
|---|---|---|
| `usn_status` | **GET** | `/api/v1/status` |
| `usn_list_pending_gates` | **GET** | `/api/v1/breath_gate/pending` |
| `usn_receipts` | **GET** | `/api/v1/inference/receipts` · `/api/v1/audit/cylinders` |
| `usn_peers` | **GET** | `/api/v1/status` (peer facts) |
| `usn_storage_read` | **GET** | `/api/v1/storage/datum/<id>` |
| `usn_capacity_propose` | **GET** then quotes verbatim | `/api/v1/status` → `grants[].renew_run/revoke_run` |
| `usn_gate_prepare` | **GET** + drafts RUN text | reads `/breath_gate/pending`; RUN text references `…/approve\|deny`, `…/sanction` |
| `usn_propose_port_crossing` | **drafts RUN text only** | `POST /api/v1/port/crossing` (KM runs it) |
| `usn_storage_propose` | **drafts RUN text only** | `POST /api/v1/storage/datum` (KM's datums) |
| `usn_refuse_peer_prepare` | **drafts RUN text only** | `POST /api/v1/peers/refuse` |
| `usn_clean_exit_prepare` | **drafts RUN text only** | `POST /api/v1/peers/clean_exit` |

**The operator never POSTs a USN route.** Every POST above appears only inside RUN text the operator
hands to KM. The node's access log shows **GETs and nothing else** from the operator (verify row U2).

## Locks (v1, non-negotiable)

- **Q1** — RUN-text only. No tool POSTs any USN route, including `/port/crossing`. Sanction/approve/deny
  stay `@require_owner` on the node; the operator surfaces them, KM disposes.
- **Q2** — memory lives **wholly** under `~/.sovereign_operator/` (a local SQLite notebook). The operator
  has no route that writes the USN registry.
- **Frontier model = a drafted Port crossing**, never a silent fallback in code. The operator's own mind
  is a **loopback** model (Ollama/vLLM) only.

## Failure law

- Node API down → the operator says so and degrades to **memory-only**, labeled
  *"node unreachable — facts unknown as of `<t>`"*. It never fabricates facts.
- Local model down → the read tools and builtins still work (facts + exact proposals; no prose).

## Deny-by-default

Every tool returns `{ok, data}` or `{ok:false, out_reason:"route not in live API — OUT"}`. A `404`/absent
route is **OUT** — the tool layer never invents a route.
