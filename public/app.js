const NAV_ITEMS = [
  ["today", "◉", "오늘"],
  ["tasks", "▦", "전체 업무"],
  ["projects", "◆", "프로젝트"],
  ["calendar", "□", "스케줄표"],
  ["waiting", "↗", "대기·회신"],
  ["records", "▶", "유튜브 실적"],
  ["writer", "✦", "AI 대본 작성"],
  ["documents", "▤", "자료실"],
  ["settings", "⚙", "설정"],
];

const STATUSES = ["기획", "진행 중", "제작", "편집", "검토대기", "승인대기", "회신대기", "배포", "완료"];
const CATEGORIES = ["유튜브", "촬영", "편집", "방송", "사진", "대본", "콘텐츠", "행사", "사무 업무", "기타"];
const PRIORITIES = ["보통", "높음", "긴급"];
const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

const state = {
  page: location.hash.replace("#", "") || "today",
  data: { tasks: [], projects: [], content_records: [], documents: [], task_status_history: [] },
  loading: true,
  sortMode: "auto",
  taskSearch: "",
  taskStatus: "전체",
  taskCategory: "전체",
  calendarDate: new Date(),
  scheduleDate: seoulDate(),
  draggedTaskId: null,
};

const pageRoot = document.querySelector("#page");
const modalRoot = document.querySelector("#modal-root");
const alarmRoot = document.querySelector("#alarm-root");
const noticeArea = document.querySelector("#notice-area");
const lockScreen = document.querySelector("#lock-screen");
let alarmAudioContext = null;
let alarmHideTimer = null;

function e(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function attr(value = "") {
  return e(value ?? "");
}

function seoulDate(date = new Date()) {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(date);
  const get = (type) => parts.find((part) => part.type === type)?.value || "00";
  return `${get("year")}-${get("month")}-${get("day")}`;
}

function seoulTime(date = new Date()) {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Seoul", hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(date);
}

function prettyDate(value) {
  if (!value) return "미지정";
  const [year, month, day] = String(value).slice(0, 10).split("-");
  return `${Number(month)}월 ${Number(day)}일`;
}

function prettyFullDate(value) {
  if (!value) return "날짜 미지정";
  const date = new Date(`${String(value).slice(0, 10)}T12:00:00+09:00`);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul", year: "numeric", month: "long", day: "numeric", weekday: "short",
  }).format(date);
}

