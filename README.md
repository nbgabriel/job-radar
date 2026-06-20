# 📡 JobRadar

> I automate everything at work. So I automated the job search too.

JobRadar is a self-hosted dashboard that aggregates job listings from 10+ boards, filters them by your profiles, and lets you track applications — all running on localhost via Docker.

![JobRadar Dashboard](docs/screenshot.png)

---

## Why

Most job boards are noise. You end up with 10 tabs open, losing track of what you applied to, seeing the same listings twice across different sites.

This fixes that: one place, auto-refreshed on a schedule, with status tracking (New → Reviewing → Applied → Discarded) and a drag-and-drop Kanban view.

---

## Architecture

Three Docker services sharing a SQLite volume:

- **fetcher** (Python) — pulls from RSS feeds, JSON APIs, and headless-browser scrapers, filters by keyword profiles, stores results
- **api** (FastAPI) — REST API serving jobs, stats, profiles, and sources
- **ui** (React + Nginx) — dashboard at `localhost:3000`

### Sources

**RSS/API (every 2h — zero cost, lightweight):**
Remote OK · We Work Remotely · Himalayas · Working Nomads · Jobspresso · FindJobIT · Jobicy

**Scraped via Playwright (once/day):**
Bumeran · Computrabajo · GetOnBrd

Some LATAM job boards (Bumeran, Computrabajo) sit behind Cloudflare bot protection, and others (GetOnBrd) simply don't expose a working RSS feed. Both problems are solved the same way: a headless Chromium browser running [playwright-stealth](https://github.com/AtuboDad/playwright_stealth) to mask automation fingerprints, paired with per-site extraction — JSON-LD `JobPosting` schema where available (Bumeran), HTML parsing with stable utility classes otherwise (Computrabajo, GetOnBrd). These scrapers run once a day instead of every cycle, both because they're heavier (multiple page loads per run) and to keep traffic patterns closer to normal human browsing.

---

## Quick Start

```bash
git clone https://github.com/nbgabriel/job-radar
cd job-radar

docker compose up --build
```

Open **http://localhost:3000**

First fetch runs automatically on startup.

---

## Features

| Feature | Details |
|---|---|
| Auto-fetch | RSS/API every 2h, scrapers once/day, configurable via env vars |
| Keyword filtering | Profiles filter listings before storing — no noise |
| Status tracking | New → Reviewing → Applied → Discarded |
| Kanban view | Drag-and-drop cards between statuses, changes persist instantly |
| Tech tag detection | Extracts stack from descriptions (Ansible, K8s, AWS…) |
| Work mode detection | Remote / Hybrid / Onsite auto-detected |
| Search & filters | By status, source, work mode, free text |
| Profile editor | Add/edit/delete keyword profiles from the UI |
| Source manager | Enable/disable individual sources from the UI |
| Notes | Per-listing notes field |
| Manual scan | Trigger fetch on demand from the dashboard |

---

## Configuration

### Search Profiles
Managed from the UI → **Profiles** tab. No config file needed.

Default profiles: DevOps · SRE · Infrastructure Engineer · Automation Engineer · Linux/SysAdmin

### Sources
Managed from the UI → **Sources** tab. Enable or disable any source without touching config files.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | required | Anthropic API key |
| `FETCH_INTERVAL_HOURS` | `2` | How often the RSS/API sources run |
| `BUMERAN_INTERVAL_HOURS` | `24` | How often the Bumeran scraper runs |
| `COMPUTRABAJO_INTERVAL_HOURS` | `24` | How often the Computrabajo scraper runs |
| `GETONBRD_INTERVAL_HOURS` | `24` | How often the GetOnBrd scraper runs |

---

## Stack

| Layer | Tech |
|---|---|
| Fetcher | Python 3.12 · feedparser · requests · Playwright · playwright-stealth |
| API | FastAPI · SQLite |
| UI | React 18 · Vite · Tailwind CSS |
| Infra | Docker Compose · Nginx |

---

## Project Structure

```
job-radar/
├── docker-compose.yml
├── .env.example
├── fetcher/
│   ├── main.py                    # Orchestrator + scheduler (2h cycle + daily scrapers)
│   ├── config.yaml                # RSS source definitions
│   └── sources/
│       ├── rss_fetcher.py         # RSS/Atom feed parser
│       ├── jobicy_fetcher.py      # Jobicy JSON API client
│       ├── bumeran_fetcher.py     # Bumeran scraper (Playwright + stealth)
│       ├── computrabajo_fetcher.py # Computrabajo scraper (Playwright + stealth)
│       └── getonbrd_fetcher.py    # GetOnBrd scraper (Playwright + stealth)
├── api/
│   └── main.py                    # FastAPI — jobs, stats, profiles, sources
├── db/
│   └── init.sql                   # SQLite schema
└── ui/
    └── src/
        ├── App.jsx
        └── components/
            ├── StatsPanel.jsx
            ├── JobCard.jsx
            ├── FilterBar.jsx
            ├── KanbanView.jsx      # Drag-and-drop status board
            ├── ProfileConfig.jsx
            └── SourcesConfig.jsx
```

---

*Built by [Gabriel Bratig](https://www.linkedin.com/in/gabriel-bratig) — Senior DevOps & Infrastructure Automation Engineer*  
