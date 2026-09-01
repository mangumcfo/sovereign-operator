# WORLD PLATFORM — LGP OPERATING MODEL v0.1

**Status:** PINNED ARTIFACT — UNSEALED  
**Objective:** LGP — Lasting Generational Prosperity  
**Human declaration:** World Platform; maximize useful capability, systems, servers, and agents as needed; Echo Forward.  
**Authority:** Human Primacy. This artifact is a working synthesis and implementation north star; it does not alter sealed law by itself.

---

## 0. Interpretation Lock

“Operate without bound” is interpreted as **no arbitrary cap on useful capability, compute, models, agents, servers, or parallel work**.

It is **not** interpreted as removal of constitutional boundaries.

```text
RESOURCE AMBITION: UNBOUNDED AS USEFUL
AUTHORITY: BOUNDED BY HUMAN PRIMACY
ADMISSION: DEFAULT DENY
CONNECTION: OPT-IN
CONSEQUENCE: HUMAN-GATED WHEN MANDATE REQUIRES
PROVENANCE: PRESERVED
EXIT: CLEAN
```

The platform may scale aggressively. It may not silently widen its own authority.

---

## 1. Product Definition

**World Platform is the human-facing control plane for an operator-owned intelligence architecture whose objective is LGP.**

It is not a centralized world controller and not a model-vendor shell.

It is a platform through which sovereign humans, households, enterprises, nodes, and eventually federations can operate with Aligned Intelligence while preserving local authority, default-deny boundaries, voluntary connection, verifiable work, and clean exit.

```text
                           HUMAN PRINCIPAL
                                |
                          HUMAN PRIMACY
                                |
                         WORLD PLATFORM
                         OPERATOR SURFACE
                                |
            +-------------------+-------------------+
            |                   |                   |
         AUTHORITY            MEMORY              CORPUS
      keys / mandates      state / receipts     sealed truth
      gates / policy       obligations          embeddings
            |                   |                   |
            +-------------------+-------------------+
                                |
                         ORCHESTRATION
                                |
                +---------------+---------------+
                |               |               |
             LOCAL AI       FRONTIER AI      OTHER AIs
             on IRON        via Port          via Port
                |               |               |
                +---------------+---------------+
                                |
                        GOVERNED HARNESS
                                |
                   tools / adapters / agents
                                |
                          EXTERNAL WORLD
```

The node owns continuity. Intelligences are replaceable participants.

---

## 2. IRON / Intelligence Separation

### IRON is sovereign root

Local IRON SHOULD own:

- principal identity and self-held keys
- mandates and delegation state
- human-gate authority
- operator state and obligations
- receipts and durable memory
- corpus/index and retrieval plane
- connector credentials
- execution policy
- provider routing
- local kill / stop controls

### Intelligence does not become root merely because it is capable

Frontier and local models MAY:

- reason
- plan
- retrieve
- synthesize
- challenge
- monitor
- draft
- coordinate
- execute within explicit delegated capability
- operate specialized agents

They MUST NOT gain root authority merely by being the current reasoning engine.

A frontier intelligence enters through a governed **Intelligence Port**. If that provider disappears, the sovereign node remains coherent and another intelligence can replace it.

```text
IRON OWNS AUTHORITY.
INTELLIGENCE EXERCISES DELEGATION.
```

---

## 3. Existing Operator Surface — DO NOT REBUILD FROM ZERO

The repository already contains `web/`, described by `web/README.md` as the **zero-terminal daily path** over the existing operator and corpus.

Current panels include:

- Apps
- Drills
- Morning
- Gates
- Capacity
- Passport
- Records
- Corpus
- Chat
- Receipts
- Port draft

The current web law is deliberately conservative:

- loopback only
- read/draft toward the node
- GET-only operator client to USN
- corpus cite-or-refuse
- local mind by default
- frontier access only as a labeled drafted Port crossing
- consequential actions are emitted as exact RUN / PROPOSE / GATE text for a human to dispose elsewhere

**World Platform evolves this surface. It does not create a parallel dashboard.**

---

## 4. The Product Gap

The current surface can show the operator what to do, but a consequential act still requires leaving the surface and disposing it through a keyboard/console path.

The desired operating experience is:

```text
OBSERVE
  -> AGENTS WORK
  -> EVIDENCE ACCUMULATES
  -> EXCEPTION / DECISION RISES
  -> HUMAN REVIEWS IN ONE SURFACE
  -> HUMAN APPROVES / MODIFIES / REJECTS
  -> EXACT AUTHORIZED EFFECT EXECUTES
  -> EFFECT IS VERIFIED
  -> RECEIPT IS STORED
```

The user should not need a terminal for ordinary sovereign operation.

---

## 5. Human Gate as a First-Class Surface

