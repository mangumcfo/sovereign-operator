"""Pure composition for the operator's Needs You feed.

The feed mints no authority and stores no state. It turns existing pending USN gates and Port
exceptions into plain human-readable cards with their provenance and exact current evidence.
"""
from __future__ import annotations

from copy import deepcopy


HOUSEHOLD_FP = "a682845eb6d5"


def _honest_kpi(port: dict | None) -> dict | None:
    """Fail closed unless Port's complete Open-node READY signal agrees."""
    if not port or not isinstance(port.get("kpi"), dict):
        return None
    kpi = deepcopy(port["kpi"])
    open_node = kpi.get("open_node")
    if not isinstance(open_node, dict):
        return kpi
    ready = (open_node.get("state") == "READY"
             and open_node.get("click") is True
             and open_node.get("fp") == HOUSEHOLD_FP)
    if not ready:
        open_node["state"] = "BLOCKED"
        open_node["click"] = False
    return kpi


def _gate_card(item: dict, dispose: dict) -> dict:
    request = item.get("request") or {}
    provenance = item.get("provenance") or {}
    gate_id = item.get("req_id") or item.get("id") or "unknown"
    action = request.get("action_class") or "governed action"
    return {
        "id": f"gate:{gate_id}",
        "source": "USN gate",
        "kind": "DECISION",
        "state": "PENDING",
        "what": action.replace("_", " "),
        "why": f"This exact act crossed the {provenance.get('boundary') or 'human'} boundary.",
        "evidence": {
            "gate_id": gate_id,
            "risk": request.get("risk_level"),
            "proposed_by": provenance.get("source") or "node",
        },
        "exact_effect": dispose.get("PROPOSE") or f"dispose gate {gate_id}",
        "disposition": "DRAFT_ONLY",
        "run_approve": dispose.get("RUN_approve"),
        "run_deny": dispose.get("RUN_deny"),
    }


def _port_card(row: dict) -> dict:
    owner = row.get("owns") or "Unknown"
    state = row.get("state") or "UNKNOWN"
    blockers = [name for name in ("open_node", "money_path", "lgp") if row.get(f"blocks_{name}")]
    if owner == "KM":
        why = "This obligation is assigned to the human principal."
    elif blockers:
        why = f"This obligation blocks {', '.join(x.replace('_', ' ') for x in blockers)}."
    else:
        why = f"The {owner} seat reports {state}; it is not progressing normally."
    return {
        "id": f"port:{row.get('obligation_id') or owner.lower()}",
        "source": "Port :8490",
        "kind": "OBLIGATION",
        "state": state,
        "what": row.get("current_obligation") or f"{owner} obligation",
        "why": why,
        "evidence": {
            "owner": owner,
            "owed_since": row.get("owed_since"),
            "last_beat": row.get("last_beat"),
            "open": row.get("open_n"),
            "total": row.get("open_total"),
            "blocks": blockers,
        },
        "exact_effect": None,
        "disposition": "OBSERVE_ONLY",
    }


def build(gates: list[dict], port: dict | None, *, node_error: str | None = None,
          port_error: str | None = None) -> dict:
    """Compose the human pile and a separate fleet projection.

    Only matters with an actual human disposition enter ``cards``. Port rows are observations, not
    approval controls, so exceptional rows remain visible under ``parked`` without paging KM.
    """
    cards = [_gate_card(x.get("gate") or {}, x.get("dispose") or {}) for x in gates]
    rows = (port or {}).get("rows") or []
    parked = [_port_card(row) for row in rows
              if row.get("state") not in {"WORKING", "DONE"}
              and not row.get("blocks_open_node")]
    priority = {"DECISION": 0, "OBLIGATION": 1}
    cards.sort(key=lambda card: (priority.get(card["kind"], 9), card["state"] != "BLOCKED", card["id"]))
    parked.sort(key=lambda card: (card["state"] != "BLOCKED", card["id"]))
    return {
        "ok": node_error is None or port_error is None,
        "count": len(cards),
        "cards": cards,
        "parked": parked,
        "feeds": {
            "node": {"ok": node_error is None, "error": node_error},
            "port": {"ok": port_error is None, "error": port_error,
                     "observed_at": (port or {}).get("ts")},
        },
        "kpi": _honest_kpi(port),
        "note": "Only matters needing your disposition appear in Needs You. Fleet observations are parked below.",
    }
