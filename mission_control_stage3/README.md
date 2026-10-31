# Mission Control — Stage 3

Safe AI-assisted **routing and decision layer**. Upgrades Stage 2 with intake,
classification, routing, validation, reminders, live queue, daily brief, audit
trail, and an approval gate for high-risk actions.

Stage 3 **never** sends, pays, deletes, shares, or files on its own.

## Layout

```
mission_control_stage3/
  app.py
  config/office_rules.json
  config/global_rules.json
  data/*.csv
  prompts/*_prompt.txt
  agents/
  services/
```

## Quick start

```bash
cd mission_control_stage3
python3 app.py init
python3 app.py brief
python3 app.py intake --title "Pay water bill" --action pay --due-date 2026-11-05
python3 app.py request-approval --decision-id D009 --action pay --office "Money & Debt"
python3 app.py decide-approval --approval-id A001 --approve
```

## Safety rules

- Source of truth = `data/decisions.csv` (chat is coordination only)
- Live = Active / Waiting / Needs Approval → `live_decisions.csv`
- Stale → `stale_review.csv`
- High-risk (`send`, `pay`, `delete`, `share`, `file`, `government_filing`) stay behind approvals
- Max 7 approvals/day; loop ≥3 → escalate
- Only the lead office tells the user; no lane crossing
- Calendar + alarms = reminder system (`reminder_log.csv`)
- Every action appends to `audit_log.csv`

## Office rules (`config/office_rules.json`)

Each office includes: `name`, `role`, `lane`, `keywords`, `allowed_actions`,
`forbidden_without_approval`, `may_contact_user`, `default_support`, `urgency_default`.