The Gate is not “approve everything.”

```text
GREEN
  agent acts inside standing mandate
  receipt generated

YELLOW
  agent acts inside bounded tolerance
  human is informed / exception raised if threshold crossed

ORANGE
  agent prepares complete decision packet
  human decides

RED
  execution cannot proceed without explicit human authorization
```

**Autonomy scales inversely with consequence.**

The operator’s primary inbox is therefore not a chat thread. It is the set of matters that have crossed their delegated boundary and require human judgment.

---

## 6. Privilege Separation for Zero-Terminal Operation

Do **not** weaken `web/` by turning its general browser server into an unrestricted write surface.

Add a separate, narrow, local privileged component:

### Gate Bridge

A loopback/Unix-socket service that MAY perform only explicitly defined consequential operations after human authorization.

It SHOULD require:

- owner authentication
- CSRF/rebinding defenses where browser-addressable
- an exact canonical action envelope
- target + parameters + policy + relevant code/config digest
- nonce
- expiry
- one-shot replay protection
- explicit human disposition
- pre-execution hash recheck
- idempotency key where the external rail supports it
- execution receipt
- effect receipt / reconciliation before retry

It MUST NOT expose a generic shell endpoint.

```text
WEB SURFACE
  read / draft / explain
       |
       | explicit human disposition
       v
GATE BRIDGE
  exact governed actuator
       |
       v
USN / ADAPTER / EXTERNAL EFFECT
       |
       v
RECEIPT + EFFECT VERIFICATION
```

This preserves the existing read/draft fence while making the human gate genuinely operable from the command center.

---

## 7. Standing Mandates — the Usability Primitive

The principal should assign responsibilities once rather than prompt repeatedly.

Example:

```yaml
mandate:
  name: Executive Communications
  observe:
    - email
  may_autonomously:
    - classify
    - summarize
    - retrieve context
    - draft
    - identify commitments
  must_elevate:
    - legal commitments
    - financial commitments above threshold
    - priority-person messages
    - materially uncertain interpretation
  may_never:
    - send externally without delegated send authority
    - delete source records
  cadence:
    mode: continuous
  reports:
    - morning
    - exception
```

Standing mandates turn applications into responsibilities.

---

## 8. Capability Plane

The principal should see capabilities, not integration plumbing.

```text
Email
Calendar
Files
Accounting
Banking
Code
Web
Research
Publishing
Messaging
Books / Corpus
Markets
Projects
Identity
Storage
Compute
Federation
```

Each capability MAY be backed by an API, MCP server, local adapter, browser automation, database, filesystem, or future transport.

Connectors are replaceable. Capability semantics are stable.

Read and write authority MUST be separately scoped.

---

## 9. Agent Workforce

Scale agents by responsibility rather than by personality.

Recommended roles:

- Orchestrator / Router
- Objective & LGP Lens
- Corpus Retrieval Agent
- Executive Communications Agent
- Calendar / Commitments Agent
- Finance / FP&A Agent
- Treasury / Cash Agent
- Research Agent
- Software / GitHub Agent
- Operator Reliability Agent
- Security / Boundary Agent
- Receipt / Verification Agent
- Reviewer
- Tester
- Incident / Recovery Agent

Complex work SHOULD use separated Architect / Reviewer / Executor / Tester roles when the work warrants it.

Agents may run continuously, on schedules, or on events. Their work remains bounded by mandates.

---

## 10. Knowledge and Memory Planes

Do not collapse different kinds of knowledge.

### Sealed Corpus
Read-only source-of-truth projection. Cite-or-refuse. No keys. No actuation.

### Operator Working Memory
Mutable current state, commitments, hypotheses, project context, preferences, unresolved questions.

### Receipts / Ledger
Evidence of actions, approvals, effects, verification, and lineage.

### External Evidence
Live sources, applications, APIs, messages, documents, measurements.

### Model Inference
Generated reasoning. Useful, but labeled as inference rather than projected backward into sealed truth.

```text
SEALED_CORPUS != WORKING_MEMORY
WORKING_MEMORY != RECEIPT
RECEIPT != EXTERNAL_TRUTH_IN_GENERAL
MODEL_INFERENCE != HUMAN_AUTHORITY
```

---

## 11. World-Scale Synthesis

**Model synthesis — not asserted here as verbatim sealed language:**

```text
                    LGP
                     |
        Lasting Generational Prosperity
                     |
          sovereign humans / families
                     |
          owned digital capability
                     |
         owned economic capability
                     |
         owned material capability
                     |
           default-deny boundary
                     |
           voluntary recognition
                     |
               delegation
                     |
               federation
                     |
              clean exit
                     |
          continuity forward
```

