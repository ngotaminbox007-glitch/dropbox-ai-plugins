#!/usr/bin/env python3
"""Generate Mission Control Stage 1 operational files (CSV + rules)."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGE1_DIR = ROOT / "mission_control_stage1"

LIVE_STATUSES = {"Active", "Waiting", "Needs Approval"}
STALE_STATUS = "Stale"

DECISIONS_HEADER = [
    "id",
    "title",
    "status",
    "lead_office",
    "support_office",
    "loop_count",
    "notes",
    "updated",
]

OFFICES_HEADER = [
    "office",
    "lane",
    "role",
]

OFFICES = [
    {
        "office": "Mission Control",
        "lane": "Traffic, briefs, decisions, routing",
        "role": "Chief of staff — assigns work; only lead office tells the user when MC is lead",
    },
    {
        "office": "Mail & Schedule",
        "lane": "Email drafts, calendar, alarms, reminders",
        "role": "Mail and calendar only — no send without approval",
    },
    {
        "office": "Money & Debt",
        "lane": "Bills, subscriptions, debt, payments",
        "role": "Money tracking only — no pay without approval",
    },
    {
        "office": "VA Benefits",
        "lane": "VA claims, evidence, deadlines, filings prep",
        "role": "VA prep only — drafts are not filings",
    },
    {
        "office": "File Vault",
        "lane": "Files, indexes, duplicates, vault hygiene",
        "role": "Records only — no delete/share/file without approval",
    },
    {
        "office": "School & Work",
        "lane": "School, apprenticeship, career paperwork",
        "role": "Career/school lane only",
    },
    {
        "office": "Photo Design & Creation",
        "lane": "Photos, design drafts, creative assets",
        "role": "Creative lane only — no share without approval",
    },
]

# Source of truth starter rows (Stage 1 samples).
DECISIONS = [
    {
        "id": "D001",
        "title": "ETASV refresh and grab",
        "status": "Active",
        "lead_office": "VA Benefits",
        "support_office": "File Vault",
        "loop_count": "0",
        "notes": "Refresh ETASV package; draft only until approval",
        "updated": "2026-10-30",
    },
    {
        "id": "D002",
        "title": "Old HLR review",
        "status": "Stale",
        "lead_office": "VA Benefits",
        "support_office": "File Vault",
        "loop_count": "2",
        "notes": "Old HLR pile — review then archive or resolve",
        "updated": "2026-09-01",
    },
    {
        "id": "D003",
        "title": "Calendar reminder cleanup",
        "status": "Active",
        "lead_office": "Mail & Schedule",
        "support_office": "Mission Control",
        "loop_count": "0",
        "notes": "Calendar + alarms are the reminder system",
        "updated": "2026-10-30",
    },
    {
        "id": "D004",
        "title": "Bill and subscription sweep",
        "status": "Waiting",
        "lead_office": "Money & Debt",
        "support_office": "Mail & Schedule",
        "loop_count": "1",
        "notes": "List bills/subs; no pay without approval",
        "updated": "2026-10-29",
    },
    {
        "id": "D005",
        "title": "Duplicate cleanup",
        "status": "Needs Approval",
        "lead_office": "File Vault",
        "support_office": "Mission Control",
        "loop_count": "0",
        "notes": "Flag duplicates; no delete without approval",
        "updated": "2026-10-30",
    },
    {
        "id": "D006",
        "title": "Newsletter draft",
        "status": "Active",
        "lead_office": "Photo Design & Creation",
        "support_office": "Mail & Schedule",
        "loop_count": "0",
        "notes": "Draft only — not a send",
        "updated": "2026-10-30",
    },
    {
        "id": "D007",
        "title": "Daily brief",
        "status": "Active",
        "lead_office": "Mission Control",
        "support_office": "Mail & Schedule",
        "loop_count": "0",
        "notes": "Top items for operator; max 7 approvals/day",
        "updated": "2026-10-31",
    },
    {
        "id": "D008",
        "title": "Old ETASV reminder",
        "status": "Stale",
        "lead_office": "VA Benefits",
        "support_office": "Mail & Schedule",
        "loop_count": "3",
        "notes": "Looped 3 times — escalate; review archive or resolve",
        "updated": "2026-08-15",
    },
]

RULES_TEXT = """Mission Control Stage 1 Rules
================================

Source of truth = decisions list (decisions.csv).
Chat is not the official record.

Live work
---------
Only Active, Waiting, and Needs Approval items are live.
Those rows appear in live_decisions.csv.

Stale work
----------
Stale items go to stale_review.csv.
Old items must be reviewed and archived or resolved.

Approvals and actions
---------------------
No office may send, pay, delete, share, or file without approval.
Drafts are not filings.
Max 7 approvals per day.
If an issue loops 3 times, escalate.

Offices
-------
One lead office and one support office per item.
Only the lead office tells the user.
No office crosses its lane.

Reminders
---------
Calendar + alarms are the reminder system.

Stage 1 scope
-------------
CSV files and plain text only.
No full AI automation yet.
"""


def write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    STAGE1_DIR.mkdir(parents=True, exist_ok=True)

    write_csv(STAGE1_DIR / "offices.csv", OFFICES_HEADER, OFFICES)
    write_csv(STAGE1_DIR / "decisions.csv", DECISIONS_HEADER, DECISIONS)

    live_rows = [row for row in DECISIONS if row["status"] in LIVE_STATUSES]
    stale_rows = [row for row in DECISIONS if row["status"] == STALE_STATUS]

    write_csv(STAGE1_DIR / "live_decisions.csv", DECISIONS_HEADER, live_rows)
    write_csv(STAGE1_DIR / "stale_review.csv", DECISIONS_HEADER, stale_rows)

    (STAGE1_DIR / "mission_control_rules.txt").write_text(RULES_TEXT, encoding="utf-8")

    print(
        "Stage 1 ready: mission_control_stage1/ "
        f"({len(DECISIONS)} decisions, {len(live_rows)} live, {len(stale_rows)} stale)."
    )


if __name__ == "__main__":
    main()
