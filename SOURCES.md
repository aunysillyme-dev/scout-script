# Scout Sources

The full set of places this system scouts for legitimate, low-risk income. These
are public, niche-agnostic sources — safe to use through **your own** accounts.
Never reuse anyone else's cookies, inbox, sessions, marketplace account, or
GitHub identity.

`python scout.py --scout` turns these into ready-to-click search links using the
search terms from your interview, and runs the GitHub bounty scan live. The
`scout-worker/` Cloudflare Worker keeps the bounty scan running on a schedule.

## Bounty platforms

| Source | URL | Automated? |
| --- | --- | --- |
| GitHub issue search | <https://github.com/search?q=type%3Aissue+state%3Aopen+bounty> | ✅ Worker + `--scout` |
| Algora | <https://algora.io/bounties> | ✅ Worker (board scrape) |
| MRWK | <https://mrwk.xyz/> | Deep link |
| Opire | <https://app.opire.dev/> | ✅ Worker (bot signal) |
| Bounty.new | <https://bounty.new/> | Deep link |
| BountyHub | <https://bountyhub.dev/> | ✅ Worker (bot signal) |
| Direct maintainer posts | GitHub / X / Discord / project sites | Manual |

## Freelance / service marketplaces

These don't expose open scouting APIs, so the scout produces pre-filled search
links for each of your terms rather than scanning them automatically.

| Source | URL |
| --- | --- |
| Upwork | <https://www.upwork.com/nx/search/jobs/> |
| Freelancer | <https://www.freelancer.com/jobs/> |
| PeoplePerHour | <https://www.peopleperhour.com/freelance-jobs> |
| Contra | <https://contra.com/opportunities> |
| Wellfound | <https://wellfound.com/jobs> |
| Y Combinator companies (outreach research) | <https://www.ycombinator.com/companies> |

## Inbox signals (opt-in)

Only if you connect **your own** email during setup. The scout watches for buyer
replies, payout/rejection notices, security/account alerts, bounty updates, and
marketplace job alerts — then triages them per the rules in the playbook. It
reads only enough to classify, never deletes, and leaves anything unresolved in
your inbox.

- Gmail / your mail provider (your own account only)
- GitHub notifications (your own account)
- Marketplace notification emails (your own accounts)

## Adding a source

Add bounty searches in `scout-worker/src/index.js` (`SEARCHES`) or via the
Worker's `NICHE_QUERY` var. Add marketplaces to the `SOURCE_REGISTRY` near the
top of `scout.py` so they appear on the deep-link board.
