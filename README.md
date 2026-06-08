# Opportunity Scout

A sanitized, template-driven system for **agent-assisted opportunity scouting** — finding legitimate, low-risk income signals (freelance leads, public bounties, inbox triage) and moving exactly one safe action forward per run.

This repo ships with **no personal data**. Every niche-specific value (income goal, service lanes, search terms) is a placeholder the client fills in for their own skillset. Bring it to your LLM or AI agent and it interviews you, builds your personalized kit, and runs the same scouting process for *your* niche.

## Quick start

```bash
python scout.py                 # print an agent-ready prompt (paste into any LLM/agent)
python scout.py --interactive   # answer questions in your terminal; scaffolds the kit locally
python scout.py --scout         # run a live bounty scan + print your deep-link search board
python scout.py --interactive --out ./my-scout   # choose the output folder
```

No dependencies. Python 3.10+.

## Three modes

| Mode | What it does |
| --- | --- |
| **Agent prompt** (default) | Prints a ready-to-paste prompt. Feed it to an LLM/agent; it interviews the client one question at a time, then scaffolds their personalized Markdown kit and wires up the scout engines. |
| **Interactive** (`--interactive`) | Runs the interview in your terminal and writes the filled-in kit locally. No agent required. |
| **Scout** (`--scout`) | Scans GitHub live for fresh paid bounties and prints a deep-link board of searches across every source, built from your saved terms. |

All three are driven by the same interview spec and source registry, so they never drift apart.

## Two scout engines

The interview builds the ledgers and pitch templates. These two engines do the actual scouting:

- **On-demand (Python):** `python scout.py --scout` — scans GitHub bounty signals (Algora / BountyHub / Opire / labels), scores and ranks candidates, and reprints your freelance + bounty deep-link board. No account needed.
- **Always-on (Cloudflare Worker):** `scout-worker/` — the same bounty scan running on an hourly cron, with optional KV persistence. Deploy it to your own free Cloudflare account. Ships with no secrets; you supply a `GITHUB_TOKEN` as a Worker secret.

Freelance marketplaces (Upwork, Contra, Freelancer, PeoplePerHour, Wellfound) have no open scouting API, so the scout produces pre-filled **search links** for each of your terms instead of scraping them. See [`SOURCES.md`](SOURCES.md).

## Email monitoring (opt-in)

The interview asks whether you want the scout to watch your inbox for buyer replies, payout/rejection notices, security alerts, and leads. If you opt in (with **your own** account), the kit includes `automations/inbox-monitoring-prompt.md`: your agent reads only enough to classify, never deletes, and leaves anything unresolved in place.

## What it generates

A folder of Markdown files the client (or their agent) uses to run the loop:

- `CASH_PIPELINE.md` — objective, priority order, hard rules
- `EARNINGS_LEDGER.md` — real status changes only
- `TARGET_QUEUE.md` — candidates, so stale searches aren't repeated
- `BOUNTY_PIPELINE.md` — bounty sources, validation gates, action boundary
- `FREELANCE_SCOUTING_MAP.md` — the client's service lanes and search terms
- `SCOUT_BOARD.md` — ready-to-click search links for every source
- `SERVICE_MENU.md`, `PITCH_PACK.md`, `REJECT_LOG.md`
- `scout.config.json` — your terms, read back by `--scout`
- `automations/hourly-loop-prompt.md` — the recurring agent prompt
- `automations/inbox-monitoring-prompt.md` — only if you opt into email

## Safety boundary

Carried into every generated file and every run:

- No spending money, credits, or connects without fresh approval.
- No account, legal, payment, identity, password, or security changes.
- No sharing secrets or requesting unnecessary private access.
- No accepting contracts or delivering final work before paid acceptance.
- Revenue counts only when payout lands.
- Each run produces one concrete outcome or a clear reason no safe action existed.

The scout engines only **read** public data and only ever **report** — they never claim work, comment, open PRs, or touch your accounts.

## Files

- `scout.py` — the setup tool + on-demand scout engine
- `scout-worker/` — the always-on Cloudflare Worker bounty scout
- `SOURCES.md` — the full list of bounty + freelance + inbox sources
- `SCOUTING_AUTOMATION_PRODUCT_PLAYBOOK.md` — the sanitized source playbook the tool is built from
