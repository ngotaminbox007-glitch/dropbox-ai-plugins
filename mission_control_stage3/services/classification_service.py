"""Classify raw tasks by office, urgency, and approval need (rule-based Stage 3)."""

from __future__ import annotations

from .common import audit, load_global_rules, load_office_rules

URGENCY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _score_office(text: str, keywords: list[str]) -> int:
    score = 0
    for keyword in keywords:
        if keyword.lower() in text:
            score += 1
    return score


def classify_task(
    title: str,
    notes: str = "",
    requested_action: str = "",
    urgency_hint: str = "",
) -> dict:
    """Return lead office candidate, urgency, and whether approval is required."""
    offices = load_office_rules()["offices"]
    global_rules = load_global_rules()
    high_risk = {a.lower() for a in global_rules.get("high_risk_actions", [])}

    blob = f"{title} {notes}".lower()
    scored: list[tuple[int, dict]] = []
    for office in offices:
        scored.append((_score_office(blob, office.get("keywords", [])), office))
    scored.sort(key=lambda item: item[0], reverse=True)

    best_score, best_office = scored[0]
    if best_score == 0:
        best_office = next(o for o in offices if o["name"] == "Mission Control")

    urgency = (urgency_hint or best_office.get("urgency_default") or "medium").lower()
    if urgency not in URGENCY_RANK:
        urgency = "medium"

    # Bump urgency for money / VA keywords.
    if any(k in blob for k in ("urgent", "deadline", "overdue", "today")):
        urgency = "high" if URGENCY_RANK[urgency] < URGENCY_RANK["high"] else urgency

    action = requested_action.lower().strip()
    needs_approval = action in high_risk
    if not action:
        # Infer high-risk intent from text.
        for risk in high_risk:
            if risk.replace("_", " ") in blob or risk in blob:
                needs_approval = True
                action = risk
                break

    result = {
        "office_name": best_office["name"],
        "office": best_office,
        "urgency": urgency,
        "needs_approval": needs_approval,
        "requested_action": action,
        "score": best_score,
    }
    audit(
        "classification_service",
        "classify",
        "",
        f"office={result['office_name']} urgency={urgency} needs_approval={needs_approval}",
    )
    return result
