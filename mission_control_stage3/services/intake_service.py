"""Intake raw tasks into Stage 3 decision records (no risky execution)."""

from __future__ import annotations

from datetime import datetime
from typing import Any


DECISION_FIELDS = [
    "id",
    "title",
    "status",
    "urgency",
    "lead_office",
    "support_office",
    "needs_approval",
    "loop_count",
    "due_date",
    "missing_fields",
    "notes",
    "created_at",
    "updated_at",
]


def next_decision_id(existing: list[dict[str, str]]) -> str:
    nums = []
    for row in existing:
        raw = (row.get("id") or "").strip()
        if raw.startswith("D") and raw[1:].isdigit():
            nums.append(int(raw[1:]))
    n = max(nums, default=0) + 1
    return f"D{n:03d}"


def intake_raw_task(
    raw_text: str,
    *,
    existing: list[dict[str, str]],
    classification: dict[str, Any],
    now: str | None = None,
) -> dict[str, str]:
    """Create one decision record from a raw task + classification result."""
    stamp = now or datetime.now().replace(microsecond=0).isoformat()
    title = (raw_text or "").strip().split("\n", 1)[0][:120] or "Untitled task"
    missing = classification.get("missing_fields") or []
    if isinstance(missing, str):
        missing_s = missing
    else:
        missing_s = ";".join(missing)

    needs = "yes" if classification.get("needs_approval") else "no"
    status = "Needs Approval" if needs == "yes" else "Active"
    if missing:
        status = "Waiting"

    return {
        "id": next_decision_id(existing),
        "title": title,
        "status": status,
        "urgency": str(classification.get("urgency", "normal")),
        "lead_office": str(classification.get("lead_office", "Mission Control")),
        "support_office": str(classification.get("support_office", "Mail & Schedule")),
        "needs_approval": needs,
        "loop_count": "0",
        "due_date": str(classification.get("due_date", "")),
        "missing_fields": missing_s,
        "notes": str(classification.get("notes", raw_text.strip()[:300])),
        "created_at": stamp,
        "updated_at": stamp,
    }