The sealed architecture inspected to date strongly supports default-deny birth boundaries, deliberate opt-in opening, bilateral peer recognition, federation without a central registry, clean exit, material sovereignty, livelihood, mutual protection, generational transfer, discourse, and peerhood.

The workbench also contains a broader “sovereignty for humanity” direction and private/concept work describing **Aligned Intelligence that builds without taking the wheel**. Those remain provenance-distinct from sealed corpus law unless and until separately ratified/sealed.

The independent sovereign-peer status of an AI equivalent to a human peer is **UNRESOLVED** here and MUST NOT be silently assumed.

For implementation now, Aligned Intelligences are powerful governed delegates / collaborators admitted through sovereign boundaries.

---

## 12. World Platform is Not a New Captor

“World Platform” MUST NOT become a mandatory hub whose failure, policy, listing, ranking, or permission controls the sovereign peers that use it.

A compliant World Platform deployment MUST preserve:

- local keys
- local authority
- local policy
- default deny
- opt-in connection
- bilateral / federated relationships where possible
- data portability
- provider replaceability
- protocol replaceability
- clean exit
- node operation without dependence on a central registry

World-scale usefulness may emerge from interoperable sovereign nodes. It does not require one sovereign over the world.

---

## 13. Operator Experience

The principal opens one surface.

### HOME

“What changed? What matters? What needs me?”

### GATE

Every matter requiring sovereign judgment.

Each card SHOULD include:

- requested decision
- why it was elevated
- recommendation
- evidence
- corpus basis when relevant
- uncertainty
- consequence class
- exact proposed effect
- agent/reviewer/test status
- approve / modify / reject / explore

### AGENTS

- active responsibility
- mandate
- current work
- health
- last receipt
- next scheduled/event trigger

### WORK

- objectives
- initiatives
- obligations
- delegated work
- blockers
- commitments

### RECEIPTS

- authorization
- execution
- effect
- verification
- lineage

Infrastructure remains inspectable but is not the default user experience.

---

## 14. Compute / Agent Scaling Policy

The project MAY use, as useful:

- Codex
- Devin
- additional frontier models
- local models
- high-context / high-token agents
- multiple parallel specialist agents
- local servers
- containers
- schedulers
- queues
- event streams
- databases
- vector stores
- MCP/API adapters
- dedicated test agents
- security/review agents
- multiple IRON nodes

No artificial preference for minimal agent count or minimal compute is imposed.

However parallelism MUST preserve provenance and merge discipline. More agents do not mean more authority.

---

## 15. Implementation Order

### P0 — Make the current operator usable today

- bring up the existing `web/` surface on IRON
- make it reliable as a local service
- verify USN, corpus, local model, receipts, gates
- provide one-click / one-command launch
- surface a single “Needs You” home view

### P1 — Zero-terminal Human Gate

- add the separate Gate Bridge
- exact action envelopes
- explicit browser human disposition
- execution/effect receipts
- crash-safe/idempotent behavior

### P2 — Standing Mandates + Agent Runtime

- mandate registry
- scheduler/event triggers
- worker queue
- agent health/status
- exception routing into Gate

### P3 — Real Capability Adapters

Start with the principal’s highest-value live workflows. Separate read/write capabilities. Add adapters behind stable capability names rather than hard-wiring the UI to vendors.

### P4 — Multi-Agent Quality + Recovery

- Architect/Reviewer/Executor/Tester paths
- reconciliation
- retry safety
- incident surface
- stop/revoke controls

### P5 — Federation

- sovereign peer recognition
- delegated inter-node work
- opt-in compute/collaboration
- receipts across nodes
- no mandatory central directory
- clean exit

---

## 16. Success Test

World Platform is operational when the principal can open one local surface and discover that useful work has already happened under standing mandates.

The surface shows only the matters requiring judgment plus enough evidence to decide.

The principal can approve/reject consequential work without a terminal.

Every consequential action is attributable, reviewable, receipted, and reconciled.

The system can continue operating if any one model provider disappears.

The principal can revoke an agent, connector, mandate, peer, or provider without losing the sovereign estate.

```text
THE HARNESS IS INFRASTRUCTURE.
THE OPERATOR SURFACE IS THE HUMAN EXPERIENCE.
THE NODE HOLDS SOVEREIGNTY.
THE AGENTS DO THE WORK.
THE GATE RETURNS CONSEQUENCE TO THE HUMAN.
THE OBJECTIVE IS LGP.
```

---

## 17. Echo Forward

World Platform does not ask the human to become the orchestrator of dozens of applications and agents.

It turns that complexity downward into governed infrastructure.

The agents sense, retrieve, calculate, build, test, coordinate, and prepare.

The platform elevates what crosses delegated boundaries.

The human governs the consequential edge.

**ECHO FORWARD.**
