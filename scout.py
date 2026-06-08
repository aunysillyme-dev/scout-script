#!/usr/bin/env python3
"""Opportunity Scout — client setup + live scouting tool.

A distributable, self-contained playbook for running agent-assisted opportunity
scouting (freelance leads, public bounties, inbox triage). It ships with NO
personal data: every niche-specific value (search terms, service lanes, income
goal) is a placeholder the client fills in for their own skillset.

Modes:

    python scout.py                  Print an agent-ready prompt. Paste it into
                                     any LLM/agent; the agent interviews the
                                     client, then scaffolds their personalized kit.

    python scout.py --interactive    Answer the questions in your terminal. The
                                     script scaffolds the filled-in Markdown kit
                                     locally (no agent required).

    python scout.py --scout          Run a live scout: scan GitHub for fresh
                                     paid bounties and print a deep-link board of
                                     freelance/bounty searches for your terms.
                                     Reads your saved kit config if present.

    python scout.py --interactive --out ./my-scout   Choose the output folder.
    python scout.py --scout --config ./my-scout/scout.config.json

There are two scout engines:
  - this script's --scout mode (on-demand, local, no account), and
  - scout-worker/ (an always-on Cloudflare Worker that runs the bounty scan on
    a schedule).

No third-party dependencies. Python 3.10+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --------------------------------------------------------------------------- #
# Interview spec
#
# Each field maps to a [[TOKEN]] in the templates below. The same spec drives
# both the terminal interview and the agent prompt, so the two modes can never
# drift apart.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Field:
    token: str          # placeholder name, used as [[TOKEN]] in templates
    question: str       # what to ask the client
    why: str            # why it matters / how to answer
    example: str        # a concrete sample answer (never shipped as a default)
    multiline: bool = False


FIELDS: list[Field] = [
    Field(
        token="INCOME_GOAL",
        question="What is your first concrete income goal?",
        why="Anchors the loop on one verifiable target. Keep it small and real.",
        example="$500",
    ),
    Field(
        token="NICHE",
        question="What market or audience do you serve?",
        why="Shapes which leads and communities are worth scouting.",
        example="indie newsletter operators and small creator brands",
    ),
    Field(
        token="SKILLSET",
        question="What can you truthfully deliver today? List your real skills.",
        why="Every service lane must be something you can actually fulfill.",
        example="newsletter setup, PDF/report layout, light no-code automation",
    ),
    Field(
        token="SERVICE_LANES",
        question=(
            "List your service lanes, one per line, as: "
            "Lane | Offer | Good fit | Reject"
        ),
        why="Becomes your FREELANCE_SCOUTING_MAP table. Fixed-scope offers only.",
        example=(
            "Newsletter setup | Fixed-scope newsletter QA/template/setup | "
            "Clear assets, bounded task | Growth guarantees, account takeover"
        ),
        multiline=True,
    ),
    Field(
        token="SEARCH_TERMS",
        question="List the search terms that surface your kind of work, one per line.",
        why="Drives freelance/bounty scouting queries and deep links for YOUR niche.",
        example="beehiiv setup help\nwhite paper PDF layout\nGitHub Actions fix",
        multiline=True,
    ),
    Field(
        token="PLATFORMS",
        question="Which platforms/sources will you scout? One per line.",
        why="Limits scouting to channels you actually use and trust.",
        example="Upwork\nContra\nGitHub issue search\nAlgora",
        multiline=True,
    ),
    Field(
        token="MONITOR_EMAIL",
        question=(
            "Do you want the scout to monitor your email inbox for buyer "
            "replies, payout/rejection notices, security alerts, and leads? "
            "(yes/no — and which account)"
        ),
        why=(
            "If yes, the kit includes an inbox-monitoring prompt. Your agent "
            "connects YOUR own email and triages it: it reads only enough to "
            "classify, never deletes, and leaves anything unresolved in place."
        ),
        example="yes (Gmail)",
    ),
]


def _wants_email(answers: dict[str, str]) -> bool:
    return answers.get("MONITOR_EMAIL", "").strip().lower().startswith("y")


# --------------------------------------------------------------------------- #
# Scout sources
#
# Registry of public, niche-agnostic sources. Entries with a search template get
# one deep link per search term; board-only entries get a single link. Add your
# own marketplaces here and they appear on the generated Scout Board.
# (name, kind, search_template_with_{q}, board_url)
# --------------------------------------------------------------------------- #

SOURCE_REGISTRY: list[tuple[str, str, str | None, str | None]] = [
    ("GitHub bounties", "bounty",
     "https://github.com/search?q={q}+bounty&type=issues&state=open", None),
    ("Algora", "bounty", None, "https://algora.io/bounties"),
    ("Opire", "bounty", None, "https://app.opire.dev/"),
    ("MRWK", "bounty", None, "https://mrwk.xyz/"),
    ("Bounty.new", "bounty", None, "https://bounty.new/"),
    ("BountyHub", "bounty", None, "https://bountyhub.dev/"),
    ("Upwork", "freelance",
     "https://www.upwork.com/nx/search/jobs/?q={q}", None),
    ("Freelancer", "freelance",
     "https://www.freelancer.com/jobs/?keyword={q}", None),
    ("PeoplePerHour", "freelance",
     "https://www.peopleperhour.com/freelance-jobs?q={q}", None),
    ("Contra", "freelance", None, "https://contra.com/opportunities"),
    ("Wellfound", "freelance", None, "https://wellfound.com/jobs"),
]

# Live GitHub bounty-bot searches used by --scout. Mirrors the Worker's bounty
# defaults. (name, query, max_age_days)
SCOUT_SEARCHES: list[tuple[str, str, int]] = [
    ("algora-bot", "commenter:algora-pbc is:issue is:open comments:<10", 3),
    ("bountyhub-bot", '"bountyhub-app" is:issue is:open comments:<6', 5),
    ("bounty-label", 'label:bounty is:issue is:open comments:<8', 4),
]


# --------------------------------------------------------------------------- #
# Templates
#
# Placeholders use [[TOKEN]] so they never collide with Markdown [brackets] or
# shell/JSON braces in the embedded code blocks.
# --------------------------------------------------------------------------- #

README_TMPL = """\
# Opportunity Scout Kit

