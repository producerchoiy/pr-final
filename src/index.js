const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

const SESSION_COOKIE = "pr_flow_session";
const SESSION_DURATION_MS = 12 * 60 * 60 * 1000;

const TASK_FIELDS = [
  "title", "category", "status", "previous_status", "priority", "deadline",
  "execution_date", "start_time", "end_time", "next_action", "waiting_for",
  "waiting_type", "followup_at", "description", "project_id", "workflow_steps",
  "reminder_enabled", "reminder_minutes_before", "alarm_last_fired_at",
  "repeat_type", "repeat_days", "repeat_start_date", "repeat_end_date",
  "excluded_dates", "sort_order", "completed_at", "reopened_at", "deleted_at",
];

const PROJECT_FIELDS = [
  "name", "description", "start_date", "deadline", "department", "status",
  "priority", "memo",
];

const CONTENT_FIELDS = [
  "task_id", "platform", "title", "professor", "department", "content_type",
  "upload_date", "url", "memo",
];

const DOCUMENT_FIELDS = ["title", "category", "content", "task_id"];

function response(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...JSON_HEADERS, ...extraHeaders },
  });
}

function error(message, status = 400) {
  return response({ ok: false, message }, status);
}

function now() {
  return new Date().toISOString();
}

function base64Url(bytes) {
  let binary = "";
  for (const byte of new Uint8Array(bytes)) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

function sessionSecret(env) {
  return String(env.APP_LOCK_PASSWORD || "0915");
}

async function sessionSignature(secret, expiresAt) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return base64Url(await crypto.subtle.sign("HMAC", key, encoder.encode(String(expiresAt))));
}

async function createSessionToken(env) {
  const expiresAt = Date.now() + SESSION_DURATION_MS;
  return `${expiresAt}.${await sessionSignature(sessionSecret(env), expiresAt)}`;
}

function cookieValue(request, name) {
  const cookies = request.headers.get("cookie") || "";
  for (const part of cookies.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return rest.join("=");
  }
  return "";
}

async function hasValidSession(request, env) {
  const token = cookieValue(request, SESSION_COOKIE);
  const [expiresText, signature] = token.split(".");
  const expiresAt = Number(expiresText);
  if (!expiresAt || expiresAt <= Date.now() || !signature) return false;
  const expected = await sessionSignature(sessionSecret(env), expiresAt);
  if (signature.length !== expected.length) return false;
  let difference = 0;
  for (let index = 0; index < signature.length; index += 1) {
    difference |= signature.charCodeAt(index) ^ expected.charCodeAt(index);
  }
  return difference === 0;
}

function sessionCookie(token) {
  return `${SESSION_COOKIE}=${token}; Path=/; HttpOnly; Secure; SameSite=Strict`;
}

function clearSessionCookie() {
  return `${SESSION_COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0`;
}

function id(prefix) {
  return `${prefix}-${crypto.randomUUID().replaceAll("-", "").slice(0, 12).toUpperCase()}`;
}

function taskId() {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const get = (type) => parts.find((part) => part.type === type)?.value || "00";
  const seoul = `${get("year")}${get("month")}${get("day")}`;
  return `TASK-${seoul}-${crypto.randomUUID().slice(0, 6).toUpperCase()}`;
}

function parseJson(value, fallback = []) {
  if (Array.isArray(value)) return value;
  try {
    const parsed = JSON.parse(value || "[]");
    return Array.isArray(parsed) ? parsed : fallback;
  } catch {
    return fallback;
  }
}

function hydrateTask(row) {
  if (!row) return row;
  return {
    ...row,
    reminder_enabled: Boolean(row.reminder_enabled),
    workflow_steps: parseJson(row.workflow_steps),
    repeat_days: parseJson(row.repeat_days),
    excluded_dates: parseJson(row.excluded_dates),
  };
}

function cleanValue(field, value) {
  if (["workflow_steps", "repeat_days", "excluded_dates"].includes(field)) {
    return JSON.stringify(Array.isArray(value) ? value : []);
  }
  if (field === "reminder_enabled") return value ? 1 : 0;
  if (field === "reminder_minutes_before" || field === "sort_order") {
    return Number.isFinite(Number(value)) ? Number(value) : 0;
  }
  if (value === "") return null;
  return value ?? null;
}

async function bodyOf(request) {
  try {
    return await request.json();
  } catch {
    throw new Error("요청 내용을 읽을 수 없습니다.");
  }
}

