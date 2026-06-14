CREATE TABLE IF NOT EXISTS insight_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name TEXT NOT NULL,
    crawler_type TEXT NOT NULL,
    started_ts INTEGER NOT NULL,
    finished_ts INTEGER,
    exit_code INTEGER,
    notes_crawled INTEGER DEFAULT 0,
    comments_crawled INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    error_msg TEXT
);
CREATE INDEX IF NOT EXISTS idx_insight_runs_job ON insight_runs (job_name, started_ts);
