from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import streamlit as st

from app_data import first_pending_step, initial_store
from database import DatabaseError, SupabaseClient


DOCUMENT_BUCKET = "pr-documents"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "strftime") and value.__class__.__name__ == "time":
        return value.strftime("%H:%M")
    return value


def _clean(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: _value(value) for key, value in payload.items()}


class Repository:
    """One data gateway shared by every screen.

    With Streamlit secrets configured this class talks to Supabase. Otherwise it
    uses session memory only; it never writes user data into the GitHub checkout.
    """

    def __init__(self) -> None:
        self.db = SupabaseClient()
        if "pr_store" not in st.session_state or st.session_state.get("pr_store_version") != 2:
            st.session_state.pr_store = initial_store()
            st.session_state.pr_store_version = 2

    @property
    def persistent(self) -> bool:
        return self.db.available

    @property
    def mode_label(self) -> str:
        return "Supabase 영구 저장" if self.persistent else "체험 모드 · 세션 저장"

    def _rows(self, table: str, order: str | None = None) -> list[dict[str, Any]]:
        if self.persistent:
            return self.db.select(table, order=order)
        return deepcopy(st.session_state.pr_store.get(table, []))

    def _insert(self, table: str, row: dict[str, Any], *, upsert: bool = False) -> dict[str, Any]:
        row = _clean(row)
        if self.persistent:
            result = self.db.insert(table, row, upsert=upsert)
            return result[0] if result else row
        rows = st.session_state.pr_store.setdefault(table, [])
        if upsert:
            key_name = "task_id" if table == "waiting_items" else "id"
            match = next((index for index, item in enumerate(rows) if item.get(key_name) == row.get(key_name)), None)
            if match is not None:
                rows[match] = {**rows[match], **deepcopy(row)}
                return deepcopy(rows[match])
        rows.append(deepcopy(row))
        return deepcopy(row)

    def _update(self, table: str, id_field: str, item_id: str, changes: dict[str, Any]) -> None:
        changes = _clean(changes)
        if self.persistent:
            self.db.update(table, {id_field: f"eq.{item_id}"}, changes)
            return
        rows = st.session_state.pr_store.setdefault(table, [])
        for index, row in enumerate(rows):
            if str(row.get(id_field)) == str(item_id):
                rows[index] = {**row, **deepcopy(changes)}
                return

    def _delete(self, table: str, id_field: str, item_id: str) -> None:
        if self.persistent:
            self.db.delete(table, {id_field: f"eq.{item_id}"})
            return
        rows = st.session_state.pr_store.setdefault(table, [])
        st.session_state.pr_store[table] = [row for row in rows if str(row.get(id_field)) != str(item_id)]

    def list_tasks(self, *, include_deleted: bool = False) -> list[dict[str, Any]]:
        tasks = self._rows("tasks", "execution_date.asc,start_time.asc")
        if not include_deleted:
            tasks = [task for task in tasks if not task.get("deleted_at")]
        steps = self._rows("task_steps", "step_order.asc")
        grouped: dict[str, list[dict[str, Any]]] = {}
        for step in steps:
            grouped.setdefault(str(step["task_id"]), []).append(step)
        for task in tasks:
            if str(task["task_id"]) in grouped:
                task["workflow_steps"] = grouped[str(task["task_id"])]
            else:
                task.setdefault("workflow_steps", [])
        return sorted(tasks, key=lambda item: (item.get("execution_date") or "9999-12-31", item.get("start_time") or "23:59"))

    def get_task(self, task_id: str | None) -> dict[str, Any] | None:
        if not task_id:
            return None
        return next((task for task in self.list_tasks() if task.get("task_id") == task_id), None)

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        today = datetime.now(ZoneInfo("Asia/Seoul")).date()
        prefix = f"TASK-{today.strftime('%Y%m%d')}-"
        suffixes = []
        for task in self.list_tasks():
            current_id = str(task.get("task_id", ""))
            if current_id.startswith(prefix) and current_id.removeprefix(prefix).isdigit():
                suffixes.append(int(current_id.removeprefix(prefix)))
        task_id = f"{prefix}{max(suffixes, default=0) + 1:03d}"
        steps_input = payload.pop("workflow_steps", [])
        steps = [
            {
                "id": f"{task_id}-S{index:02d}",
                "task_id": task_id,
                "step_order": index,
                "title": str(step.get("title", "")).strip(),
                "completed": bool(step.get("completed", False)),
                "completed_at": _now() if step.get("completed") else None,
            }
            for index, step in enumerate(steps_input, start=1)
            if str(step.get("title", "")).strip()
        ]
        now = _now()
        task = {
            "task_id": task_id,
            "title": str(payload.get("title", "")).strip(),
            "category": payload.get("category", "기타"),
            "status": payload.get("status", "기획"),
            "priority": payload.get("priority", "보통"),
            "deadline": _value(payload.get("deadline")) if payload.get("deadline") else None,
            "execution_date": _value(payload.get("execution_date")) if payload.get("execution_date") else None,
            "start_time": _value(payload.get("start_time")) if payload.get("start_time") else None,
            "end_time": _value(payload.get("end_time")) if payload.get("end_time") else None,
            "next_action": str(payload.get("next_action") or first_pending_step(steps)).strip(),
            "waiting_for": str(payload.get("waiting_for") or "").strip() or None,
            "waiting_type": str(payload.get("waiting_type") or "").strip() or None,
            "request_date": _value(payload.get("request_date")) if payload.get("request_date") else None,
            "followup_date": _value(payload.get("followup_date")) if payload.get("followup_date") else None,
            "description": str(payload.get("description") or "").strip(),
            "featured": bool(payload.get("featured", False)),
            "project_id": payload.get("project_id") or None,
            "previous_status": None,
            "completed_at": None,
            "reopened_at": None,
            "deleted_at": None,
            "reminder_enabled": bool(payload.get("reminder_enabled", True)),
            "reminder_minutes_before": int(payload.get("reminder_minutes_before", 0) or 0),
            "alarm_last_fired_at": None,
            "repeat_type": payload.get("repeat_type") or "none",
            "repeat_days": [int(day) for day in payload.get("repeat_days", [])],
            "repeat_start_date": _value(payload.get("repeat_start_date") or payload.get("execution_date")) if (payload.get("repeat_start_date") or payload.get("execution_date")) else None,
            "repeat_end_date": _value(payload.get("repeat_end_date")) if payload.get("repeat_end_date") else None,
            "excluded_dates": [],
            "sort_order": int(payload.get("sort_order", 9999) or 9999),
            "created_at": now,
            "updated_at": now,
        }
        self._insert("tasks", task)
        for step in steps:
            self._insert("task_steps", step)
        task["workflow_steps"] = steps
        self._sync_waiting(task)
        return task

    def update_task(self, task_id: str, changes: dict[str, Any]) -> None:
        current = self.get_task(task_id)
        if not current:
            return
        changes = deepcopy(changes)
        steps = changes.pop("workflow_steps", None)
        if steps is not None:
            normalized = [
                {
                    "id": str(step.get("id") or f"{task_id}-S{index:02d}"),
                    "task_id": task_id,
                    "step_order": index,
                    "title": str(step.get("title", "")).strip(),
                    "completed": bool(step.get("completed", False)),
                    "completed_at": _now() if step.get("completed") else None,
                }
                for index, step in enumerate(steps, start=1)
                if str(step.get("title", "")).strip()
            ]
            changes["next_action"] = first_pending_step(normalized)
            if self.persistent:
                self.db.delete("task_steps", {"task_id": f"eq.{task_id}"})
                if normalized:
                    self.db.insert("task_steps", normalized)
            else:
                for task in st.session_state.pr_store["tasks"]:
                    if task.get("task_id") == task_id:
                        task["workflow_steps"] = normalized
                        break
        old_status = str(current.get("status") or "")
        new_status = str(changes.get("status") or old_status)
        changes["updated_at"] = _now()
        self._update("tasks", "task_id", task_id, changes)
        if new_status != old_status:
            self._insert(
                "task_status_history",
                {
                    "id": f"STATUS-{uuid4().hex[:12].upper()}",
                    "task_id": task_id,
                    "from_status": old_status or None,
                    "to_status": new_status,
                    "changed_at": changes["updated_at"],
                },
            )
        refreshed = {**current, **changes}
        self._sync_waiting(refreshed)

    def complete_task(self, task_id: str) -> None:
        task = self.get_task(task_id)
        if not task or task.get("status") == "완료":
            return
        self.update_task(
            task_id,
            {
                "previous_status": task.get("status") or "진행 중",
                "status": "완료",
                "completed_at": _now(),
                "next_action": "완료 처리됨",
            },
        )

    def reopen_task(self, task_id: str) -> None:
        task = self.get_task(task_id)
        if not task or task.get("status") != "완료":
            return
        restored = str(task.get("previous_status") or "진행 중")
        if restored == "완료":
            restored = "진행 중"
        self.update_task(
            task_id,
            {
                "status": restored,
                "completed_at": None,
                "reopened_at": _now(),
                "next_action": first_pending_step(task.get("workflow_steps", [])),
            },
        )

    def list_task_status_history(self, task_id: str) -> list[dict[str, Any]]:
        try:
            rows = self._rows("task_status_history", "changed_at.desc")
        except DatabaseError:
            return []
        return [row for row in rows if str(row.get("task_id")) == str(task_id)]

    def delete_task(self, task_id: str) -> None:
        task = self.get_task(task_id)
        if not task:
            return
        deleted_at = _now()
        self._update("tasks", "task_id", task_id, {"deleted_at": deleted_at, "updated_at": deleted_at})
        self._insert(
            "task_status_history",
            {
                "id": f"STATUS-{uuid4().hex[:12].upper()}",
                "task_id": task_id,
                "from_status": task.get("status"),
                "to_status": "삭제",
                "changed_at": deleted_at,
            },
        )
        self._delete("waiting_items", "task_id", task_id)

    def exclude_occurrence(self, task_id: str, occurrence_date: date) -> None:
        task = self.get_task(task_id)
        if not task:
            return
        excluded = {str(value)[:10] for value in (task.get("excluded_dates") or [])}
        excluded.add(occurrence_date.isoformat())
        self.update_task(task_id, {"excluded_dates": sorted(excluded)})

    @staticmethod
    def task_occurs_on(task: dict[str, Any], target_date: date) -> bool:
        if task.get("deleted_at") or target_date.isoformat() in {str(value)[:10] for value in (task.get("excluded_dates") or [])}:
            return False
        repeat_type = str(task.get("repeat_type") or "none")
        if repeat_type == "none":
            return str(task.get("execution_date") or "")[:10] == target_date.isoformat()
        start_text = task.get("repeat_start_date") or task.get("execution_date")
        if not start_text:
            return False
        try:
            start_date = date.fromisoformat(str(start_text)[:10])
            end_date = date.fromisoformat(str(task.get("repeat_end_date"))[:10]) if task.get("repeat_end_date") else None
        except ValueError:
            return False
        if target_date < start_date or (end_date and target_date > end_date):
            return False
        if repeat_type == "daily":
            return True
        if repeat_type == "weekday":
            return target_date.weekday() < 5
        if repeat_type == "weekly":
            return target_date.weekday() in {int(day) for day in (task.get("repeat_days") or [])}
        return False

    def tasks_for_date(self, target_date: date, *, timed_only: bool = False) -> list[dict[str, Any]]:
        rows = [task for task in self.list_tasks() if self.task_occurs_on(task, target_date)]
        if timed_only:
            rows = [task for task in rows if task.get("start_time")]
        return sorted(rows, key=lambda item: (item.get("sort_order", 9999), item.get("start_time") or "23:59"))

    def mark_task_alarm_fired(self, task_id: str, fired_at: str) -> None:
        self._update("tasks", "task_id", task_id, {"alarm_last_fired_at": fired_at, "updated_at": _now()})

    def update_task_order(self, task_ids: list[str]) -> None:
        for index, task_id in enumerate(task_ids, start=1):
            self._update("tasks", "task_id", task_id, {"sort_order": index, "updated_at": _now()})

    def _sync_waiting(self, task: dict[str, Any]) -> None:
        task_id = str(task["task_id"])
        if task.get("waiting_for") and task.get("status") != "완료" and not task.get("deleted_at"):
            row = {
                "id": f"WAIT-{task_id}",
                "task_id": task_id,
                "waiting_for": task.get("waiting_for"),
                "waiting_type": task.get("waiting_type") or "회신",
                "requested_at": task.get("request_date"),
                "followup_at": task.get("followup_date"),
                "completed": False,
            }
            self._insert("waiting_items", row, upsert=True)
        else:
            self._delete("waiting_items", "task_id", task_id)

    def list_waiting_items(self) -> list[dict[str, Any]]:
        tasks = {task["task_id"]: task for task in self.list_tasks()}
        rows = self._rows("waiting_items", "followup_at.asc")
        known = {row.get("task_id") for row in rows}
        rows.extend(
            {
                "id": f"WAIT-{task['task_id']}",
                "task_id": task["task_id"],
                "waiting_for": task.get("waiting_for"),
                "waiting_type": task.get("waiting_type"),
                "requested_at": task.get("request_date"),
                "followup_at": task.get("followup_date"),
                "completed": False,
            }
            for task in tasks.values()
            if task.get("waiting_for") and task.get("task_id") not in known
        )
        return [{**row, "task": tasks.get(row.get("task_id"))} for row in rows if not row.get("completed") and tasks.get(row.get("task_id"))]

    def complete_waiting(self, task_id: str) -> None:
        task = self.get_task(task_id)
        next_status = "기획" if task and task.get("status") == "회신대기" else (task.get("status") if task else "기획")
        self.update_task(task_id, {"waiting_for": None, "waiting_type": None, "request_date": None, "followup_date": None, "status": next_status})

    def recontact(self, task_id: str) -> None:
        now = datetime.now().astimezone()
        self.update_task(task_id, {"request_date": now.isoformat(), "followup_date": (now + timedelta(days=1)).isoformat(), "status": "회신대기"})

    def list_categories(self) -> list[dict[str, Any]]:
        return sorted(self._rows("categories", "name.asc"), key=lambda item: item["name"])

    def add_category(self, name: str) -> None:
        clean_name = name.strip()
        if clean_name and clean_name not in {row["name"] for row in self.list_categories()}:
            self._insert("categories", {"id": f"CAT-{uuid4().hex[:8].upper()}", "name": clean_name})

    def delete_category(self, item_id: str) -> None:
        self._delete("categories", "id", item_id)

    def list_projects(self) -> list[dict[str, Any]]:
        return self._rows("projects", "name.asc")

    def add_project(self, name: str, description: str = "", **details: Any) -> dict[str, Any]:
        now = _now()
        return self._insert(
            "projects",
            {
                "id": f"PROJECT-{uuid4().hex[:8].upper()}",
                "name": name.strip(),
                "description": description.strip(),
                "start_date": _value(details.get("start_date")) if details.get("start_date") else None,
                "deadline": _value(details.get("deadline")) if details.get("deadline") else None,
                "department": str(details.get("department") or "").strip(),
                "status": details.get("status") or "진행 중",
                "priority": details.get("priority") or "보통",
                "memo": str(details.get("memo") or "").strip(),
                "created_at": now,
                "updated_at": now,
            },
        )

    def update_project(self, item_id: str, **changes: Any) -> None:
        self._update("projects", "id", item_id, {**changes, "updated_at": _now()})

    def delete_project(self, item_id: str, *, delete_tasks: bool = False) -> None:
        related = [task for task in self.list_tasks() if task.get("project_id") == item_id]
        if delete_tasks:
            for task in related:
                self.delete_task(str(task["task_id"]))
        else:
            for task in related:
                self.update_task(str(task["task_id"]), {"project_id": None})
        self._delete("projects", "id", item_id)

    def list_task_templates(self) -> list[dict[str, Any]]:
        return self._rows("task_templates", "name.asc")

    def add_task_template(self, name: str, category: str, steps: list[str]) -> None:
        self._insert("task_templates", {"id": f"TPL-{uuid4().hex[:8].upper()}", "name": name.strip(), "category": category, "steps": [step.strip() for step in steps if step.strip()]})

    def delete_task_template(self, item_id: str) -> None:
        self._delete("task_templates", "id", item_id)

    def list_reminders(self) -> list[dict[str, Any]]:
        return sorted(self._rows("reminders", "reminder_time.asc"), key=lambda item: item.get("reminder_time") or "")

    def add_reminder(self, title: str, reminder_time: str, repeat_type: str = "weekday") -> None:
        self._insert("reminders", {"id": f"REM-{uuid4().hex[:8].upper()}", "title": title.strip(), "reminder_time": reminder_time[:5], "repeat_type": repeat_type, "enabled": True})

    def update_reminder(self, item_id: str, **changes: Any) -> None:
        self._update("reminders", "id", item_id, changes)

    def delete_reminder(self, item_id: str) -> None:
        self._delete("reminders", "id", item_id)

    def list_checklists(self) -> list[dict[str, Any]]:
        return self._rows("checklists", "created_at.asc")

    def add_checklist(self, title: str) -> None:
        self._insert("checklists", {"id": f"CHK-{uuid4().hex[:8].upper()}", "title": title.strip(), "enabled": True, "checked_on": None, "created_at": _now()})

    def update_checklist(self, item_id: str, **changes: Any) -> None:
        self._update("checklists", "id", item_id, changes)

    def delete_checklist(self, item_id: str) -> None:
        self._delete("checklists", "id", item_id)

    def list_content_records(self) -> list[dict[str, Any]]:
        return self._rows("content_records", "upload_date.desc")

    def get_content_record(self, item_id: str | None) -> dict[str, Any] | None:
        if not item_id:
            return None
        return next((row for row in self.list_content_records() if str(row.get("id")) == str(item_id)), None)

    def get_content_record_by_task(self, task_id: str | None) -> dict[str, Any] | None:
        if not task_id:
            return None
        return next((row for row in self.list_content_records() if str(row.get("task_id")) == str(task_id)), None)

    def add_content_record(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_content_record_by_task(payload.get("task_id"))
        if existing:
            return existing
        now = _now()
        row = {"id": f"CONTENT-{uuid4().hex[:8].upper()}", "created_at": now, "updated_at": now, **_clean(payload)}
        return self._insert("content_records", row)

    def update_content_record(self, item_id: str, payload: dict[str, Any]) -> None:
        self._update("content_records", "id", item_id, {**_clean(payload), "updated_at": _now()})

    def delete_content_record(self, item_id: str) -> None:
        self._delete("content_records", "id", item_id)

    def list_document_templates(self) -> list[dict[str, Any]]:
        return self._rows("document_templates", "name.asc")

    def add_document_template(self, name: str, document_type: str, content: str) -> None:
        self._insert("document_templates", {"id": f"DOC-TPL-{uuid4().hex[:8].upper()}", "name": name.strip(), "document_type": document_type.strip(), "content": content, "updated_at": _now()})

    def update_document_template(self, item_id: str, **changes: Any) -> None:
        self._update("document_templates", "id", item_id, {**changes, "updated_at": _now()})

    def delete_document_template(self, item_id: str) -> None:
        self._delete("document_templates", "id", item_id)

    def list_documents(self) -> list[dict[str, Any]]:
        return self._rows("documents", "created_at.desc")

    def add_document(
        self,
        *,
        title: str,
        category: str,
        department: str,
        professor: str,
        task_id: str | None,
        content: str,
        file_name: str | None = None,
        file_bytes: bytes | None = None,
        mime_type: str = "application/octet-stream",
    ) -> None:
        item_id = f"DOC-{uuid4().hex[:8].upper()}"
        file_path = None
        if file_name and file_bytes and self.persistent:
            safe_name = PurePosixPath(file_name).name.replace(" ", "_")
            file_path = self.db.upload(DOCUMENT_BUCKET, f"{item_id}/{safe_name}", file_bytes, mime_type)
        row: dict[str, Any] = {
            "id": item_id,
            "title": title.strip(),
            "category": category,
            "department": department.strip(),
            "professor": professor.strip(),
            "task_id": task_id or None,
            "content": content,
            "file_path": file_path,
            "file_name": file_name,
            "mime_type": mime_type,
            "created_at": _now(),
            "updated_at": _now(),
        }
        if file_bytes and not self.persistent:
            row["_file_bytes"] = file_bytes
        self._insert("documents", row)

    def update_document(self, item_id: str, **changes: Any) -> None:
        self._update("documents", "id", item_id, {**changes, "updated_at": _now()})

    def document_bytes(self, document: dict[str, Any]) -> bytes | None:
        if self.persistent and document.get("file_path"):
            return self.db.download(DOCUMENT_BUCKET, str(document["file_path"]))
        value = document.get("_file_bytes")
        return bytes(value) if value else None

    def delete_document(self, document: dict[str, Any]) -> None:
        if self.persistent and document.get("file_path"):
            try:
                self.db.delete_object(DOCUMENT_BUCKET, str(document["file_path"]))
            except DatabaseError:
                pass
        self._delete("documents", "id", str(document["id"]))

    def export_bundle(self) -> dict[str, list[dict[str, Any]]]:
        try:
            status_history = self._rows("task_status_history", "changed_at.desc")
        except DatabaseError:
            status_history = []
        bundle = {
            "tasks": self.list_tasks(),
            "waiting_items": self.list_waiting_items(),
            "categories": self.list_categories(),
            "projects": self.list_projects(),
            "task_templates": self.list_task_templates(),
            "reminders": self.list_reminders(),
            "checklists": self.list_checklists(),
            "content_records": self.list_content_records(),
            "documents": self.list_documents(),
            "document_templates": self.list_document_templates(),
            "task_status_history": status_history,
        }
        for document in bundle["documents"]:
            document.pop("_file_bytes", None)
        return bundle
