# WORLD PLATFORM — EXECUTION PACKET v0.1

**Status:** PINNED ARTIFACT — UNSEALED  
**Objective:** LGP  
**Companion:** `WORLD_PLATFORM_LGP_v0.1.md`  
**Primary implementation rule:** extend the existing sovereign operator; do not create a parallel product.

---

## Mission

Turn the existing `sovereign-operator` into a practical, daily, human-operated command center on local IRON.

The principal should be able to open one surface, see what changed, see what agents did, see what requires judgment, dispose gated matters, and inspect receipts without needing to orchestrate tools or live in a terminal.

The system should support substantial autonomous work under standing mandates while preserving Human Primacy, default deny, provenance, and clean exit.

---

## Existing Assets to Compose

Before adding infrastructure, read and preserve the contracts in:

- `web/README.md`
- `web/server.py`
- `web/public/index.html`
- `corpus/README.md`
- `corpus/retrieval.py`
- `corpus/index/MANIFEST.json`
- operator/node auth and governance surfaces already used by the web server
- receipt / obligation / gate / Port surfaces already present in the operator and sovereign-agent starter

Current `web/` already provides the zero-terminal read/draft surface and includes Apps, Drills, Morning, Gates, Capacity, Passport, Records, Corpus, Chat, Receipts, and Port draft.

Do not re-implement those concepts in a new framework merely for fashion.

---

# P0 — OPERATOR BOOT / DAILY USABILITY

## Goal

A human on IRON can start the sovereign operating environment reliably and reach one browser URL.

## Work

1. Inventory exact local runtime dependencies:
   - sovereign node / USN endpoint
   - sovereign-operator checkout
   - Python environment
   - corpus index
   - Ollama
   - `nomic-embed-text`
   - local chat model
   - credential paths
   - receipt/state paths

2. Provide supervised local startup.
   Prefer user-level services or an equally inspectable local supervisor over a collection of shell sessions.

3. Add health checks for:
   - node
   - operator web
   - corpus
   - embedding model
   - local mind
   - receipt store

4. Add one launcher:

```text
sovereign-operator start
```

or the closest repository-native equivalent.

5. Add one status command:

```text
sovereign-operator status
```

6. Make the browser surface clearly distinguish:
   - node up/down
   - corpus available/unavailable
   - mind available/unavailable
   - gates waiting
   - workers running

## Acceptance

- cold boot to usable UI is deterministic
- no manual terminal choreography beyond the single launcher
- a degraded component is shown honestly rather than silently substituted
- corpus queries cite or refuse
- node remains local-authority root

---

# P1 — “NEEDS YOU” / HUMAN GATE

## Goal

The principal can dispose ordinary gated matters from the local operator surface without copying RUN text to another terminal.

## Critical rule

**Do not convert the general web server into a generic actuator.** Preserve its narrow read/draft posture.

Create a separately privileged **Gate Bridge**.

## Gate Bridge properties

- loopback or Unix socket only
- owner-authenticated
- no generic shell execution
- only registered action types
- exact canonical action envelope
- explicit human click / disposition
- nonce + expiry
- single-use authorization
- replay rejection
- pre-execution hash verification
- target and parameter validation
- policy / mandate validation
- auditable authorization receipt
- execution receipt
- effect receipt or reconciliation result
- safe retry semantics

## Initial action classes

Implement only actions already represented by governed routes and existing operator commands, for example:

- gate approve
- gate deny
- bounded grant renew/revoke
- sanctioned Port crossing where existing node law already permits it
- other existing owner-gated actions discovered from current code

Do not create a new authority merely to make the UI convenient.

## Needs You card

Each card should include:

```text
WHAT
WHY IT ROSE
WHO/WHAT PROPOSED IT
MANDATE
CONSEQUENCE CLASS
EVIDENCE
CORPUS BASIS (when relevant)
UNCERTAINTY
REVIEW/TEST STATUS
EXACT EFFECT
```

Actions:

```text
APPROVE
MODIFY
REJECT
EXPLORE
```

A modification invalidates the old action hash and produces a new proposal requiring fresh disposition.

## Acceptance

