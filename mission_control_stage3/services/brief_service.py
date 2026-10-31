"""Daily brief + ops packet generation (lead office only narrative)."""

from __future__ import annotations

from datetime import datetime


def write_daily_brief(
    path,
    *,
    live: list[dict[str, str]],
    stale: list[dict[str, str]],
    loops: list[dict[str, str]],
    approvals: list[dict[str, str]],
    warnings: list[str],
    max_approvals: int,
    generated_at: str | None = None,
) -> str:
    stamp = generated_at or datetime.now().replace(microsecond=0).isoformat()
    lines = [
        "Mission Control — Daily Brief (Stage 3)",
        f"Generated: {stamp}",
        "",
        "Source of truth: data/decisions.csv + data/live_decisions.csv",
        "Chat is coordination only.",
        "No send / pay / delete / share / file without approval.",
        "Only the lead office tells the user.",
        "",
        f"Live decisions ({len(live)}) — Active / Waiting / Needs Approval",
        f"Approval gate: {len(approvals)} queued (max {max_approvals}/day)",
    ]
    if not live:
        lines.append("- (none)")
    for row in live:
        lines.append(
            f"- [{row['id']}] {row['title']} | {row.get('status')} | "
            f"urgency={row.get('urgency', 'normal')} | "
            f"lead={row.get('lead_office')} support={row.get('support_office')}"
        )

    lines.extend(["", f"Stale review ({len(stale)}) — archive or reactivate"])
    if not stale:
        lines.append("- (none)")
    for row in stale:
        lines.append(
            f"- [{row['id']}] {row['title']} | loops={row.get('loop_count', '0')} | "
            f"lead={row.get('lead_office')}"
        )

    lines.extend(["", f"Loop alerts ({len(loops)})"])
    if not loops:
        lines.append("- (none)")
    for row in loops:
        lines.append(f"- [{row['decision_id']}] {row['office']}: {row['reason']}")

    lines.extend(["", f"Approvals awaiting ({len(approvals)})"])
    if not approvals:
        lines.append("- (none)")
    for row in approvals:
        lines.append(
            f"- [{row['approval_id']}] {row['decision_id']} | {row['lead_office']} | {row['ask']}"
        )

    if warnings:
        lines.extend(["", "Validation warnings"])
        for w in warnings:
            lines.append(f"- {w}")

    lines.extend(
        [
            "",
            "Reminders: data/reminder_log.csv (calendar + alarms).",
            "Audit: data/audit_log.csv.",
        ]
    )
    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")
    return text
