CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    description TEXT,
    tags TEXT DEFAULT '[]',
    work_mode TEXT DEFAULT 'unknown',
    salary TEXT,
    posted_at TEXT,
    fetched_at TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'new',
    applied_at TEXT,
    notes TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_external_id ON jobs(external_id);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT 'rss',
    enabled INTEGER DEFAULT 1,
    last_fetched TEXT,
    last_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    keywords TEXT NOT NULL,
    enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fetch_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT DEFAULT (datetime('now')),
    finished_at TEXT,
    total_found INTEGER DEFAULT 0,
    new_jobs INTEGER DEFAULT 0,
    errors TEXT DEFAULT '[]'
);

INSERT OR IGNORE INTO profiles (name, keywords) VALUES
    ('DevOps', '["devops", "dev ops", "devsecops"]'),
    ('SRE', '["sre", "site reliability", "site reliability engineer"]'),
    ('Infrastructure', '["infrastructure engineer", "infra engineer", "platform engineer"]'),
    ('Automation', '["automation engineer", "automatización", "automatizacion"]'),
    ('Linux/SysAdmin', '["linux administrator", "sysadmin", "unix administrator", "administrador linux"]');
