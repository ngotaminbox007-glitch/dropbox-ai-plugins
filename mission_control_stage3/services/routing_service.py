"""Route decisions into live / stale queues and reminder / loop logs."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


LIVE_STATUSES = {"Active", "Waiting", "Needs Approval"}
STALE_STATUS = "Stale"
LOOP_ESCALATE_AT = 3

REMINDER_FIELDS = [
    "decision_id",
    "office",
    "reminder_type",
    "scheduled_for",
    "status",
    "created_at",
]

LOOP_FIELDS = [
    "decision_id",
    "office",
    "reason",
    "loop_count",
    "created_at",
]


def split_live_stale(
    decisions: list[dict[str, str]],
    live_statuses: list[str] | None = None,
    stale_status: str = STALE_STATUS,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    live_set = set(live_statuses or list(LIVE_STATUSES))
    live = [r for r in decisions if r.get("status") in live_set]
    stale = [r for r in decisions if r.get("status") == stale_status]
    return live, stale


def build_reminders(
    live: list[dict[str, str]], created_at: str | None = None
) -> list[dict[str, str]]:
    stamp = created_at or datetime.now().replace(microsecond=0).isoformat()
    rows: list[dict[str, str]] = []
    for item in live:
        due = (item.get("due_date") or "").strip()
        if not due:
            continue
        lead = item.get("lead_office") or "Mission Control"
        rows.append(
            {
                "decision_id": item["id"],
                "office": lead,
                "reminder_type": "due_date",
                "scheduled_for": f"{due}T09:00:00",
                "status": "scheduled",
                "created_at": stamp,
            }
        )
        try:
            due_d = date.fromisoformat(due)
            day_before = (due_d - timedelta(days=1)).isoformat()
            rows.append(
                {
                    "decision_id": item["id"],
                    "office": "Mail & Schedule",
                    "reminder_type": "alarm",
                    "scheduled_for": f"{day_before}T18:00:00",
                    "status": "scheduled",
                    "created_at": stamp,
                }
            )
        except ValueError:
            pass
    return rows


def build_loop_alerts(
    decisions: list[dict[str, str]],
    *,
    escalate_at: int = LOOP_ESCALATE_AT,
    created_at: str | None = None,
) -> list[dict[str, str]]:
    stamp = created_at or datetime.now().replace(microsecond=0).isoformat()
    alerts: list[dict[str, str]] = []
    for item in decisions:
        try:
            loops = int(item.get("loop_count") or "0")
        except ValueError:
            loops = 0
        if loops < escalate_at:
            continue
        alerts.append(
            {
                "decision_id": item["id"],
                "office": item.get("lead_office") or "Mission Control",
                "reason": f"loop_count {loops} >= {escalate_at}; escalate",
                "loop_count": str(loops),
                "created_at": stamp,
            }
        )
    return alerts


def validate_lanes(
    decisions: list[dict[str, str]], office_names: set[str]
) -> list[str]:
    warnings: list[str] = []
    for row in decisions:
        did = row.get("id", "?")
        lead = row.get("lead_office", "")
        support = row.get("support_office", "")
        if lead not in office_names:
            warnings.append(f"{did}: unknown lead_office '{lead}'")
        if support not in office_names:
            warnings.append(f"{did}: unknown support_office '{support}'")
        if lead and support and lead == support:
            warnings.append(f"{did}: lead and support must differ (no lane collapse)")
    return warnings
