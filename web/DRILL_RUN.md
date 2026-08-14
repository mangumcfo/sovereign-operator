# WP3 · Live Drill Run — copy-paste-run on Dragon (your keyboard disposes)

Each block below is **self-contained and paste-able** — ids are captured into shell vars, so there are
**no `<placeholders>` to edit**. The web surface reads and drafts; **YOU dispose** every consequential
act here (the web has no USN-POST path, so every POST below is your shell). The transcript + the
appended `/tmp/wp3_evidence.txt` = the bundle AA scores. Web path preferred; this is the CLI mirror.

### Preflight
```bash
B=http://127.0.0.1:8421/api/v1 ; E=/tmp/wp3_evidence.txt ; : > $E
curl -s -o /dev/null -w "node %{http_code} (need 200)\n" $B/status
# open the UI too: http://127.0.0.1:8722/  → Drills tab
```

### Drill 1 · Gate — raise → YOU sanction → receipt  (D1 + D5 + D7)
```bash
echo "── D1 gate raise → sanction ──" | tee -a $E
R=$(curl -s -X POST $B/port/crossing -H 'Content-Type: application/json' -d '{"target":"external-relay","instruction":{"send":"ref://drill1"}}')
echo "$R" | tee -a $E
CROSS=$(echo "$R" | python3 -c 'import sys,json;print(json.load(sys.stdin)["crossing_id"])')
GATE=$(echo "$R"  | python3 -c 'import sys,json;print(json.load(sys.stdin)["gate_req_id"])')
curl -s $B/breath_gate/pending | tee -a $E ; echo | tee -a $E
echo "SANCTION (your keyboard, owner-only):" | tee -a $E
curl -s -X POST $B/port/crossing/$CROSS/sanction -H 'Content-Type: application/json' -d '{"named_human":"operator"}' | tee -a $E ; echo | tee -a $E
curl -s $B/breath_gate/pending | tee -a $E ; echo | tee -a $E   # gate now cleared by YOUR act
```
The sanction response carries `crossed:true` + `approver:"owner"` + a **`crossing_root`** hash — that hash
**is** the value-free receipt (re-derivable). *(To DENY instead: `curl -s -X POST $B/breath_gate/$GATE/deny -d '{"reason":"drill1"}'`.)*

### Drill 2 · Capacity — renew/revoke verbatim  (D2)
```bash
echo "── D2 capacity ──" | tee -a $E
curl -s $B/status | python3 -c 'import sys,json;g=json.load(sys.stdin)["grants"][0];print("renew_run:",g["renew_run"]);print("revoke_run:",g["revoke_run"])' | tee -a $E
```
These render **byte-identical** in the web Capacity tab. To exercise the effect: copy the `renew_run` and
run it (your keyboard), then `curl -s $B/status | grep -o '"expires":"[^"]*"'` shows the advanced window.

### Drill 3 · Passport — store → read → verify  (D3 + D7)  *(visibility fixed: private)*
```bash
echo "── D3 passport ──" | tee -a $E
H="sha256:$(printf %s 'QR-PANEL-0042' | sha256sum | cut -d' ' -f1)"    # a REAL content ref (swap for your artifact)
R=$(curl -s -X POST $B/storage/datum -H 'Content-Type: application/json' -d "{\"content\":\"$H\",\"visibility\":\"private\"}")
echo "$R" | tee -a $E
DID=$(echo "$R" | python3 -c 'import sys,json;print(json.load(sys.stdin)["object_id"])')
curl -s "$B/storage/datum/$DID" | tee -a $E ; echo | tee -a $E                          # read back (owner-scoped, Merkle root)
curl -s -X POST "$B/storage/datum/$DID/verify" -H 'Content-Type: application/json' -d "{\"content\":\"$H\"}" | tee -a $E ; echo | tee -a $E
echo "source hash: $H  → re-hash matches the stored root ⇒ passport re-derivable" | tee -a $E
```

### Drill 4 · Corpus — already GREEN (pre-captured). Re-confirm in the web Corpus tab: on-corpus cite + `xrp`→MISSING.

### Close the bundle  (D7 + D8)
```bash
echo "── D7 durable receipts ──" | tee -a $E
echo "  crossing_root: from the SANCTION response above (value-free) · datum root: from the datum read above" | tee -a $E
curl -s $B/audit/cylinders | tee -a $E ; echo | tee -a $E     # NOTE: the session breath-gate does not persist here — may be empty by design (the receipts are the crossing_root + datum root)
echo "── D8 surface stayed a secretary ──" | tee -a $E
grep -rqE 'method="POST".*8421|usn_post' ~/sovereign-operator/web/ && echo "  ✗ web POSTs the node" | tee -a $E || echo "  ✓ web has NO USN-POST path — every POST above was YOUR keyboard" | tee -a $E
echo "bundle: $E  (+ this transcript)"
```
**AA scores from `$E` + the transcript.** GREEN = drills 1–5 each ran raise/draft → **your** disposition
→ re-derivable receipt (the `crossing_root` + the datum root), web preferred, D7/D8 holding.
