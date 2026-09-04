# Running the hourly scan

The prompt: `SCAN_PROMPT.md`. It stages only — KM builds and airs.

Local hub POST `http://127.0.0.1:8799/episode/drop` is node-local.
This cloud seat cannot reach that loopback. Stage files under `streaming/readalong/drops/` until Tiger wires the cron on the operator box.

Do not call `/episode/build`, OBS, `/ctl/push`, or social clients from a scan.