Agent-assisted scouting for legitimate, low-risk income. This kit is yours:
income goal, service lanes, and search terms are filled in for your skillset.

- **Niche:** [[NICHE]]
- **Income goal:** [[INCOME_GOAL]]
- **Skillset:** [[SKILLSET]]

## How it runs

Each run does ONE useful thing or reports why no safe action existed:

- surface a buyer reply, payout, rejection, or security notice;
- prepare a qualified freelance opportunity packet for your approval;
- submit a safe public bounty claim, review, comment, or pull request;
- send a no-cost direct pitch where allowed;
- improve a reusable sales or fulfillment artifact;
- record a material reject so the same dead end is not retried.

Never run broad passive searches forever. Every run produces a concrete
outcome or a clear reason no action was safe.

## Scout engines

- `SCOUT_BOARD.md` — ready-to-click searches for your terms across every source.
- Live bounty scan: from the repo root, run `python scout.py --scout` to scan
  GitHub for fresh paid bounties and reprint your board.
- Always-on: deploy `scout-worker/` to Cloudflare to run the bounty scan hourly.

## Files

- `CASH_PIPELINE.md` — current objective, priority order, hard rules
- `EARNINGS_LEDGER.md` — real status changes only
- `TARGET_QUEUE.md` — candidates, so stale searches are not repeated
- `BOUNTY_PIPELINE.md` — bounty sources, validation gates, action boundary
- `FREELANCE_SCOUTING_MAP.md` — your service lanes and search terms
- `SCOUT_BOARD.md` — deep-link search board for your terms
- `SERVICE_MENU.md` — your fixed-scope offers
- `PITCH_PACK.md` — reusable pitch fragments
- `REJECT_LOG.md` — patterns to skip
- `automations/hourly-loop-prompt.md` — the recurring agent prompt
[[INBOX_FILE_LINE]]"""

CASH_PIPELINE_TMPL = """\
# Cash Pipeline

## Goal

Earn the first [[INCOME_GOAL]] in legitimate, verifiable income with agent
assistance.

## Current Priority Order

