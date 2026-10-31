"""Approval gate for high-risk actions. Max N approvals per day."""

from __future__ import annotations

from .common import (
    APPROVAL_FIELDS,
    DATA,
    DECISION_FIELDS,
    audit,
    load_global_rules,
    now_iso,
    read_csv,
    write_csv,
)


def _today_prefix() -> str:
    return now_iso()[:10]


def approvals_used_today() -> int:
    rows = read_csv(DATA / "approvals.csv")
    today = _today_prefix()
    return sum(
        1
        for row in rows
        if row.get("status") == "approved"
        and (row.get("decided_at") or "").startswith(today)
    )


def request_approval(
    decision_id: str, action: str, office: str, notes: str = ""
) -> dict[str, str]:
    """Queue a high-risk action behind the approval gate (does not execute it)."""
    rules = load_global_rules()
    high_risk = {a.lower() for a in rules.get("high_risk_actions", [])}
    action_l = action.lower().strip()
    if action_l not in high_risk:
        raise ValueError(
            f"Action '{action}' is not high-risk; only high-risk actions use the gate."
        )

    decisions = {row["id"]: row for row in read_csv(DATA / "decisions.csv")}
    if decision_id not in decisions:
        raise ValueError(f"Unknown decision_id: {decision_id}")

    approvals = read_csv(DATA / "approvals.csv")
    approval_id = f"A{len(approvals) + 1:03d}"
    row = {
        "approval_id": approval_id,
        "decision_id": decision_id,
        "action": action_l,
        "office": office,
        "status": "pending",
        "requested_at": now_iso(),
        "decided_at": "",
        "notes": notes or "Awaiting operator approval; action not executed",
    }
    approvals.append(row)
    write_csv(DATA / "approvals.csv", APPROVAL_FIELDS, approvals)

    # Mark decision Needs Approval.
    all_decisions = read_csv(DATA / "decisions.csv")
    for item in all_decisions:
        if item["id"] == decision_id:
            item["status"] = "Needs Approval"
            item["needs_approval"] = "yes"
            item["updated_at"] = now_iso()
            break
    write_csv(DATA / "decisions.csv", DECISION_FIELDS, all_decisions)

    audit(
        "approval_service",
        "request_approval",
        decision_id,
        f"{approval_id} action={action_l} office={office}",
    )
    return row


def decide_approval(approval_id: str, approve: bool, notes: str = "") -> dict[str, str]:
    """
    Record approve/deny. Never executes send/pay/delete/share/file.
    Enforces max approvals per day.
    """
    rules = load_global_rules()
    max_per_day = int(rules.get("max_approvals_per_day", 7))
    approvals = read_csv(DATA / "approvals.csv")
    target = None
    for row in approvals:
        if row.get("approval_id") == approval_id:
            target = row
            break
    if target is None:
        raise ValueError(f"Unknown approval_id: {approval_id}")
    if target.get("status") != "pending":
        raise ValueError(f"Approval {approval_id} already {target.get('status')}")

    if approve and approvals_used_today() >= max_per_day:
        raise ValueError(
            f"Max {max_per_day} approvals per day reached. Park or wait until tomorrow."
        )

    target["status"] = "approved" if approve else "denied"
    target["decided_at"] = now_iso()
    if notes:
        target["notes"] = notes
    else:
        target["notes"] = (
            "Approved — operator must still perform the action; Stage 3 does not send/pay/file."
            if approve
            else "Denied — action blocked."
        )
    write_csv(DATA / "approvals.csv", APPROVAL_FIELDS, approvals)
    audit(
        "approval_service",
        "decide_approval",
        target.get("decision_id", ""),
        f"{approval_id} -> {target['status']}",
    )
    return target
