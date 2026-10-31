"""Approval gate — high-risk actions never execute here; they only queue."""

from __future__ import annotations

from datetime import datetime
from typing import Any


APPROVAL_FIELDS = [
    "approval_id",
    "decision_id",
    "title",
    "lead_office",
    "action_type",
    "ask",
    "priority",
    "status",
    "created_at",
]

AUDIT_FIELDS = [
    "timestamp",
    "actor",
    "action",
    "decision_id",
    "detail",
    "risk",
]


def build_approvals(
    decisions: list[dict[str, str]],
    loop_alerts: list[dict[str, str]],
    *,
    max_per_day: int = 7,
    created_at: str | None = None,
) -> list[dict[str, str]]:
    """Queue Needs Approval + escalations, capped at max_per_day."""
    stamp = created_at or datetime.now().replace(microsecond=0).isoformat()
    rows: list[dict[str, str]] = []
    n = 0

    def add(row: dict[str, str]) -> None:
        nonlocal n
        if n >= max_per_day:
            return
        n += 1
        rows.append(row)

    for item in decisions:
        if item.get("status") != "Needs Approval" and item.get("needs_approval") != "yes":
            continue
        if item.get("status") == "Stale":
            continue
        add(
            {
                "approval_id": f"A{n+1:03d}",
                "decision_id": item["id"],
                "title": item.get("title", ""),
                "lead_office": item.get("lead_office", "Mission Control"),
                "action_type": "high_risk_gate",
                "ask": f"Approve next step for: {item.get('title', '')}",
                "priority": item.get("urgency", "normal"),
                "status": "awaiting_approval",
                "created_at": stamp,
            }
        )

    for alert in loop_alerts:
        add(
            {
                "approval_id": f"A{n+1:03d}",
                "decision_id": alert["decision_id"],
                "title": f"Escalate loop {alert['decision_id']}",
                "lead_office": alert.get("office", "Mission Control"),
                "action_type": "escalate_loop",
                "ask": alert.get("reason", "Escalate repeated loop"),
                "priority": "high",
                "status": "awaiting_approval",
                "created_at": stamp,
            }
        )

    # Fix approval_id sequence after capped adds
    for i, row in enumerate(rows, start=1):
        row["approval_id"] = f"A{i:03d}"
    return rows


def is_action_allowed(
    action_type: str,
    *,
    office: dict[str, Any],
    global_rules: dict[str, Any],
    approved: bool = False,
) -> tuple[bool, str]:
    """Enforce lane + approval gate. Returns (allowed, reason)."""
    high_risk = set(global_rules.get("high_risk_actions") or [])
    allowed_free = set(global_rules.get("allowed_without_approval") or [])
    blocked = set(office.get("blocked_without_approval") or [])
    office_allowed = set(office.get("allowed_actions") or [])

    if action_type in high_risk or action_type in blocked:
        if approved:
            return True, "approved_high_risk"
        return False, "blocked_pending_approval"

    if action_type in allowed_free or action_type in office_allowed:
        return True, "allowed_safe_action"

    return False, "action_not_in_office_lane"


def audit_event(
    *,
    actor: str,
    action: str,
    decision_id: str = "",
    detail: str = "",
    risk: str = "low",
    now: str | None = None,
) -> dict[str, str]:
    return {
        "timestamp": now or datetime.now().replace(microsecond=0).isoformat(),
        "actor": actor,
        "action": action,
        "decision_id": decision_id,
        "detail": detail,
        "risk": risk,
    }