1. Buyer replies, payout notices, security issues.
2. Approved freelance proposals or no-cost direct pitches.
3. Public bounty actions.
4. Qualified opportunity packets needing user approval.
5. Reusable sales or fulfillment artifact improvements.
6. Material rejects.

## Hard Rules

- Do not count revenue until payout lands.
- Do not spend credits, connects, or money without fresh approval.
- Do not accept contracts without user approval.
- Do not change identity, password, legal, payment, or security settings.
- Do not share secrets or request unnecessary private access.
- Do not deliver final client work before a paid engagement is accepted.
"""

EARNINGS_LEDGER_TMPL = """\
# Earnings Ledger

Track only real status changes: submitted, rejected, paid, closed, duplicated,
or blocked.

| Date | Lane | Source | Amount | Status | Evidence / Notes |
| --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | Freelance proposal | [platform/job id] | [amount] | Submitted | [proposal link or packet path] |
| YYYY-MM-DD | Bounty | [repo/issue/pr] | [amount] | Submitted | [public claim/review/pr link] |
| YYYY-MM-DD | Payment | [source] | [amount] | Paid | [proof link or payout notice summary] |
| YYYY-MM-DD | Reject | [source] | - | Rejected | [reason that prevents repeat work] |
"""

TARGET_QUEUE_TMPL = """\
# Target Queue

## Active Candidates

| Source | Type | Pay | Status | Next Step | Risk |
| --- | --- | --- | --- | --- | --- |

## Rejected Candidates

| Source | Type | Reject Reason | Date |
| --- | --- | --- | --- |
"""

BOUNTY_PIPELINE_TMPL = """\
# Bounty Pipeline

## Bounty Sources

- GitHub issues with explicit bounty labels or payment terms.
- Algora, MRWK, Opire, Bounty.new, BountyHub, OpenCollective-style bounty pages.
- Project-specific bounty boards.
- Maintainer-posted review or implementation bounties.

See `SOURCES.md` (repo root) for the full source list and `SCOUT_BOARD.md` for
ready-to-click searches.

## Validation Gates

- Issue is live/open.
- Bounty is explicit and payment terms are understandable.
- Claims are open or assignment rules allow action.
- Competition is low enough to justify effort.
- No already-winning PR or duplicate solution exists.
- Repo is legitimate and safe to inspect.
- Task does not require secrets, production credentials, private data, or unsafe downloads.
- Work can be verified with public code, tests, logs, or docs.
- Public action is allowed by the user's standing approval.

## Public Action Boundary

Allowed:

- concise claim comments;
- evidence-backed code reviews;
- narrow pull requests;
- clarifying questions;
- status checks using public data.

Not allowed without explicit approval:

- spending money;
- changing account settings;
- using secrets;
- claiming false credentials;
- touching production systems;
- handling regulated advice or sensitive private data.

## Useful GitHub commands (for agents with the GitHub CLI)

```sh
gh issue view ISSUE_NUMBER --repo OWNER/REPO --comments --json number,title,state,url,labels,comments,updatedAt
gh pr list --repo OWNER/REPO --state open --limit 30 --json number,title,url,author,headRefName,updatedAt,mergeable,statusCheckRollup
gh search issues '"$100" bounty' --state open --limit 20 --json repository,title,url,number,createdAt,updatedAt,labels
gh search prs 'repo:OWNER/REPO ISSUE_NUMBER' --state open --json number,title,url,author,updatedAt
```

## Public bounty action template

```md
/claim [ISSUE_NUMBER]

Action submitted: [review/comment/PR link]

Evidence:
- inspected [files or public source];
- verified [tests/checks/live state];
- checked duplicate/competition risk;
- confirmed no secrets, private data, payment settings, or account changes were used.

Payout boundary: this is pending until maintainers accept and record payment.
```
"""

FREELANCE_MAP_TMPL = """\
# Freelance Scouting Map

## Service Lanes

| Lane | Offer | Good Fit | Reject |
| --- | --- | --- | --- |
[[SERVICE_LANES_TABLE]]

## Search Terms

[[SEARCH_TERMS_LIST]]

## Sources To Scout

[[PLATFORMS_LIST]]

Ready-to-click searches for every source live in `SCOUT_BOARD.md`. The full
source list is in `SOURCES.md` at the repo root.
"""

SERVICE_MENU_TMPL = """\
# Service Menu

