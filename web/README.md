# web — Operator Web Surface (WP2)

The **zero-terminal daily path**: a loopback browser UI over the *existing* operator + corpus
read/draft surfaces. A non-terminal human runs `morning`, sees grants/gates, drafts acts, and searches
the corpus with citations — without living in the CLI. **Not a new product, not a Claude competitor,
not a node capability** — a surface over what already exists.

## Law (same fences as the operator CLI, behind a browser)

- **Read/draft only toward the node.** The server talks to the USN **only** through the operator's
  GET-only client (`sovereign_operator.tools`); it has **no path that POSTs a USN route**. The node's
  access log shows GETs and nothing else from this surface. Consequential acts (renew/revoke, gate
  disposition, Port crossing, storage) are returned as **RUN/PROPOSE/GATE text** with a Copy button —
  KM disposes on the keyboard or the console. Nothing is executed here.
- **Loopback only.** Binds `127.0.0.1`; refuses to start off loopback. The browser POSTs (chat, draft
  requests) go to *this* server, never to the USN.
- **Loopback mind; frontier is a drafted crossing.** Chat uses the local model (loopback); a frontier
  model is only ever a labeled, drafted Port crossing KM sanctions — never a silent fallback.
- **Compose, don't re-implement.** Corpus search rides `corpus.retrieval` (cite-or-refuse); the shelf
  is not re-implemented. Stdlib only; zero third-party deps.

## Panels

`Needs You` (Port obligations + pending gates, exception-only) · `Morning` (status + LGP lens) · `Gates` (pending, with the exact dispose RUN text) · `Capacity`
(grants + verbatim renew/revoke) · `Corpus` (search → cited sealed chunks, or MISSING/refuse) · `Chat`
(local mind; PROPOSE/RUN/GATE) · `Receipts` · `Port draft` (crossing RUN text).

## Run (Dragon, against the live USN)

```bash
cd ~/sovereign-operator
.venv/bin/python web/server.py --port 8722      # or: setsid ~/start_operator_web.sh </dev/null >/tmp/operweb.log 2>&1 &
# open in a browser on the node (loopback):
#   http://127.0.0.1:8722/
```
Env (defaults shown): `OPERATOR_USN_URL=http://127.0.0.1:8421/api/v1` · `OPERATOR_PORT_URL=http://127.0.0.1:8490` · `OPERATOR_PRINCIPAL=operator` (selects `~/.breathline/credentials/<principal>.token`, or set `OPERATOR_USN_TOKEN_FILE`) · `OPERATOR_MIND_URL=http://127.0.0.1:11434/v1/chat/completions` · `OPERATOR_WEB_PORT=8722`. Corpus search needs a
local embed model (`ollama pull nomic-embed-text`).

## Endpoints (all read/draft)

GET `/api/needs-you` `/api/morning` `/api/status` `/api/gates` `/api/capacity` `/api/receipts` `/api/corpus?q=` ·
POST (browser→this server only) `/api/chat` `/api/draft/crossing` `/api/draft/storage`. None POST the USN.
