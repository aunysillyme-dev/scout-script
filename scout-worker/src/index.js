// Opportunity Scout Worker
//
// An always-on bounty scout. On a schedule (or on demand via /run) it searches
// live GitHub issue signals for fresh, paid, bounty-style work, re-reads each
// candidate through the GitHub API, scores payout / competition / scope /
// maintainer / pre-clone security risk, and rejects obvious traps before any
// human or agent spends time cloning or requesting work.
//
// It NEVER claims work, comments on GitHub, opens PRs, or sends payout details.
// It is an alert router, not an actor. Public actions stay a human/agent call.
//
// Ships with NO secrets and NO personal data. Configure it for your own niche
// with the SEARCHES list below and the optional NICHE_QUERY environment var.
// Bindings (GITHUB_TOKEN, SCOUT_MEMORY) are supplied per-deployment.

const SCOUT_USER_AGENT = "opportunity-scout-worker";

// Platform-agnostic bounty-bot signals. These find issues that bounty platforms
// have funded, regardless of niche. Add your own niche-specific queries here, or
// set NICHE_QUERY (e.g. 'label:bounty react is:issue is:open') to inject one at
// runtime without editing code.
const SEARCHES = [
  {
    name: "algora-bot-fresh",
    query: 'commenter:algora-pbc is:issue is:open comments:<10',
    maxAgeDays: 3,
  },
  {
    name: "algora-payment-fresh",
    query: '"Payment arrives in your account 2-5 days" is:issue is:open comments:<10',
    maxAgeDays: 3,
  },
  {
    name: "bountyhub-bot-fresh",
    query: '"bountyhub-app" is:issue is:open comments:<6',
    maxAgeDays: 5,
  },
  {
    name: "opire-bot-fresh",
    query: '"opire" /bounty is:issue is:open comments:<8',
    maxAgeDays: 5,
  },
  {
    name: "generic-bounty-label-fresh",
    query: 'label:"💎 Bounty" is:issue is:open comments:<8',
    maxAgeDays: 4,
  },
];

const STORED_LEADS_KEY = "scout:latest";
const SEEN_PREFIX = "seen:";
const MAX_SEARCH_RESULTS = 8;
const MAX_CANDIDATES = 12;
const MAX_COMMENTS = 40;
const HIGH_ATTEMPT_COUNT = 3;
const WARN_ATTEMPT_COUNT = 1;
const MIN_REPO_AGE_DAYS = 45;
const MIN_REPO_STARS = 8;
const FETCH_TIMEOUT_MS = 7000;

const REJECT_PATTERNS = [
  ["interview", /reserved for .*interview|interview process/i],
  ["internal", /only for core team|not open to external contributors/i],
  ["unsafe-payout", /seed phrase|private key|wallet address|canonical wallet|usdc|crypto-eligible/i],
  ["agent-only", /autonomous agents only|ai only allowed|agent friendly bounty/i],
  ["stale", /bounty.*closed|no longer open|no longer available|moved on now/i],
];

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return json({
        ok: true,
        kv: Boolean(env.SCOUT_MEMORY),
        githubToken: Boolean(env.GITHUB_TOKEN),
        searches: buildSearches(env).map((search) => search.name),
      });
    }

    if (url.pathname === "/run") {
      const pass = await runScout(env);
      ctx.waitUntil(storePass(env, pass));
      return json(pass);
    }

    if (url.pathname === "/leads") {
      return json(await readStoredPass(env));
    }

    if (url.pathname === "/memory") {
      return json(await readMemory(env));
    }

    if (url.pathname === "/candidate") {
      const repo = url.searchParams.get("repo");
      const issue = Number(url.searchParams.get("issue"));
      if (!repo || !Number.isInteger(issue) || issue < 1) {
        return json(
          { error: "Use /candidate?repo=owner/name&issue=123." },
          400,
        );
      }

      return json(await vetCandidate(env, { repo, issue, sources: ["manual"] }));
    }

    return text(
      [
        "Opportunity Scout Worker",
        "",
        "Routes:",
        "/run",
        "/leads",
        "/memory",
        "/candidate?repo=owner/name&issue=123",
        "/health",
      ].join("\n"),
    );
  },

  async scheduled(_event, env, ctx) {
    ctx.waitUntil(runScout(env).then((pass) => storePass(env, pass)));
  },
};

