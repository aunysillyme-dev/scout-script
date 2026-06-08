# Setup Guide

Pick the path that fits you. Most people only need **Path A**.

- **Path A — No install.** Use any AI assistant. ~5 minutes. *(recommended)*
- **Path B — Run it locally.** Adds the live bounty scanner. ~10 minutes.
- **Path C — Always-on.** Deploy the scout so it runs by itself. Optional, for later.

You can always start with A and add B or C whenever you want.

---

## Path A — No install (recommended)

You don't need to download anything or use a terminal.

1. Open your AI assistant (Claude, ChatGPT, or any chat AI).
2. Open [`PROMPT.md`](PROMPT.md) in this repo, copy **everything** in it.
3. Paste it into the AI and send.
4. The AI interviews you one question at a time — your income goal, your niche,
   your real skills, your search terms, and whether you want your email watched.
   Answer honestly; if you can't actually do a service, leave it out.
5. When it's done, the AI hands you your personalized kit: a set of Markdown
   files (your pipeline, ledgers, pitch templates, and a search board) plus a
   recurring "run my scout" prompt.

That's it. To run your scout from then on, paste the
`automations/hourly-loop-prompt.md` the AI gave you whenever you want it to find
and move one opportunity forward.

> **Tip:** If you're using an AI that can see these files (like Claude Code or
> Cursor), you can skip the copy-paste and just say:
> *"Read scout.py and set up my Opportunity Scout kit by interviewing me."*

---

## Path B — Run it locally

This adds the **live bounty scanner** (`--scout`), which checks GitHub for fresh
paid bounties right now and builds clickable search links for your niche.

### 1. Check you have Python

Open Terminal (Mac: press `Cmd+Space`, type "Terminal", Enter) and run:

```bash
python3 --version
```

If you see `Python 3.10` or higher, you're set. If not, install it from
<https://www.python.org/downloads/> (click the big yellow button, run the
installer). No other downloads are needed — this tool has zero dependencies.

### 2. Get the files

Download this repo (green **Code** button on GitHub → **Download ZIP**), unzip
it, then in Terminal move into the folder:

```bash
cd ~/Downloads/scout-script-main      # adjust if you unzipped elsewhere
```

### 3. Build your kit

```bash
python3 scout.py --interactive
```

Answer the questions. It writes your kit into a new `opportunity-scout/` folder.

### 4. Scout for work

```bash
python3 scout.py --scout
```

This prints a ranked list of fresh bounties plus ready-to-click search links for
Upwork, Contra, Algora, and the rest — using the terms from your interview.

> **Optional:** a free GitHub token raises the scan's rate limit. Create one at
> <https://github.com/settings/tokens> (no scopes/permissions needed — it only
> reads public data), then run `export GITHUB_TOKEN=your_token_here` before
> `--scout`.

---

## Path C — Always-on scout (optional)

This deploys the bounty scanner to **Cloudflare** so it runs on a schedule
(hourly by default) without you doing anything. The free plan is plenty. Skip
this until you want hands-off scouting.

1. Make a free account at <https://dash.cloudflare.com/sign-up>.
2. Install Node.js from <https://nodejs.org/> (the "LTS" button).
3. In Terminal, from the repo:

   ```bash
   cd scout-worker
   npm install
   cp wrangler.toml.example wrangler.toml
   npx wrangler login                      # opens your browser to connect Cloudflare
   npx wrangler secret put GITHUB_TOKEN    # paste a free GitHub token (reads public data only)
   npm run deploy
   ```

4. Wrangler prints your worker's URL. Visit `your-url/run` to see a scout pass,
   or `your-url/leads` for the latest results. It now runs every hour on its own.

Full details and options are in [`scout-worker/README.md`](scout-worker/README.md).

---

## What stays safe, always

This system **reads public information and reports** — it never spends money,
sends a pitch, claims a bounty, accepts a contract, or changes any account
setting on its own. Every one of those is your call. It only watches your email
if you opt in, with your own account, and it never deletes anything.

## Stuck?

- "command not found: python3" → install Python (Path B, step 1).
- "command not found: npm" → install Node.js (Path C, step 2).
- The scan found nothing → bounty feeds are quiet sometimes; try again later, or
  add a `GITHUB_TOKEN`. The clickable search links always work.
- Anything else → paste the error into your AI assistant and ask it to help.
