# Sealed Book Corpus → Agent-Retrievable Source of Truth — design memo (GB, 2026-08-14)

**Design only — no implement, no arm, no seal, no USN merge, no invented volume.** This memo designs how the sealed
book shelf becomes a reliable retrieval plane so the sovereign-operator (and later agents) can *speak architecture
from sealed truth, with citations*. It lives in `sovereign-operator/corpus/` as **its own folder** so it can be
split into a standalone repo later without disentangling from the operator.

**Two KM answers already fixed:** (a) attach to **sovereign-operator**, own folder; (b) **PDF binaries stay on KDP**
for the human reader — the agent retrieves from an **extracted-text + embedding index**, never the PDF.

**First principles (do not conflate):**
- **Books = sealed manuscripts** (law / teach). Immutable. The corpus is a *read-only projection* of them, never a
  second source of truth.
- **Notebook = operator working memory.** Separate plane; the corpus never writes it and never claims its authority.
- **Atlas-leads:** the catalog is what the Atlas says exists. A title with no sealed artifact (XRP) is an **explicit
  GAP**, never a hallucinated book.

---

## 1 · Inventory method (folder → catalog rows)

Deterministic join of three sources already on hand — no manual keying:

| Source | Yields |
|---|---|
| the gathered shelf folder (126 final PDFs, per series) | `series / vol / title / local_path / artifact_sha256 = sha256(pdf)` |
| `series_roadmap.yaml` | `reader_order · vol_id · title · subtitle · chapter list (n/title)` — the Atlas truth |
| **receipt registers (UNION — every built volume has one)** | **(a)** the crypto **runtime seal ledger** `seal_ledger.jsonl` — dual-signed `receipt_sha256 · artifact_sha256 · prior_receipt · sealed_utc · sig_scheme` for the co-extruded set (Mangum Executive Series (S0) V06–08, Programmable Sovereign ERP (S3) V1–V4, and all of Series 5–14); **(b)** the vault **per-series seal/validation registers** for the rest — Mangum Executive Series (S0) `_RECEIPT_LOG`/`MANIFEST_*.sha256` · Agentic AI Playbooks for Executives (S1) seal-prep/ASIN · Building the Agentic Harness (S2) `S2_REPUBLISH_MANIFEST` · Programmable Sovereign ERP (S3) `SEAL_RECEIPTS_S3` · Sovereign Token & Economic Organism (S4) `S4_VALIDATION_RECEIPTS`. **These three (Series 2–4) all carry receipts.** |

**Procedure:** walk the folder → normalize each PDF to `(series_number, vol_id)` → left-join roadmap (title/chapters)
→ left-join ledger (receipt, if sealed) → emit one **volume row** per book. Then **reconcile against the Atlas**: any
Atlas row with no folder artifact is emitted as a **GAP row**.

**The 127-vs-126 delta:** Atlas lists **127 numbered**; the folder holds **126**. The single delta is
**S0-04 "XRP"** — `status: MISSING` (unbuilt / manuscript-only, excluded from available-title lists). It appears in
the catalog as a **named gap with `path: null`, no chunks** — so a query about it returns MISSING, never a fabrication.
**Receipt/seal-id is recoverable for every one of the 126 built volumes** via the union of registers above — **Building the Agentic Harness (S2), Programmable Sovereign ERP (S3), and Sovereign Token & Economic Organism (S4) included.** The
only book with no receipt is the XRP GAP (it is unbuilt). The catalog records **which register**
each receipt came from — a crypto dual-signed `receipt_sha256` (runtime ledger) reads differently from a vault
seal/validation record; both are honest citations, so the register is shown.

---

## 2 · Recommended architecture (v1)

Text source: **`pdftotext` over the sealed PDF** — the PDF is the seal-anchored artifact, so extracted chunks bind to
its `artifact_sha256` and to its `receipt_ref` (present for **every** built volume — Series 2–4 included — via the register
union in §1). Extracted text lives **private in the corpus folder**; the PDF stays KDP-side.

**Catalog schema (two tables + a gap table):**

*volumes*
| field | note |
|---|---|
| `series_number · series_name · press_track` | canonical name (full-name law) |
| `vol_id · reader_order · title · subtitle` | from roadmap |
| `tier` | `teach` (Series 0–1) · `spec` (Series 2–4) · `sealed` (Series 5–14) |
| `seal_status` | `sealed · published · spec · teach · MISSING` |
| `receipt_ref · receipt_register · artifact_sha256 · sealed_utc` | present for **every built volume**; `receipt_register` ∈ {`runtime-seal` (crypto dual-signed) · `vault-seal`/`validation`} |
| `local_path` | private; **never** shipped public |
| `chapter_count · catalog_gen` | provenance |

*chunks*
| field | note |
|---|---|
| `chunk_id` | **content-addressed** = `sha256(normalized_text)` → idempotent re-index |
| `vol_id · chapter_n · chapter_title` | citation anchors |
| `text · token_count · char_offset` | the sealed prose slice |
| `embedding_ref · catalog_gen` | vector store key |

*gaps* — `atlas_row · reason · status=MISSING` (e.g. XRP).

**Chunking rules:** chapter-aware. Sealed volumes carry explicit chapters (`ch1…chN`, ~8 in the sealed-runtime volumes). One chunk ≈ one
chapter, sub-split to ~800–1,200 tokens with ~15% overlap, **never crossing a chapter boundary**. Each chunk keeps
its chapter/beat header so a retrieved slice is self-citing.

