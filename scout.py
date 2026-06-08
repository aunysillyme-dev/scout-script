#!/usr/bin/env python3
"""Scouting Automation — client setup tool.

A distributable, self-contained playbook for running agent-assisted opportunity
scouting (freelance leads, public bounties, inbox triage). It ships with NO
personal data: every niche-specific value (search terms, service lanes, income
goal) is a placeholder the client fills in for their own skillset.

Two modes:

    python scout.py                  Print an agent-ready prompt. Paste it into
                                     any LLM/agent; the agent interviews the
                                     client, then scaffolds their personalized kit.

    python scout.py --interactive    Answer the questions in your terminal. The
                                     script scaffolds the filled-in Markdown kit
                                     locally (no agent required).

    python scout.py --interactive --out ./my-scout   Choose the output folder.

No third-party dependencies. Python 3.10+.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
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
        why="Drives freelance/bounty scouting queries for YOUR niche.",
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

## Files

- `CASH_PIPELINE.md` — current objective, priority order, hard rules
- `EARNINGS_LEDGER.md` — real status changes only
- `TARGET_QUEUE.md` — candidates, so stale searches are not repeated
- `BOUNTY_PIPELINE.md` — bounty sources, validation gates, action boundary
- `FREELANCE_SCOUTING_MAP.md` — your service lanes and search terms
- `SERVICE_MENU.md` — your fixed-scope offers
- `PITCH_PACK.md` — reusable pitch fragments
- `REJECT_LOG.md` — patterns to skip
- `automations/hourly-loop-prompt.md` — the recurring agent prompt
"""

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
- Algora, BountyHub, OpenCollective-style bounty pages, issue threads.
- Project-specific bounty boards.
- Maintainer-posted review or implementation bounties.

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
- SERVICE_MENU.md
- PITCH_PACK.md
- REJECT_LOG.md

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

# token -> (relative path, template)
KIT: dict[str, tuple[str, str]] = {
    "README": ("README.md", README_TMPL),
    "CASH": ("CASH_PIPELINE.md", CASH_PIPELINE_TMPL),
    "EARNINGS": ("EARNINGS_LEDGER.md", EARNINGS_LEDGER_TMPL),
    "QUEUE": ("TARGET_QUEUE.md", TARGET_QUEUE_TMPL),
    "BOUNTY": ("BOUNTY_PIPELINE.md", BOUNTY_PIPELINE_TMPL),
    "FREELANCE": ("FREELANCE_SCOUTING_MAP.md", FREELANCE_MAP_TMPL),
    "MENU": ("SERVICE_MENU.md", SERVICE_MENU_TMPL),
    "PITCH": ("PITCH_PACK.md", PITCH_PACK_TMPL),
    "REJECT": ("REJECT_LOG.md", REJECT_LOG_TMPL),
    "LOOP": ("automations/hourly-loop-prompt.md", HOURLY_LOOP_TMPL),
}


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _lines_to_bullets(value: str) -> str:
    items = [ln.strip() for ln in value.splitlines() if ln.strip()]
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


def render(answers: dict[str, str]) -> dict[str, str]:
    """Return {relative_path: rendered_content} for the whole kit."""
    # Derived, formatted placeholders.
    derived = {
        "SERVICE_LANES_TABLE": _lanes_to_rows(answers.get("SERVICE_LANES", "")),
        "SEARCH_TERMS_LIST": _lines_to_bullets(answers.get("SEARCH_TERMS", "")),
        "PLATFORMS_LIST": _lines_to_bullets(answers.get("PLATFORMS", "")),
    }

    def fill(text: str) -> str:
        for field in FIELDS:
            text = text.replace(f"[[{field.token}]]", answers.get(field.token, ""))
        for token, value in derived.items():
            text = text.replace(f"[[{token}]]", value)
        return text

    return {path: fill(tmpl) for _, (path, tmpl) in KIT.items()}


def write_kit(answers: dict[str, str], out: Path) -> list[Path]:
    written: list[Path] = []
    for rel, content in render(answers).items():
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        written.append(dest)
    return written


# --------------------------------------------------------------------------- #
# Modes
# --------------------------------------------------------------------------- #


def build_agent_prompt() -> str:
    """A ready-to-paste prompt that makes an LLM/agent interview the client."""
    q_block = "\n".join(
        f"{i}. {f.question}\n   - Why: {f.why}\n   - Example: {f.example}"
        for i, f in enumerate(FIELDS, 1)
    )
    files = "\n".join(f"- {path}" for _, (path, _) in KIT.items())
    return f"""\
You are setting up a personalized "Opportunity Scout" kit for the person you are
talking to (the client). Do NOT assume their niche, skills, or goals — those
belong to them, not to whoever shared this template.

STEP 1 — Interview the client. Ask the questions below ONE AT A TIME, wait for
each answer, and follow up until each answer is concrete and truthful. Reject
anything the client cannot actually deliver — every service lane must be real.

{q_block}

STEP 2 — Generate the kit. Produce these Markdown files, substituting the
client's answers everywhere. Keep all safety rules intact and unmodified:

{files}

STEP 3 — Safety boundary (carry into every generated file and every future run):
- Do not spend money, credits, or connects without fresh approval.
- Do not change account, legal, payment, identity, password, or security settings.
- Do not share secrets or request unnecessary private access.
- Do not accept contracts or deliver final client work before paid acceptance.
- Count revenue only when payout lands.
- Every run produces exactly one concrete outcome or a clear reason no safe
  action existed. No endless passive searching.

After generating the kit, hand the client `automations/hourly-loop-prompt.md` as
the recurring job to run their scout.
"""


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
    print("\nNext: run automations/hourly-loop-prompt.md with your agent.")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Set up a personalized Opportunity Scout kit.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run the interview in this terminal and scaffold the kit locally.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("opportunity-scout"),
        help="Output folder for --interactive (default: ./opportunity-scout).",
    )
    args = parser.parse_args(argv)

    if args.interactive:
        run_interview(args.out)
    else:
        print(build_agent_prompt())
    return 0


if __name__ == "__main__":
    sys.exit(main())
