from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional

app = FastAPI(title="Job Radar API")

DB_PATH = os.environ.get("DATABASE_URL", "/data/jobradar.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_sql_path = "/app/init.sql"
    if os.path.exists(init_sql_path):
        with open(init_sql_path) as f:
            conn.executescript(f.read())
    conn.commit()
    conn.close()


@app.on_event("startup")
def on_startup():
    init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Jobs ──────────────────────────────────────────────────────────────────────

@app.get("/jobs")
def list_jobs(
    status: Optional[str] = None,
    source: Optional[str] = None,
    work_mode: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 300,
    offset: int = 0,
):
    conn = get_db()
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if source:
        query += " AND source = ?"
        params.append(source)
    if work_mode:
        query += " AND work_mode = ?"
        params.append(work_mode)
    if search:
        query += " AND (title LIKE ? OR company LIKE ? OR description LIKE ?)"
        params += [f"%{search}%"] * 3

    query += " ORDER BY fetched_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.patch("/jobs/{job_id}/status")
def update_job_status(job_id: int, body: dict):
    status = body.get("status")
    if status not in ("new", "seen", "applied", "discarded"):
        raise HTTPException(400, "Invalid status")

    conn = get_db()
    applied_at = datetime.now().isoformat() if status == "applied" else None
    conn.execute(
        "UPDATE jobs SET status = ?, applied_at = COALESCE(?, applied_at) WHERE id = ?",
        (status, applied_at, job_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.patch("/jobs/{job_id}/notes")
def update_job_notes(job_id: int, body: dict):
    conn = get_db()
    conn.execute("UPDATE jobs SET notes = ? WHERE id = ?", (body.get("notes", ""), job_id))
    conn.commit()
    conn.close()
    return {"ok": True}


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/stats")
def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    new = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'new'").fetchone()[0]
    applied = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'applied'").fetchone()[0]
    seen = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'seen'").fetchone()[0]
    today = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE DATE(fetched_at) = DATE('now')"
    ).fetchone()[0]
    by_source = conn.execute(
        "SELECT source, COUNT(*) as count FROM jobs GROUP BY source ORDER BY count DESC LIMIT 10"
    ).fetchall()
    last_fetch = conn.execute(
        "SELECT finished_at, new_jobs FROM fetch_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    return {
        "total": total,
        "new": new,
        "seen": seen,
        "applied": applied,
        "today": today,
        "by_source": [dict(r) for r in by_source],
        "last_fetch": dict(last_fetch) if last_fetch else None,
    }


# ── Sources ───────────────────────────────────────────────────────────────────

@app.get("/sources")
def list_sources():
    conn = get_db()
    rows = conn.execute("SELECT * FROM sources ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.patch("/sources/{source_id}/toggle")
def toggle_source(source_id: int):
    conn = get_db()
    conn.execute("UPDATE sources SET enabled = NOT enabled WHERE id = ?", (source_id,))
    conn.commit()
    row = conn.execute("SELECT enabled FROM sources WHERE id = ?", (source_id,)).fetchone()
    conn.close()
    return {"enabled": bool(row["enabled"])}


# ── Profiles ──────────────────────────────────────────────────────────────────

@app.get("/profiles")
def list_profiles():
    conn = get_db()
    rows = conn.execute("SELECT * FROM profiles").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["keywords"] = json.loads(d["keywords"])
        result.append(d)
    return result


class ProfileBody(BaseModel):
    name: str
    keywords: list[str]
    enabled: bool = True


@app.post("/profiles")
def create_profile(body: ProfileBody):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO profiles (name, keywords, enabled) VALUES (?, ?, ?)",
        (body.name, json.dumps(body.keywords), int(body.enabled)),
    )
    conn.commit()
    conn.close()
    return {"id": cur.lastrowid}


@app.put("/profiles/{profile_id}")
def update_profile(profile_id: int, body: ProfileBody):
    conn = get_db()
    conn.execute(
        "UPDATE profiles SET name = ?, keywords = ?, enabled = ? WHERE id = ?",
        (body.name, json.dumps(body.keywords), int(body.enabled), profile_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int):
    conn = get_db()
    conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ── Fetch trigger ─────────────────────────────────────────────────────────────

@app.post("/fetch/trigger")
def trigger_fetch():
    import subprocess
    subprocess.Popen(
        ["python3", "/app/main.py", "--once"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return {"ok": True, "message": "Fetch triggered"}


@app.get("/fetch/log")
def fetch_log():
    conn = get_db()
    rows = conn.execute("SELECT * FROM fetch_log ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/health")
def health():
    return {"status": "ok"}
