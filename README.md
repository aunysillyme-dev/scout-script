# Opportunity Scout

A sanitized, template-driven setup tool for **agent-assisted opportunity scouting** — finding legitimate, low-risk income signals (freelance leads, public bounties, inbox triage) and moving exactly one safe action forward per run.

This repo ships with **no personal data**. Every niche-specific value (income goal, service lanes, search terms) is a placeholder the client fills in for their own skillset.

## Quick start

```bash
python scout.py                 # print an agent-ready prompt (paste into any LLM/agent)
python scout.py --interactive   # answer questions in your terminal; scaffolds the kit locally
python scout.py --interactive --out ./my-scout   # choose the output folder
```

No dependencies. Python 3.10+.

## Two modes

| Mode | What it does |
| --- | --- |
| **Agent prompt** (default) | Prints a ready-to-paste prompt. Feed it to an LLM/agent; the agent interviews the client one question at a time, then scaffolds their personalized Markdown kit. |
| **Interactive** (`--interactive`) | Runs the interview in your terminal and writes the filled-in kit locally. No agent required. |

Both modes are driven by the same interview spec, so they never drift apart.

## What it generates

A folder of Markdown files the client (or their agent) uses to run the loop:

- `CASH_PIPELINE.md` — objective, priority order, hard rules
- `EARNINGS_LEDGER.md` — real status changes only
- `TARGET_QUEUE.md` — candidates, so stale searches aren't repeated
- `BOUNTY_PIPELINE.md` — bounty sources, validation gates, action boundary
- `FREELANCE_SCOUTING_MAP.md` — the client's service lanes and search terms
- `SERVICE_MENU.md`, `PITCH_PACK.md`, `REJECT_LOG.md`
- `automations/hourly-loop-prompt.md` — the recurring agent prompt

## Safety boundary

Carried into every generated file and every run:

- No spending money, credits, or connects without fresh approval.
- No account, legal, payment, identity, password, or security changes.
- No sharing secrets or requesting unnecessary private access.
- No accepting contracts or delivering final work before paid acceptance.
- Revenue counts only when payout lands.
- Each run produces one concrete outcome or a clear reason no safe action existed.

## Files

- `scout.py` — the setup tool
- `SCOUTING_AUTOMATION_PRODUCT_PLAYBOOK.md` — the sanitized source playbook the tool is built from
