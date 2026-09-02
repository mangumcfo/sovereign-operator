# Gate Bridge — synthetic v0.1

Separate loopback privileged process implementing the unsealed SEE envelope against the existing
HumanApprovalGate principle. It is not part of `web/server.py` and has exactly one write route:
`POST /v1/execute`.

Current scope is deliberately narrow: one reversible `synthetic.marker.v1` handler whose envelope
must carry machine-readable `synthetic: true` and `money: false`. Requests cannot provide a command,
URL, module, function, path, or handler implementation. The bridge refuses wrong owner proof,
invalid/expired envelopes, code/spec/policy drift, unsafe identifiers, and execution-id or nonce
replay. It durably claims an envelope before effect; a crash leaves `EXECUTING` for reconciliation
and cannot silently retry.

This commit satisfies AA B1 and the buildable guard portion of B3 with fixtures. It does **not**
claim the live B2/B4–B6 acceptance path: no owner secret has been provisioned, no live service has
been started, no human disposition has occurred, and no receipt is painted in `:8722` yet.
