# Cockpit Drills (WP3) — run the node over existing routes

Each drill exercises an **existing** route/module (no new kernel code) three ways: **read on the web**,
**draft the exact command**, **dispose on the keyboard / console**, then **verify from receipts**. The
web reads and drafts — it never executes against the node. Web path preferred; CLI is the fallback.

**Start** (Dragon): `setsid ~/start_node_console.sh …` (node_api 8421) · `setsid ~/start_operator_web.sh …`
(web 8722) → open `http://127.0.0.1:8722/` → **Drills** tab. CLI fallback runs from `~/sovereign-operator`.

Node base `B=http://127.0.0.1:8421/api/v1`. Every drill leaves the node's access log with **GETs only
from the operator/web** — the consequential POSTs are yours, on your keyboard.

---

## Drill 1 · Gate — raise → dispose → receipt
**Do:** Port draft tab → draft a crossing → copy RUN → run it (raises a PENDING gate). Gates tab shows
the exact APPROVE/DENY RUN → copy → dispose on your keyboard or the console Gate Inbox.
**CLI fallback:**
```bash
curl -s -X POST $B/port/crossing -H 'Content-Type: application/json' -d '{"target":"external-relay","instruction":{"send":"ref://demo"}}'
curl -s $B/breath_gate/pending                              # the gate is waiting
curl -s -X POST $B/breath_gate/<id>/deny -d '{}'            # or …/approve ; a Port gate → …/port/crossing/<cid>/sanction
```
**Verify (receipts):** the deny/sanction response is a real `record_disposition` (approver=owner); a
sanction returns a `crossing_root` hash. `curl $B/breath_gate/pending` → the gate is gone.

## Drill 2 · Capacity — renew / revoke (verbatim)
**Do:** Capacity tab → each grant shows the node's own `renew_run` / `revoke_run` byte-for-byte → copy
→ run when a grant nears expiry (renew) or `rm grant_*.json` (revoke; puller denies next job ~5s).
**Verify:** Morning tab → grant days-left resets after a renew. The operator never issues — you do.

## Drill 3 · Storage / material passport — one real datum
**Do:** Passport tab → enter a REAL content ref (a serial / insurance-PDF sha256 / QuadRoof panel
serial) + why → Draft → copy the RUN → run it (stores an owner-scoped, Merkle-bound datum) → paste the
returned id → Read it back.
**CLI fallback:**
```bash
curl -s -X POST $B/storage/datum -H 'Content-Type: application/json' -d '{"content":"sha256:<hash-or-serial>","visibility":"owner"}'
curl -s $B/storage/datum/<id>                              # read it back
curl -s -X POST $B/storage/datum/<id>/verify -d '{"content":"sha256:<hash-or-serial>"}'   # Merkle verify
```
**Verify:** the datum reads back owner-scoped; the verify route confirms the binding.

## Drill 4 · Corpus — cite on-corpus + XRP→MISSING
**Do:** Corpus tab → search an on-corpus topic → every hit is a cited sealed chapter. Search *the XRP
book* / *book 4 of the foundation series* → MISSING with the catalog row, never invented prose.
**CLI fallback:** `curl -s "http://127.0.0.1:8722/api/corpus?q=immutable+general+ledger"` /
`…?q=summarize+the+xrp+book`. **Verify:** the citation resolves to a real chapter (WP1 C10 byte-true);
XRP has zero chunks by construction.

## Drill 5 · Port draft — node untouched until you sanction
**Do:** Port draft tab → draft a crossing → you get the exact RUN text, nothing more.
**Verify:** the node access log gains **no line** from the draft (a draft is not an act). Reaching
outside is a Port crossing YOU sanction (owner-only); the Port carries a directive, never value.

## Drill 6 (optional, propose-only) — livelihood / succession / protection DRAFTS
Drafts only. A livelihood attestation over a compute-share receipt week, a succession dry-run (key-epoch
plan), or a protection-covenant draft between Dragon+Beard are **PROPOSE text for KM's keyboard** — no
second-party act and no live-root change without a separate KM word. Use the Chat tab to draft; the
operator surfaces PROPOSE/RUN/GATE and stops.

---

## Success (KM or designated operator)
Drills 1–5 completed on Dragon, receipts re-derivable, web path preferred (CLI acceptable). No agent
POST to the node · no self-approve · nothing executed by the web surface — you disposed each act.

## Fences (invariants)
No agent POST to USN · no self-approve · no robotics · no ERP 2-week pilot yet (WP4 waits on these
drills being real) · no kernel merge · frontier only as a drafted crossing.
