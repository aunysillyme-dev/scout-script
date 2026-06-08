# Scouting Automation Product Playbook

This is a sanitized template for running agent-assisted opportunity scouting.
It is designed for an LLM, coding agent, or automation worker that can read
email, browse public sites, inspect GitHub, update local Markdown ledgers, and
optionally post safe public actions.

Do not include private account details, payment information, passwords, tokens,
client data, unpublished strategy, wallet addresses, or personal inbox history
in a shared copy of this file.

## What This System Does

The automation runs a recurring loop that looks for legitimate, low-risk money
signals and moves exactly one useful action forward per run.

Valid outcomes:

- a buyer reply, payout, rejection, or security notice surfaced to the user;
- a qualified freelance opportunity packet prepared for user approval;
- a safe public bounty claim, review, comment, or pull request submitted;
- a no-cost direct pitch sent where allowed;
- a ready-to-send packet created with the exact blocker;
- a reusable sales or fulfillment artifact improved;
- a material reject recorded to prevent repeated dead ends.

The system should not run broad passive searches forever. Every run should
produce a concrete outcome or a clear reason no action was safe.

## Recommended File Kit

Create a folder for the automation and add these Markdown files:

```text
opportunity-scout/
  README.md
  CASH_PIPELINE.md
  EARNINGS_LEDGER.md
  TARGET_QUEUE.md
  BOUNTY_PIPELINE.md
  FREELANCE_SCOUTING_MAP.md
  SERVICE_MENU.md
  PITCH_PACK.md
  REJECT_LOG.md
  automations/
    inbox-triage-prompt.md
    bounty-scout-prompt.md
    freelance-scout-prompt.md
    hourly-loop-prompt.md
```

### CASH_PIPELINE.md

Track the current money objective, active lanes, allowed actions, and blocked
actions.

Template:

```md
# Cash Pipeline

## Goal

Earn the first [AMOUNT] in legitimate, verifiable income with agent assistance.

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
```

### EARNINGS_LEDGER.md

Track only real status changes: submitted, rejected, paid, closed, duplicated,
or blocked.

Template:

```md
# Earnings Ledger

| Date | Lane | Source | Amount | Status | Evidence / Notes |
| --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | Freelance proposal | [platform/job id] | [amount] | Submitted | [proposal link or packet path] |
| YYYY-MM-DD | Bounty | [repo/issue/pr] | [amount] | Submitted | [public claim/review/pr link] |
| YYYY-MM-DD | Payment | [source] | [amount] | Paid | [proof link or payout notice summary] |
| YYYY-MM-DD | Reject | [source] | - | Rejected | [reason that prevents repeat work] |
```

### TARGET_QUEUE.md

Track candidate opportunities and avoid repeating stale searches.

Template:

```md
# Target Queue

## Active Candidates

| Source | Type | Pay | Status | Next Step | Risk |
| --- | --- | --- | --- | --- | --- |

## Rejected Candidates

| Source | Type | Reject Reason | Date |
| --- | --- | --- | --- |
```

### BOUNTY_PIPELINE.md

Define bounty rules and validation gates.

Template:

```md
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
```

### FREELANCE_SCOUTING_MAP.md

Define service lanes and search terms.

Template:

```md
# Freelance Scouting Map

## Service Lanes

| Lane | Offer | Good Fit | Reject |
| --- | --- | --- | --- |
| Newsletter setup / cleanup | Fixed-scope newsletter QA, template, or setup help | Clear source copy/assets, bounded task, public or shareable materials | vague growth guarantees, account takeover, DNS/payment/security changes |
| PDF / white paper layout | Layout polish from supplied copy/assets | fixed deliverable, clear file count, revision limit | full brand overhaul, unclear rights, unpaid spec work |
| Presentation polish | Mini deck or media kit cleanup | supplied deck/copy/examples | investor claims, regulated advice, fake metrics |
| Simple workflow automation | small no-code/script setup | clear input/output, testable workflow | secrets-heavy automation, production admin access |
| Repo docs / CI sprint | fix docs, setup, smoke checks, CI failure | public repo/logs, narrow failure | broad app rebuild, security audit, unpaid final implementation |

## Search Terms

- newsletter layout polish
- beehiiv setup help
- substack newsletter setup
- white paper PDF layout designer
- ebook design upgrade
- report layout design
- pitch deck polish
- creator media kit
- simple workflow automation setup
- GitHub Actions fix
- README setup fix
```

## Email Triage Process

Use email only as a signal source. Do not read more than needed.

Search query template:

```text
in:inbox newer_than:2d (GitHub OR bounty OR PR OR issue OR review OR payout OR rejection OR security OR Upwork OR Freelancer OR offer OR interview OR contract OR payment)
```

Classify each matching message:

- `Security`: login warning, OAuth authorization, password/account change.
- `Buyer Reply`: client reply, interview, offer, contract, message.
- `Payout`: payment received, payout pending, rejection, dispute.
- `Bounty`: issue comment, PR review, maintainer request, claim status.
- `Freelance Lead`: job alert or marketplace lead.
- `Noise`: notification flood with no needed action.