// Built-in searches plus an optional runtime niche query from the environment.
function buildSearches(env) {
  const searches = [...SEARCHES];
  if (env.NICHE_QUERY) {
    searches.push({ name: "niche", query: env.NICHE_QUERY, maxAgeDays: 5 });
  }
  return searches;
}

async function runScout(env) {
  const startedAt = new Date().toISOString();
  const discoveryResults = await Promise.all([
    discoverAlgoraBoard(),
    ...buildSearches(env).map((search) => searchIssues(env, search)),
  ]);
  const candidates = dedupeCandidates(discoveryResults.flat()).slice(0, MAX_CANDIDATES);
  const vetted = await Promise.all(
    candidates.map((candidate) => vetCandidate(env, candidate)),
  );

  const leads = vetted
    .filter((result) => result.verdict === "lead")
    .sort((a, b) => b.score - a.score)
    .slice(0, 8);
  const rejects = vetted
    .filter((result) => result.verdict !== "lead")
    .sort((a, b) => b.score - a.score)
    .slice(0, 16);

  return {
    startedAt,
    completedAt: new Date().toISOString(),
    candidateCount: candidates.length,
    leadCount: leads.length,
    leads,
    rejects,
    note: "Leads still need contribution-rule and install-script inspection before a public attempt.",
  };
}

async function discoverAlgoraBoard() {
  const response = await fetchWithTimeout("https://algora.io/bounties", {
    headers: { "User-Agent": SCOUT_USER_AGENT },
  });
  if (!response.ok) return [];

  const html = await response.text();
  return extractGitHubIssueLinks(html).map((candidate) => ({
    ...candidate,
    sources: ["algora-board"],
  }));
}

async function searchIssues(env, search) {
  const params = new URLSearchParams({
    q: appendFreshness(search.query, search.maxAgeDays),
    sort: "updated",
    order: "desc",
    per_page: String(MAX_SEARCH_RESULTS),
  });
  const response = await github(env, `/search/issues?${params}`);

  if (!response.ok) {
    return [];
  }

  const payload = await response.json();
  return (payload.items ?? [])
    .filter((item) => item.state === "open" && !item.pull_request)
    .map((item) => ({
      repo: repoFromIssueUrl(item.repository_url),
      issue: item.number,
      issueTitle: item.title,
      sources: [search.name],
    }))
    .filter((candidate) => candidate.repo);
}