**Citation format (the whole point):**
`[Full Production ERP (Series 5) · Vol 5 · Ch 3 · seal 80bf44d0]` — i.e. **series (canonical name) · volume ·
chapter · receipt-prefix**. A receipt is shown for **every built volume** (with its register — `runtime-seal` vs
`vault-seal`); only the XRP GAP has none.

---

## 3 · RAG vs graph vs hybrid — pick for ~126 long volumes

**v1 = metadata-filtered hybrid RAG** (dense embeddings **+** sparse BM25), no graph.
- **Why:** the v1 job is *"answer architecture from sealed text, with a citation"* — that is retrieval, not traversal.
  126 vols × ~8 ch × ~2 sub ≈ **~2,000 chunks** — trivial for a local vector store (e.g. sqlite-vec / FAISS); no
  infra justification for a graph DB yet.
- **Hybrid, not pure-dense:** sealed prose is full of exact terms (`money_path`, `refuse_recognition`, fence names,
  receipt ids). BM25 guarantees exact-term recall dense vectors miss; dense catches paraphrase. Fuse the two.
- **Metadata pre-filter first** (series/tier/sealed-only/chapter), then rank — so an agent can scope to *sealed law*
  and exclude teach/spec when it needs authority.

**Graph edges wait for v1.1** (once retrieval is trusted): capability → `sealed_home` (from the ratified card home
map) · cross-volume forward-home citations · fence → source-volume lineage · series build-order. Graph adds
*"trace the relationship / lineage,"* which is a different question than *"quote the law."*

---

## 4 · Agent tool surface (signatures only — read-only)

```
corpus_search(query: str, filters?: {series?, tier?, sealed_only?, vol?, chapter?}, k?: int)
    -> [{ chunk_id, text, citation, score }]

corpus_get(series: int, vol: int, chapter?: int)
    -> { text, citation, seal_status }  |  { status: "MISSING", reason }

corpus_homes(capability: str)                 # e.g. "clean exit", "port"
    -> [{ capability, sealed_home_citation }] # from the ratified card home map

corpus_status(series?: int, vol?: int)
    -> [ volume_row ]                          # tier, seal_status, GAP flags
```

**Contract (AA verifies this):** **cite-or-refuse** — every substantive answer carries a citation or the tool returns
MISSING. **No-invent-gap** — `corpus_get(0, 4)` (XRP) returns `{status: MISSING, reason: "S0-04 XRP unbuilt — Atlas
gap, not a book"}`, never prose. Deny anything **not in the catalog**. Read-only: no write path exists.

---

## 5 · Update / refresh (extend, never rewrite history)

- **Deterministic regenerate** from `(folder + roadmap + ledger)`; the catalog stamps `generated_from` = folder
  digest · roadmap sha · ledger tip, and a monotonic `catalog_gen`.
- **Content-addressed chunk ids** (`sha256(text)`) make re-index **idempotent** — unchanged chapters keep their ids
  and embeddings; nothing is recomputed or rewritten.
- **New seal:** add that volume's rows + chunks under the next `catalog_gen`. Prior chunks untouched.
- **Reseal / revised edition:** only the changed chapters get new `chunk_id`s; superseded chunks are **tombstoned**
  (marked `superseded_by`), never deleted — the history of what was cited stays auditable.
- The corpus never edits a book; a book change flows *in* from a new seal, one direction only.

---

## 6 · Non-goals (hard)
- **No rewriting the books** — the corpus is a projection, immutable-source-in.
- **No "AI summary shelf" as authority** — summaries may be *generated for reading*, but the citation is always the
  **sealed chunk**, never the summary. A summary never outranks sealed text.
- **No kernel imports · no key custody · no USN merge** — the corpus is read-only retrieval, not a node capability;
  it holds no keys and arms nothing.
- **No public exposure of sealed prose** — PDFs stay KDP; extracted text stays private in the operator's corpus folder.

---

## 7 · Open questions for KM (≤5; 3 already answered ✓)
*Answered: attach to sovereign-operator ✓ · own folder ✓ · PDFs stay KDP, agent retrieves the text index ✓.*

1. **Embedding model — local-only?** Recommend a local open model (e.g. a bge/gte-class embedder) run on operator
   iron, **no cloud embedding API** (sovereignty: sealed prose never leaves your machine). Confirm.
2. **Index visibility.** The *derived* chunk text and vectors — private-only in the operator repo (never public / never
   USN substrate), same posture as the PDFs? (Recommend yes.)
3. **Scope.** Index all 126 (tag `teach/spec/sealed`), or **sealed-runtime only (Series 5–14)** with teach/spec as
   citation-only stubs? Recommend all-with-tier so the agent can prefer sealed law but still cite a teach book.
4. **Citation floor.** Is **chapter-level** citation enough for v1, or do you want **beat/paragraph** anchors (finer,
   higher build cost)? Recommend chapter for v1, beat in v1.1.
5. **XRP gap posture.** Leave XRP as a permanent MISSING row until/unless it is built, or drop it from the catalog
   entirely? Recommend keep-as-MISSING (atlas-leads honesty).

---

## 8 · Suggested owners
- **GB** — catalog ↔ Atlas alignment (the 127-vs-126 delta, tiers, `sealed_home` map for `corpus_homes`), citation format.
- **Tiger** — index build: extract → chunk → embed → the read-only tool surface, in `sovereign-operator/corpus/`.
- **AA** — verify **cite-or-refuse / no-invent-gap** (XRP returns MISSING; every answer cites; nothing outside the
  catalog answers), and that no key/kernel/USN surface was touched.

**STOP — design only. No arm, no seal, no build.** ∞Δ∞
