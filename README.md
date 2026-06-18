# 📡 Job Radar

> Automated job intelligence platform — scrapes 20+ job boards, parses listings with Claude AI, and serves a real-time dashboard on localhost.

Built because I automate everything else at work. Why not the job search?

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   docker compose up                  │
├──────────────┬──────────────────┬───────────────────┤
│   fetcher    │       api        │        ui         │
│  (Python)    │    (FastAPI)     │  (React + Nginx)  │
│              │                  │                   │
│ RSS feeds ──►│                  │  ┌─────────────┐  │
│              │  SQLite (shared  │  │  Dashboard  │  │
│ Claude AI ──►│    volume)       │◄─│  Kanban     │  │
│  web_search  │                  │  │  Profiles   │  │
│              │  REST API        │  └─────────────┘  │
│ Cron every   │  /jobs /stats    │                   │
│   2 hours    │  /profiles       │  localhost:3000   │
└──────────────┴──────────────────┴───────────────────┘
```

**Sources:**
- **Category A (RSS/API):** RemoteOK, We Work Remotely, Himalayas, Remotive, Working Nomads, Jobspresso, Nodesk, Wellfound, GetOnBrd, Workana, WeRemoto, Hubstaff Talent
- **Category B (Claude AI search):** Bumeran, Zonajobs, Computrabajo, Indeed AR, Glassdoor, Talent.com

---

## Quick Start

```bash
git clone https://github.com/gnbratig/job-radar
cd job-radar

cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

docker compose up --build
```

Open **http://localhost:3000**

---

## Features

- **Auto-fetch** every 2 hours (configurable via `FETCH_INTERVAL_HOURS`)
- **AI-powered parsing** — Claude extracts tech tags, work mode, salary from raw listings
- **Status tracking** — New → Seen → Applied → Discarded
- **Kanban view** for visual pipeline management
- **Search profiles** — fully editable from the UI (no config file needed)
- **Notes** per listing
- **Manual scan** trigger from the dashboard

---

## Configuration

### Search Profiles (via UI)
Add/edit/delete keyword profiles directly in the dashboard → **Profiles** tab.

### Sources (via `fetcher/config.yaml`)
Enable/disable RSS feeds and search sources. Changes take effect on next container restart.

### Environment Variables
| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | required | Claude API key |
| `FETCH_INTERVAL_HOURS` | `2` | Fetch interval in hours |

---

## Stack

| Layer | Tech |
|---|---|
| Fetcher | Python 3.12, feedparser, Anthropic SDK |
| API | FastAPI, SQLite |
| UI | React 18, Vite, Tailwind CSS |
| Infra | Docker Compose, Nginx |
| AI | Claude Sonnet (web_search tool) |

---

## Project Structure

```
job-radar/
├── docker-compose.yml
├── .env.example
├── fetcher/
│   ├── main.py              # Orchestrator + scheduler
│   ├── config.yaml          # Source definitions
│   └── sources/
│       ├── rss_fetcher.py   # Category A: direct RSS/API
│       └── search_fetcher.py # Category B: Claude web search
├── api/
│   └── main.py              # FastAPI REST API
├── db/
│   └── init.sql             # SQLite schema
└── ui/
    └── src/
        ├── App.jsx
        └── components/
            ├── StatsPanel.jsx
            ├── JobCard.jsx
            ├── FilterBar.jsx
            ├── KanbanView.jsx
            └── ProfileConfig.jsx
```

---

## Why Claude for job search?

Most job portals don't have structured APIs. Claude's `web_search` tool can query sites like Bumeran or Glassdoor and return normalized JSON — no brittle CSS selectors, no CAPTCHA fights, no maintenance overhead when the site redesigns.

The tradeoff: it costs a few API cents per search cycle. For a 2-hour interval, that's negligible.

---

*Built by [Gabriel Bratig](https://linkedin.com/in/gabriel-bratig) — Senior DevOps & Infrastructure Automation Engineer*