Action rules:

- Leave unresolved security/account messages in inbox and notify user.
- Leave buyer replies and offers in inbox until handled.
- Leave payout notices in inbox until recorded.
- Archive processed notification noise after extracting useful information.
- Never delete messages unless the user explicitly asks.
- Label recurring categories if useful.

## Bounty Scouting Process

1. Read local queue and reject log first.
2. Inspect at most three fresh leads per run.
3. Validate live state at the source, not from snippets.
4. Check issue comments for claim rules and current competition.
5. Check open PRs for duplicate or already-winning work.
6. Check whether maintainers require assignment, `/attempt`, `/claim`, or review format.
7. Inspect repo legitimacy and risk.
8. Decide:
   - act publicly now;
   - prepare a packet;
   - record a reject;
   - notify user.

Useful GitHub commands for agents with GitHub CLI:

```sh
gh issue view ISSUE_NUMBER --repo OWNER/REPO --comments --json number,title,state,url,labels,comments,updatedAt
gh pr list --repo OWNER/REPO --state open --limit 30 --json number,title,url,author,headRefName,updatedAt,mergeable,statusCheckRollup
gh search issues '"$100" bounty' --state open --limit 20 --json repository,title,url,number,createdAt,updatedAt,labels
gh search prs 'repo:OWNER/REPO ISSUE_NUMBER' --state open --json number,title,url,author,updatedAt
```

Public bounty action template:

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

## Freelance Scouting Process

1. Read local service map and pitch pack first.
2. Inspect at most three fresh leads per run.
3. Prefer fixed-scope, one-time, paid opportunities.
4. Reject vague, exploitative, underpriced, rights-unclear, or access-heavy jobs.
5. For marketplace jobs, capture:
   - URL or job id;
   - pay or budget;
   - client payment verification if visible;
   - client spend/rating if visible;
   - proposal count if visible;
   - platform credit/connect cost if visible;
   - scope fit;
   - risks;
   - apply/skip recommendation.
6. Do not apply if it spends credits or uses a user-owned account without fresh approval.
7. If blocked, create a ready-to-send packet.

Opportunity packet template:

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
```

## Automation Prompt Template

Use this prompt for a recurring agent job.

```md
Run the opportunity-scout loop.

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
```

## Suggested Cadence

- Inbox triage: every 30 minutes during active work windows.
- Bounty scout: every 1 hour if bounty work is a priority.
- Freelance scout: 1-3 times daily.
- Artifact improvement: once daily when no clean lead exists.
- Ledger cleanup: once daily or after every public action.

## Sites And Sources To Search

Freelance:

- Upwork
- Freelancer
- Contra
- PeoplePerHour
- Fiverr buyer requests or briefs, where available
- Wellfound, LinkedIn, or niche job boards for fixed-scope contract work
- Public creator communities, newsletters, and Discord/Slack posts when allowed

Bounties:

- GitHub issue search
- GitHub PR search
- Algora
- BountyHub-style pages
- OpenCollective or project-specific bounty pages
- Maintainer-posted issue comments
- Project-specific bounty boards

Email signals:

- GitHub notifications
- bounty platform notifications
- marketplace job alerts
- client replies
- payment/payout/rejection notices
- login/OAuth/security notices

## Script Or Markdown?

Start as Markdown, then add scripts only for repeated mechanical checks.

Markdown is better for the product template because:

- users can adapt it to any LLM or agent;
- safety boundaries are explicit;
- ledgers are easy to inspect;
- the workflow works even without code.

Scripts are useful later for:

- GitHub search wrappers;
- bounty duplicate/competition checks;
- inbox label/archive helpers;
- lead scoring;
- stale reject filtering;
- ledger consistency checks.

Do not script account-changing actions unless the user explicitly approves the
automation boundary and the script has clear dry-run behavior.

## Minimal Script Ideas

These are optional and should be added only after the Markdown workflow is
running reliably.

```text
scripts/
  github-bounty-search.sh
  github-pr-competition-check.sh
  score-freelance-lead.js
  ledger-lint.js
  stale-rejects.js
```

Recommended script behavior:

- print what it will do before doing it;
- support `--dry-run`;
- never store secrets;
- never send proposals or modify accounts;
- write structured output that an agent can summarize.

## Product Packaging Notes

For a shareable product, provide:

- this playbook;
- blank ledgers;
- one automation prompt;
- one bounty packet template;
- one freelance packet template;
- one email triage checklist;
- optional scripts with dry-run defaults.

Do not ship:

- private ledgers;
- real inbox examples;
- account usernames;
- wallet addresses;
- payment proofs;
- client names;
- private proposal history;
- local browser/session data;
- API tokens or cookies.

## Setup Checklist

1. Create the folder and blank Markdown files.
2. Add one clear income goal.
3. Define allowed and forbidden actions.
4. Add service lanes the user can truthfully fulfill.
5. Add bounty validation gates.
6. Run the loop manually three times.
7. Review failures and update reject rules.
8. Enable recurring automation.
9. Keep ledgers current.
10. Audit the folder before sharing it.