function shiftIsoDate(value, amount) {
  const date = new Date(`${String(value).slice(0, 10)}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + amount);
  return date.toISOString().slice(0, 10);
}

function prettyDateTime(value) {
  if (!value) return "미지정";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit",
  }).format(date);
}

function optionList(values, current) {
  return values.map((value) => `<option value="${attr(value)}" ${value === current ? "selected" : ""}>${e(value)}</option>`).join("");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "content-type": "application/json", ...(options.headers || {}) },
  });
  let data;
  try { data = await response.json(); } catch { data = {}; }
  if (response.status === 401 && !["/api/unlock", "/api/session"].includes(path)) {
    lockApp({ notifyServer: false });
  }
  if (!response.ok) throw new Error(data.message || "저장 중 오류가 발생했습니다.");
  return data;
}

function toast(message) {
  const node = document.createElement("div");
  node.className = "toast";
  node.textContent = message;
  document.querySelector("#toast-root").append(node);
  setTimeout(() => node.remove(), 3600);
}

function prepareAlarmSound() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return false;
  if (!alarmAudioContext) alarmAudioContext = new AudioContextClass();
  if (alarmAudioContext.state === "suspended") alarmAudioContext.resume().catch(() => {});
  return true;
}

function playAlarmSound() {
  if (!prepareAlarmSound() || alarmAudioContext.state !== "running") return;
  const start = alarmAudioContext.currentTime;
  [0, .24, .48].forEach((delay, index) => {
    const oscillator = alarmAudioContext.createOscillator();
    const gain = alarmAudioContext.createGain();
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(index === 1 ? 880 : 660, start + delay);
    gain.gain.setValueAtTime(.0001, start + delay);
    gain.gain.exponentialRampToValueAtTime(.22, start + delay + .025);
    gain.gain.exponentialRampToValueAtTime(.0001, start + delay + .2);
    oscillator.connect(gain);
    gain.connect(alarmAudioContext.destination);
    oscillator.start(start + delay);
    oscillator.stop(start + delay + .22);
  });
}

function showSiteAlarm(task, message) {
  clearTimeout(alarmHideTimer);
  alarmRoot.innerHTML = `<section class="site-alarm" role="alertdialog" aria-label="일정 알림">
    <div class="site-alarm-icon" aria-hidden="true">⏰</div>
    <div><strong>일정 알림</strong><p>${e(message)}</p></div>
    ${task?.task_id ? `<button type="button" data-action="alarm-open-task" data-id="${attr(task.task_id)}">업무 열기</button>` : ""}
    <button class="site-alarm-close" type="button" data-action="dismiss-alarm" aria-label="알림 닫기">×</button>
  </section>`;
  playAlarmSound();
  alarmHideTimer = setTimeout(() => { alarmRoot.innerHTML = ""; }, 60_000);
}

function showNotice(message) {
  noticeArea.innerHTML = message ? `<div class="notice">${e(message)}</div>` : "";
}

async function reloadData({ quiet = false } = {}) {
  if (!quiet) {
    state.loading = true;
    render();
  }
  try {
    state.data = await api("/api/bootstrap");
    showNotice("");
  } catch (cause) {
    showNotice(cause.message);
  } finally {
    state.loading = false;
    render();
  }
}

function navigate(page) {
  state.page = NAV_ITEMS.some(([key]) => key === page) ? page : "today";
  location.hash = state.page;
  closeModal();
  renderNav();
  render();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderNav() {
  const markup = NAV_ITEMS.map(([key, icon, label]) => `
    <button type="button" class="nav-button ${state.page === key ? "active" : ""}" data-nav="${key}">
      <span class="nav-icon">${icon}</span><span>${label}</span>
    </button>`).join("");
  document.querySelector("#main-nav").innerHTML = markup;
  document.querySelector("#mobile-nav").innerHTML = NAV_ITEMS.map(([key, icon, label]) => `
    <button type="button" class="${state.page === key ? "active" : ""}" data-nav="${key}">
      <span>${icon}</span>${label}
    </button>`).join("");
}

function heading(kicker, title, description, action = "") {
  return `<div class="page-heading"><div><p class="eyebrow">${e(kicker)}</p><h1>${e(title)}</h1><p>${e(description)}</p></div>${action}</div>`;
}

function occursOn(task, target) {
  if (!task || task.deleted_at || (task.excluded_dates || []).includes(target)) return false;
  const repeat = task.repeat_type || "none";
  if (repeat === "none") return String(task.execution_date || "").slice(0, 10) === target;
  const start = String(task.repeat_start_date || task.execution_date || "").slice(0, 10);
  const end = String(task.repeat_end_date || "").slice(0, 10);
  if (!start || target < start || (end && target > end)) return false;
  const weekday = new Date(`${target}T12:00:00`).getDay();
  if (repeat === "daily") return true;
  if (repeat === "weekday") return weekday >= 1 && weekday <= 5;
  if (repeat === "weekly") return (task.repeat_days || []).map(Number).includes(weekday);
  return false;
}

function autoSort(tasks) {
  const rank = { "긴급": 0, "높음": 1, "보통": 2 };
  return [...tasks].sort((a, b) =>
    (rank[a.priority] ?? 9) - (rank[b.priority] ?? 9)
    || String(a.deadline || "9999-12-31").localeCompare(String(b.deadline || "9999-12-31"))
    || String(a.start_time || "23:59").localeCompare(String(b.start_time || "23:59"))
  );
}

function manualSort(tasks) {
  return [...tasks].sort((a, b) => Number(a.sort_order || 9999) - Number(b.sort_order || 9999));
}

function priorityBadge(priority) {
  const cls = priority === "긴급" ? "urgent" : priority === "높음" ? "high" : "";
  return `<span class="badge ${cls}">${e(priority || "보통")}</span>`;
}

function taskCard(task, { draggable = false, index = 0, total = 0 } = {}) {
  const repeat = { daily: "매일", weekday: "평일", weekly: "매주", none: "반복 없음" }[task.repeat_type || "none"];
  const completed = task.status === "완료";
  return `<article class="task-card ${task.priority === "긴급" ? "urgent" : ""}" data-task-card="${attr(task.task_id)}" ${draggable ? 'draggable="true"' : ""}>
    <div class="task-top">
      <div class="badges"><span class="badge">${e(task.category)}</span>${priorityBadge(task.priority)}<span class="badge">${e(task.status)}</span></div>
      <span class="task-id">${e(task.task_id)}</span>
    </div>
    <h3>${e(task.title)}</h3>
    <p><strong>다음 행동</strong> · ${e(task.next_action || "지정 필요")}</p>
    <div class="task-meta"><span>실행 ${prettyDate(task.execution_date)} ${e((task.start_time || "").slice(0,5))}</span><span>마감 ${prettyDate(task.deadline)}</span><span>${e(repeat)}</span></div>
    <div class="card-actions">
      ${draggable ? '<span class="drag-handle" title="끌어서 순서 변경">☰ 이동</span>' : ""}
      <button type="button" data-action="edit-task" data-id="${attr(task.task_id)}">수정</button>
      <button type="button" data-action="toggle-complete" data-id="${attr(task.task_id)}">${completed ? "↩ 다시 열기" : "✓ 완료"}</button>
      <button type="button" data-action="delete-task" data-id="${attr(task.task_id)}">삭제</button>
      ${draggable ? `<span class="order-buttons"><button type="button" data-action="move-up" data-id="${attr(task.task_id)}" ${index === 0 ? "disabled" : ""} aria-label="위로 이동">↑</button><button type="button" data-action="move-down" data-id="${attr(task.task_id)}" ${index === total - 1 ? "disabled" : ""} aria-label="아래로 이동">↓</button></span>` : ""}
    </div>
  </article>`;
}

function taskCards(tasks, options = {}) {
  if (!tasks.length) return `<div class="empty-state">조건에 맞는 업무가 없습니다.</div>`;
  return `<div class="card-grid">${tasks.map((task, index) => taskCard(task, { ...options, index, total: tasks.length })).join("")}</div>`;
}

function scheduleItem(task) {
  const minutes = Number(task.reminder_minutes_before || 0);
  const alarm = task.reminder_enabled ? (minutes ? `${minutes}분 전 알람` : "시작 알람") : "알람 끔";
  const completed = task.status === "완료";
  return `<div class="schedule-item ${completed ? "completed" : ""}">
    <div class="schedule-time">${e((task.start_time || "--:--").slice(0,5))}–${e((task.end_time || "--:--").slice(0,5))}</div>
    <div class="schedule-main"><strong>${e(task.title)}</strong><small>${e(task.next_action || "다음 행동 미지정")} · ${e(alarm)} · ${e(task.status)}</small></div>
    <button class="ghost-button" type="button" data-action="edit-task" data-id="${attr(task.task_id)}">열기</button>
  </div>`;
}

function renderToday() {
  const today = seoulDate();
  const scheduleDate = state.scheduleDate || today;
  const tasks = state.data.tasks || [];
  const active = tasks.filter((task) => task.status !== "완료");
  const todayTasks = active.filter((task) => occursOn(task, today));
  const scheduleTasks = tasks.filter((task) => occursOn(task, scheduleDate));
  const scheduled = scheduleTasks.filter((task) => task.start_time).sort((a,b) => String(a.start_time).localeCompare(String(b.start_time)));
  const unscheduled = autoSort(scheduleTasks.filter((task) => !task.start_time));
  const completedToday = tasks.filter((task) => task.status === "완료" && occursOn(task, today));
  const waiting = active.filter((task) => task.waiting_for || ["검토대기","승인대기","회신대기"].includes(task.status));
  const deadlines = active.filter((task) => task.deadline === today);
  const ordered = state.sortMode === "manual" ? manualSort(todayTasks) : autoSort(todayTasks);
  const urgent = active.filter((task) => task.priority === "긴급");
  const workflowStatuses = STATUSES.filter((status) => status !== "완료");
  pageRoot.innerHTML = `
    ${heading("TODAY", "오늘의 홍보 업무", `${prettyDate(today)} · D1에 저장된 업무만 표시합니다.`, '<button class="primary-button" type="button" data-action="new-task">＋ 새 업무</button>')}
    <div class="stats-grid">
      <div class="stat-card"><small>오늘 실행</small><strong>${todayTasks.length}건</strong></div>
      <div class="stat-card"><small>오늘 마감</small><strong>${deadlines.length}건</strong></div>
      <div class="stat-card"><small>대기·회신</small><strong>${waiting.length}건</strong></div>
      <div class="stat-card"><small>완료</small><strong>${completedToday.length}건</strong></div>
    </div>
    <section class="section-panel">
      <div class="section-head"><span class="section-kicker">DAILY SCHEDULE ARCHIVE</span><h2>일자별 시간표</h2><p>어제 일정도 사라지지 않습니다. 날짜를 이동하면 해당 날짜의 기록을 그대로 확인할 수 있습니다.</p></div>
      <div class="schedule-date-nav">
        <button class="ghost-button" type="button" data-action="schedule-prev" aria-label="이전 날짜">← 이전 날</button>
        <label class="schedule-date-picker">시간표 날짜<input id="schedule-date" type="date" value="${attr(scheduleDate)}" /></label>
        <button class="secondary-button" type="button" data-action="schedule-today">오늘</button>
        <button class="ghost-button" type="button" data-action="schedule-next" aria-label="다음 날짜">다음 날 →</button>
      </div>
      <div class="panel-toolbar"><strong>${e(prettyFullDate(scheduleDate))}</strong><div class="toolbar-actions"><span class="toolbar-meta">${scheduleDate === today ? "30초마다 알람 확인 · " : "보관 일정 · "}${scheduled.length}건</span><button class="secondary-button" type="button" data-action="new-schedule" data-date="${attr(scheduleDate)}">＋ 이 날짜에 일정 등록</button></div></div>
      <div class="schedule-list">${scheduled.length ? scheduled.map(scheduleItem).join("") : '<div class="empty-state">이 날짜에는 시간이 지정된 일정이 없습니다.<br>위의 ‘이 날짜에 일정 등록’을 눌러 추가할 수 있습니다.</div>'}</div>
    </section>
    ${unscheduled.length ? `<section class="section-panel"><div class="section-head"><span class="section-kicker">UNASSIGNED TIME</span><h2>${scheduleDate === today ? "오늘" : prettyDate(scheduleDate)} 미배정 업무</h2><p>해당 날짜에 실행하지만 시작 시간이 정해지지 않은 업무입니다.</p></div>${taskCards(unscheduled)}</section>` : ""}
    ${urgent.length ? `<section class="section-panel"><div class="section-head"><span class="section-kicker">URGENT</span><h2>긴급 업무</h2><p>실행일과 관계없이 긴급도가 가장 높은 업무입니다.</p></div>${taskCards(urgent)}</section>` : ""}
    <div class="paired-grid">
      <section class="section-panel">
        <div class="section-head"><span class="section-kicker">ACTION NOW</span><h2>오늘 할 일 · 실행 업무</h2><p>자동 우선순위 또는 직접 정한 순서로 실행합니다.</p></div>
        <div class="panel-toolbar">
          <div class="segmented"><button type="button" data-action="sort-mode" data-mode="auto" class="${state.sortMode === "auto" ? "active" : ""}">자동 정렬</button><button type="button" data-action="sort-mode" data-mode="manual" class="${state.sortMode === "manual" ? "active" : ""}">내 순서</button></div>
          <span class="toolbar-meta">${ordered.length}건</span>
        </div>
        <div class="task-list">${ordered.length ? ordered.map((task,index) => taskCard(task,{ draggable: state.sortMode === "manual", index, total: ordered.length })).join("") : '<div class="empty-state">조건에 맞는 오늘 업무가 없습니다.</div>'}</div>
      </section>
      <section class="section-panel">
        <div class="section-head"><span class="section-kicker">WAITING</span><h2>대기·회신</h2><p>검토, 승인, 일정 회신을 기다리는 업무입니다.</p></div>
        <div class="panel-toolbar"><span class="toolbar-meta">재확인 임박순</span><span class="toolbar-meta">${waiting.length}건</span></div>
        <div class="waiting-list">${waiting.length ? waiting.slice(0,8).map((task) => `<div class="waiting-card"><strong>${e(task.waiting_for || task.status)}</strong><p>${e(task.title)}<br>${e(task.waiting_type || "확인")} · 재확인 ${prettyDateTime(task.followup_at)}</p><button class="ghost-button" type="button" data-action="edit-task" data-id="${attr(task.task_id)}">업무 열기</button></div>`).join("") : '<div class="empty-state">현재 기다리는 회신이 없습니다.</div>'}</div>
      </section>
    </div>
    <section class="section-panel" style="margin-top:1rem">
      <div class="section-head"><span class="section-kicker">WORKFLOW</span><h2>업무 흐름</h2><p>모든 위치의 카드는 동일한 업무 ID를 사용합니다.</p></div>
      <div class="workflow-grid">${workflowStatuses.map((status) => {
        const rows = active.filter((task) => task.status === status);
        return `<div class="workflow-column"><h3>${e(status)} · ${rows.length}</h3>${rows.slice(0,4).map((task) => `<button type="button" class="calendar-task workflow-item" data-action="edit-task" data-id="${attr(task.task_id)}">${e(task.title)}</button>`).join("") || '<div class="workflow-item">대기 업무 없음</div>'}</div>`;
      }).join("")}</div>
    </section>
    ${completedToday.length ? `<section class="section-panel"><div class="section-head"><span class="section-kicker">COMPLETED</span><h2>오늘 완료 업무</h2><p>추가 수정이 생기면 언제든 완료 직전 단계로 다시 열 수 있습니다.</p></div>${taskCards(completedToday)}</section>` : ""}`;
  bindDragAndDrop();
}

function renderTasks() {
  let tasks = [...(state.data.tasks || [])];
  const query = state.taskSearch.trim().toLowerCase();
  if (query) tasks = tasks.filter((task) => Object.values(task).join(" ").toLowerCase().includes(query));
  if (state.taskStatus !== "전체") tasks = tasks.filter((task) => task.status === state.taskStatus);
  if (state.taskCategory !== "전체") tasks = tasks.filter((task) => task.category === state.taskCategory);
  pageRoot.innerHTML = `${heading("ALL TASKS", "전체 업무", "검색·수정·완료·복구 결과가 모든 화면에 바로 반영됩니다.", '<button class="primary-button" type="button" data-action="new-task">＋ 새 업무</button>')}
    <div class="filters">
      <label>업무 검색<input id="task-search" value="${attr(state.taskSearch)}" placeholder="업무명, 다음 행동, 업무 ID" /></label>
      <label>상태<select id="task-status"><option>전체</option>${optionList(STATUSES, state.taskStatus)}</select></label>
      <label>업무 유형<select id="task-category"><option>전체</option>${optionList(CATEGORIES, state.taskCategory)}</select></label>
    </div>${taskCards(tasks)}`;
}

function renderProjects() {
  const projects = state.data.projects || [];
  pageRoot.innerHTML = `${heading("PROJECTS", "프로젝트 관리", "상위 프로젝트와 하위 업무의 일정과 진행률을 함께 봅니다.", '<button class="primary-button" type="button" data-action="new-project">＋ 새 프로젝트</button>')}
    <div class="card-grid">${projects.length ? projects.map((project) => {
      const tasks = state.data.tasks.filter((task) => task.project_id === project.id);
      const done = tasks.filter((task) => task.status === "완료").length;
      const ratio = tasks.length ? Math.round(done / tasks.length * 100) : 0;
      return `<article class="project-card"><div class="badges">${priorityBadge(project.priority)}<span class="badge">${e(project.status)}</span></div><h3>${e(project.name)}</h3><p>${e(project.description || "설명 없음")}</p><div class="task-meta"><span>${e(project.department || "부서 미지정")}</span><span>마감 ${prettyDate(project.deadline)}</span><span>${done}/${tasks.length} 완료</span></div><div class="progress-track"><div class="progress-value" style="width:${ratio}%"></div></div><div class="card-actions"><button data-action="edit-project" data-id="${attr(project.id)}">수정</button><button data-action="delete-project" data-id="${attr(project.id)}">삭제</button></div></article>`;
    }).join("") : '<div class="empty-state">등록된 프로젝트가 없습니다.</div>'}</div>`;
}

function monthGrid(date) {
  const year = date.getFullYear();
  const month = date.getMonth();
  const first = new Date(year, month, 1);
  const start = new Date(year, month, 1 - first.getDay());
  const days = [];
  for (let index = 0; index < 42; index += 1) {
    const day = new Date(start);
    day.setDate(start.getDate() + index);
    const iso = `${day.getFullYear()}-${String(day.getMonth()+1).padStart(2,"0")}-${String(day.getDate()).padStart(2,"0")}`;
    days.push({ day, iso, muted: day.getMonth() !== month });
  }
  return { year, month, days };
}

function renderCalendar() {
  const { year, month, days } = monthGrid(state.calendarDate);
  pageRoot.innerHTML = `${heading("SCHEDULE CALENDAR", "업무·콘텐츠 스케줄표", "과거 일정도 보관됩니다. 원하는 날짜 칸을 누르면 해당 날짜가 입력된 일정 등록창이 열립니다.", '<button class="primary-button" type="button" data-action="new-schedule" data-date="' + attr(seoulDate()) + '">＋ 일정 추가</button>')}
    <section class="section-panel"><div class="calendar-nav"><button class="ghost-button" data-action="calendar-prev">← 이전 달</button><strong>${year}년 ${month+1}월</strong><button class="ghost-button" data-action="calendar-next">다음 달 →</button></div>
    <div class="calendar-grid">${WEEKDAYS.map((day) => `<div class="calendar-day-name">${day}</div>`).join("")}${days.map(({ day, iso, muted }) => {
      const tasks = state.data.tasks.filter((task) => occursOn(task, iso));
      return `<div class="calendar-cell ${muted ? "muted" : ""}" data-action="new-schedule" data-date="${attr(iso)}" role="button" tabindex="0" aria-label="${attr(prettyFullDate(iso))} 일정 추가"><div class="calendar-cell-head"><span class="calendar-date">${day.getDate()}</span><span class="calendar-add" aria-hidden="true">＋</span></div>${tasks.slice(0,3).map((task) => `<button class="calendar-task ${task.status === "완료" ? "completed" : ""}" data-action="edit-task" data-id="${attr(task.task_id)}">${e(task.title)}</button>`).join("")}${tasks.length > 3 ? `<small>외 ${tasks.length-3}건</small>` : ""}</div>`;
    }).join("")}</div></section>`;
}

function renderWaiting() {
  const tasks = state.data.tasks.filter((task) => task.waiting_for || ["검토대기","승인대기","회신대기"].includes(task.status));
  tasks.sort((a,b) => String(a.followup_at || "9999").localeCompare(String(b.followup_at || "9999")));
  pageRoot.innerHTML = `${heading("WAITING & FOLLOW-UP", "대기·회신", "재확인 시간을 기준으로 놓치기 쉬운 회신을 모아 봅니다.")}
    <div class="waiting-list">${tasks.length ? tasks.map((task) => `<article class="waiting-card"><div class="badges"><span class="badge">${e(task.waiting_type || task.status)}</span></div><strong>${e(task.waiting_for || "대기 대상 미지정")}</strong><p>${e(task.title)}<br>재확인 ${prettyDateTime(task.followup_at)}</p><div class="card-actions"><button data-action="edit-task" data-id="${attr(task.task_id)}">업무 열기</button><button data-action="clear-waiting" data-id="${attr(task.task_id)}">회신 완료</button></div></article>`).join("") : '<div class="empty-state">현재 기다리는 회신이 없습니다.</div>'}</div>`;
}

function renderRecords() {
  const records = state.data.content_records || [];
  pageRoot.innerHTML = `${heading("CONTENT RECORDS", "유튜브 실적", "등록된 실적을 수정하면 다운로드 자료에도 즉시 반영됩니다.", '<button class="primary-button" data-action="new-record">＋ 실적 등록</button>')}
    <div class="panel-toolbar"><span class="toolbar-meta">총 ${records.length}건</span><button class="secondary-button" data-action="download-records">Excel용 CSV 다운로드</button></div>
    <div class="table-wrap"><table><thead><tr><th>업로드일</th><th>제목</th><th>교수명</th><th>진료과</th><th>유형</th><th>관리</th></tr></thead><tbody>${records.map((record) => `<tr><td>${e(record.upload_date || "-")}</td><td>${e(record.title)}</td><td>${e(record.professor || "-")}</td><td>${e(record.department || "-")}</td><td>${e(record.content_type || "-")}</td><td><div class="card-actions"><button data-action="edit-record" data-id="${attr(record.id)}">수정</button>${record.task_id ? `<button data-action="edit-task" data-id="${attr(record.task_id)}">업무</button>` : ""}<button data-action="delete-record" data-id="${attr(record.id)}">삭제</button></div></td></tr>`).join("") || '<tr><td colspan="6">아직 등록된 실적이 없습니다.</td></tr>'}</tbody></table></div>`;
}

function renderWriter() {
  pageRoot.innerHTML = `${heading("AI WRITER", "AI 대본 작성", "주제와 의료진 정보를 넣어 인터뷰 질문지 초안을 빠르게 만듭니다.")}
    <section class="section-panel"><form id="writer-form" class="form-grid"><label>콘텐츠 제목<input name="title" required placeholder="예: 환절기 독감 예방법" /></label><label>교수명<input name="professor" /></label><label>진료과<input name="department" /></label><label>형식<select name="type"><option>유튜브 인터뷰</option><option>LG헬로비전</option><option>YTN 라디오</option><option>쇼츠</option></select></label><label class="full">핵심 참고자료<textarea name="reference" placeholder="확인된 의료정보와 꼭 포함할 내용을 입력하세요."></textarea></label><div class="full"><button class="primary-button" type="submit">대본 초안 만들기</button></div><label class="full">생성 결과<textarea id="writer-result" style="min-height:360px" placeholder="생성된 초안이 여기에 표시됩니다."></textarea></label></form></section>`;
}

function renderDocuments() {
  const documents = state.data.documents || [];
  pageRoot.innerHTML = `${heading("DOCUMENT LIBRARY", "자료실", "대본·질문지·촬영 메모를 D1에 저장합니다.", '<button class="primary-button" data-action="new-document">＋ 자료 등록</button>')}
    <div class="card-grid">${documents.length ? documents.map((document) => `<article class="document-card"><span class="badge">${e(document.category)}</span><h3>${e(document.title)}</h3><p>${e((document.content || "").slice(0,160))}</p><div class="task-meta"><span>${prettyDateTime(document.updated_at)}</span><span>${e(document.task_id || "업무 연결 안 함")}</span></div><div class="card-actions"><button data-action="edit-document" data-id="${attr(document.id)}">수정</button><button data-action="delete-document" data-id="${attr(document.id)}">삭제</button></div></article>`).join("") : '<div class="empty-state">등록된 자료가 없습니다.</div>'}</div>`;
}

function renderSettings() {
  pageRoot.innerHTML = `${heading("SETTINGS", "설정", "Cloudflare D1 저장과 화면 잠금 상태를 확인합니다.")}
    <div class="card-grid"><section class="section-panel"><div class="section-head"><span class="section-kicker">DATA</span><h2>D1 영구 저장</h2><p>업무 데이터는 브라우저가 아니라 Cloudflare D1을 기준으로 관리합니다.</p></div><button class="secondary-button" data-action="refresh">지금 데이터 새로고침</button></section><section class="section-panel"><div class="section-head"><span class="section-kicker">SITE ALARM</span><h2>30분 전 사이트 알림</h2><p>사이트가 열려 있으면 업무 시작 30분 전에 알림음·화면 알림·브라우저 알림을 제공합니다. 업무별로 알람 시점을 바꿀 수도 있습니다.</p></div><div class="card-actions"><button class="secondary-button" data-action="test-site-alarm">사이트 알림 테스트</button><button class="secondary-button" data-action="allow-notification">브라우저 알림 허용</button></div></section><section class="section-panel"><div class="section-head"><span class="section-kicker">PRIVACY</span><h2>접속 잠금</h2><p>새 브라우저 탭에서 처음 접속할 때 비밀번호를 확인하며, 우측 상단 버튼으로 즉시 다시 잠글 수 있습니다.</p></div><button class="lock-button" data-action="lock">🔒 지금 잠그기</button></section><section class="section-panel"><div class="section-head"><span class="section-kicker">DISPLAY</span><h2>반응형 화면</h2><p>PC, 태블릿, 휴대폰의 가로·세로 전환에 맞춰 메뉴와 카드가 자동으로 재배치됩니다.</p></div></section></div>`;
}

function render() {
  renderNav();
  if (state.loading) {
    pageRoot.innerHTML = `<div class="empty-state">홍보 업무를 불러오고 있습니다.</div>`;
    return;
  }
  const pages = { today: renderToday, tasks: renderTasks, projects: renderProjects, calendar: renderCalendar, waiting: renderWaiting, records: renderRecords, writer: renderWriter, documents: renderDocuments, settings: renderSettings };
  (pages[state.page] || renderToday)();
}

function openModal(content, size = "") {
  modalRoot.innerHTML = `<div class="modal-backdrop" data-action="backdrop-close"><section class="modal ${size}" role="dialog" aria-modal="true">${content}</section></div>`;
  modalRoot.querySelector("input, select, textarea, button")?.focus();
}

function closeModal() { modalRoot.innerHTML = ""; }

function modalHead(title, subtitle = "") {
  return `<div class="modal-head"><div><h2>${e(title)}</h2>${subtitle ? `<p>${e(subtitle)}</p>` : ""}</div><button class="modal-close" type="button" data-action="close-modal" aria-label="닫기">×</button></div>`;
}

function projectOptions(current) {
  return `<option value="">연결 안 함</option>${state.data.projects.map((project) => `<option value="${attr(project.id)}" ${project.id === current ? "selected" : ""}>${e(project.name)}</option>`).join("")}`;
}

function taskOptions(current) {
  return `<option value="">연결 안 함</option>${state.data.tasks.map((task) => `<option value="${attr(task.task_id)}" ${task.task_id === current ? "selected" : ""}>${e(task.title)} · ${e(task.task_id)}</option>`).join("")}`;
}

function openTaskForm(task = null, defaults = {}) {
  const editing = Boolean(task);
  const initialDate = task?.execution_date || defaults.execution_date || "";
  const reminderMinutes = task ? Number(task.reminder_minutes_before ?? 30) : 30;
  const days = (task?.repeat_days || []).map(Number);
  const history = editing ? state.data.task_status_history.filter((row) => row.task_id === task.task_id).slice(0,12) : [];
  openModal(`${modalHead(editing ? "업무 상세·수정" : "새 일정·업무 등록", editing ? task.task_id : `${initialDate ? `${prettyFullDate(initialDate)} · ` : ""}저장하면 날짜가 지나도 기록이 유지됩니다.`)}
    <form id="task-form" data-id="${attr(task?.task_id || "")}" class="form-grid">
      <label>업무명 *<input name="title" required value="${attr(task?.title)}" /></label>
      <label>업무 유형<select name="category">${optionList(CATEGORIES, task?.category || "기타")}</select></label>
      <label>현재 단계<select name="status">${optionList(STATUSES, task?.status || "기획")}</select></label>
      <label>우선순위<select name="priority">${optionList(PRIORITIES, task?.priority || "보통")}</select></label>
      <label>실행 예정일<input name="execution_date" type="date" value="${attr(initialDate)}" /></label>
      <label>최종 마감일<input name="deadline" type="date" value="${attr(task?.deadline)}" /></label>
      <label>시작 시간<input name="start_time" type="time" value="${attr((task?.start_time || "").slice(0,5))}" /></label>
      <label>종료 시간<input name="end_time" type="time" value="${attr((task?.end_time || "").slice(0,5))}" /></label>
      <label class="full">다음 행동<input name="next_action" value="${attr(task?.next_action)}" placeholder="예: 촬영 동선 최종 확인" /></label>
      <label>상위 프로젝트<select name="project_id">${projectOptions(task?.project_id)}</select></label>
      <label>대기 대상<input name="waiting_for" value="${attr(task?.waiting_for)}" placeholder="예: 김OO 교수" /></label>
      <label>대기 유형<input name="waiting_type" value="${attr(task?.waiting_type)}" placeholder="검토·승인·일정 회신" /></label>
      <label>재확인 시각<input name="followup_at" type="datetime-local" value="${attr((task?.followup_at || "").slice(0,16))}" /></label>
      <label>반복<select name="repeat_type"><option value="none" ${(task?.repeat_type || "none") === "none" ? "selected" : ""}>반복 없음</option><option value="daily" ${task?.repeat_type === "daily" ? "selected" : ""}>매일</option><option value="weekday" ${task?.repeat_type === "weekday" ? "selected" : ""}>평일</option><option value="weekly" ${task?.repeat_type === "weekly" ? "selected" : ""}>매주 특정 요일</option></select></label>
      <label>반복 종료일<input name="repeat_end_date" type="date" value="${attr(task?.repeat_end_date)}" /></label>
      <div class="full check-row"><span>반복 요일</span>${WEEKDAYS.map((day,index) => `<label><input type="checkbox" name="repeat_days" value="${index}" ${days.includes(index) ? "checked" : ""} />${day}</label>`).join("")}</div>
      <label>알람 시점<select name="reminder_minutes_before"><option value="0" ${reminderMinutes === 0 ? "selected" : ""}>시작 시간</option><option value="5" ${reminderMinutes === 5 ? "selected" : ""}>5분 전</option><option value="10" ${reminderMinutes === 10 ? "selected" : ""}>10분 전</option><option value="30" ${reminderMinutes === 30 ? "selected" : ""}>30분 전</option><option value="60" ${reminderMinutes === 60 ? "selected" : ""}>1시간 전</option></select></label>
      <label class="check-row"><input name="reminder_enabled" type="checkbox" ${task?.reminder_enabled !== false ? "checked" : ""} /> 일정 알람 사용</label>
      <label class="full">순차 단계 · 한 줄에 하나<textarea name="workflow_steps">${e((task?.workflow_steps || []).map((step) => step.title).join("\n"))}</textarea></label>
      <label class="full">업무 설명·메모<textarea name="description">${e(task?.description || "")}</textarea></label>
      ${history.length ? `<div class="full"><strong>상태 변경 이력</strong>${history.map((row) => `<p class="toolbar-meta">${prettyDateTime(row.changed_at)} · ${e(row.from_status || "신규")} → ${e(row.to_status)}</p>`).join("")}</div>` : ""}
      <p class="form-error full" data-form-error></p>
      <div class="modal-actions full">
        ${editing ? `<button class="secondary-button" type="button" data-action="toggle-complete" data-id="${attr(task.task_id)}">${task.status === "완료" ? "↩ 업무 다시 열기" : "✓ 업무 완료"}</button><button class="danger-button" type="button" data-action="delete-task" data-id="${attr(task.task_id)}">업무 삭제</button>` : ""}
        <button class="ghost-button" type="button" data-action="close-modal">취소</button><button class="primary-button" type="submit">${editing ? "변경사항 저장" : "업무 등록"}</button>
      </div>
    </form>`);
}

function openProjectForm(project = null) {
  openModal(`${modalHead(project ? "프로젝트 수정" : "새 프로젝트")}
    <form id="project-form" data-id="${attr(project?.id || "")}" class="form-grid"><label>프로젝트명 *<input name="name" required value="${attr(project?.name)}" /></label><label>관련 진료과·부서<input name="department" value="${attr(project?.department)}" /></label><label>시작일<input type="date" name="start_date" value="${attr(project?.start_date)}" /></label><label>최종 마감일<input type="date" name="deadline" value="${attr(project?.deadline)}" /></label><label>상태<select name="status">${optionList(["기획","진행 중","보류","완료"], project?.status || "진행 중")}</select></label><label>우선순위<select name="priority">${optionList(PRIORITIES, project?.priority || "보통")}</select></label><label class="full">설명<textarea name="description">${e(project?.description || "")}</textarea></label><label class="full">메모<textarea name="memo">${e(project?.memo || "")}</textarea></label><p class="form-error full" data-form-error></p><div class="modal-actions full"><button class="ghost-button" type="button" data-action="close-modal">취소</button><button class="primary-button" type="submit">저장</button></div></form>`);
}

function openRecordForm(record = null) {
  openModal(`${modalHead(record ? "콘텐츠 실적 수정" : "콘텐츠 실적 등록")}
    <form id="record-form" data-id="${attr(record?.id || "")}" class="form-grid"><label class="full">연결 업무<select name="task_id">${taskOptions(record?.task_id)}</select></label><label class="full">제목 *<input name="title" required value="${attr(record?.title)}" /></label><label>출연 교수<input name="professor" value="${attr(record?.professor)}" /></label><label>진료과<input name="department" value="${attr(record?.department)}" /></label><label>업로드일<input type="date" name="upload_date" value="${attr(record?.upload_date || seoulDate())}" /></label><label>콘텐츠 유형<select name="content_type">${optionList(["롱폼","쇼츠","인터뷰","건강정보"], record?.content_type || "인터뷰")}</select></label><label class="full">유튜브 URL<input name="url" type="url" value="${attr(record?.url)}" /></label><label class="full">메모<textarea name="memo">${e(record?.memo || "")}</textarea></label><p class="form-error full" data-form-error></p><div class="modal-actions full"><button class="ghost-button" type="button" data-action="close-modal">취소</button><button class="primary-button" type="submit">${record ? "수정 내용 저장" : "실적 저장"}</button></div></form>`);
}

function openDocumentForm(document = null) {
  openModal(`${modalHead(document ? "자료 수정" : "자료 등록")}
    <form id="document-form" data-id="${attr(document?.id || "")}" class="form-grid"><label>자료 제목 *<input name="title" required value="${attr(document?.title)}" /></label><label>분류<select name="category">${optionList(["대본","질문지","영상기획안","촬영자료","방송자료","참고자료","기타"], document?.category || "참고자료")}</select></label><label class="full">연결 업무<select name="task_id">${taskOptions(document?.task_id)}</select></label><label class="full">본문 및 메모<textarea name="content" style="min-height:300px">${e(document?.content || "")}</textarea></label><p class="form-error full" data-form-error></p><div class="modal-actions full"><button class="ghost-button" type="button" data-action="close-modal">취소</button><button class="primary-button" type="submit">저장</button></div></form>`);
}

function openDeleteChoice(task) {
  if ((task.repeat_type || "none") !== "none") {
    openModal(`${modalHead("반복 일정 삭제 범위")}` + `<p><strong>${e(task.title)}</strong></p><p>오늘 일정만 숨기거나 반복 일정 전체를 삭제할 수 있습니다.</p><div class="modal-actions"><button class="ghost-button" data-action="close-modal">취소</button><button class="secondary-button" data-action="exclude-today" data-id="${attr(task.task_id)}">오늘만 제외</button><button class="danger-button" data-action="delete-series" data-id="${attr(task.task_id)}">반복 전체 삭제</button></div>`, "small");
  } else {
    openModal(`${modalHead("업무 삭제")}` + `<p><strong>${e(task.title)}</strong> 업무를 삭제할까요?</p><p>삭제 기록은 D1에 남고 화면을 다시 열어도 되살아나지 않습니다.</p><div class="modal-actions"><button class="ghost-button" data-action="close-modal">취소</button><button class="danger-button" data-action="confirm-delete-task" data-id="${attr(task.task_id)}">정말 삭제</button></div>`, "small");
  }
}

function openProjectDelete(project) {
  const count = state.data.tasks.filter((task) => task.project_id === project.id).length;
  openModal(`${modalHead("프로젝트 삭제")}` + `<p><strong>${e(project.name)}</strong>에 연결된 업무는 ${count}건입니다.</p><p>업무는 유지하면서 프로젝트 연결만 해제하거나, 하위 업무도 함께 삭제할 수 있습니다.</p><div class="modal-actions"><button class="ghost-button" data-action="close-modal">취소</button><button class="secondary-button" data-action="confirm-delete-project" data-id="${attr(project.id)}" data-cascade="0">연결만 해제</button><button class="danger-button" data-action="confirm-delete-project" data-id="${attr(project.id)}" data-cascade="1">하위 업무도 삭제</button></div>`, "small");
}

function formPayload(form) {
  return Object.fromEntries(new FormData(form).entries());
}

async function saveTask(form) {
  const payload = formPayload(form);
  payload.reminder_enabled = form.elements.reminder_enabled.checked;
  payload.reminder_minutes_before = Number(payload.reminder_minutes_before || 0);
  payload.repeat_days = [...form.querySelectorAll('input[name="repeat_days"]:checked')].map((node) => Number(node.value));
  const existing = state.data.tasks.find((task) => task.task_id === form.dataset.id);
  const oldSteps = new Map((existing?.workflow_steps || []).map((step) => [step.title, step]));
  payload.workflow_steps = String(payload.workflow_steps || "").split("\n").map((title) => title.trim()).filter(Boolean).map((title) => ({ title, completed: Boolean(oldSteps.get(title)?.completed) }));
  payload.repeat_start_date = payload.execution_date || null;
  const method = form.dataset.id ? "PUT" : "POST";
  const path = form.dataset.id ? `/api/tasks/${encodeURIComponent(form.dataset.id)}` : "/api/tasks";
  await api(path, { method, body: JSON.stringify(payload) });
}

async function saveGeneric(form, basePath) {
  const payload = formPayload(form);
  const idValue = form.dataset.id;
  await api(idValue ? `${basePath}/${encodeURIComponent(idValue)}` : basePath, { method: idValue ? "PUT" : "POST", body: JSON.stringify(payload) });
}

function setFormError(form, message) {
  const target = form.querySelector("[data-form-error]");
  if (target) target.textContent = message;
}

function bindDragAndDrop() {
  if (state.sortMode !== "manual") return;
  pageRoot.querySelectorAll("[data-task-card][draggable=true]").forEach((card) => {
    card.addEventListener("dragstart", () => { state.draggedTaskId = card.dataset.taskCard; card.classList.add("dragging"); });
    card.addEventListener("dragend", () => { state.draggedTaskId = null; card.classList.remove("dragging"); });
    card.addEventListener("dragover", (event) => event.preventDefault());
    card.addEventListener("drop", async (event) => {
      event.preventDefault();
      const targetId = card.dataset.taskCard;
      if (!state.draggedTaskId || state.draggedTaskId === targetId) return;
      const tasks = manualSort(state.data.tasks.filter((task) => occursOn(task, seoulDate()) && task.status !== "완료"));
      const ids = tasks.map((task) => task.task_id);
      const from = ids.indexOf(state.draggedTaskId);
      const to = ids.indexOf(targetId);
      ids.splice(to, 0, ids.splice(from, 1)[0]);
      await api("/api/task-order", { method: "POST", body: JSON.stringify({ task_ids: ids }) });
      await reloadData({ quiet: true });
      toast("내 업무 순서를 저장했습니다.");
    });
  });
}

async function moveTask(taskIdValue, delta) {
  const tasks = manualSort(state.data.tasks.filter((task) => occursOn(task, seoulDate()) && task.status !== "완료"));
  const ids = tasks.map((task) => task.task_id);
  const index = ids.indexOf(taskIdValue);
  const target = index + delta;
  if (index < 0 || target < 0 || target >= ids.length) return;
  [ids[index], ids[target]] = [ids[target], ids[index]];
  await api("/api/task-order", { method: "POST", body: JSON.stringify({ task_ids: ids }) });
  await reloadData({ quiet: true });
}

async function handleAction(button, sourceEvent) {
  const action = button.dataset.action;
  const itemId = button.dataset.id;
  if (action === "close-modal") return closeModal();
  if (action === "dismiss-alarm") { alarmRoot.innerHTML = ""; return; }
  if (action === "alarm-open-task") {
    alarmRoot.innerHTML = "";
    return openTaskForm(state.data.tasks.find((task) => task.task_id === itemId));
  }
  if (action === "backdrop-close" && button === sourceEvent?.target) return closeModal();
  if (action === "new-task") return openTaskForm();
  if (action === "new-schedule") return openTaskForm(null, { execution_date: button.dataset.date || state.scheduleDate || seoulDate() });
  if (action === "edit-task") return openTaskForm(state.data.tasks.find((task) => task.task_id === itemId));
  if (action === "new-project") return openProjectForm();
  if (action === "edit-project") return openProjectForm(state.data.projects.find((project) => project.id === itemId));
  if (action === "delete-project") return openProjectDelete(state.data.projects.find((project) => project.id === itemId));
  if (action === "new-record") return openRecordForm();
  if (action === "edit-record") return openRecordForm(state.data.content_records.find((record) => record.id === itemId));
  if (action === "new-document") return openDocumentForm();
  if (action === "edit-document") return openDocumentForm(state.data.documents.find((document) => document.id === itemId));
  if (action === "delete-task") return openDeleteChoice(state.data.tasks.find((task) => task.task_id === itemId));
  if (action === "sort-mode") { state.sortMode = button.dataset.mode; return render(); }
  if (action === "calendar-prev" || action === "calendar-next") { state.calendarDate.setMonth(state.calendarDate.getMonth() + (action === "calendar-prev" ? -1 : 1)); return render(); }
  if (action === "schedule-prev" || action === "schedule-next") { state.scheduleDate = shiftIsoDate(state.scheduleDate || seoulDate(), action === "schedule-prev" ? -1 : 1); return render(); }
  if (action === "schedule-today") { state.scheduleDate = seoulDate(); return render(); }
  if (action === "refresh") return reloadData();
  if (action === "lock") return lockApp();
  if (action === "move-up" || action === "move-down") return moveTask(itemId, action === "move-up" ? -1 : 1);
  if (action === "allow-notification") {
    prepareAlarmSound();
    if (!("Notification" in window)) return toast("이 브라우저는 알림을 지원하지 않습니다.");
    const permission = await Notification.requestPermission();
    return toast(permission === "granted" ? "브라우저 알림을 허용했습니다." : "브라우저 알림이 허용되지 않았습니다.");
  }
  if (action === "test-site-alarm") {
    prepareAlarmSound();
    showSiteAlarm(null, "사이트 알림음과 화면 알림이 정상적으로 연결되었습니다.");
    return;
  }
  if (action === "toggle-complete") {
    const task = state.data.tasks.find((row) => row.task_id === itemId);
    await api(`/api/tasks/${encodeURIComponent(itemId)}/${task.status === "완료" ? "reopen" : "complete"}`, { method: "POST" });
    closeModal(); await reloadData({ quiet: true }); toast(task.status === "완료" ? "업무를 다시 열었습니다." : "업무를 완료했습니다."); return;
  }
  if (action === "confirm-delete-task" || action === "delete-series") {
    await api(`/api/tasks/${encodeURIComponent(itemId)}`, { method: "DELETE" }); closeModal(); await reloadData({ quiet: true }); toast("업무를 삭제했습니다."); return;
  }
  if (action === "exclude-today") {
    await api(`/api/tasks/${encodeURIComponent(itemId)}/exclude`, { method: "POST", body: JSON.stringify({ occurrence_date: seoulDate() }) }); closeModal(); await reloadData({ quiet: true }); toast("오늘 일정만 제외했습니다."); return;
  }
  if (action === "clear-waiting") {
    await api(`/api/tasks/${encodeURIComponent(itemId)}`, { method: "PUT", body: JSON.stringify({ waiting_for: null, waiting_type: null, followup_at: null, status: "진행 중" }) }); await reloadData({ quiet: true }); toast("회신 완료로 처리했습니다."); return;
  }
  if (action === "confirm-delete-project") {
    await api(`/api/projects/${encodeURIComponent(itemId)}?cascade=${button.dataset.cascade}`, { method: "DELETE" }); closeModal(); await reloadData({ quiet: true }); toast("프로젝트 삭제 결과를 반영했습니다."); return;
  }
  if (action === "delete-record") {
    if (!confirm("이 콘텐츠 실적을 삭제할까요?")) return;
    await api(`/api/content-records/${encodeURIComponent(itemId)}`, { method: "DELETE" }); await reloadData({ quiet: true }); toast("콘텐츠 실적을 삭제했습니다."); return;
  }
  if (action === "delete-document") {
    if (!confirm("이 자료를 삭제할까요?")) return;
    await api(`/api/documents/${encodeURIComponent(itemId)}`, { method: "DELETE" }); await reloadData({ quiet: true }); toast("자료를 삭제했습니다."); return;
  }
  if (action === "download-records") return downloadRecords();
}

function downloadRecords() {
  const headers = ["업로드일","제목","교수명","진료과","콘텐츠 유형","URL","업무 ID","메모"];
  const quote = (value) => `"${String(value ?? "").replaceAll('"','""')}"`;
  const rows = state.data.content_records.map((record) => [record.upload_date,record.title,record.professor,record.department,record.content_type,record.url,record.task_id,record.memo].map(quote).join(","));
  const blob = new Blob(["\ufeff" + [headers.join(","), ...rows].join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url; link.download = `youtube-content-${seoulDate()}.csv`; link.click(); URL.revokeObjectURL(url);
}

function lockApp({ notifyServer = true } = {}) {
  sessionStorage.removeItem("pr-flow-unlocked");
  document.body.classList.add("locked");
  lockScreen.hidden = false;
  closeModal();
  if (notifyServer) {
    fetch("/api/lock", { method: "POST", headers: { "content-type": "application/json" } }).catch(() => {});
  }
  setTimeout(() => document.querySelector("#unlock-password")?.focus(), 0);
}

function unlockApp() {
  sessionStorage.setItem("pr-flow-unlocked", "1");
  document.body.classList.remove("locked");
  lockScreen.hidden = true;
  document.querySelector("#unlock-password").value = "";
}

async function checkAlarms() {
  if (document.body.classList.contains("locked")) return;
  const nowDate = new Date();
  const today = seoulDate(nowDate);
  const currentTime = seoulTime(nowDate);
  const currentMinutes = Number(currentTime.slice(0,2)) * 60 + Number(currentTime.slice(3,5));
  for (const task of state.data.tasks || []) {
    if (!task.reminder_enabled || !task.start_time || task.status === "완료" || !occursOn(task, today)) continue;
    const [hour, minute] = task.start_time.slice(0,5).split(":").map(Number);
    const reminderMinutes = Number(task.reminder_minutes_before ?? 30);
    const alarmMinutes = hour * 60 + minute - reminderMinutes;
    const firedAt = task.alarm_last_fired_at ? new Date(task.alarm_last_fired_at) : null;
    const firedToday = firedAt && !Number.isNaN(firedAt.getTime()) && seoulDate(firedAt) === today;
    if (alarmMinutes === currentMinutes && !firedToday) {
      const message = reminderMinutes > 0
        ? `${task.start_time.slice(0,5)} ${task.title} 시작 ${reminderMinutes}분 전입니다.`
        : `${task.start_time.slice(0,5)} ${task.title} 시간입니다.`;
      toast(`⏰ ${message}`);
      showSiteAlarm(task, message);
      if ("Notification" in window && Notification.permission === "granted") new Notification("홍보의 바다", { body: message });
      task.alarm_last_fired_at = new Date().toISOString();
      api(`/api/tasks/${encodeURIComponent(task.task_id)}/alarm`, { method: "POST" }).catch(console.error);
    }
  }
}

function registerWebMcp() {
  const context = document.modelContext;
  if (!context?.registerTool) return;
  const safeRegister = (tool) => Promise.resolve(context.registerTool(tool)).catch(console.error);
  safeRegister({
    name: "list_today_pr_tasks", title: "오늘 홍보 업무 보기",
    description: "오늘 실행 예정인 홍보 업무를 읽습니다.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true, untrustedContentHint: false },
    execute: async () => ({ tasks: state.data.tasks.filter((task) => occursOn(task, seoulDate())).map(({ task_id, title, status, start_time, next_action }) => ({ task_id, title, status, start_time, next_action })) }),
  });
  safeRegister({
    name: "create_pr_task", title: "홍보 업무 등록",
    description: "업무명과 선택적인 실행일로 새 홍보 업무를 D1에 등록합니다.",
    inputSchema: { type: "object", properties: { title: { type: "string" }, execution_date: { type: "string" }, next_action: { type: "string" } }, required: ["title"], additionalProperties: false },
    annotations: { readOnlyHint: false, untrustedContentHint: false },
    execute: async (input) => { const result = await api("/api/tasks", { method: "POST", body: JSON.stringify(input) }); await reloadData({ quiet: true }); return { task_id: result.task.task_id, status: "created" }; },
  });
}

document.addEventListener("click", async (event) => {
  const nav = event.target.closest("[data-nav]");
  if (nav) return navigate(nav.dataset.nav);
  const home = event.target.closest("[data-home-link]");
  if (home) { event.preventDefault(); return navigate("today"); }
  const action = event.target.closest("[data-action]");
  if (!action) return;
  try { await handleAction(action, event); } catch (cause) { toast(cause.message); }
});

document.addEventListener("keydown", async (event) => {
  if (!['Enter', ' '].includes(event.key)) return;
  const cell = event.target.closest(".calendar-cell[data-action='new-schedule']");
  if (!cell || event.target.closest(".calendar-task")) return;
  event.preventDefault();
  try { await handleAction(cell, event); } catch (cause) { toast(cause.message); }
});

document.addEventListener("input", (event) => {
  if (event.target.id === "task-search") { state.taskSearch = event.target.value; renderTasks(); document.querySelector("#task-search")?.focus(); }
});

document.addEventListener("change", (event) => {
  if (event.target.id === "task-status") { state.taskStatus = event.target.value; renderTasks(); }
  if (event.target.id === "task-category") { state.taskCategory = event.target.value; renderTasks(); }
  if (event.target.id === "schedule-date") { state.scheduleDate = event.target.value || seoulDate(); renderToday(); }
});

document.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  try {
    if (form.id === "task-form") await saveTask(form);
    else if (form.id === "project-form") await saveGeneric(form, "/api/projects");
    else if (form.id === "record-form") await saveGeneric(form, "/api/content-records");
    else if (form.id === "document-form") await saveGeneric(form, "/api/documents");
    else if (form.id === "writer-form") {
      const values = formPayload(form);
      document.querySelector("#writer-result").value = `[${values.type}]\n\n제목: ${values.title}\n출연: ${values.department || "진료과"} ${values.professor || "교수"}\n\n[오프닝]\n오늘은 ${values.title}에 대해 정확하고 쉽게 알아보겠습니다.\n\n[질문]\n1. 먼저 이 주제를 시청자가 꼭 알아야 하는 이유는 무엇인가요?\n2. 흔히 잘못 알고 있는 오해는 무엇인가요?\n3. 일상에서 실천할 수 있는 예방법이나 관리법은 무엇인가요?\n4. 병원을 찾아야 하는 위험 신호는 무엇인가요?\n\n[확인된 참고자료]\n${values.reference || "의료진 검토 후 보완해 주세요."}\n\n[클로징]\n정확한 정보와 의료진 상담을 통해 건강을 지키시기 바랍니다.`;
      return toast("검토용 대본 초안을 만들었습니다.");
    } else if (form.id === "unlock-form") {
      prepareAlarmSound();
      const values = formPayload(form);
      await api("/api/unlock", { method: "POST", body: JSON.stringify(values) });
      document.querySelector("#unlock-error").textContent = "";
      unlockApp();
      await reloadData();
      await checkAlarms();
      return;
    } else return;
    closeModal();
    await reloadData({ quiet: true });
    toast("저장 결과를 모든 화면에 반영했습니다.");
  } catch (cause) {
    if (form.id === "unlock-form") document.querySelector("#unlock-error").textContent = cause.message;
    else setFormError(form, cause.message);
  }
});

document.querySelector("#lock-button").addEventListener("click", lockApp);
document.querySelector("#refresh-button").addEventListener("click", () => reloadData());
window.addEventListener("hashchange", () => navigate(location.hash.replace("#", "") || "today"));

async function initialize() {
  lockApp({ notifyServer: false });
  renderNav();
  if (sessionStorage.getItem("pr-flow-unlocked") !== "1") return;
  try {
    await api("/api/session");
    unlockApp();
    await reloadData();
  } catch {
    lockApp({ notifyServer: false });
  }
}

initialize();
setInterval(checkAlarms, 30_000);
setInterval(() => { if (!modalRoot.firstChild && !document.body.classList.contains("locked")) reloadData({ quiet: true }); }, 60_000);
registerWebMcp();