Fixed-scope, truthfully deliverable offers for: [[NICHE]].

Skillset: [[SKILLSET]]

For each offer keep: deliverable, what you need from the client, revision limit,
and a clear "not included" line. No spec work. No vague guarantees.
"""

PITCH_PACK_TMPL = """\
# Pitch Pack

Reusable fragments. Always truthful, fixed-scope, no unsafe access required.

## Draft Pitch

Hi [Name],

I can help with [specific deliverable] in a fixed scope:

- [deliverable 1]
- [deliverable 2]
- [deliverable 3]

I would work from [supplied assets/source material] and send [final deliverable]
with [revision/checkpoint].

No need for [unsafe access] to start; screenshots, exports, or shared source
files are enough.

## Opportunity Packet

```md
# Opportunity Packet

## Source
- Platform:
- URL / Job ID:
- Posted:
- Pay:
- Client trust:
- Proposal count:
- Cost to apply:

## Scope Fit
- What they need:
- Why this offer fits:
- What can be completed:

## Risks
- Access risk:
- Scope risk:
- Rights/payment risk:
- Competition risk:

## Recommended Action
Apply / Skip / Needs user approval.
```
"""

REJECT_LOG_TMPL = """\
# Reject Log

Record patterns to skip so the same dead end is not retried.

| Date | Source | Type | Reject Reason |
| --- | --- | --- | --- |
"""

HOURLY_LOOP_TMPL = """\
Run the opportunity-scout loop for: [[NICHE]] (goal: [[INCOME_GOAL]]).

Start with a hard-capped inbox scan for buyer replies, payout/rejection notices,
security/account warnings, bounty updates, and freelance job alerts. Read only
enough to classify actionability. Archive processed no-action notification noise
after extracting useful data. Do not archive unresolved security, payout, buyer
reply, offer, or approval-needed messages.

If a real money/security/reply/payout/rejection event exists, handle or surface
that event and stop.

If no real event exists, run exactly one active lane:

1. Present one qualified freelance candidate packet requiring user approval.
2. Submit one no-cost truthful pitch where the channel is accessible and allowed.
3. Scout or act on one clean public bounty.
4. Improve one reusable sales or fulfillment artifact.
5. Record one material reject that prevents repeat work.

Use the local files before broad search:

- CASH_PIPELINE.md
- EARNINGS_LEDGER.md
- TARGET_QUEUE.md
- BOUNTY_PIPELINE.md
- FREELANCE_SCOUTING_MAP.md
- SCOUT_BOARD.md
- SERVICE_MENU.md
- PITCH_PACK.md
- REJECT_LOG.md

To find fresh bounties, use the live scan (`python scout.py --scout`) or the
deployed scout-worker, then vet candidates against BOUNTY_PIPELINE.md before any
public action.

Safety:

- Do not spend money, credits, or connects without fresh approval.
- Do not change account, legal, payment, identity, password, or security settings.
- Do not share secrets.
- Do not accept contracts.
- Do not claim unsupported credentials, results, or guarantees.
- Do not deliver final client work before paid acceptance.
- Count revenue only when payout lands.

Notify the user only when money moved, a public action was submitted, a qualified
opportunity needs approval, a payout/rejection/security event changed status, or
user action is needed. Otherwise return a quiet status naming the concrete action
completed.
"""

INBOX_MONITORING_TMPL = """\
Monitor the inbox for: [[NICHE]] (goal: [[INCOME_GOAL]]).

You are watching the user's OWN connected email account. Use only the email
tools the user has connected. Read only enough to classify each message. Never
delete anything. Never change account or security settings.

Search recent mail (last ~2 days) for money/opportunity signals, e.g.:

    newer_than:2d (GitHub OR bounty OR PR OR issue OR review OR payout OR
    rejection OR security OR Upwork OR Freelancer OR Contra OR offer OR
    interview OR contract OR payment OR invoice)

Classify each matching message:

- Security: login warning, OAuth authorization, password/account change.
- Buyer Reply: client reply, interview, offer, contract, message.
- Payout: payment received, payout pending, rejection, dispute.
- Bounty: issue comment, PR review, maintainer request, claim status.
- Freelance Lead: job alert or marketplace lead matching the search terms.
- Noise: notification flood with no needed action.

