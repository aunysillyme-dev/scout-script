# Opportunity Scout Worker

An always-on bounty scout that runs on [Cloudflare Workers](https://workers.cloudflare.com/)
(free tier is plenty). It searches live GitHub issue signals for fresh paid
bounty work, re-reads each candidate through the GitHub API, scores it, and
rejects obvious traps — so you (or your agent) only look at request-ready leads.

It **never** claims work, comments on GitHub, opens PRs, or sends payout
details. It is an alert router, not an actor. Every public action stays a
human/agent decision.

This is the *always-on* half of the scout. For an on-demand local scan plus
freelance-site deep links, use `python scout.py --scout` in the repo root — no
Cloudflare account required.

## What it does

- Searches GitHub for recently updated bounty-bot threads (Algora, BountyHub,
  Opire, and generic bounty labels), plus the Algora board.
- Re-reads each issue, its comments, and its repository metadata.
- Scores payout signal, competition, scope shape, maintainer signal, and
  pre-clone security risk.
- Stores the latest leads and rejects in Cloudflare KV when `SCOUT_MEMORY` is
  bound (optional).

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Short route guide. |
| `/health` | Runtime and KV status. |
| `/run` | Run a scout pass and return scored leads and rejects. |
| `/leads` | Read the last stored scout pass. |
| `/memory` | Show recent seen issue IDs from KV. |
| `/candidate?repo=owner/name&issue=123` | Vet one known GitHub issue. |

## Configure it for your niche

Bounties are mostly niche-agnostic — a funded issue is a funded issue — so the
defaults work out of the box. To bias the scout toward your skillset:

- edit the `SEARCHES` list at the top of `src/index.js`, or
- set a one-line `NICHE_QUERY` env var (e.g. `label:bounty react is:issue is:open`)
  to add a search without touching code.

Whether a lead actually *fits* your skills stays a judgment call — the Worker
surfaces and de-risks candidates; it does not decide what you can deliver.

## Rejection posture

The Worker rejects candidates early when it sees closed issues, open PR races,
heavy `/attempt` or `/claim` pressure, already-assigned work, interview-reserved
or internal-only work, suspicious crypto/wallet/private-key payout language, or
archived/disabled/tiny-new repositories. Rejected targets stay out of normal
scouting for ~14 days (via KV) unless a material trigger changes.

## Local setup

```bash
npm install
npm run check   # syntax check
npm run dev     # run locally at http://localhost:8787
```

An optional `GITHUB_TOKEN` in `.dev.vars` improves GitHub API rate limits
(`cp .dev.vars.example .dev.vars`).

## Deploy to Cloudflare

```bash
cp wrangler.toml.example wrangler.toml      # then edit it
npx wrangler kv namespace create SCOUT_MEMORY   # optional persistence
npx wrangler secret put GITHUB_TOKEN            # optional, recommended
npm run deploy
```

The default cron runs hourly. With a `GITHUB_TOKEN` secret and KV in place you
can safely increase the cadence later.

## Safety

No secrets live in this code. `GITHUB_TOKEN` and the KV namespace id are
supplied per-deployment (token as a Worker secret, never committed). The scout
only reads public data and only ever *reports* — it takes no action on your
accounts.
