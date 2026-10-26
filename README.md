# Illumineers Digest

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
| Tournaments | [Lorcanahunter](https://lorcanahunter.com/en/past-events) event pages | Events with decklists, used for the ink-pair and player tables. Usually a week or two behind. |
| Events this week | [inkdecks](https://inkdecks.com/lorcana-tournaments) RSS feed | Used with the site owner's permission: titles, descriptions and links only, never decklists. Cloudflare blocks scripts from the feed, so see "Saving the inkdecks feed" below. |
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
  Install Claude Code, then run `claude` once and log in. This backend ignores `ANTHROPIC_API_KEY`, so it never bills the API by accident.
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

## Saving the inkdecks feed

The collector tries the live feed first. While Cloudflare blocks it, save a copy
from your browser before each run:

1. Open https://inkdecks.com/lorcana-tournaments/feed.rss and save it.
2. Move it into the project folder as `inkdecks.rss`, for example
   `mv ~/Downloads/feed.rss inkdecks.rss`.

The file is git-ignored, since it's inkdecks' content. A copy older than three
days still works but prints a warning; without any copy, the digest notes that
inkdecks failed and carries on. Change the location with
`tournaments.inkdecks.saved_file` in `config/sources.yaml`.

## Scheduling and publishing

Digests are built on a Mac, not in GitHub Actions. Reddit and Lorcanahunter
(behind Cloudflare) block requests from cloud servers like GitHub's, but allow
a home connection.

- `scripts/publish.sh` pulls, builds a digest, then commits and pushes `data/`
  and `site/`. Arguments go to `digest build`, so an on-demand run is
  `scripts/publish.sh --days 3`. Set `NO_PUSH=1` to commit without pushing.
- `scripts/install-schedule.sh` installs a launchd job that runs `publish.sh`
  every Monday at 9:00 local time. If the Mac is asleep then, the job runs when
  it wakes; if it's shut down, that week is skipped. The log is at
  `~/Library/Logs/illumineers-digest.log`. Remove it with
  `scripts/install-schedule.sh --uninstall`.
- `.github/workflows/digest.yml` only deploys `site/` to GitHub Pages when a
  push changes it. It needs no secrets.

The Mac needs Claude Code logged in and `git push` working without a prompt
(an SSH key in the macOS keychain, or the HTTPS credential helper). Optional
Bluesky search credentials (`BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`) can go in
`publish.sh`'s environment.

## Cost

Two Claude requests per digest: a web-search pass (up to 8 searches) and one
summary over about 100 items. On the `claude-code` backend these count toward
your subscription's usage limits. On the `api` backend, expect well under a
dollar per digest on Claude Opus 5.5.
