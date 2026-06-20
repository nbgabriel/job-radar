import logging
import os
import json
import sqlite3
import sys
import time
import yaml
from datetime import datetime
from sources.rss_fetcher import fetch_rss
from sources.search_fetcher import fetch_via_claude_search
from sources.jobicy_fetcher import fetch_jobicy
from sources.bumeran_fetcher import fetch_bumeran
from sources.computrabajo_fetcher import fetch_computrabajo
from sources.getonbrd_fetcher import fetch_getonbrd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fetcher")

DB_PATH = os.environ.get("DATABASE_URL", "/data/jobradar.db")
FETCH_INTERVAL = int(os.environ.get("FETCH_INTERVAL_HOURS", "2")) * 3600
CONFIG_PATH = os.environ.get("CONFIG_PATH", "/app/config.yaml")

# Bumeran uses Playwright + stealth, which is much heavier/slower than RSS
# and hits a Cloudflare-protected site, so it runs on its own daily cadence
# instead of the main 2h loop. State is tracked in a small marker file.
BUMERAN_INTERVAL = int(os.environ.get("BUMERAN_INTERVAL_HOURS", "24")) * 3600
BUMERAN_STATE_PATH = os.environ.get("BUMERAN_STATE_PATH", "/data/.bumeran_last_run")

COMPUTRABAJO_INTERVAL = int(os.environ.get("COMPUTRABAJO_INTERVAL_HOURS", "24")) * 3600
COMPUTRABAJO_STATE_PATH = os.environ.get("COMPUTRABAJO_STATE_PATH", "/data/.computrabajo_last_run")

# GetOnBrd's RSS feed always returns empty, so this scrapes the search page
# directly. It's a single page load (no per-job detail fetch), much lighter
# than Bumeran/Computrabajo, but kept on the same daily cadence for consistency
# and to avoid hammering the site across every 2h cycle.
GETONBRD_INTERVAL = int(os.environ.get("GETONBRD_INTERVAL_HOURS", "24")) * 3600
GETONBRD_STATE_PATH = os.environ.get("GETONBRD_STATE_PATH", "/data/.getonbrd_last_run")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def get_profiles(conn):
    rows = conn.execute("SELECT * FROM profiles WHERE enabled = 1").fetchall()
    return [dict(r) for r in rows]


def wait_for_db(retries=30, delay=2):
    for i in range(retries):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("SELECT 1 FROM profiles LIMIT 1")
            conn.close()
            logger.info("Database ready")
            return True
        except Exception:
            logger.info(f"Waiting for database... ({i+1}/{retries})")
            time.sleep(delay)
    return False


