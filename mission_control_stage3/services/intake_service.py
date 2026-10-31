"""Intake raw tasks into validated Stage 3 decision records."""

from __future__ import annotations

from . import classification_service, routing_service
from .common import (
    DATA,
    DECISION_FIELDS,
    audit,
    next_decision_id,
    now_iso,
    read_csv,
    write_csv,
)

REQUIRED_FIELDS = ("title",)


def validate_raw_task(raw: dict) -> list[str]:
    """Return missing required field names."""
    missing: list[str] = []
    for field in REQUIRED_FIELDS:
        if not str(raw.get(field, "")).strip():
            missing.append(field)
    return missing


def intake_task(raw: dict) -> dict[str, str]:
    """
    Intake a raw task dict.

    Expected keys: title (required), notes, due_date, urgency (optional),
    requested_action (optional; high-risk actions force approval).
    """
    missing = validate_raw_task(raw)
    title = str(raw.get("title", "")).strip() or "(untitled)"
    notes = str(raw.get("notes", "")).strip()
    due_date = str(raw.get("due_date", "")).strip()
    requested_action = str(raw.get("requested_action", "")).strip().lower()

    classification = classification_service.classify_task(
        title=title,
        notes=notes,
        requested_action=requested_action,
        urgency_hint=str(raw.get("urgency", "")).strip(),
    )
    routed = routing_service.assign_offices(classification)

    decisions = read_csv(DATA / "decisions.csv")
    created = now_iso()
    decision_id = next_decision_id(decisions)

    needs_approval = "yes" if classification["needs_approval"] else "no"
    status = "Needs Approval" if classification["needs_approval"] else "Active"
    if missing:
        status = "Waiting"
        needs_approval = "yes" if classification["needs_approval"] else needs_approval

    record = {
        "id": decision_id,
        "title": title,
        "status": status,
        "urgency": classification["urgency"],
        "lead_office": routed["lead_office"],
        "support_office": routed["support_office"],
        "needs_approval": needs_approval,
        "missing_fields": ",".join(missing),
        "loop_count": "0",
        "due_date": due_date,
        "notes": notes
        or f"Classified to {routed['lead_office']}; action={requested_action or 'none'}",
        "created_at": created,
        "updated_at": created,
    }

    decisions.append(record)
    write_csv(DATA / "decisions.csv", DECISION_FIELDS, decisions)
    audit(
        "intake_service",
        "intake_create",
        decision_id,
        f"lead={record['lead_office']} status={record['status']} urgency={record['urgency']}",
    )
    return record