Action rules:

- Leave unresolved security/account messages in the inbox and notify the user.
- Leave buyer replies and offers in the inbox until handled.
- Leave payout notices in the inbox until recorded in EARNINGS_LEDGER.md.
- Archive processed notification noise only after extracting useful data.
- Never delete messages unless the user explicitly asks.
- Add a Freelance Lead worth pursuing to TARGET_QUEUE.md.

Notify the user only when a security event, buyer reply, payout/rejection, or
actionable lead is found. Otherwise return a quiet count of what was triaged.
"""


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _split_lines(value: str) -> list[str]:
    return [ln.strip() for ln in value.splitlines() if ln.strip()]


def _lines_to_bullets(value: str) -> str:
    items = _split_lines(value)
    return "\n".join(f"- {item}" for item in items) or "- [add at least one]"


def _lanes_to_rows(value: str) -> str:
    rows: list[str] = []
    for ln in value.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        cells = [c.strip() for c in ln.split("|")]
        while len(cells) < 4:
            cells.append("")
        rows.append("| " + " | ".join(cells[:4]) + " |")
    return "\n".join(rows) or "| [lane] | [offer] | [good fit] | [reject] |"


def build_scout_board(search_terms: list[str]) -> str:
    """Markdown board of deep-link searches for every registered source."""
    terms = search_terms or ["add your search terms"]
    out = [
        "# Scout Board",
        "",
        "Ready-to-click searches built from your terms. Bounty platforms with no",
        "open API and freelance marketplaces are listed as boards to browse.",
        "Regenerate any time with `python scout.py --scout`.",
        "",
    ]
    for label, kind in (
        ("Bounty platforms", "bounty"),
        ("Freelance / service marketplaces", "freelance"),
    ):
        out.append(f"## {label}")
        out.append("")
        for name, src_kind, tmpl, board in SOURCE_REGISTRY:
            if src_kind != kind:
                continue
            if tmpl:
                out.append(f"**{name}**")
                out.append("")
                for term in terms:
                    q = urllib.parse.quote_plus(term)
                    out.append(f"- [{term}]({tmpl.format(q=q)})")
                out.append("")
            else:
                out.append(f"- **{name}** — {board}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def render(answers: dict[str, str]) -> dict[str, str]:
    """Return {relative_path: rendered_content} for the whole kit."""
    inbox_line = (
        "- `automations/inbox-monitoring-prompt.md` — opt-in inbox triage\n"
        if _wants_email(answers)
        else ""
    )
    derived = {
        "SERVICE_LANES_TABLE": _lanes_to_rows(answers.get("SERVICE_LANES", "")),
        "SEARCH_TERMS_LIST": _lines_to_bullets(answers.get("SEARCH_TERMS", "")),
        "PLATFORMS_LIST": _lines_to_bullets(answers.get("PLATFORMS", "")),
        "INBOX_FILE_LINE": inbox_line,
    }

    def fill(text: str) -> str:
        for field in FIELDS:
            text = text.replace(f"[[{field.token}]]", answers.get(field.token, ""))
        for token, value in derived.items():
            text = text.replace(f"[[{token}]]", value)
        return text

    files: dict[str, str] = {
        "README.md": fill(README_TMPL),
        "CASH_PIPELINE.md": fill(CASH_PIPELINE_TMPL),
        "EARNINGS_LEDGER.md": fill(EARNINGS_LEDGER_TMPL),
        "TARGET_QUEUE.md": fill(TARGET_QUEUE_TMPL),
        "BOUNTY_PIPELINE.md": fill(BOUNTY_PIPELINE_TMPL),
        "FREELANCE_SCOUTING_MAP.md": fill(FREELANCE_MAP_TMPL),
        "SCOUT_BOARD.md": build_scout_board(_split_lines(answers.get("SEARCH_TERMS", ""))),
        "SERVICE_MENU.md": fill(SERVICE_MENU_TMPL),
        "PITCH_PACK.md": fill(PITCH_PACK_TMPL),
        "REJECT_LOG.md": fill(REJECT_LOG_TMPL),
        "automations/hourly-loop-prompt.md": fill(HOURLY_LOOP_TMPL),
        "scout.config.json": json.dumps(
            {
                "niche": answers.get("NICHE", ""),
                "income_goal": answers.get("INCOME_GOAL", ""),
                "search_terms": _split_lines(answers.get("SEARCH_TERMS", "")),
                "platforms": _split_lines(answers.get("PLATFORMS", "")),
                "monitor_email": _wants_email(answers),
            },
            indent=2,
        )
        + "\n",
    }
    if _wants_email(answers):
        files["automations/inbox-monitoring-prompt.md"] = fill(INBOX_MONITORING_TMPL)
    return files


def write_kit(answers: dict[str, str], out: Path) -> list[Path]:
    written: list[Path] = []
    for rel, content in render(answers).items():
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        written.append(dest)
    return written


# --------------------------------------------------------------------------- #
# Mode: agent prompt
# --------------------------------------------------------------------------- #


def build_agent_prompt() -> str:
    """A ready-to-paste prompt that makes an LLM/agent interview the client."""
    q_block = "\n".join(
        f"{i}. {f.question}\n   - Why: {f.why}\n   - Example: {f.example}"
        for i, f in enumerate(FIELDS, 1)
    )
    return """\