def upsert_job(conn, job: dict) -> bool:
    """Insert job if not exists. Returns True if new."""
    try:
        conn.execute(
            """INSERT OR IGNORE INTO jobs 
               (external_id, title, company, url, source, description, 
                tags, work_mode, salary, posted_at, location)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job.get("external_id"),
                job.get("title", ""),
                job.get("company", ""),
                job.get("url", ""),
                job.get("source", ""),
                job.get("description", ""),
                job.get("tags", "[]"),
                job.get("work_mode", "unknown"),
                job.get("salary", ""),
                job.get("posted_at"),
                job.get("location", ""),
            ),
        )
        return conn.execute("SELECT changes()").fetchone()[0] > 0
    except Exception as e:
        logger.error(f"DB insert error: {e} | job: {job.get('title', '?')}")
        return False


def update_source_stats(conn, name: str, count: int):
    conn.execute(
        """INSERT INTO sources (name, url, type, last_fetched, last_count)
           VALUES (?, '', 'rss', datetime('now'), ?)
           ON CONFLICT(name) DO UPDATE SET 
           last_fetched = datetime('now'), last_count = ?""",
        (name, count, count),
    )


def register_sources(conn, config):
    """Ensure every source from config.yaml exists in the sources table,
    even before its first successful fetch, so it can be toggled from the UI."""
    for source in config.get("rss_sources", []):
        conn.execute(
            """INSERT INTO sources (name, url, type, enabled)
               VALUES (?, ?, 'rss', 1)
               ON CONFLICT(name) DO NOTHING""",
            (source["name"], source.get("url", "")),
        )
    for source in config.get("search_sources", []):
        conn.execute(
            """INSERT INTO sources (name, url, type, enabled)
               VALUES (?, ?, 'search', 1)
               ON CONFLICT(name) DO NOTHING""",
            (source["name"], source.get("base_url", "")),
        )
    # Bumeran and Computrabajo are code-defined sources (not in config.yaml)
    conn.execute(
        """INSERT INTO sources (name, url, type, enabled)
           VALUES ('Bumeran', 'https://www.bumeran.com.ar', 'scrape', 1)
           ON CONFLICT(name) DO NOTHING"""
    )
    conn.execute(
        """INSERT INTO sources (name, url, type, enabled)
           VALUES ('Computrabajo', 'https://ar.computrabajo.com', 'scrape', 1)
           ON CONFLICT(name) DO NOTHING"""
    )
    conn.execute(
        """INSERT INTO sources (name, url, type, enabled)
           VALUES ('GetOnBrd', 'https://www.getonbrd.com', 'scrape', 1)
           ON CONFLICT(name) DO NOTHING"""
    )
    conn.commit()


def get_enabled_source_names(conn) -> set:
    rows = conn.execute("SELECT name FROM sources WHERE enabled = 1").fetchall()
    return {r["name"] for r in rows}


def _should_run_daily(state_path: str, interval_seconds: int) -> bool:
    """Generic daily-cadence check via a marker file (separate from the
    main fetch cycle's DB-backed timing). Used by scrapers that are too
    heavy/slow or too risky (Cloudflare-protected) to run every cycle."""
    if not os.path.exists(state_path):
        return True
    try:
        last_run = float(open(state_path).read().strip())
    except (ValueError, OSError):
        return True
    return (time.time() - last_run) >= interval_seconds


def _mark_ran(state_path: str):
    with open(state_path, "w") as f:
        f.write(str(time.time()))


def should_run_bumeran() -> bool:
    return _should_run_daily(BUMERAN_STATE_PATH, BUMERAN_INTERVAL)


def mark_bumeran_ran():
    _mark_ran(BUMERAN_STATE_PATH)


def should_run_computrabajo() -> bool:
    return _should_run_daily(COMPUTRABAJO_STATE_PATH, COMPUTRABAJO_INTERVAL)


def mark_computrabajo_ran():
    _mark_ran(COMPUTRABAJO_STATE_PATH)


def should_run_getonbrd() -> bool:
    return _should_run_daily(GETONBRD_STATE_PATH, GETONBRD_INTERVAL)


def mark_getonbrd_ran():
    _mark_ran(GETONBRD_STATE_PATH)


def run_fetch():
    logger.info("=" * 50)
    logger.info("Starting fetch cycle")

    if not wait_for_db():
        logger.error("Database not available, skipping cycle")
        return

    config = load_config()
    conn = get_db()
    register_sources(conn, config)
    enabled_names = get_enabled_source_names(conn)
    profiles = get_profiles(conn)

    if not profiles:
        logger.warning("No enabled profiles found — using defaults")
        profiles = [{"name": "DevOps", "keywords": ["devops", "sysadmin", "automation engineer"]}]

    log_id = conn.execute(
        "INSERT INTO fetch_log (started_at) VALUES (datetime('now'))"
    ).lastrowid
    conn.commit()

    total_found = 0
    new_jobs = 0
    errors = []
    skipped = 0

    # ── Category A: RSS ───────────────────────────────────────────────────────
    for source in config.get("rss_sources", []):
        if source["name"] not in enabled_names:
            skipped += 1
            continue
        try:
            jobs = fetch_rss(source, profiles)
            inserted = 0
            for job in jobs:
                if upsert_job(conn, job):
                    inserted += 1
            conn.commit()
            new_jobs += inserted
            total_found += len(jobs)
            update_source_stats(conn, source["name"], len(jobs))
            conn.commit()
            if jobs:
                logger.info(f"[RSS] {source['name']}: {len(jobs)} fetched, {inserted} new")
        except Exception as e:
            err = f"RSS {source['name']}: {e}"
            logger.error(err)
            errors.append(err)

    # ── Jobicy JSON API ──────────────────────────────────────────────────────
    try:
        jobs = fetch_jobicy(profiles)
        inserted = 0
        for job in jobs:
            if upsert_job(conn, job):
                inserted += 1
        conn.commit()
        new_jobs += inserted
        total_found += len(jobs)
        update_source_stats(conn, "Jobicy", len(jobs))
        conn.commit()
    except Exception as e:
        err = f"Jobicy API: {e}"
        logger.error(err)
        errors.append(err)

    # ── Bumeran (Playwright + stealth — runs at most once/day) ────────────────
    if "Bumeran" in enabled_names and should_run_bumeran():
        try:
            logger.info("[Bumeran] Daily scrape window reached, running...")
            jobs = fetch_bumeran(profiles=profiles)
            inserted = 0
            for job in jobs:
                if upsert_job(conn, job):
                    inserted += 1
            conn.commit()
            new_jobs += inserted
            total_found += len(jobs)
            update_source_stats(conn, "Bumeran", len(jobs))
            conn.commit()
            mark_bumeran_ran()
            logger.info(f"[Bumeran] {len(jobs)} fetched, {inserted} new")
        except Exception as e:
            err = f"Bumeran scrape: {e}"
            logger.error(err)
            errors.append(err)
    elif "Bumeran" in enabled_names:
        logger.info("[Bumeran] Skipping — daily window not reached yet")

    # ── Computrabajo (Playwright + stealth — runs at most once/day) ───────────
    if "Computrabajo" in enabled_names and should_run_computrabajo():
        try:
            logger.info("[Computrabajo] Daily scrape window reached, running...")
            jobs = fetch_computrabajo(profiles=profiles)
            inserted = 0
            for job in jobs:
                if upsert_job(conn, job):
                    inserted += 1
            conn.commit()
            new_jobs += inserted
            total_found += len(jobs)
            update_source_stats(conn, "Computrabajo", len(jobs))
            conn.commit()
            mark_computrabajo_ran()
            logger.info(f"[Computrabajo] {len(jobs)} fetched, {inserted} new")
        except Exception as e:
            err = f"Computrabajo scrape: {e}"
            logger.error(err)
            errors.append(err)
    elif "Computrabajo" in enabled_names:
        logger.info("[Computrabajo] Skipping — daily window not reached yet")

    # ── GetOnBrd (Playwright + stealth — runs at most once/day) ───────────────
    if "GetOnBrd" in enabled_names and should_run_getonbrd():
        try:
            logger.info("[GetOnBrd] Daily scrape window reached, running...")
            jobs = fetch_getonbrd(profiles=profiles)
            inserted = 0
            for job in jobs:
                if upsert_job(conn, job):
                    inserted += 1
            conn.commit()
            new_jobs += inserted
            total_found += len(jobs)
            update_source_stats(conn, "GetOnBrd", len(jobs))
            conn.commit()
            mark_getonbrd_ran()
            logger.info(f"[GetOnBrd] {len(jobs)} fetched, {inserted} new")
        except Exception as e:
            err = f"GetOnBrd scrape: {e}"
            logger.error(err)
            errors.append(err)
    elif "GetOnBrd" in enabled_names:
        logger.info("[GetOnBrd] Skipping — daily window not reached yet")

    # ── Category B: Claude web search ─────────────────────────────────────────
    for source in config.get("search_sources", []):
        if source["name"] not in enabled_names:
            skipped += 1
            continue
        try:
            jobs = fetch_via_claude_search(source, profiles)
            inserted = 0
            for job in jobs:
                if upsert_job(conn, job):
                    inserted += 1
            conn.commit()
            new_jobs += inserted
            total_found += len(jobs)
            update_source_stats(conn, source["name"], len(jobs))
            conn.commit()
        except Exception as e:
            err = f"Search {source['name']}: {e}"
            logger.error(err)
            errors.append(err)

    # ── Finalize log ──────────────────────────────────────────────────────────
    conn.execute(
        """UPDATE fetch_log SET 
           finished_at = datetime('now'), 
           total_found = ?,
           new_jobs = ?,
           errors = ?
           WHERE id = ?""",
        (total_found, new_jobs, json.dumps(errors), log_id),
    )
    conn.commit()
    conn.close()

    logger.info(f"Fetch complete — found: {total_found}, new: {new_jobs}, errors: {len(errors)}, skipped (disabled): {skipped}")
    logger.info("=" * 50)


def main():
    once = "--once" in sys.argv

    if once:
        run_fetch()
        return

    logger.info(f"Fetcher starting. Interval: {FETCH_INTERVAL // 3600}h")
    time.sleep(15)  # wait for api/db to initialize
    run_fetch()

    while True:
        logger.info(f"Next fetch in {FETCH_INTERVAL // 3600} hours")
        time.sleep(FETCH_INTERVAL)
        run_fetch()


if __name__ == "__main__":
    main()