async function currentTask(db, taskIdValue) {
  return db.prepare("SELECT * FROM tasks WHERE task_id = ? AND deleted_at IS NULL")
    .bind(taskIdValue).first();
}

async function bootstrap(db) {
  const [tasks, projects, records, documents, history] = await Promise.all([
    db.prepare("SELECT * FROM tasks WHERE deleted_at IS NULL ORDER BY sort_order, execution_date, start_time").all(),
    db.prepare("SELECT * FROM projects ORDER BY deadline, name").all(),
    db.prepare("SELECT * FROM content_records ORDER BY upload_date DESC, updated_at DESC").all(),
    db.prepare("SELECT * FROM documents ORDER BY updated_at DESC").all(),
    db.prepare("SELECT * FROM task_status_history ORDER BY changed_at DESC LIMIT 500").all(),
  ]);
  return {
    ok: true,
    tasks: tasks.results.map(hydrateTask),
    projects: projects.results,
    content_records: records.results,
    documents: documents.results,
    task_status_history: history.results,
    server_time: now(),
  };
}

async function createTask(db, payload) {
  const title = String(payload.title || "").trim();
  if (!title) return error("업무명을 입력해 주세요.");
  const timestamp = now();
  const taskIdValue = taskId();
  const row = {
    task_id: taskIdValue,
    title,
    category: payload.category || "기타",
    status: payload.status || "기획",
    previous_status: null,
    priority: payload.priority || "보통",
    deadline: payload.deadline || null,
    execution_date: payload.execution_date || null,
    start_time: payload.start_time || null,
    end_time: payload.end_time || null,
    next_action: payload.next_action || "",
    waiting_for: payload.waiting_for || null,
    waiting_type: payload.waiting_type || null,
    followup_at: payload.followup_at || null,
    description: payload.description || "",
    project_id: payload.project_id || null,
    workflow_steps: JSON.stringify(payload.workflow_steps || []),
    reminder_enabled: payload.reminder_enabled === false ? 0 : 1,
    reminder_minutes_before: Number(payload.reminder_minutes_before ?? 30),
    alarm_last_fired_at: null,
    repeat_type: payload.repeat_type || "none",
    repeat_days: JSON.stringify(payload.repeat_days || []),
    repeat_start_date: payload.repeat_start_date || payload.execution_date || null,
    repeat_end_date: payload.repeat_end_date || null,
    excluded_dates: "[]",
    sort_order: Number(payload.sort_order || 9999),
    completed_at: null,
    reopened_at: null,
    deleted_at: null,
    created_at: timestamp,
    updated_at: timestamp,
  };
  const columns = Object.keys(row);
  const placeholders = columns.map(() => "?").join(", ");
  await db.prepare(`INSERT INTO tasks (${columns.join(", ")}) VALUES (${placeholders})`)
    .bind(...columns.map((column) => row[column])).run();
  return response({ ok: true, task: hydrateTask(row) }, 201);
}

async function updateTask(db, taskIdValue, payload) {
  const current = await currentTask(db, taskIdValue);
  if (!current) return error("업무를 찾을 수 없습니다.", 404);
  const entries = TASK_FIELDS
    .filter((field) => Object.hasOwn(payload, field))
    .map((field) => [field, cleanValue(field, payload[field])]);
  if (!entries.length) return response({ ok: true, task: hydrateTask(current) });
  const timestamp = now();
  const statusChanged = Object.hasOwn(payload, "status") && payload.status !== current.status;
  if (statusChanged && payload.status === "완료") {
    if (!entries.some(([field]) => field === "previous_status")) entries.push(["previous_status", current.status || "진행 중"]);
    if (!entries.some(([field]) => field === "completed_at")) entries.push(["completed_at", timestamp]);
  } else if (statusChanged && current.status === "완료") {
    if (!entries.some(([field]) => field === "completed_at")) entries.push(["completed_at", null]);
    if (!entries.some(([field]) => field === "reopened_at")) entries.push(["reopened_at", timestamp]);
  }
  entries.push(["updated_at", timestamp]);
  const statement = db.prepare(
    `UPDATE tasks SET ${entries.map(([field]) => `${field} = ?`).join(", ")} WHERE task_id = ?`,
  ).bind(...entries.map(([, value]) => value), taskIdValue);
  const batch = [statement];
  if (statusChanged) {
    batch.push(db.prepare(
      "INSERT INTO task_status_history (id, task_id, from_status, to_status, changed_at) VALUES (?, ?, ?, ?, ?)",
    ).bind(id("STATUS"), taskIdValue, current.status, payload.status, timestamp));
  }
  await db.batch(batch);
  return response({ ok: true });
}

