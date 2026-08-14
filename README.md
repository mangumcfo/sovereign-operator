# sovereign-operator

**A secretary with a good notebook, standing in front of a node that is the law.**

`sovereign-operator` is a small, separate, public tool that sits in front of a
[Universal Sovereign Node](https://github.com/mangumcfo/sovereign-agent-starter) and gives it the one
thing the node deliberately does **not** have: **durable conversational and working memory**. It
remembers what you did yesterday, flags a grant about to expire, and drafts the exact command to renew
it — then stops. It holds **no keys, no authority, and no execution path**.

Derived from the Universal Sovereign Node by Kenneth Mangum (KM-1176).

## What it is (and is not)

- **Is:** memory (a local notebook), drafting (proposals, renew/revoke reminders, morning briefs), and
  orchestration of **reads** against your node's API.
- **Is not:** a custodian, a signer, a second approver, or a cloud brain. It never POSTs a node route.

## The locks (v1, non-negotiable)

- **Read-and-draft only.** The operator talks to the node over HTTP and **only ever GETs**. Every
  consequential act comes back to you as **PROPOSE + RUN + GATE** text for your keyboard. Your node's
  access log shows GETs and nothing else from the operator.
- **Memory is yours, and local.** Everything the operator remembers lives under `~/.sovereign_operator/`
  — never in the node's registry.
- **Loopback mind only.** Its own model is a local Ollama/vLLM. Reaching a frontier model is a *drafted
  Port crossing you sanction*, never a silent fallback.

## Install (loopback-runnable after clone — pure stdlib, zero runtime deps)

```bash
git clone https://github.com/mangumcfo/sovereign-operator.git && cd sovereign-operator
python3 -m venv .venv && ./.venv/bin/pip install -e .
# point it at your local node (defaults shown):
export OPERATOR_USN_URL=http://127.0.0.1:8421/api/v1
export OPERATOR_MIND_URL=http://127.0.0.1:11434/v1/chat/completions   # optional: your loopback model
```

## Use

```bash
operator morning          # one screen: status · grants with days-to-expiry · pending gates · LGP lens
operator chat             # conversational; memory persists across sessions. /status /propose /gates /export /help
operator export           # notebook → human-readable markdown under ~/.sovereign_operator/exports/
```

`operator morning` flags an expiring grant from **live facts**; `operator chat` remembers across
sessions; every material suggestion is **PROPOSE / RUN / GATE** text. Facts (from the node) and memory
(from the notebook) are always labeled — they never blend.

## Compose contract

See [`docs/COMPOSE_USN.md`](docs/COMPOSE_USN.md) for the exact routes consumed and the USN tag this
version targets. The boundary is HTTP; the operator imports zero node packages.

## License

Constitutional Federation Sovereign License — © 2026 Kenneth Mangum (KM-1176). Fork it; keep it
sovereign.
