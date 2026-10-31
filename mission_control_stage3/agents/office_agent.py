"""Per-office agent helper — stays in lane; lead-only user contact."""

from __future__ import annotations

from services.common import PROMPTS, audit, load_office_rules, read_csv, DATA

PROMPT_FILES = {
    "Mission Control": "mission_control_prompt.txt",
    "Mail & Schedule": "mail_schedule_prompt.txt",
    "Money & Debt": "money_debt_prompt.txt",
    "VA Benefits": "va_benefits_prompt.txt",
    "File Vault": "file_vault_prompt.txt",
    "School & Work": "school_work_prompt.txt",
    "Photo Design & Creation": "photo_design_prompt.txt",
}


class OfficeAgent:
    def __init__(self, office_name: str) -> None:
        offices = {o["name"]: o for o in load_office_rules()["offices"]}
        if office_name not in offices:
            raise ValueError(f"Unknown office: {office_name}")
        self.office = offices[office_name]
        self.name = office_name
        prompt_name = PROMPT_FILES[office_name]
        self.prompt = (PROMPTS / prompt_name).read_text(encoding="utf-8")

    def prompt_text(self) -> str:
        return self.prompt

    def lane_items(self) -> list[dict[str, str]]:
        """Live items where this office is lead or support."""
        live = read_csv(DATA / "live_decisions.csv")
        rows = [
            row
            for row in live
            if row.get("lead_office") == self.name or row.get("support_office") == self.name
        ]
        audit("office_agent", "lane_items", "", f"{self.name} count={len(rows)}")
        return rows

    def may_tell_user(self, decision: dict[str, str]) -> bool:
        """Only the lead office tells the user."""
        return decision.get("lead_office") == self.name

    def assert_action_allowed(self, action: str) -> None:
        action_l = action.lower().strip()
        forbidden = {a.lower() for a in self.office.get("forbidden_without_approval", [])}
        if action_l in forbidden:
            raise PermissionError(
                f"{self.name} cannot '{action_l}' without approval. "
                "Use Mission Control approval gate."
            )
