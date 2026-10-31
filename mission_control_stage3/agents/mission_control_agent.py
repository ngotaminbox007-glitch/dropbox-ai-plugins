"""Mission Control agent — owns intake, routing, brief, approval gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.office_agent import OfficeAgent
from services.approval_service import (
    APPROVAL_FIELDS,
    AUDIT_FIELDS,
    audit_event,
    build_approvals,
)
from services.brief_service import write_daily_brief
from services.classification_service import classify_task
from services.csv_store import append_csv, read_csv, write_csv
from services.intake_service import DECISION_FIELDS, intake_raw_task
from services.routing_service import (
    LOOP_FIELDS,
    REMINDER_FIELDS,
    build_loop_alerts,
    build_reminders,
    split_live_stale,
    validate_lanes,
)


class MissionControlAgent(OfficeAgent):
    def __init__(
        self,
        office: dict[str, Any],
        global_rules: dict[str, Any],
        office_rules: dict[str, Any],
        data_dir: Path,
        stage_root: Path,
        prompt_path: Path | None = None,
    ) -> None:
        super().__init__(office, global_rules, prompt_path)
        self.office_rules = office_rules
        self.data_dir = data_dir
        self.stage_root = stage_root

    def intake(self, raw_text: str, now: str | None = None) -> dict[str, str]:
        decisions_path = self.data_dir / "decisions.csv"
        existing = read_csv(decisions_path)
        classification = classify_task(raw_text, self.office_rules)
        record = intake_raw_task(
            raw_text, existing=existing, classification=classification, now=now
        )
        existing.append(record)
        write_csv(decisions_path, DECISION_FIELDS, existing)
        append_csv(
            self.data_dir / "audit_log.csv",
            AUDIT_FIELDS,
            audit_event(
                actor="Mission Control",
                action="intake",
                decision_id=record["id"],
                detail=f"Classified lead={record['lead_office']}",
                risk="low",
                now=now,
            ),
        )
        return record

    def rebuild_queues(self, now: str | None = None) -> dict[str, Any]:
        decisions = read_csv(self.data_dir / "decisions.csv")
        offices = {
            o["name"] for o in (self.office_rules.get("offices") or []) if o.get("name")
        }
        live_statuses = list(self.global_rules.get("live_statuses") or [])
        stale_status = str(self.global_rules.get("stale_status") or "Stale")
        escalate_at = int(self.global_rules.get("loop_escalate_at") or 3)
        max_approvals = int(self.global_rules.get("max_approvals_per_day") or 7)

        warnings = validate_lanes(decisions, offices)
        live, stale = split_live_stale(
            decisions, live_statuses=live_statuses, stale_status=stale_status
        )
        reminders = build_reminders(live, created_at=now)
        loops = build_loop_alerts(decisions, escalate_at=escalate_at, created_at=now)
        approvals = build_approvals(
            decisions, loops, max_per_day=max_approvals, created_at=now
        )

        write_csv(self.data_dir / "live_decisions.csv", DECISION_FIELDS, live)
        write_csv(self.data_dir / "stale_review.csv", DECISION_FIELDS, stale)
        write_csv(self.data_dir / "reminder_log.csv", REMINDER_FIELDS, reminders)
        write_csv(self.data_dir / "loop_alerts.csv", LOOP_FIELDS, loops)
        write_csv(self.data_dir / "approvals.csv", APPROVAL_FIELDS, approvals)

        write_daily_brief(
            self.stage_root / "daily_brief.txt",
            live=live,
            stale=stale,
            loops=loops,
            approvals=approvals,
            warnings=warnings,
            max_approvals=max_approvals,
            generated_at=now,
        )

        append_csv(
            self.data_dir / "audit_log.csv",
            AUDIT_FIELDS,
            audit_event(
                actor="Mission Control",
                action="rebuild_queues",
                detail=(
                    f"live={len(live)} stale={len(stale)} "
                    f"reminders={len(reminders)} loops={len(loops)} "
                    f"approvals={len(approvals)}"
                ),
                risk="low",
                now=now,
            ),
        )
        return {
            "live": len(live),
            "stale": len(stale),
            "reminders": len(reminders),
            "loops": len(loops),
            "approvals": len(approvals),
            "warnings": warnings,
        }