async function completeTask(db, taskIdValue) {
  const task = await currentTask(db, taskIdValue);
  if (!task) return error("업무를 찾을 수 없습니다.", 404);
  if (task.status === "완료") return response({ ok: true });
  const timestamp = now();
  await db.batch([
    db.prepare("UPDATE tasks SET previous_status = ?, status = '완료', completed_at = ?, updated_at = ? WHERE task_id = ?")
      .bind(task.status || "진행 중", timestamp, timestamp, taskIdValue),
    db.prepare("INSERT INTO task_status_history (id, task_id, from_status, to_status, changed_at) VALUES (?, ?, ?, '완료', ?)")
      .bind(id("STATUS"), taskIdValue, task.status, timestamp),
  ]);
  return response({ ok: true });
}

async function reopenTask(db, taskIdValue) {
  const task = await currentTask(db, taskIdValue);
  if (!task) return error("업무를 찾을 수 없습니다.", 404);
  if (task.status !== "완료") return response({ ok: true });
  const restored = task.previous_status && task.previous_status !== "완료" ? task.previous_status : "진행 중";
  const steps = parseJson(task.workflow_steps);
  const nextAction = steps.find((step) => !step.completed)?.title || "업무 재개";
  const timestamp = now();
  await db.batch([
    db.prepare("UPDATE tasks SET status = ?, completed_at = NULL, reopened_at = ?, next_action = ?, updated_at = ? WHERE task_id = ?")
      .bind(restored, timestamp, nextAction, timestamp, taskIdValue),
    db.prepare("INSERT INTO task_status_history (id, task_id, from_status, to_status, changed_at) VALUES (?, ?, '완료', ?, ?)")
      .bind(id("STATUS"), taskIdValue, restored, timestamp),
  ]);
  return response({ ok: true });
}

async function deleteTask(db, taskIdValue) {
  const task = await currentTask(db, taskIdValue);
  if (!task) return error("업무를 찾을 수 없습니다.", 404);
  const timestamp = now();
  await db.batch([
    db.prepare("UPDATE tasks SET deleted_at = ?, updated_at = ? WHERE task_id = ?")
      .bind(timestamp, timestamp, taskIdValue),
    db.prepare("INSERT INTO task_status_history (id, task_id, from_status, to_status, changed_at) VALUES (?, ?, ?, '삭제', ?)")
      .bind(id("STATUS"), taskIdValue, task.status, timestamp),
  ]);
  return response({ ok: true });
}

async function excludeOccurrence(db, taskIdValue, payload) {
  const task = await currentTask(db, taskIdValue);
  if (!task) return error("업무를 찾을 수 없습니다.", 404);
  const occurrenceDate = String(payload.occurrence_date || "").slice(0, 10);
  if (!occurrenceDate) return error("제외할 날짜가 필요합니다.");
  const dates = new Set(parseJson(task.excluded_dates));
  dates.add(occurrenceDate);
  await db.prepare("UPDATE tasks SET excluded_dates = ?, updated_at = ? WHERE task_id = ?")
    .bind(JSON.stringify([...dates].sort()), now(), taskIdValue).run();
  return response({ ok: true });
}

async function updateOrder(db, payload) {
  const ids = Array.isArray(payload.task_ids) ? payload.task_ids : [];
  if (!ids.length) return error("저장할 업무 순서가 없습니다.");
  const timestamp = now();
  const statements = ids.map((taskIdValue, index) => db.prepare(
    "UPDATE tasks SET sort_order = ?, updated_at = ? WHERE task_id = ? AND deleted_at IS NULL",
  ).bind(index + 1, timestamp, taskIdValue));
  await db.batch(statements);
  return response({ ok: true });
}

async function createProject(db, payload) {
  const name = String(payload.name || "").trim();
  if (!name) return error("프로젝트명을 입력해 주세요.");
  const timestamp = now();
  const row = {
    id: id("PROJECT"), name, description: payload.description || "",
    start_date: payload.start_date || null, deadline: payload.deadline || null,
    department: payload.department || "", status: payload.status || "진행 중",
    priority: payload.priority || "보통", memo: payload.memo || "",
    created_at: timestamp, updated_at: timestamp,
  };
  const fields = Object.keys(row);
  await db.prepare(`INSERT INTO projects (${fields.join(", ")}) VALUES (${fields.map(() => "?").join(", ")})`)
    .bind(...fields.map((field) => row[field])).run();
  return response({ ok: true, project: row }, 201);
}

