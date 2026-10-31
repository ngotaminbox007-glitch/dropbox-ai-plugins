"""Classify raw tasks by office, urgency, and missing fields."""

from __future__ import annotations

import re
from typing import Any


HIGH_RISK_HINTS = [
    "send",
    "pay",
    "delete",
    "share",
    "file to",
    "filing",
    "submit",
    "mail certified",
    "freeze credit",
]

URGENT_HINTS = ["urgent", "asap", "today", "overdue", "deadline", "due"]


def _score_office(text: str, office: dict[str, Any]) -> int:
    lower = text.lower()
    score = 0
    for kw in office.get("keywords") or []:
        if kw.lower() in lower:
            score += 2 if len(kw) > 4 else 1
    return score


def classify_task(raw_text: str, office_rules: dict[str, Any]) -> dict[str, Any]:
    """Return lead/support offices, urgency, approval need, missing fields."""
    text = (raw_text or "").strip()
    offices = office_rules.get("offices") or []
    scored = sorted(
        (( _score_office(text, o), o) for o in offices),
        key=lambda x: x[0],
        reverse=True,
    )
    best_score, lead = scored[0] if scored else (0, {"name": "Mission Control", "default_support": "Mail & Schedule"})
    if best_score == 0:
        lead = next(
            (o for o in offices if o.get("name") == "Mission Control"),
            lead,
        )

    lead_name = lead.get("name", "Mission Control")
    support = lead.get("default_support") or "Mail & Schedule"
    if support == lead_name:
        support = "Mail & Schedule" if lead_name != "Mail & Schedule" else "Mission Control"

    lower = text.lower()
    urgency = "high" if any(h in lower for h in URGENT_HINTS) else "normal"
    needs_approval = any(h in lower for h in HIGH_RISK_HINTS)

    missing: list[str] = []
    if not re.search(r"\d{4}-\d{2}-\d{2}", text):
        # due date helpful but not always required
        if any(h in lower for h in ("due", "deadline", "by ")):
            missing.append("due_date")
    if needs_approval and "approve" not in lower and "yes-" not in lower:
        missing.append("explicit_approval")

    due_match = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    due_date = due_match.group(1) if due_match else ""

    notes = f"Classified to {lead_name} (score={best_score})."
    if needs_approval:
        notes += " High-risk language detected — approval required before execute."

    return {
        "lead_office": lead_name,
        "support_office": support,
        "urgency": urgency,
        "needs_approval": needs_approval,
        "missing_fields": missing,
        "due_date": due_date,
        "notes": notes,
        "score": best_score,
    }
