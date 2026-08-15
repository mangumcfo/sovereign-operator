# Composite v0 — Skepticism-Release Week Protocol (X10)

Defined here so it starts on day one with no further design. The composite is the surface; this is the rule
for reading the week that decides whether the operator's skepticism is released. **The verdict is the owner's,
from the week, at the keyboard — the composite never issues it.**

## What counts (the only thing that counts)

A **terminal appearance** = a **T2 ceremony the owner ran at the keyboard**, confirmed on the Receipts screen:
- a **gate disposition** (approve or deny) → a durable disposition receipt (`durable_count` increments);
- a **Port sanction** → a value-free `crossing_root` receipt;
- a **storage store + verify** → a datum root that re-verifies against re-presented content.

**Nothing else counts.** Reading a screen, drafting a chip, asking the chat, installing/uninstalling an app —
none are terminal. Receipts appear only from real acts, never from asking a question.

## How the week's evidence reads (two independent sources, must agree)

1. **The Receipts screen** (`/api/receipts` → `durable_count` + the disposition list) — what the console shows.
2. **`objects.ndjson`** under the node's `SUBSTRATE_STORAGE_ROOT` — the durable ground truth, re-derivable
   offline. Every terminal appearance on the screen must have its object on disk; the two counts must match.

Each day: `durable_count` on the screen == the count of `disposition:` + `crossing:` + `datum:` objects in
`objects.ndjson` under the app's mandate. A screen number without a matching object on disk is a defect, not a
day's progress. (The records index's three states — live / MISSING / unverified — mean a listed record is never
counted as present unless the node holds it right now.)

## The rules of the week

- **Every signature is the owner's.** The composite holds no credential and executes no T2; if any terminal
  appearance in the week was not the owner's own keyboard act, the week is void. (This is why the surface still
  cannot sign — the release only means something if every signature in it was the owner's.)
- **Restarts don't reset the count.** Durable receipts survive node restarts (WP3.5/WP4); the week's tally is
  cumulative across the inevitable restarts of a multi-day run.
- **Honest degrade counts as honest.** A day the node was down reads as `unverified` on every screen — that is a
  true day of the week (the surface didn't lie), not a failed one.

## What ends the week

**The owner's word, at the keyboard.** The protocol defines the count; it does not define the threshold or the
verdict. When the owner judges the week's terminal appearances sufficient — every one their own signature, every
one re-derivable from `objects.ndjson` — the owner releases the skepticism. Nothing here, and nothing in the
composite, issues that verdict.

*(This week may or may not be the WP4 pilot's opening stretch — that is the owner's choice; the counting rule is
the same either way.)*