- approval never authorizes a different effect than the card showed
- stale/changed code or parameters force re-gating
- action cannot replay
- a crash after external effect does not blindly retry
- the human can see what happened from receipts

---

# P2 — STANDING MANDATES / AGENT RUNTIME

## Goal

The principal delegates responsibilities once; agents work continuously or on events; only exceptions rise.

## Runtime primitives

Implement or compose:

```text
Mandate
Worker
Trigger
Task
Run
Proposal
Gate
Receipt
Escalation
Health
Revocation
```

## Mandate fields

At minimum:

```yaml
id: stable-id
owner: principal-id
name: human label
objective: LGP-linked purpose
observe: []
may_read: []
may_write: []
may_autonomously: []
must_elevate: []
may_never: []
thresholds: {}
model_policy: {}
corpus_policy: {}
cadence: {}
expiry: optional
revocable: true
```

## Worker requirements

- workers do not own credentials independently when avoidable
- workers receive scoped capability leases
- every run has a stable run id
- output carries provenance
- a worker cannot widen its own mandate
- worker failure is visible
- agent/provider can be swapped without losing mandate state

## Event sources

Support:

- schedule
- webhook/event
- file/repo change
- message arrival
- threshold crossing
- manual request
- dependency completion

## Acceptance

At least three real mandates run end-to-end and produce useful work without a human prompt each time.

---

# P3 — CAPABILITY ADAPTERS

## Goal

Expose stable capabilities while allowing vendor implementations to change underneath.

## Interface concept

```text
capability.email.read
capability.email.draft
capability.email.send
capability.calendar.read
capability.calendar.write
capability.files.read
capability.files.write
capability.code.read
capability.code.propose
capability.code.merge
capability.finance.read
capability.finance.write
...
```

Read and write are separate grants.

## Initial practical adapters

Choose by actual principal value, not by ecosystem popularity.

Strong starting set:

1. Email
2. Calendar
3. GitHub/code
4. Files/documents
5. Finance/accounting read surfaces
6. Research/web where permitted by the selected intelligence provider

## Adapter rules

- credentials stay on IRON or in an operator-controlled secrets boundary
- provider-specific tokens never enter corpus
- adapters return normalized evidence records
- consequential writes route through mandate + gate policy
- external idempotency keys are used when supported
- connector loss must degrade cleanly

---

# P4 — AGENT SWARM / QUALITY SEPARATION

## Goal

Use abundant agent/model capacity to improve throughput and quality without concentrating authority.

## Recommended lanes

### 1. Product Integrator
Owns operator experience and end-to-end coherence.

### 2. Runtime / Kernel Integrator
Owns mandate runtime, task lifecycle, action envelopes, Gate Bridge.

### 3. UI / Operator Surface
Owns Home, Needs You, Agents, Work, Receipts.

### 4. Connectors
Owns capability adapters, auth boundaries, evidence normalization.

### 5. Corpus / Retrieval
Owns cite-or-refuse integration and semantic routing support; remains read-only.

### 6. Security / Boundary Reviewer
Attacks authority widening, replay, CSRF, stale-action execution, secret leakage, connector privilege.

### 7. Reliability / Recovery
Owns service supervision, queues, crash consistency, idempotency, reconciliation.

### 8. ARET Quality Cell
For complex changes:

```text
Architect
Reviewer
Executor
Tester
```

These roles should be separated by run/task identity even if the same underlying model family is used.

## Parallel-development law

- separate branches/worktrees by lane
- explicit owned directories when possible
- no silent direct-to-main merges
- review cross-boundary changes
- provenance on generated artifacts
- tests and receipts before handoff

High token availability is an opportunity for deeper review, adversarial testing, and parallel exploration—not a reason to flood the codebase with redundant abstractions.

---

# P5 — OPERATOR HOME

## Goal

The home surface answers in under one minute:

```text
What changed?
What matters?
What is working for me?
What is blocked?
What needs my judgment?
```

## Suggested home structure

### NOW
Top 3–7 matters requiring human attention.

### OVERNIGHT / SINCE LAST VISIT
Agent runs, completed work, detected changes.

