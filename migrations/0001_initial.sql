PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  start_date TEXT,
  deadline TEXT,
  department TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT '진행 중',
  priority TEXT NOT NULL DEFAULT '보통',
  memo TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT '기타',
  status TEXT NOT NULL DEFAULT '기획',
  previous_status TEXT,
  priority TEXT NOT NULL DEFAULT '보통',
  deadline TEXT,
  execution_date TEXT,
  start_time TEXT,
  end_time TEXT,
  next_action TEXT NOT NULL DEFAULT '',
  waiting_for TEXT,
  waiting_type TEXT,
  followup_at TEXT,
  description TEXT NOT NULL DEFAULT '',
  project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
  workflow_steps TEXT NOT NULL DEFAULT '[]',
  reminder_enabled INTEGER NOT NULL DEFAULT 1,
  reminder_minutes_before INTEGER NOT NULL DEFAULT 0,
  alarm_last_fired_at TEXT,
  repeat_type TEXT NOT NULL DEFAULT 'none',
  repeat_days TEXT NOT NULL DEFAULT '[]',
  repeat_start_date TEXT,
  repeat_end_date TEXT,
  excluded_dates TEXT NOT NULL DEFAULT '[]',
  sort_order INTEGER NOT NULL DEFAULT 9999,
  completed_at TEXT,
  reopened_at TEXT,
  deleted_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_status_history (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
  from_status TEXT,
  to_status TEXT NOT NULL,
  changed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_records (
  id TEXT PRIMARY KEY,
  task_id TEXT REFERENCES tasks(task_id) ON DELETE SET NULL,
  platform TEXT NOT NULL DEFAULT 'YouTube',
  title TEXT NOT NULL,
  professor TEXT NOT NULL DEFAULT '',
  department TEXT NOT NULL DEFAULT '',
  content_type TEXT NOT NULL DEFAULT '',
  upload_date TEXT,
  url TEXT NOT NULL DEFAULT '',
  memo TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT '참고자료',
  content TEXT NOT NULL DEFAULT '',
  task_id TEXT REFERENCES tasks(task_id) ON DELETE SET NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_active_execution
ON tasks(deleted_at, execution_date, start_time);

CREATE INDEX IF NOT EXISTS idx_tasks_active_deadline
ON tasks(deleted_at, deadline);

CREATE INDEX IF NOT EXISTS idx_tasks_project
ON tasks(project_id);

CREATE INDEX IF NOT EXISTS idx_tasks_followup
ON tasks(followup_at)
WHERE waiting_for IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_history_task_time
ON task_status_history(task_id, changed_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_content_records_task_unique
ON content_records(task_id)
WHERE task_id IS NOT NULL;

PRAGMA optimize;
