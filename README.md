# Ilumineers Digest

A weekly (and on-demand) Disney Lorcana digest: tournament results, news and
community highlights, summarized by Claude with a citation on every bullet.
The output is static HTML in `site/`, ready to drop onto any website.

## How it works

```
collect  →  web search  →  summarize  →  render  →  publish
```

1. **Collect** (`src/digest/collectors/`) — each source becomes a list of items with an ID.
2. **Web search** — Claude searches for the week's official news, articles and big X stories.
   A story is kept only if its URL actually came back from a search.
3. **Summarize** — Claude writes the digest as structured JSON, citing item IDs.
   Citations to IDs that weren't collected are dropped in code, so links can't be invented.
4. **Render** — Jinja templates produce one self-contained page per digest, plus
   `site/index.html` (the archive) and `site/feed.xml` (RSS).

Tournament statistics (ink-pair wins, repeat podium players) are calculated in
Python, not by Claude.

## Sources

| Source | How | Notes |
|---|---|---|
| Tournaments | [Lorcanahunter](https://lorcanahunter.com/en/past-events) event pages | Events with decklists only. inkdecks.com isn't used: its robots.txt blocks AI crawlers and it sits behind a Cloudflare challenge. |
| Reddit | Public RSS of r/Lorcana top posts for the week | No API key. |
| YouTube | Channel RSS feeds | Add channel IDs in `config/accounts.yaml`. |
| Bluesky | Public author feeds; optional keyword search | Search needs `BLUESKY_HANDLE` + `BLUESKY_APP_PASSWORD`. |
| X / Twitter | Claude web search | No X API (it's paid per read). X handles in `accounts.yaml` help Claude recognize notable posts. |
| Facebook group | `inbox.md` | Meta has no API for groups and logged-out requests are blocked. Paste notable post links here. |

## Setup

```bash
uv sync
```

Summaries can run two ways, set by `claude.backend` in `config/sources.yaml`
(or `--backend` on the command line):

- **`claude-code`** (default) runs through the Claude Code CLI and counts
  against your Claude subscription's usage limits instead of costing extra.
  Install Claude Code, then run `claude` once and log in. In CI, create a token
  with `claude setup-token` and store it as the `CLAUDE_CODE_OAUTH_TOKEN` secret.
  This backend ignores `ANTHROPIC_API_KEY`, so it never bills the API by accident.
- **`api`** calls the Anthropic API directly and needs `ANTHROPIC_API_KEY`.
  Billed per token.

Keep the subscription backend to personal use like this digest. Using a
subscription login to power a service for other people is not allowed.

Then fill in `config/accounts.yaml` with the players and creators you want to
follow, and set `site.base_url` in `config/sources.yaml`.

## Running it

```bash
uv run digest build                  # last 7 days, ending today
uv run digest build --days 3         # on-demand: just the last 3 days
uv run digest build --no-ai          # no Claude calls; raw results and links
uv run digest build --backend api    # use the API instead of your subscription
uv run digest build --publish-to ../my-site/lorcana
uv run digest render 2026-10-26      # re-render a saved digest after editing templates
```

Each run saves what it collected to `data/<date>/` and writes
`site/digests/<date>.html`.

## Scheduling

`.github/workflows/digest.yml` runs every Monday at 13:00 UTC and has a
**Run workflow** button for on-demand digests. It commits `data/` and `site/`
back to the repo and deploys `site/` to GitHub Pages.

Repository secrets: `CLAUDE_CODE_OAUTH_TOKEN` for the `claude-code` backend or
`ANTHROPIC_API_KEY` for the `api` backend, plus optional `BLUESKY_HANDLE` and
`BLUESKY_APP_PASSWORD`. If your personal site is hosted somewhere
other than GitHub Pages, replace the Pages steps with a push to that site.

## Cost

Two Claude requests per digest: a web-search pass (up to 8 searches) and one
summary over about 100 items. On the `claude-code` backend these count toward
your subscription's usage limits. On the `api` backend, expect well under a
dollar per digest on Claude Opus 5.5.