function extractGitHubIssueLinks(html) {
  const candidates = [];
  const issueLinks =
    /https:\/\/github\.com\/([^/"?#]+\/[^/"?#]+)\/issues\/(\d+)/g;

  for (const match of html.matchAll(issueLinks)) {
    candidates.push({
      repo: match[1],
      issue: Number(match[2]),
    });
  }

  return candidates;
}

async function vetCandidate(env, candidate) {
  const [issueResponse, commentsResponse, repoResponse, openPrsResponse] = await Promise.all([
    github(env, `/repos/${candidate.repo}/issues/${candidate.issue}`),
    github(
      env,
      `/repos/${candidate.repo}/issues/${candidate.issue}/comments?per_page=${MAX_COMMENTS}`,
    ),
    github(env, `/repos/${candidate.repo}`),
    searchOpenPullRequests(env, candidate),
  ]);

  if (!issueResponse.ok || !repoResponse.ok) {
    return reject(candidate, 0, ["github-enrichment-failed"], {
      issueStatus: issueResponse.status,
      repoStatus: repoResponse.status,
    });
  }

  const issue = await issueResponse.json();
  const repo = await repoResponse.json();
  const comments = commentsResponse.ok ? await commentsResponse.json() : [];
  const openPrs = openPrsResponse.ok ? await openPrsResponse.json() : { items: [] };
  const textSurface = [
    issue.title,
    issue.body ?? "",
    ...comments.map((comment) => comment.body ?? ""),
  ].join("\n");
  const payout = extractPayout(textSurface);
  const platform = detectPlatform(textSurface);
  const attempts = countMatches(textSurface, /\/attempt\b/gi);
  const claims = countMatches(textSurface, /\/claim\b/gi);
  const linkedPrHints = countMatches(textSurface, /pull request|linked a pull request|#\d{3,}/gi);
  const rejectionReasons = [];
  const warnings = [];

  if (issue.state !== "open") {
    rejectionReasons.push("issue-closed");
  }
  if (issue.assignees?.length) {
    rejectionReasons.push("assigned");
  }
  if ((openPrs.total_count ?? openPrs.items?.length ?? 0) > 0) {
    rejectionReasons.push("open-pr-race");
  }
  if (!payout.amount) {
    rejectionReasons.push("no-clear-dollar-payout");
  }
  if (attempts >= HIGH_ATTEMPT_COUNT || claims >= HIGH_ATTEMPT_COUNT) {
    rejectionReasons.push("crowded-attempt-thread");
  } else if (attempts >= WARN_ATTEMPT_COUNT || claims >= WARN_ATTEMPT_COUNT) {
    warnings.push("some-attempt-pressure");
  }
  if (linkedPrHints >= 6) {
    warnings.push("linked-pr-hints-present");
  }

  for (const [reason, pattern] of REJECT_PATTERNS) {
    if (pattern.test(textSurface)) {
      rejectionReasons.push(reason);
    }
  }

  const repoRisk = vetRepo(repo);
  rejectionReasons.push(...repoRisk.rejects);
  warnings.push(...repoRisk.warnings);

  const score = scoreCandidate({
    payout,
    platform,
    attempts,
    claims,
    issue,
    repo,
    warnings,
  });
  const detail = {
    title: issue.title,
    url: issue.html_url,
    repoUrl: repo.html_url,
    payout,
    platform,
    score,
    attempts,
    claims,
    commentCount: issue.comments ?? comments.length,
    linkedPrHints,
    openPrs: (openPrs.items ?? []).slice(0, 5).map((pr) => ({
      number: pr.number,
      title: pr.title,
      url: pr.html_url,
    })),
    repoMeta: {
      fullName: repo.full_name,
      stars: repo.stargazers_count,
      forks: repo.forks_count,
      openIssues: repo.open_issues_count,
      ageDays: ageDays(repo.created_at),
      archived: repo.archived,
      fork: repo.fork,
      license: repo.license?.spdx_id ?? null,
    },
    security: {
      verdict: rejectionReasons.some((reason) =>
        ["unsafe-payout", "agent-only", "repo-too-new", "tiny-new-repo"].includes(reason),
      )
        ? "reject"
        : warnings.length
          ? "review"
          : "clear-preclone",
      warnings,
    },
    sources: candidate.sources,
  };

  if (rejectionReasons.length) {
    return reject(candidate, score, unique(rejectionReasons), detail);
  }

  return {
    verdict: "lead",
    repo: candidate.repo,
    issue: candidate.issue,
    ...detail,
    nextAction: "Inspect contribution rules, install scripts, and live PR state before asking for work.",
  };
}

function scoreCandidate({ payout, platform, attempts, claims, issue, repo, warnings }) {
  let score = 0;

  if (payout.amount >= 100) score += 2;
  else if (payout.amount > 0) score += 1;

  if (platform === "algora") score += 2;
  if (platform === "bountyhub" || platform === "opire" || platform === "bounty.new") score += 1;

  if (attempts === 0 && claims === 0) score += 2;
  if ((issue.comments ?? 0) <= 4) score += 1;
  if (!issue.assignees?.length) score += 1;
  if ((repo.stargazers_count ?? 0) >= 100) score += 1;
  if (repo.license) score += 1;

  score -= Math.min(warnings.length, 2);
  return score;
}

function vetRepo(repo) {
  const rejects = [];
  const warnings = [];
  const repoAgeDays = ageDays(repo.created_at);

  if (repo.archived || repo.disabled) rejects.push("repo-inactive");
  if (repo.fork) warnings.push("repo-is-fork");
  if (!repo.license) warnings.push("no-license-metadata");
  if (repoAgeDays < MIN_REPO_AGE_DAYS) rejects.push("repo-too-new");
  if (repoAgeDays < 180 && (repo.stargazers_count ?? 0) < MIN_REPO_STARS) {
    rejects.push("tiny-new-repo");
  }

  return { rejects, warnings };
}

function extractPayout(textSurface) {
  const dollarMatches = [...textSurface.matchAll(/\$\s?([\d,]+(?:\.\d{1,2})?)/g)].map(
    (match) => Number(match[1].replaceAll(",", "")),
  );
  const bountyMatches = [
    ...textSurface.matchAll(/\/bounty\s+\$?\s?([\d,]+(?:\.\d{1,2})?)/gi),
  ].map((match) => Number(match[1].replaceAll(",", "")));
  const amounts = [...dollarMatches, ...bountyMatches].filter(Number.isFinite);
  const amount = amounts.length ? Math.max(...amounts) : 0;

  return {
    amount,
    signal: amount ? `$${amount}` : null,
  };
}

function detectPlatform(textSurface) {
  if (/algora-pbc|algora\.io|payment arrives.*2-5 days/i.test(textSurface)) {
    return "algora";
  }
  if (/bountyhub-app|bountyhub\.dev/i.test(textSurface)) {
    return "bountyhub";
  }
  if (/opire/i.test(textSurface)) {
    return "opire";
  }
  if (/bounty\.new/i.test(textSurface)) {
    return "bounty.new";
  }
  return "direct-or-unknown";
}

function appendFreshness(query, maxAgeDays) {
  if (!maxAgeDays) return query;

  const since = new Date(Date.now() - maxAgeDays * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10);
  return `${query} updated:>=${since}`;
}

function reject(candidate, score, reasons, detail = {}) {
  return {
    verdict: "reject",
    repo: candidate.repo,
    issue: candidate.issue,
    score,
    reasons,
    sources: candidate.sources,
    ...detail,
  };
}

function dedupeCandidates(candidates) {
  const byKey = new Map();

  for (const candidate of candidates) {
    const key = `${candidate.repo}#${candidate.issue}`;
    const existing = byKey.get(key);
    if (existing) {
      existing.sources = unique([...existing.sources, ...candidate.sources]);
    } else {
      byKey.set(key, candidate);
    }
  }

  return [...byKey.values()];
}

async function storePass(env, pass) {
  if (!env.SCOUT_MEMORY) return;

  await env.SCOUT_MEMORY.put(STORED_LEADS_KEY, JSON.stringify(pass), {
    expirationTtl: 60 * 60 * 48,
  });

  await Promise.all(
    [...pass.leads, ...pass.rejects].map((result) =>
      env.SCOUT_MEMORY.put(`${SEEN_PREFIX}${result.repo}#${result.issue}`, pass.completedAt, {
        expirationTtl: 60 * 60 * 24 * 14,
      }),
    ),
  );
}

async function readStoredPass(env) {
  if (!env.SCOUT_MEMORY) {
    return { stored: false, reason: "SCOUT_MEMORY is not bound." };
  }

  const stored = await env.SCOUT_MEMORY.get(STORED_LEADS_KEY, "json");
  return stored ?? { stored: false, reason: "No scout pass stored yet." };
}

async function readMemory(env) {
  if (!env.SCOUT_MEMORY) {
    return { stored: false, reason: "SCOUT_MEMORY is not bound." };
  }

  const list = await env.SCOUT_MEMORY.list({ prefix: SEEN_PREFIX, limit: 100 });
  return {
    keys: list.keys.map((entry) => entry.name),
    cursor: list.cursor || null,
  };
}

async function github(env, path) {
  return fetchWithTimeout(`https://api.github.com${path}`, {
    headers: {
      Accept: "application/vnd.github+json",
      "User-Agent": SCOUT_USER_AGENT,
      ...(env.GITHUB_TOKEN ? { Authorization: `Bearer ${env.GITHUB_TOKEN}` } : {}),
    },
  });
}

async function searchOpenPullRequests(env, candidate) {
  const params = new URLSearchParams({
    q: `repo:${candidate.repo} is:pr is:open "#${candidate.issue}"`,
    per_page: "5",
  });
  return github(env, `/search/issues?${params}`);
}

async function fetchWithTimeout(url, options) {
  const signal = AbortSignal.timeout(FETCH_TIMEOUT_MS);
  return fetch(url, { ...options, signal });
}

function repoFromIssueUrl(repositoryUrl) {
  return repositoryUrl?.replace("https://api.github.com/repos/", "") ?? null;
}

function countMatches(text, pattern) {
  return [...text.matchAll(pattern)].length;
}

function ageDays(dateString) {
  return Math.floor((Date.now() - new Date(dateString).getTime()) / (1000 * 60 * 60 * 24));
}

function unique(values) {
  return [...new Set(values)];
}

function json(value, status = 200) {
  return new Response(JSON.stringify(value, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

function text(value, status = 200) {
  return new Response(value, {
    status,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}