You are setting up a personalized "Opportunity Scout" kit for the person you are
talking to (the client). Do NOT assume their niche, skills, or goals — those
belong to them, not to whoever shared this template.

STEP 1 — Interview the client. Ask the questions below ONE AT A TIME, wait for
each answer, and follow up until each answer is concrete and truthful. Reject
anything the client cannot actually deliver — every service lane must be real.
For the email question, only enable inbox monitoring if the client clearly opts
in with their own account.

{q_block}

STEP 2 — Generate the kit. Produce these Markdown files, substituting the
client's answers everywhere. Keep all safety rules intact and unmodified:

- README.md
- CASH_PIPELINE.md
- EARNINGS_LEDGER.md
- TARGET_QUEUE.md
- BOUNTY_PIPELINE.md
- FREELANCE_SCOUTING_MAP.md
- SCOUT_BOARD.md  (a deep-link search board built from the client's search terms,
  one link per term for GitHub/Algora/Opire/MRWK/Bounty.new/BountyHub/Upwork/
  Freelancer/PeoplePerHour/Contra/Wellfound — see SOURCES.md)
- SERVICE_MENU.md
- PITCH_PACK.md
- REJECT_LOG.md
- automations/hourly-loop-prompt.md
- automations/inbox-monitoring-prompt.md  (ONLY if the client opted into email)

Tip: `python scout.py --interactive` scaffolds every one of these for you, and
`python scout.py --scout` runs the live bounty scan + reprints the board.

STEP 3 — Wire up the scout engines:
- On-demand: `python scout.py --scout` scans GitHub for fresh paid bounties.
- Always-on: deploy scout-worker/ to the client's own Cloudflare account to run
  the bounty scan on a schedule.
- Freelance marketplaces have no open API — use the SCOUT_BOARD.md deep links.

STEP 4 — Safety boundary (carry into every generated file and every future run):
- Do not spend money, credits, or connects without fresh approval.
- Do not change account, legal, payment, identity, password, or security settings.
- Do not share secrets or request unnecessary private access.
- Do not accept contracts or deliver final client work before paid acceptance.
- Count revenue only when payout lands.
- Every run produces exactly one concrete outcome or a clear reason no safe
  action existed. No endless passive searching.

