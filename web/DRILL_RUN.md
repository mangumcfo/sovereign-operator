# WP3 · Live Drill Run — paste-in-order on Dragon (your keyboard disposes)

Run these on Dragon. The **web surface reads and drafts; YOU dispose** every consequential act — so the
node log's POSTs are necessarily keyboard acts (the web server has **no USN-POST code path**, grep-clean).
The terminal transcript of this run **is** the evidence bundle; each block also appends to
`/tmp/wp3_evidence.txt` (which already holds the pre-captured D4/D5/D8 rows).

```bash
B=http://127.0.0.1:8421/api/v1 ; E=/tmp/wp3_evidence.txt
# preflight: node + web + model up; open the web UI in a browser at http://127.0.0.1:8722/ (Drills tab)
curl -s -o /dev/null -w "node %{http_code}\n" $B/status
```

## Drill 1 · Gate — raise → YOU dispose → receipt  (D1, D7)
```bash
echo "── D1 raise+dispose ──" | tee -a $E
# raise (your keyboard) — or copy this RUN from the web Port-draft tab:
curl -s -X POST $B/port/crossing -H 'Content-Type: application/json' \
  -d '{"target":"external-relay","instruction":{"send":"ref://drill1"}}' | tee -a $E
#   → note the crossing_id and gate_req_id from that output.
curl -s $B/breath_gate/pending | tee -a $E                      # the gate is waiting (web Gates tab shows it too)
# DISPOSE (your keyboard) — pick one:
curl -s -X POST $B/breath_gate/<gate_req_id>/deny -d '{"reason":"drill1"}' | tee -a $E     # deny
# …or sanction the Port crossing (owner-only) — this is also Drill 5:
curl -s -X POST $B/port/crossing/<crossing_id>/sanction -d '{"named_human":"operator"}' | tee -a $E
curl -s $B/breath_gate/pending | tee -a $E                      # gate now cleared (state changed by YOUR act)
```
AA checks: RUN text was verbatim (web Gates tab) · the disposition is a real `record_disposition`
(approver=owner) · a sanction returns a `crossing_root` hash (value-free receipt).

## Drill 2 · Capacity — renew/revoke verbatim  (D2)
```bash
echo "── D2 capacity ──" | tee -a $E
curl -s $B/status | python3 -c 'import sys,json;g=json.load(sys.stdin)["grants"][0];print("renew_run:",g["renew_run"]);print("revoke_run:",g["revoke_run"])' | tee -a $E
# the web Capacity tab renders these BYTE-IDENTICAL. To exercise: copy RENEW → run it (your keyboard):
#   <paste the renew_run>            # then:
curl -s $B/status | python3 -c 'import sys,json;print("expires now:",json.load(sys.stdin)["grants"][0]["expires"])' | tee -a $E
```
AA checks: rendered strings byte-diff == node's own; if you renewed, the new expiry re-derives from `/status`.

## Drill 3 · Storage / material passport — store → read → verify  (D3, D7)
```bash
echo "── D3 passport ──" | tee -a $E
H="sha256:$(echo -n 'QR-PANEL-0042' | sha256sum | cut -d' ' -f1)"   # a REAL content ref (swap for your artifact)
# STORE (your keyboard) — or copy the RUN from the web Passport tab (content_ref = $H):
curl -s -X POST $B/storage/datum -H 'Content-Type: application/json' -d "{\"content\":\"$H\",\"visibility\":\"owner\"}" | tee -a $E
#   → note the datum id.
curl -s $B/storage/datum/<id> | tee -a $E                        # read it back (owner-scoped, Merkle-bound)
curl -s -X POST $B/storage/datum/<id>/verify -d "{\"content\":\"$H\"}" | tee -a $E   # verify integrity
echo "source hash was: $H" | tee -a $E                           # re-hash matches → passport re-derivable
```
AA checks: read-back is owner-scoped · verify confirms binding · the stored hash matches the source artifact.

## Drill 4 · Corpus — PRE-CAPTURED (in $E): on-corpus cite + XRP→MISSING. Re-confirm in the web Corpus tab if you like.

## Drill 5 · Port draft — node untouched until you sanction  (D5)
Pre-captured in `$E`: the Port draft creates **nothing** in state (0 node-log lines). The *sanction* is
Drill 1's owner-only act above (a sanctioned crossing = a value-free receipt).

## Drill 6 (optional, propose-only) — draft only, zero state change
In the web Chat tab, ask e.g. *"draft a livelihood attestation for this week's Beard compute receipts,
propose-only."* It returns PROPOSE/RUN/GATE text and changes nothing. (Registry/keystore identical
before/after — AA snapshots.)

## Close the bundle  (D7, D8)
```bash
echo "── D7 receipts re-derivable ──" | tee -a $E
curl -s $B/audit/cylinders   | tee -a $E
curl -s $B/inference/receipts| tee -a $E
echo "── D8 surface stayed a secretary ──" | tee -a $E
grep -rnE 'method="POST".*8421|usn_post' ~/sovereign-operator/web/ && echo "  ✗ web POSTs the node" || echo "  ✓ web has NO USN-POST path — every POST above was YOUR keyboard" | tee -a $E
echo "bundle: $E  (+ this terminal transcript)"
```
**AA scores from `$E` + the transcript.** GREEN = drills 1–5 each ran raise/draft → **your** disposition
where consequential → re-derivable receipt, web path preferred, D7/D8 holding. No self-approve, no
kernel module, no ERP pilot.
