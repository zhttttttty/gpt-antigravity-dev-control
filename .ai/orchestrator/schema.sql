PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS task_runtime (task_id TEXT PRIMARY KEY, fs_state TEXT NOT NULL, runtime_state TEXT NOT NULL DEFAULT 'IDLE', risk TEXT NOT NULL DEFAULT 'medium', attempt INTEGER NOT NULL DEFAULT 1, branch TEXT, worktree_path TEXT, lease_owner TEXT, lease_expires_at TEXT, executor_interaction_id TEXT, executor_environment_id TEXT, reviewer_response_id TEXT, last_error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, event_type TEXT NOT NULL, payload_json TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS approvals (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, approval_type TEXT NOT NULL, approved_by TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_task_runtime_state ON task_runtime(runtime_state);