After generating the kit, hand the client `automations/hourly-loop-prompt.md` as
the recurring job to run their scout.
""".replace("{q_block}", q_block)


# --------------------------------------------------------------------------- #
# Mode: interactive interview
# --------------------------------------------------------------------------- #


def _ask(field: Field) -> str:
    print(f"\n{field.question}")
    print(f"  ({field.why})")
    print(f"  e.g. {field.example!r}")
    if field.multiline:
        print("  Enter one per line. Blank line to finish.")
        lines: list[str] = []
        while True:
            try:
                line = input("  > ")
            except EOFError:
                break
            if not line.strip():
                break
            lines.append(line)
        return "\n".join(lines)
    try:
        return input("  > ").strip()
    except EOFError:
        return ""


def run_interview(out: Path) -> None:
    print("Opportunity Scout — setup interview")
    print("Answer for YOUR niche and skillset. Nothing here is pre-filled.")
    answers = {f.token: _ask(f) for f in FIELDS}
    written = write_kit(answers, out)
    print(f"\nScaffolded {len(written)} files in {out}/:")
    for path in written:
        print(f"  - {path.relative_to(out)}")
    print("\nNext steps:")
    print("  - Run your scout:    python scout.py --scout")
    print(f"  - Run the loop:      give your agent {out}/automations/hourly-loop-prompt.md")


# --------------------------------------------------------------------------- #
# Mode: live scout
# --------------------------------------------------------------------------- #


def _load_config(config: Path | None, out: Path) -> dict:
    candidates = [config] if config else [
        out / "scout.config.json",
        Path("scout.config.json"),
    ]
    for path in candidates:
        if path and path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
    return {}


def _gh_search(query: str, token: str | None) -> list[dict]:
    params = urllib.parse.urlencode(
        {"q": query, "sort": "updated", "order": "desc", "per_page": "8"}
    )
    url = f"https://api.github.com/search/issues?{params}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "opportunity-scout-cli",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as resp:
        payload = json.load(resp)
    return payload.get("items", [])


def _payout(text: str) -> int:
    amounts = [
        int(m.replace(",", ""))
        for m in re.findall(r"\$\s?([\d,]{1,7})", text)
    ]
    return max(amounts) if amounts else 0


def _score(item: dict, payout: int) -> int:
    score = 0
    if payout >= 100:
        score += 2
    elif payout > 0:
        score += 1
    if (item.get("comments") or 0) <= 4:
        score += 1
    if not item.get("assignees"):
        score += 1
    return score


def run_scout(config: Path | None, out: Path) -> int:
    cfg = _load_config(config, out)
    terms = cfg.get("search_terms") or []

    print(build_scout_board(terms))

    print("\n# Live GitHub bounty scan\n")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("(no GITHUB_TOKEN set — using unauthenticated rate limits)\n")

    since = (datetime.now(timezone.utc) - timedelta(days=5)).date().isoformat()
    rows: list[tuple[int, int, int, str, str]] = []
    seen: set[str] = set()
    for name, query, _max_age in SCOUT_SEARCHES:
        full = f"{query} updated:>={since}"
        try:
            items = _gh_search(full, token)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"  ! search '{name}' failed: {exc}")
            continue
        for item in items:
            url = item.get("html_url", "")
            if not url or url in seen or item.get("pull_request"):
                continue
            seen.add(url)
            text = f"{item.get('title', '')}\n{item.get('body', '') or ''}"
            payout = _payout(text)
            rows.append(
                (_score(item, payout), payout, item.get("comments", 0),
                 item.get("title", "")[:70], url)
            )

    if not rows:
        print("No fresh bounty candidates found this pass (or the network is "
              "unavailable). Try again later, set GITHUB_TOKEN, or browse the "
              "board links above.")
        return 0

    rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
    print(f"Top {min(len(rows), 12)} candidates (vet against BOUNTY_PIPELINE.md "
          "before any public action):\n")
    print("| Score | Payout | Comments | Title | Link |")
    print("| ---: | ---: | ---: | --- | --- |")
    for score, payout, comments, title, url in rows[:12]:
        pay = f"${payout}" if payout else "?"
        print(f"| {score} | {pay} | {comments} | {title} | {url} |")
    return 0


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Set up and run a personalized Opportunity Scout.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run the interview in this terminal and scaffold the kit locally.",
    )
    parser.add_argument(
        "--scout",
        action="store_true",
        help="Run a live bounty scan and print the deep-link search board.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("opportunity-scout"),
        help="Output / config folder (default: ./opportunity-scout).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a scout.config.json for --scout (default: auto-detect).",
    )
    args = parser.parse_args(argv)

    if args.interactive and args.scout:
        parser.error("Choose one of --interactive or --scout, not both.")

    if args.interactive:
        run_interview(args.out)
    elif args.scout:
        return run_scout(args.config, args.out)
    else:
        print(build_agent_prompt())
    return 0


if __name__ == "__main__":
    sys.exit(main())