async function updateProject(db, projectId, payload) {
  const entries = PROJECT_FIELDS.filter((field) => Object.hasOwn(payload, field))
    .map((field) => [field, payload[field] === "" ? null : payload[field]]);
  if (!entries.length) return response({ ok: true });
  entries.push(["updated_at", now()]);
  await db.prepare(`UPDATE projects SET ${entries.map(([field]) => `${field} = ?`).join(", ")} WHERE id = ?`)
    .bind(...entries.map(([, value]) => value), projectId).run();
  return response({ ok: true });
}

async function deleteProject(db, projectId, cascade) {
  if (cascade) {
    const rows = await db.prepare("SELECT task_id, status FROM tasks WHERE project_id = ? AND deleted_at IS NULL")
      .bind(projectId).all();
    const timestamp = now();
    const statements = [];
    for (const task of rows.results) {
      statements.push(db.prepare("UPDATE tasks SET deleted_at = ?, updated_at = ? WHERE task_id = ?")
        .bind(timestamp, timestamp, task.task_id));
      statements.push(db.prepare("INSERT INTO task_status_history (id, task_id, from_status, to_status, changed_at) VALUES (?, ?, ?, '삭제', ?)")
        .bind(id("STATUS"), task.task_id, task.status, timestamp));
    }
    statements.push(db.prepare("DELETE FROM projects WHERE id = ?").bind(projectId));
    await db.batch(statements);
  } else {
    await db.batch([
      db.prepare("UPDATE tasks SET project_id = NULL, updated_at = ? WHERE project_id = ?").bind(now(), projectId),
      db.prepare("DELETE FROM projects WHERE id = ?").bind(projectId),
    ]);
  }
  return response({ ok: true });
}

async function createRecord(db, payload) {
  const title = String(payload.title || "").trim();
  if (!title) return error("콘텐츠 제목을 입력해 주세요.");
  if (payload.task_id) {
    const existing = await db.prepare("SELECT id FROM content_records WHERE task_id = ?").bind(payload.task_id).first();
    if (existing) return error("이 업무에는 이미 실적이 있습니다. 기존 기록을 수정해 주세요.", 409);
  }
  const timestamp = now();
  const row = {
    id: id("CONTENT"), task_id: payload.task_id || null, platform: payload.platform || "YouTube",
    title, professor: payload.professor || "", department: payload.department || "",
    content_type: payload.content_type || "", upload_date: payload.upload_date || null,
    url: payload.url || "", memo: payload.memo || "", created_at: timestamp, updated_at: timestamp,
  };
  const fields = Object.keys(row);
  await db.prepare(`INSERT INTO content_records (${fields.join(", ")}) VALUES (${fields.map(() => "?").join(", ")})`)
    .bind(...fields.map((field) => row[field])).run();
  return response({ ok: true, record: row }, 201);
}

async function updateSimple(db, table, key, itemId, payload, allowed) {
  const entries = allowed.filter((field) => Object.hasOwn(payload, field))
    .map((field) => [field, payload[field] === "" ? null : payload[field]]);
  if (!entries.length) return response({ ok: true });
  entries.push(["updated_at", now()]);
  await db.prepare(`UPDATE ${table} SET ${entries.map(([field]) => `${field} = ?`).join(", ")} WHERE ${key} = ?`)
    .bind(...entries.map(([, value]) => value), itemId).run();
  return response({ ok: true });
}

async function createDocument(db, payload) {
  const title = String(payload.title || "").trim();
  if (!title) return error("자료 제목을 입력해 주세요.");
  const timestamp = now();
  const row = {
    id: id("DOC"), title, category: payload.category || "참고자료",
    content: payload.content || "", task_id: payload.task_id || null,
    created_at: timestamp, updated_at: timestamp,
  };
  await db.prepare("INSERT INTO documents (id, title, category, content, task_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)")
    .bind(row.id, row.title, row.category, row.content, row.task_id, row.created_at, row.updated_at).run();
  return response({ ok: true, document: row }, 201);
}