### OBJECTIVES
LGP-linked initiatives and movement.

### AGENT HEALTH
Only degraded/stuck workers by default; healthy fleet summarized.

### UPCOMING
Calendar, deadlines, commitments, predicted decision points.

### RECEIPT PULSE
Recent consequential actions and any reconciliation warnings.

### ASK OPERATOR
Universal intent input. The user does not choose the agent; the orchestrator routes.

---

# P6 — INTELLIGENCE ROUTER

## Goal

Use the strongest appropriate intelligence without making any model provider the sovereign dependency.

## Router considerations

- task type
- confidentiality
- required tools
- reasoning depth
- latency
- token budget
- local-only requirement
- corpus need
- coding need
- multimodal need
- provider health
- mandate model policy

## Example

```text
simple deterministic task -> code/local worker
private structured task     -> local model
frontier reasoning          -> frontier Port
large code task             -> Codex/Devin worker
independent review          -> different agent/model lane
```

Provider substitution is a design requirement.

---

# P7 — FEDERATION / WORLD SCALE

Do not begin with a mandatory central control plane.

Scale through sovereign nodes that can:

- identify from self-held keys
- admit by default-deny policy
- recognize bilaterally
- delegate explicitly
- exchange receipted messages/work
- offer/consume bounded compute
- join pools/federations voluntarily
- revoke relationships
- cleanly exit

A public discovery or convenience service MAY exist as a projection/adapter, but sovereign standing MUST NOT depend on it.

---

# FIRST THREE LIVE MANDATES

Use real work to force the platform into practical shape.

## A. Executive Communications

Observe email. Triage, retrieve context, identify commitments, draft. Elevate consequential sends and uncertain/high-impact matters.

## B. Daily Sovereign Brief

Aggregate calendar, commitments, active objectives, agent results, finance/business signals, code/project state, and exceptions into one morning surface.

## C. Sovereign Software Development

Continuously inspect operator/starter work, run separated architecture/review/test agents, prepare patches/PRs, elevate merge/release decisions.

These three exercise connectors, corpus, agent runtime, Gate, receipts, and the operator surface without requiring every future capability first.

---

# DEFINITION OF DONE — FIRST OPERATIONAL MILESTONE

The milestone is not “the architecture supports agents.”

It is this:

1. IRON boots the operator stack reliably.
2. The principal opens one local URL.
3. At least three standing mandates have run since the last visit.
4. Home shows useful completed work and exceptions.
5. At least one consequential item can be approved/rejected from the human Gate with no terminal.
6. The exact effect is receipted and inspectable.
7. Corpus-backed claims cite sealed source or refuse.
8. Revoking a worker/provider/connector does not damage sovereign state.
9. No frontier provider holds the sovereign keys.
10. The system can explain why an item rose to the human.

At that point, the harness has become an operating environment.

---

# AGENT HANDOFF PROMPT

Use this with Devin/Codex or another implementation agent:

```text
You are implementing World Platform inside mangumcfo/sovereign-operator.

Read first:
- artifacts/world-platform/WORLD_PLATFORM_LGP_v0.1.md
- artifacts/world-platform/WORLD_PLATFORM_EXECUTION_PACKET_v0.1.md
- web/README.md
- web/server.py
- web/public/index.html
- corpus/README.md
- corpus/retrieval.py
- relevant governance/auth/gate/receipt code before changing an authority boundary.

Objective: LGP.

Do not build a parallel dashboard. Evolve the existing operator web into the principal's daily command center.

Preserve Human Primacy, default deny, opt-in connection, provenance, clean exit, and local key custody.

Use abundant agents/compute where useful. Parallelize architecture, implementation, review, testing, reliability, and security work. Do not let parallelism silently widen authority or create redundant stacks.

First operational target:
- reliable IRON bring-up
- one local operator URL
- Needs You surface
- separate privileged Gate Bridge for explicit human dispositions
- exact action envelopes + replay protection + receipts
- three real standing mandates
- visible autonomous work before the human asks

Keep main protected. Work in reviewable branches. Report concrete runnable evidence, not architecture claims.

ECHO FORWARD.
```
