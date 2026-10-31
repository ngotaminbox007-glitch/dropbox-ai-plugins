"""Office agent — stays in lane; never executes high-risk actions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.approval_service import is_action_allowed


class OfficeAgent:
    def __init__(
        self,
        office: dict[str, Any],
        global_rules: dict[str, Any],
        prompt_path: Path | None = None,
    ) -> None:
        self.office = office
        self.global_rules = global_rules
        self.prompt = ""
        if prompt_path and prompt_path.exists():
            self.prompt = prompt_path.read_text(encoding="utf-8").strip()

    @property
    def name(self) -> str:
        return str(self.office.get("name", "Unknown"))

    def can_tell_user(self, *, is_lead: bool) -> bool:
        mode = self.office.get("may_contact_user", "when_lead")
        if mode == "yes":
            return True
        return bool(is_lead and mode == "when_lead")

    def propose(self, action_type: str, *, approved: bool = False) -> dict[str, Any]:
        ok, reason = is_action_allowed(
            action_type,
            office=self.office,
            global_rules=self.global_rules,
            approved=approved,
        )
        return {
            "office": self.name,
            "action_type": action_type,
            "allowed": ok,
            "reason": reason,
            "executed": False,  # Stage 3 never auto-executes risky work
        }
