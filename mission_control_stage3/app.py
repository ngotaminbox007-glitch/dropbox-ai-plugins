#!/usr/bin/env python3
"""Mission Control Stage 3 — safe AI-assisted routing and decision layer."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

STAGE_ROOT = Path(__file__).resolve().parent
if str(STAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(STAGE_ROOT))

from agents.mission_control_agent import MissionControlAgent
from agents.office_agent import OfficeAgent
from services.csv_store import write_csv
from services.intake_service import DECISION_FIELDS

CONFIG = STAGE_ROOT / "config"
DATA = STAGE_ROOT / "data"
PROMPTS = STAGE_ROOT / "prompts"

SEED_DECISIONS = [
    {
        "id": "D001",
        "title": "ETASV refresh and grab",
        "status": "Active",
        "urgency": "normal",
        "lead_office": "School & Work",
        "support_office": "Mail & Schedule",
        "needs_approval": "no",
        "loop_count": "0",
        "due_date": "2026-11-01",
        "missing_fields": "",
        "notes": "Refresh ETASV status; grab next steps. Draft only until approved.",
        "created_at": "2026-10-31T00:00:00",
        "updated_at": "2026-10-31T00:00:00",
    },
    {
        "id": "D002",
        "title": "Old HLR review",
        "status": "Stale",
        "urgency": "low",
        "lead_office": "VA Benefits",
        "support_office": "File Vault",
        "needs_approval": "no",
        "loop_count": "2",
        "due_date": "2026-10-15",
        "missing_fields": "",
        "notes": "Old Higher-Level Review item — review and archive or resolve.",
        "created_at": "2026-10-31T00:00:00",
        "updated_at": "2026-10-31T00:00:00",
    },
    {
        "id": "D003",
        "title": "Calendar reminder cleanup",
        "status": "Needs Approval",
        "urgency": "normal",
        "lead_office": "Mail & Schedule",
        "support_office": "Mission Control",
        "needs_approval": "yes",
        "loop_count": "0",
        "due_date": "2026-10-31",
        "missing_fields": "explicit_approval",
        "notes": "Clean outdated reminders; calendar + alarms are the reminder system.",
        "created_at": "2026-10-31T00:00:00",
        "updated_at": "2026-10-31T00:00:00",
    },
    {
        "id": "D004",
        "title": "Bill and subscription sweep",
        "status": "Waiting",
        "urgency": "normal",
        "lead_office": "Money & Debt",
        "support_office": "Mail & Schedule",
        "needs_approval": "yes",
        "loop_count": "1",
        "due_date": "2026-11-01",
        "missing_fields": "explicit_approval",
        "notes": "Sweep bills/subscriptions. No pay without approval.",
        "created_at": "2026-10-31T00:00:00",
        "updated_at": "2026-10-31T00:00:00",
    },
    {
        "id": "D005",
        "title": "Duplicate cleanup",
        "status": "Needs Approval",
        "urgency": "normal",
        "lead_office": "File Vault",
        "support_office": "Photo Design & Creation",
        "needs_approval": "yes",
        "loop_count": "0",
        "due_date": "2026-11-02",
        "missing_fields": "explicit_approval",
        "notes": "Flag duplicates for archive. No delete/file without approval.",
        "created_at": "2026-10-31T00:00:00",
        "updated_at": "2026-10-31T00:00:00",
    },
    {
        "id": "D006",
        "title": "Newsletter draft",
        "status": "Active",
        "urgency": "normal",
        "lead_office": "Photo Design & Creation",
        "support_office": "Mail & Schedule",
        "needs_approval": "yes",
        "loop_count": "0",
        "due_date": "2026-11-03",
        "missing_fields": "",
        "notes": "Draft only — drafts are not filings; no send without approval.",
        "created_at": "2026-10-31T00:00:00",
        "updated_at": "2026-10-31T00:00:00",
    },
    {
        "id": "D007",
        "title": "Daily brief",
        "status": "Active",
        "urgency": "normal",
        "lead_office": "Mission Control",
        "support_office": "Mail & Schedule",
        "needs_approval": "no",
        "loop_count": "0",
        "due_date": "2026-10-31",
        "missing_fields": "",
        "notes": "Top-3 brief. Chat is coordination only — log outcomes in decisions.csv.",
        "created_at": "2026-10-31T00:00:00",
        "updated_at": "2026-10-31T00:00:00",
    },
    {
        "id": "D008",
        "title": "Old ETASV reminder",
        "status": "Stale",
        "urgency": "high",
        "lead_office": "School & Work",
        "support_office": "Mail & Schedule",
        "needs_approval": "no",
        "loop_count": "3",
        "due_date": "2026-10-20",
        "missing_fields": "",
        "notes": "Looped 3 times — escalate; review and archive or resolve.",
        "created_at": "2026-10-31T00:00:00",
        "updated_at": "2026-10-31T00:00:00",
    },
]

OFFICE_CSV_FIELDS = [
    "office",
    "role",
    "lane",
    "may_contact_user",
    "default_support",
    "notes",
]

PROMPT_MAP = {
    "Mission Control": "mission_control_prompt.txt",
    "Mail & Schedule": "mail_schedule_prompt.txt",
    "Money & Debt": "money_debt_prompt.txt",
    "VA Benefits": "va_benefits_prompt.txt",
    "File Vault": "file_vault_prompt.txt",
    "School & Work": "school_work_prompt.txt",
    "Photo Design & Creation": "photo_design_prompt.txt",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_if_needed(office_rules: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    decisions_path = DATA / "decisions.csv"
    if not decisions_path.exists():
        write_csv(decisions_path, DECISION_FIELDS, SEED_DECISIONS)

    offices_path = DATA / "offices.csv"
    if not offices_path.exists():
        rows = []
        for o in office_rules.get("offices") or []:
            rows.append(
                {
                    "office": o.get("name", ""),
                    "role": o.get("role", ""),
                    "lane": o.get("lane", ""),
                    "may_contact_user": o.get("may_contact_user", "when_lead"),
                    "default_support": o.get("default_support", ""),
                    "notes": "No lane crossing; blocked actions need approval",
                }
            )
        write_csv(offices_path, OFFICE_CSV_FIELDS, rows)

    # Touch empty audit log header if missing
    audit = DATA / "audit_log.csv"
    if not audit.exists():
        write_csv(
            audit,
            ["timestamp", "actor", "action", "decision_id", "detail", "risk"],
            [],
        )


def build_mc(global_rules: dict, office_rules: dict) -> MissionControlAgent:
    mc_office = next(
        o for o in office_rules["offices"] if o["name"] == "Mission Control"
    )
    return MissionControlAgent(
        office=mc_office,
        global_rules=global_rules,
        office_rules=office_rules,
        data_dir=DATA,
        stage_root=STAGE_ROOT,
        prompt_path=PROMPTS / "mission_control_prompt.txt",
    )


def build_office_agents(global_rules: dict, office_rules: dict) -> dict[str, OfficeAgent]:
    agents: dict[str, OfficeAgent] = {}
    for o in office_rules.get("offices") or []:
        name = o["name"]
        if name == "Mission Control":
            continue
        prompt = PROMPTS / PROMPT_MAP.get(name, "")
        agents[name] = OfficeAgent(
            office=o,
            global_rules=global_rules,
            prompt_path=prompt if prompt.exists() else None,
        )
    return agents


def cmd_init(_args: argparse.Namespace) -> None:
    global_rules = load_json(CONFIG / "global_rules.json")
    office_rules = load_json(CONFIG / "office_rules.json")
    seed_if_needed(office_rules)
    mc = build_mc(global_rules, office_rules)
    now = datetime.now().replace(microsecond=0).isoformat()
    stats = mc.rebuild_queues(now=now)
    print(
        "Stage 3 ready: mission_control_stage3/ "
        f"(live={stats['live']} stale={stats['stale']} "
        f"reminders={stats['reminders']} loops={stats['loops']} "
        f"approvals={stats['approvals']})"
    )


def cmd_intake(args: argparse.Namespace) -> None:
    global_rules = load_json(CONFIG / "global_rules.json")
    office_rules = load_json(CONFIG / "office_rules.json")
    seed_if_needed(office_rules)
    mc = build_mc(global_rules, office_rules)
    now = datetime.now().replace(microsecond=0).isoformat()
    record = mc.intake(args.text, now=now)
    stats = mc.rebuild_queues(now=now)
    print(
        f"Intake OK: {record['id']} → lead={record['lead_office']} "
        f"status={record['status']} urgency={record['urgency']}"
    )
    print(
        f"Queues refreshed: live={stats['live']} stale={stats['stale']} "
        f"approvals={stats['approvals']}"
    )


def cmd_check_action(args: argparse.Namespace) -> None:
    global_rules = load_json(CONFIG / "global_rules.json")
    office_rules = load_json(CONFIG / "office_rules.json")
    agents = build_office_agents(global_rules, office_rules)
    mc_office = next(o for o in office_rules["offices"] if o["name"] == "Mission Control")
    agents["Mission Control"] = OfficeAgent(mc_office, global_rules)
    agent = agents.get(args.office)
    if not agent:
        print(f"Unknown office: {args.office}")
        sys.exit(1)
    result = agent.propose(args.action, approved=args.approved)
    print(
        f"{result['office']} action={result['action_type']} "
        f"allowed={result['allowed']} reason={result['reason']} "
        f"executed={result['executed']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mission Control Stage 3 (safe routing + decision layer)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Seed data and rebuild all queues/brief")
    p_init.set_defaults(func=cmd_init)

    p_intake = sub.add_parser("intake", help="Intake a raw task text")
    p_intake.add_argument("text", help="Raw task description")
    p_intake.set_defaults(func=cmd_intake)

    p_check = sub.add_parser(
        "check-action", help="Test whether an office action is allowed"
    )
    p_check.add_argument("--office", required=True)
    p_check.add_argument("--action", required=True)
    p_check.add_argument(
        "--approved",
        action="store_true",
        help="Simulate that approval was already granted",
    )
    p_check.set_defaults(func=cmd_check_action)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