async function routeApi(request, env) {
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method;

  if (path === "/api/unlock" && method === "POST") {
    const payload = await bodyOf(request);
    const password = String(env.APP_LOCK_PASSWORD || "0915");
    if (payload.password !== password) return error("비밀번호가 맞지 않습니다.", 401);
    const token = await createSessionToken(env);
    return response({ ok: true }, 200, { "set-cookie": sessionCookie(token) });
  }
  if (path === "/api/health") return response({ ok: true, storage: env.DB ? "D1" : "not-connected", time: now() });
  if (path === "/api/session" && method === "GET") {
    return await hasValidSession(request, env)
      ? response({ ok: true })
      : error("잠금 해제가 필요합니다.", 401);
  }
  if (path === "/api/lock" && method === "POST") {
    return response({ ok: true }, 200, { "set-cookie": clearSessionCookie() });
  }
  if (!(await hasValidSession(request, env))) return error("잠금 해제가 필요합니다.", 401);
  if (!env.DB) return error("D1 데이터베이스가 연결되지 않았습니다. README의 D1 연결 순서를 확인해 주세요.", 503);
  if (path === "/api/bootstrap" && method === "GET") return response(await bootstrap(env.DB));
  if (path === "/api/tasks" && method === "POST") return createTask(env.DB, await bodyOf(request));
  if (path === "/api/task-order" && method === "POST") return updateOrder(env.DB, await bodyOf(request));
  if (path === "/api/projects" && method === "POST") return createProject(env.DB, await bodyOf(request));
  if (path === "/api/content-records" && method === "POST") return createRecord(env.DB, await bodyOf(request));
  if (path === "/api/documents" && method === "POST") return createDocument(env.DB, await bodyOf(request));

  const taskMatch = path.match(/^\/api\/tasks\/([^/]+)(?:\/(complete|reopen|exclude|alarm))?$/);
  if (taskMatch) {
    const taskIdValue = decodeURIComponent(taskMatch[1]);
    const action = taskMatch[2];
    if (!action && method === "PUT") return updateTask(env.DB, taskIdValue, await bodyOf(request));
    if (!action && method === "DELETE") return deleteTask(env.DB, taskIdValue);
    if (action === "complete" && method === "POST") return completeTask(env.DB, taskIdValue);
    if (action === "reopen" && method === "POST") return reopenTask(env.DB, taskIdValue);
    if (action === "exclude" && method === "POST") return excludeOccurrence(env.DB, taskIdValue, await bodyOf(request));
    if (action === "alarm" && method === "POST") {
      await env.DB.prepare("UPDATE tasks SET alarm_last_fired_at = ?, updated_at = ? WHERE task_id = ?")
        .bind(now(), now(), taskIdValue).run();
      return response({ ok: true });
    }
  }

  const projectMatch = path.match(/^\/api\/projects\/([^/]+)$/);
  if (projectMatch) {
    const projectId = decodeURIComponent(projectMatch[1]);
    if (method === "PUT") return updateProject(env.DB, projectId, await bodyOf(request));
    if (method === "DELETE") return deleteProject(env.DB, projectId, url.searchParams.get("cascade") === "1");
  }

  const recordMatch = path.match(/^\/api\/content-records\/([^/]+)$/);
  if (recordMatch) {
    const recordId = decodeURIComponent(recordMatch[1]);
    if (method === "PUT") return updateSimple(env.DB, "content_records", "id", recordId, await bodyOf(request), CONTENT_FIELDS);
    if (method === "DELETE") {
      await env.DB.prepare("DELETE FROM content_records WHERE id = ?").bind(recordId).run();
      return response({ ok: true });
    }
  }

  const documentMatch = path.match(/^\/api\/documents\/([^/]+)$/);
  if (documentMatch) {
    const documentId = decodeURIComponent(documentMatch[1]);
    if (method === "PUT") return updateSimple(env.DB, "documents", "id", documentId, await bodyOf(request), DOCUMENT_FIELDS);
    if (method === "DELETE") {
      await env.DB.prepare("DELETE FROM documents WHERE id = ?").bind(documentId).run();
      return response({ ok: true });
    }
  }

  return error("API 경로를 찾을 수 없습니다.", 404);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    try {
      if (url.pathname.startsWith("/api/")) return await routeApi(request, env);
      return env.ASSETS.fetch(request);
    } catch (cause) {
      console.error("PR Flow request failed", cause);
      return error(cause instanceof Error ? cause.message : "처리 중 오류가 발생했습니다.", 500);
    }
  },
};
