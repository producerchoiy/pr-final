from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from html import escape
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import streamlit as st

from app_data import DEFAULT_CATEGORIES, PRIORITIES, WAITING_STATUSES, WORKFLOW_STATUSES, parse_time
from app_styles import (
    inject_css,
    render_app_heading,
    render_family_closing,
    render_sidebar_brand,
    render_sister_note,
    schedule_row,
    section_heading,
    task_card,
    waiting_card,
)
from database import DatabaseError
from date_utils import as_date, calendar_weeks, human_date, human_datetime, korea_now, week_end
from export_utils import content_records_excel
from llm_service import LLMError, generate_script, is_configured as llm_is_configured
from repository import Repository


BASE_DIR = Path(__file__).parent
TODAY = korea_now().date()

st.set_page_config(
    page_title="홍보 바다 | 업무 자동화",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
repo = Repository()

STATE_DEFAULTS = {
    "flash": "",
    "home_filter": "오늘 할 일",
    "show_create_task": False,
    "create_default_date": TODAY,
    "show_task_detail": False,
    "selected_task_id": None,
    "confirm_delete_task_id": None,
    "youtube_record_task_id": None,
    "calendar_year": TODAY.year,
    "calendar_month": TODAY.month,
    "ai_result": "",
}
for key, value in STATE_DEFAULTS.items():
    st.session_state.setdefault(key, value)


def set_flash(message: str) -> None:
    st.session_state.flash = message


def show_flash() -> None:
    if st.session_state.flash:
        st.toast(st.session_state.flash, icon="🌊")
        st.session_state.flash = ""


def run_action(action: Callable[[], Any], success: str, *, rerun: bool = True) -> bool:
    try:
        action()
    except DatabaseError as error:
        st.error(str(error))
        return False
    set_flash(success)
    if rerun:
        st.rerun()
    return True


def open_task(task_id: str) -> None:
    st.session_state.selected_task_id = task_id
    st.session_state.show_task_detail = True


def request_create_task(default_date: date | None = None) -> None:
    st.session_state.create_default_date = default_date or TODAY
    st.session_state.show_create_task = True


def task_options(tasks: list[dict[str, Any]]) -> dict[str, str]:
    return {f"{task['title']} · {task['task_id']}": task["task_id"] for task in tasks}


def category_names() -> list[str]:
    rows = repo.list_categories()
    return [row["name"] for row in rows] or DEFAULT_CATEGORIES


@st.dialog("새 업무 등록", width="large")
def create_task_dialog() -> None:
    templates = repo.list_task_templates()
    template_map = {"직접 입력": None, **{template["name"]: template for template in templates}}
    selected_name = st.selectbox("업무 세트", list(template_map), key="create_template_select")
    selected_template = template_map[selected_name]
    categories = category_names()
    default_category = selected_template.get("category") if selected_template else categories[0]
    default_steps = selected_template.get("steps", []) if selected_template else []
    st.caption("한 번 등록한 업무는 시간표, 캘린더, 업무 흐름, 대기·회신 화면에 같은 업무 ID로 연결됩니다.")

    with st.form("create_task_form"):
        left, right = st.columns(2)
        with left:
            title = st.text_input("업무명 *", placeholder="예: 감염내과 교수 독감 인터뷰")
            category = st.selectbox("업무 유형", categories, index=categories.index(default_category) if default_category in categories else 0)
            priority = st.selectbox("우선순위", PRIORITIES)
            status = st.selectbox("현재 단계", WORKFLOW_STATUSES[:-1])
        with right:
            execution_date = st.date_input("실행 예정일", value=st.session_state.create_default_date)
            deadline = st.date_input("최종 마감일", value=st.session_state.create_default_date + timedelta(days=3))
            time_left, time_right = st.columns(2)
            start_time = time_left.time_input("시작", value=time(9, 0))
            end_time = time_right.time_input("종료", value=time(10, 0))

        projects = repo.list_projects()
        project_map = {"연결 안 함": None, **{project["name"]: project["id"] for project in projects}}
        project_name = st.selectbox("상위 프로젝트", list(project_map))
        featured = st.checkbox("⭐ 캘린더에서 우선 표시")
        description = st.text_area("업무 설명·메모", placeholder="요청사항, 참고할 내용, 주의사항")
        next_action = st.text_input("다음 행동", placeholder="비워두면 첫 번째 미완료 단계가 자동 표시됩니다.")
        steps_text = st.text_area(
            "순차 단계 · 한 줄에 하나",
            value="\n".join(str(step) for step in default_steps),
            height=150,
            key=f"create_steps_{selected_name}",
        )
        st.markdown("##### 회신이나 승인을 기다려야 한다면")
        wait_left, wait_mid, wait_right = st.columns(3)
        waiting_for = wait_left.text_input("대기 대상", placeholder="예: 김OO 교수")
        waiting_type = wait_mid.text_input("대기 유형", placeholder="일정 회신·검토·승인")
        followup_date = wait_right.date_input("재확인일", value=execution_date)
        followup_time = wait_right.time_input("재확인 시간", value=time(15, 0))

        submitted = st.form_submit_button("업무 등록", type="primary", width="stretch")
        if submitted:
            if not title.strip():
                st.error("업무명을 입력해 주세요.")
                return
            steps = [{"title": line.strip(), "completed": False} for line in steps_text.splitlines() if line.strip()]
            payload = {
                "title": title,
                "category": category,
                "priority": priority,
                "status": "회신대기" if waiting_for.strip() and status == "기획" else status,
                "execution_date": execution_date,
                "deadline": deadline,
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project_map[project_name],
                "featured": featured,
                "description": description,
                "next_action": next_action,
                "waiting_for": waiting_for,
                "waiting_type": waiting_type,
                "request_date": datetime.combine(TODAY, korea_now().time()).isoformat() if waiting_for.strip() else None,
                "followup_date": datetime.combine(followup_date, followup_time).isoformat() if waiting_for.strip() else None,
                "workflow_steps": steps,
            }
            try:
                repo.create_task(payload)
            except DatabaseError as error:
                st.error(str(error))
                return
            st.session_state.show_create_task = False
            set_flash("새 업무가 등록되었습니다.")
            st.rerun()

    if st.button("닫기", width="stretch", key="close_create_dialog"):
        st.session_state.show_create_task = False
        st.rerun()


@st.dialog("업무 상세·수정", width="large")
def task_detail_dialog(task_id: str) -> None:
    task = repo.get_task(task_id)
    if not task:
        st.error("업무를 찾을 수 없습니다.")
        st.session_state.show_task_detail = False
        return
    st.caption(f"업무 ID · {task_id}")
    categories = category_names()
    steps = task.get("workflow_steps", [])
    step_titles = [str(step.get("title", "")) for step in steps]
    completed_titles = [str(step.get("title", "")) for step in steps if step.get("completed")]

    with st.form(f"edit_task_{task_id}"):
        left, right = st.columns(2)
        with left:
            title = st.text_input("업무명", value=task.get("title", ""))
            category = st.selectbox("업무 유형", categories, index=categories.index(task.get("category")) if task.get("category") in categories else 0)
            priority = st.selectbox("우선순위", PRIORITIES, index=PRIORITIES.index(task.get("priority")) if task.get("priority") in PRIORITIES else 0)
            status = st.selectbox("현재 단계", WORKFLOW_STATUSES, index=WORKFLOW_STATUSES.index(task.get("status")) if task.get("status") in WORKFLOW_STATUSES else 0)
        with right:
            execution_date = st.date_input("실행 예정일", value=as_date(task.get("execution_date")))
            deadline = st.date_input("최종 마감일", value=as_date(task.get("deadline")))
            time_left, time_right = st.columns(2)
            start_time = time_left.time_input("시작", value=parse_time(task.get("start_time")))
            end_time = time_right.time_input("종료", value=parse_time(task.get("end_time"), time(10, 0)))

        projects = repo.list_projects()
        project_map = {"연결 안 함": None, **{project["name"]: project["id"] for project in projects}}
        current_project_name = next((name for name, item_id in project_map.items() if item_id == task.get("project_id")), "연결 안 함")
        project_name = st.selectbox("상위 프로젝트", list(project_map), index=list(project_map).index(current_project_name))
        featured = st.checkbox("⭐ 캘린더에서 우선 표시", value=bool(task.get("featured")))
        description = st.text_area("업무 설명·메모", value=task.get("description") or "")
        next_action = st.text_input("다음 행동", value=task.get("next_action") or "")
        step_text = st.text_area("순차 단계 · 한 줄에 하나", value="\n".join(step_titles), height=145)
        clean_step_titles = [line.strip() for line in step_text.splitlines() if line.strip()]
        completed = st.multiselect("완료된 단계", clean_step_titles, default=[title for title in completed_titles if title in clean_step_titles])

        st.markdown("##### 대기·회신")
        wait_left, wait_right = st.columns(2)
        waiting_for = wait_left.text_input("대기 대상", value=task.get("waiting_for") or "")
        waiting_type = wait_right.text_input("대기 유형", value=task.get("waiting_type") or "")
        current_followup = task.get("followup_date") or f"{TODAY.isoformat()}T15:00:00"
        try:
            followup_dt = datetime.fromisoformat(str(current_followup).replace("Z", "+00:00"))
        except ValueError:
            followup_dt = datetime.combine(TODAY, time(15, 0))
        follow_left, follow_right = st.columns(2)
        followup_date = follow_left.date_input("재확인일", value=followup_dt.date())
        followup_time = follow_right.time_input("재확인 시간", value=followup_dt.time().replace(tzinfo=None))

        saved = st.form_submit_button("변경사항 저장", type="primary", width="stretch")
        if saved:
            new_steps = [
                {
                    "id": steps[index].get("id") if index < len(steps) else None,
                    "title": name,
                    "completed": name in completed,
                }
                for index, name in enumerate(clean_step_titles)
            ]
            old_status = task.get("status")
            changes = {
                "title": title,
                "category": category,
                "priority": priority,
                "status": status,
                "execution_date": execution_date,
                "deadline": deadline,
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project_map[project_name],
                "featured": featured,
                "description": description,
                "next_action": next_action,
                "waiting_for": waiting_for or None,
                "waiting_type": waiting_type or None,
                "request_date": task.get("request_date") or (korea_now().isoformat() if waiting_for else None),
                "followup_date": datetime.combine(followup_date, followup_time).isoformat() if waiting_for else None,
                "workflow_steps": new_steps,
            }
            try:
                repo.update_task(task_id, changes)
            except DatabaseError as error:
                st.error(str(error))
                return
            st.session_state.show_task_detail = False
            if category == "유튜브" and status == "완료" and old_status != "완료":
                st.session_state.youtube_record_task_id = task_id
            set_flash("업무 변경사항이 모든 화면에 반영되었습니다.")
            st.rerun()

    complete_col, delete_col = st.columns(2)
    if complete_col.button("✓ 업무 완료", width="stretch", disabled=task.get("status") == "완료", key=f"dialog_complete_{task_id}"):
        try:
            repo.complete_task(task_id)
        except DatabaseError as error:
            st.error(str(error))
        else:
            st.session_state.show_task_detail = False
            if task.get("category") == "유튜브":
                st.session_state.youtube_record_task_id = task_id
            set_flash("업무를 완료했습니다.")
            st.rerun()
    confirm_delete = delete_col.checkbox("삭제 확인", key=f"dialog_delete_check_{task_id}")
    if delete_col.button("🗑 업무 삭제", width="stretch", disabled=not confirm_delete, key=f"dialog_delete_{task_id}"):
        run_action(lambda: repo.delete_task(task_id), "업무를 삭제했습니다.", rerun=False)
        st.session_state.show_task_detail = False
        st.rerun()


@st.dialog("유튜브 업로드 실적 기록", width="large")
def youtube_record_dialog(task_id: str) -> None:
    task = repo.get_task(task_id)
    if not task:
        st.session_state.youtube_record_task_id = None
        return
    st.success("유튜브 업무가 완료되었습니다. 아래 내용을 입력하면 실적표에 바로 기록됩니다.")
    with st.form(f"youtube_record_{task_id}"):
        title = st.text_input("제목", value=task.get("title", ""))
        left, right = st.columns(2)
        professor = left.text_input("출연 교수")
        department = right.text_input("진료과")
        upload_date = left.date_input("업로드일", value=TODAY)
        content_types = right.multiselect("콘텐츠 유형", ["롱폼", "쇼츠", "인터뷰", "건강정보"], default=["인터뷰"])
        url = st.text_input("유튜브 URL", placeholder="https://youtube.com/...")
        memo = st.text_area("메모")
        submitted = st.form_submit_button("실적 기록", type="primary", width="stretch")
        if submitted:
            payload = {
                "task_id": task_id,
                "platform": "YouTube",
                "title": title,
                "professor": professor,
                "department": department,
                "content_type": ", ".join(content_types),
                "upload_date": upload_date,
                "url": url,
                "memo": memo,
            }
            try:
                repo.add_content_record(payload)
            except DatabaseError as error:
                st.error(str(error))
                return
            st.session_state.youtube_record_task_id = None
            set_flash("유튜브 실적표에 자동 기록했습니다.")
            st.rerun()
    if st.button("나중에 기록", width="stretch", key=f"youtube_later_{task_id}"):
        st.session_state.youtube_record_task_id = None
        st.rerun()


def complete_task(task: dict[str, Any]) -> None:
    try:
        repo.complete_task(task["task_id"])
    except DatabaseError as error:
        st.error(str(error))
        return
    if task.get("category") == "유튜브":
        st.session_state.youtube_record_task_id = task["task_id"]
    set_flash("업무를 완료했습니다.")
    st.rerun()


def quick_actions(task: dict[str, Any], prefix: str, *, compact: bool = False) -> None:
    task_id = task["task_id"]
    edit_col, complete_col, delete_col = st.columns(3)
    if edit_col.button("✏️ 수정" if not compact else "✏️", key=f"{prefix}_edit_{task_id}", width="stretch", help="업무 상세 열기"):
        open_task(task_id)
    if complete_col.button("✓ 완료" if not compact else "✓", key=f"{prefix}_complete_{task_id}", width="stretch", disabled=task.get("status") == "완료"):
        complete_task(task)
    if delete_col.button("🗑 삭제" if not compact else "🗑", key=f"{prefix}_delete_{task_id}", width="stretch"):
        st.session_state.confirm_delete_task_id = task_id
        st.rerun()
    if st.session_state.confirm_delete_task_id == task_id:
        st.warning(f"‘{task['title']}’ 업무를 삭제할까요? 연결된 단계와 대기 정보도 함께 삭제됩니다.")
        yes, no = st.columns(2)
        if yes.button("정말 삭제", type="primary", key=f"{prefix}_confirm_{task_id}", width="stretch"):
            st.session_state.confirm_delete_task_id = None
            run_action(lambda: repo.delete_task(task_id), "업무를 삭제했습니다.")
        if no.button("취소", key=f"{prefix}_cancel_{task_id}", width="stretch"):
            st.session_state.confirm_delete_task_id = None
            st.rerun()


def task_cards(tasks: list[dict[str, Any]], prefix: str, *, columns: int = 2) -> None:
    if not tasks:
        st.markdown('<div class="empty-state">조건에 맞는 업무가 없습니다.</div>', unsafe_allow_html=True)
        return
    grid = st.columns(columns)
    for index, task in enumerate(tasks):
        with grid[index % columns]:
            st.markdown(task_card(task), unsafe_allow_html=True)
            quick_actions(task, f"{prefix}_{index}")


def filtered_home_tasks(tasks: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    end = week_end(TODAY)
    active = [task for task in tasks if task.get("status") != "완료"]
    if key == "오늘 할 일":
        return [task for task in active if as_date(task.get("execution_date")) == TODAY]
    if key == "오늘 마감":
        return [task for task in active if as_date(task.get("deadline")) == TODAY]
    if key == "대기·회신":
        return [task for task in active if task.get("waiting_for") or task.get("status") in WAITING_STATUSES]
    return [task for task in active if TODAY <= as_date(task.get("deadline")) <= end]


def render_stat_filters(tasks: list[dict[str, Any]]) -> None:
    definitions = [
        ("오늘 할 일", "🗓️", "실행 예정일이 오늘"),
        ("오늘 마감", "⏰", "최종 마감이 오늘"),
        ("대기·회신", "💌", "검토·승인·회신 대기"),
        ("이번 주 마감", "📌", "오늘부터 일요일까지"),
    ]
    columns = st.columns(4)
    for index, (column, (label, icon, note)) in enumerate(zip(columns, definitions)):
        count = len(filtered_home_tasks(tasks, label))
        with column:
            with st.container(key=f"stat_card_{index}"):
                st.markdown(
                    f'<div class="stat-label">{icon} {label}</div><div class="stat-note">{note}</div>',
                    unsafe_allow_html=True,
                )
                if st.button(f"{count}건", key=f"stat_{label}", width="stretch", help=f"{label} 업무만 보기"):
                    st.session_state.home_filter = label
                    st.rerun()


def render_schedule(tasks: list[dict[str, Any]]) -> None:
    heading, add = st.columns([4, 1])
    with heading:
        section_heading("TODAY SCHEDULE", "오늘의 시간표", "시간을 변경하면 같은 업무 ID를 사용하는 모든 화면에 즉시 반영됩니다.")
    if add.button("＋ 일정", type="primary", width="stretch", key="add_today_schedule"):
        request_create_task(TODAY)
    scheduled = sorted(
        [task for task in tasks if as_date(task.get("execution_date")) == TODAY],
        key=lambda task: task.get("start_time") or "23:59",
    )
    if not scheduled:
        st.markdown('<div class="empty-state">오늘 시간표가 비어 있습니다. ‘＋ 일정’으로 업무를 배치하세요.</div>', unsafe_allow_html=True)
        return
    for index, task in enumerate(scheduled):
        body, edit, done, delete = st.columns([6, 1, 1, 1])
        body.markdown(schedule_row(task), unsafe_allow_html=True)
        if edit.button("✏️", key=f"schedule_edit_{task['task_id']}_{index}", width="stretch", help="수정"):
            open_task(task["task_id"])
        if done.button("✓", key=f"schedule_done_{task['task_id']}_{index}", width="stretch", disabled=task.get("status") == "완료", help="완료"):
            complete_task(task)
        if delete.button("🗑", key=f"schedule_delete_{task['task_id']}_{index}", width="stretch", help="삭제"):
            st.session_state.confirm_delete_task_id = task["task_id"]
            st.rerun()
        if st.session_state.confirm_delete_task_id == task["task_id"]:
            st.warning(f"‘{task['title']}’ 일정을 삭제하면 연결된 업무도 함께 삭제됩니다.")
            yes, no = st.columns(2)
            if yes.button("정말 삭제", key=f"schedule_confirm_{task['task_id']}", type="primary", width="stretch"):
                st.session_state.confirm_delete_task_id = None
                run_action(lambda item_id=task["task_id"]: repo.delete_task(item_id), "업무를 삭제했습니다.")
            if no.button("취소", key=f"schedule_cancel_{task['task_id']}", width="stretch"):
                st.session_state.confirm_delete_task_id = None
                st.rerun()


def render_waiting_list(waiting_items: list[dict[str, Any]], prefix: str, limit: int | None = None) -> None:
    items = waiting_items[:limit] if limit else waiting_items
    if not items:
        st.markdown('<div class="empty-state">현재 기다리는 회신이 없습니다.</div>', unsafe_allow_html=True)
        return
    for index, item in enumerate(items):
        task = item.get("task") or {}
        st.markdown(waiting_card(item), unsafe_allow_html=True)
        complete, recontact, open_col = st.columns(3)
        if complete.button("회신 완료", key=f"{prefix}_wait_done_{item['task_id']}_{index}", width="stretch"):
            run_action(lambda item_id=item["task_id"]: repo.complete_waiting(item_id), "회신 완료로 처리했습니다.")
        if recontact.button("재연락", key=f"{prefix}_wait_again_{item['task_id']}_{index}", width="stretch"):
            run_action(lambda item_id=item["task_id"]: repo.recontact(item_id), "재연락 시간을 갱신했습니다.")
        if open_col.button("업무 열기", key=f"{prefix}_wait_open_{item['task_id']}_{index}", width="stretch"):
            open_task(str(task.get("task_id")))


def render_workflow(tasks: list[dict[str, Any]]) -> None:
    section_heading("WORKFLOW", "업무 흐름", "단계별 업무와 다음 행동을 함께 확인합니다.")
    active_statuses = [status for status in WORKFLOW_STATUSES if status != "완료"]
    for group_index in range(0, len(active_statuses), 4):
        columns = st.columns(4)
        for column, status in zip(columns, active_statuses[group_index : group_index + 4]):
            with column:
                rows = [task for task in tasks if task.get("status") == status]
                content = "".join(
                    f'<div class="flow-task"><b>{escape(str(task["title"]))}</b><span>다음 → {escape(str(task.get("next_action") or "지정 필요"))}</span></div>'
                    for task in rows[:4]
                ) or '<div class="flow-task"><span>대기 업무 없음</span></div>'
                st.markdown(f'<div class="flow-column"><h3>{status} · {len(rows)}</h3>{content}</div>', unsafe_allow_html=True)
                for index, task in enumerate(rows[:4]):
                    if st.button(f"열기 · {task['title'][:12]}", key=f"flow_{status}_{task['task_id']}_{index}", width="stretch"):
                        open_task(task["task_id"])


def render_end_day_checklist() -> None:
    section_heading("5-MINUTE CLOSE", "퇴근 전 5분", "퇴근 전에 확인할 항목을 직접 관리합니다.")
    left, right = st.columns([1.35, 1])
    with left:
        checks = [item for item in repo.list_checklists() if item.get("enabled", True)]
        for index, item in enumerate(checks):
            checked = item.get("checked_on") == TODAY.isoformat()
            value = st.checkbox(item["title"], value=checked, key=f"daily_check_{item['id']}_{TODAY}")
            if value != checked:
                repo.update_checklist(str(item["id"]), checked_on=TODAY.isoformat() if value else None)
            if st.session_state.get("edit_checklist_id") == item["id"]:
                edited = st.text_input("항목 수정", value=item["title"], key=f"daily_edit_text_{item['id']}")
                save, remove, cancel = st.columns(3)
                if save.button("저장", key=f"daily_edit_save_{item['id']}", width="stretch"):
                    run_action(lambda item_id=str(item["id"]), text=edited: repo.update_checklist(item_id, title=text), "점검 항목을 수정했습니다.")
                if remove.button("삭제", key=f"daily_edit_delete_{item['id']}", width="stretch"):
                    run_action(lambda item_id=str(item["id"]): repo.delete_checklist(item_id), "점검 항목을 삭제했습니다.")
                if cancel.button("취소", key=f"daily_edit_cancel_{item['id']}", width="stretch"):
                    st.session_state.edit_checklist_id = None
                    st.rerun()
            elif st.button("수정", key=f"daily_edit_{item['id']}_{index}"):
                st.session_state.edit_checklist_id = item["id"]
                st.rerun()
        with st.form("add_daily_check"):
            new_item = st.text_input("새 점검 항목", placeholder="예: 내일 촬영 배터리 충전")
            if st.form_submit_button("＋ 항목 추가", width="stretch") and new_item.strip():
                run_action(lambda: repo.add_checklist(new_item), "점검 항목을 추가했습니다.")
    with right:
        render_sister_note()
    render_family_closing()


@st.fragment(run_every="60s")
def reminder_pulse() -> None:
    now = korea_now()
    current = now.strftime("%H:%M")
    for reminder in repo.list_reminders():
        repeat_ok = reminder.get("repeat_type") != "weekday" or now.weekday() < 5
        if reminder.get("enabled") and str(reminder.get("reminder_time", ""))[:5] == current and repeat_ok:
            token = f"{now.date()}-{current}-{reminder['id']}"
            if st.session_state.get("last_reminder_token") != token:
                st.toast(f"🔔 {reminder['title']} 시간입니다.")
                st.session_state.last_reminder_token = token


def dashboard_page(tasks: list[dict[str, Any]]) -> None:
    render_app_heading(repo.mode_label)
    render_stat_filters(tasks)
    st.write("")
    render_schedule(tasks)
    st.write("")

    urgent_tasks = [task for task in tasks if task.get("priority") == "긴급" and task.get("status") != "완료"]
    if urgent_tasks:
        section_heading("URGENT", "🚨 긴급 업무", "실행 예정일과 관계없이 모든 긴급 업무를 표시합니다.")
        task_cards(urgent_tasks, "urgent", columns=2)
        st.write("")

    selected = st.session_state.home_filter
    selected_tasks = filtered_home_tasks(tasks, selected)
    left, right = st.columns([1.5, 1])
    with left:
        section_heading("ACTION NOW", f"{selected} · 실행 업무", "우선순위와 마감일을 기준으로 정렬합니다.")
        ordered = sorted(selected_tasks, key=lambda task: (task.get("priority") != "긴급", task.get("deadline") or "9999-12-31"))
        task_cards(ordered[:6], "home", columns=1)
    with right:
        section_heading("WAITING", "대기·회신", "직접 실행할 업무와 회신을 기다리는 업무를 구분합니다.")
        render_waiting_list(repo.list_waiting_items(), "home", limit=4)

    st.write("")
    render_workflow(tasks)
    st.write("")
    render_end_day_checklist()


def all_tasks_page(tasks: list[dict[str, Any]]) -> None:
    section_heading("ALL TASKS", "📋 전체 업무", "업무 ID를 기준으로 모든 화면의 변경 사항이 즉시 반영됩니다.")
    search_col, category_col, status_col = st.columns([2, 1, 1])
    search = search_col.text_input("검색", placeholder="업무명·다음 행동·대기자·업무 ID", label_visibility="collapsed")
    categories = category_names()
    category = category_col.selectbox("유형", ["전체"] + categories, label_visibility="collapsed")
    status = status_col.selectbox("단계", ["전체"] + WORKFLOW_STATUSES, label_visibility="collapsed")
    filtered = tasks
    if search:
        query = search.lower().strip()
        filtered = [task for task in filtered if query in " ".join(str(value) for value in task.values()).lower()]
    if category != "전체":
        filtered = [task for task in filtered if task.get("category") == category]
    if status != "전체":
        filtered = [task for task in filtered if task.get("status") == status]
    task_cards(filtered, "all_tasks")


def calendar_page(tasks: list[dict[str, Any]]) -> None:
    section_heading("MONTHLY CALENDAR", "📅 콘텐츠 캘린더", "실행 예정일을 기준으로 표시하며, 우선 업무는 상단에 배치합니다.")
    previous, title_col, next_col = st.columns([1, 4, 1])
    if previous.button("← 이전 달", width="stretch"):
        month = st.session_state.calendar_month - 1
        if month == 0:
            st.session_state.calendar_year -= 1
            month = 12
        st.session_state.calendar_month = month
        st.rerun()
    title_col.markdown(f"### {st.session_state.calendar_year}년 {st.session_state.calendar_month}월")
    if next_col.button("다음 달 →", width="stretch"):
        month = st.session_state.calendar_month + 1
        if month == 13:
            st.session_state.calendar_year += 1
            month = 1
        st.session_state.calendar_month = month
        st.rerun()

    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    for column, label in zip(st.columns(7), weekdays):
        column.markdown(f'<div class="day-head">{label}</div>', unsafe_allow_html=True)

    year, month = st.session_state.calendar_year, st.session_state.calendar_month
    for week_index, week in enumerate(calendar_weeks(year, month)):
        columns = st.columns(7)
        for day_index, (column, day_number) in enumerate(zip(columns, week)):
            with column:
                with st.container(key=f"calendar_cell_{week_index}_{day_index}"):
                    if day_number == 0:
                        st.markdown('<div class="calendar-empty"></div>', unsafe_allow_html=True)
                        continue
                    day = date(year, month, day_number)
                    day_tasks = [task for task in tasks if as_date(task.get("execution_date")) == day]
                    day_tasks.sort(key=lambda task: (not bool(task.get("featured")), task.get("start_time") or "23:59"))
                    st.markdown(f'<div class="calendar-date">{day_number}</div>', unsafe_allow_html=True)
                    for item_index, task in enumerate(day_tasks[:3]):
                        star = "⭐ " if task.get("featured") else ""
                        if st.button(f"{star}{task['title'][:13]}", key=f"cal_{week_index}_{day_index}_{item_index}_{task['task_id']}", width="stretch", help=f"{task.get('start_time', '')[:5]} · {task.get('next_action', '')}"):
                            open_task(task["task_id"])
                    if len(day_tasks) > 3:
                        st.caption(f"외 {len(day_tasks) - 3}건")


def waiting_page() -> None:
    section_heading("WAITING & FOLLOW-UP", "⏳ 대기·회신", "요청 시각과 재확인 시각을 놓치지 않도록 관리합니다.")
    items = repo.list_waiting_items()
    due_today = [item for item in items if item.get("followup_at") and as_date(str(item.get("followup_at"))) <= TODAY]
    c1, c2 = st.columns(2)
    c1.metric("전체 대기", len(items))
    c2.metric("오늘 재확인", len(due_today))
    st.write("")
    render_waiting_list(items, "waiting_page")


def content_records_page(tasks: list[dict[str, Any]]) -> None:
    section_heading("CONTENT RECORDS", "📊 유튜브 실적", "유튜브 업무 완료 시 팝업에서 입력한 내용이 자동으로 쌓입니다.")
    with st.expander("＋ 실적 직접 등록"):
        with st.form("manual_content_record"):
            options = task_options([task for task in tasks if task.get("category") == "유튜브"])
            task_label = st.selectbox("연결 업무", ["연결 안 함"] + list(options))
            title = st.text_input("제목 *")
            left, right = st.columns(2)
            professor = left.text_input("출연 교수")
            department = right.text_input("진료과")
            upload_date = left.date_input("업로드일", value=TODAY)
            content_type = right.selectbox("콘텐츠 유형", ["롱폼", "쇼츠", "인터뷰", "건강정보"])
            url = st.text_input("유튜브 URL")
            memo = st.text_area("메모")
            if st.form_submit_button("실적 저장", type="primary", width="stretch"):
                if not title.strip():
                    st.error("제목을 입력해 주세요.")
                else:
                    payload = {
                        "task_id": options.get(task_label),
                        "platform": "YouTube",
                        "title": title,
                        "professor": professor,
                        "department": department,
                        "content_type": content_type,
                        "upload_date": upload_date,
                        "url": url,
                        "memo": memo,
                    }
                    run_action(lambda: repo.add_content_record(payload), "유튜브 실적을 저장했습니다.")

    records = repo.list_content_records()
    if not records:
        st.markdown('<div class="empty-state">아직 기록된 유튜브 실적이 없습니다.</div>', unsafe_allow_html=True)
        return
    frame = pd.DataFrame(records)
    display_columns = [column for column in ["upload_date", "title", "professor", "department", "content_type", "url", "task_id"] if column in frame]
    display = frame[display_columns].rename(columns={"upload_date": "업로드일", "title": "제목", "professor": "출연 교수", "department": "진료과", "content_type": "유형", "url": "URL", "task_id": "업무 ID"})
    st.dataframe(display, hide_index=True, width="stretch")
    try:
        excel_data = content_records_excel(records)
        st.download_button("⬇ Excel 다운로드", data=excel_data, file_name=f"youtube-content-{TODAY.isoformat()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except ImportError:
        st.warning("Excel 생성 모듈을 설치하는 중입니다. requirements.txt의 openpyxl 설치 여부를 확인해 주세요.")

    with st.expander("기록 삭제"):
        record_map = {f"{row.get('upload_date')} · {row.get('title')}": str(row["id"]) for row in records}
        selected = st.selectbox("삭제할 기록", list(record_map))
        confirm = st.checkbox("삭제 확인", key="confirm_record_delete")
        if st.button("선택 기록 삭제", disabled=not confirm, key="delete_content_record"):
            run_action(lambda: repo.delete_content_record(record_map[selected]), "콘텐츠 기록을 삭제했습니다.")


def ai_script_page(tasks: list[dict[str, Any]]) -> None:
    section_heading("AI WRITER", "✨ AI 대본 작성", "저장된 병원 문서 양식과 참고자료를 기준으로 새 원고를 작성합니다.")
    if not llm_is_configured():
        st.info("Streamlit Secrets에 OPENAI_API_KEY를 등록하면 AI 원고 생성이 활성화됩니다. 양식 관리와 입력 화면은 현재도 사용할 수 있습니다.", icon="🔑")
    templates = repo.list_document_templates()
    if not templates:
        st.warning("설정에서 문서 양식을 먼저 등록해 주세요.")
        return
    template_map = {f"{item['document_type']} · {item['name']}": item for item in templates}
    selected_label = st.selectbox("문서 양식", list(template_map))
    selected = template_map[selected_label]
    with st.form("ai_script_form"):
        left, right = st.columns(2)
        professor = left.text_input("교수명")
        department = right.text_input("진료과")
        topic = st.text_input("주제 *", placeholder="예: 전립선암 조기검진")
        length = left.text_input("원하는 길이", value="약 7분")
        tone = right.selectbox("톤", ["쉽고 신뢰감 있게", "따뜻하고 친근하게", "방송용으로 간결하게", "전문적이고 차분하게"])
        reference = st.text_area("참고자료", height=180, placeholder="보도자료, 연구자료, 의료진 확인 내용을 붙여 넣으세요.")
        uploaded = st.file_uploader("참고 텍스트 파일", type=["txt", "md", "csv", "json"])
        generated = st.form_submit_button("AI 대본 작성", type="primary", width="stretch")
        if generated:
            if not topic.strip():
                st.error("주제를 입력해 주세요.")
            elif not llm_is_configured():
                st.error("OPENAI_API_KEY를 먼저 설정해 주세요.")
            else:
                if uploaded:
                    try:
                        reference += "\n\n" + uploaded.getvalue().decode("utf-8")
                    except UnicodeDecodeError:
                        st.warning("참고 파일의 글자를 읽지 못해 직접 입력한 참고자료만 사용합니다.")
                try:
                    with st.spinner("저장된 양식을 기준으로 원고를 작성하고 있습니다..."):
                        st.session_state.ai_result = generate_script(
                            template=selected["content"],
                            document_type=selected["document_type"],
                            professor=professor,
                            department=department,
                            topic=topic,
                            reference=reference,
                            length=length,
                            tone=tone,
                        )
                except LLMError as error:
                    st.error(str(error))

    if st.session_state.ai_result:
        result = st.text_area("생성된 원고", value=st.session_state.ai_result, height=520, key="ai_result_editor")
        task_map = {"연결 안 함": None, **task_options(tasks)}
        task_label = st.selectbox("연결할 업무", list(task_map), key="ai_task_link")
        save, clear = st.columns(2)
        if save.button("자료실에 저장", type="primary", width="stretch"):
            run_action(
                lambda: repo.add_document(
                    title=f"{topic or selected['document_type']} 원고",
                    category="대본",
                    department=department,
                    professor=professor,
                    task_id=task_map[task_label],
                    content=result,
                ),
                "생성된 원고를 자료실에 저장했습니다.",
            )
        if clear.button("초기화", width="stretch"):
            st.session_state.ai_result = ""
            st.rerun()


def documents_page(tasks: list[dict[str, Any]]) -> None:
    section_heading("DOCUMENT LIBRARY", "📁 자료실", "대본·질문지·영상기획안·촬영자료를 업무 ID와 연결해 찾습니다.")
    with st.expander("＋ 자료 등록"):
        with st.form("add_document"):
            left, right = st.columns(2)
            title = left.text_input("자료 제목 *")
            category = right.selectbox("분류", ["대본", "질문지", "영상기획안", "촬영자료", "방송자료", "참고자료", "기타"])
            department = left.text_input("진료과")
            professor = right.text_input("교수명")
            options = task_options(tasks)
            task_label = st.selectbox("연결 업무", ["연결 안 함"] + list(options))
            content = st.text_area("본문 및 메모", height=180)
            uploaded = st.file_uploader("첨부파일")
            if st.form_submit_button("자료 저장", type="primary", width="stretch"):
                if not title.strip():
                    st.error("자료 제목을 입력해 주세요.")
                else:
                    run_action(
                        lambda: repo.add_document(
                            title=title,
                            category=category,
                            department=department,
                            professor=professor,
                            task_id=options.get(task_label),
                            content=content,
                            file_name=uploaded.name if uploaded else None,
                            file_bytes=uploaded.getvalue() if uploaded else None,
                            mime_type=uploaded.type if uploaded else "application/octet-stream",
                        ),
                        "자료를 저장했습니다.",
                    )

    search_col, category_col = st.columns([2, 1])
    search = search_col.text_input("자료 검색", placeholder="제목·교수명·진료과·키워드")
    category_filter = category_col.selectbox("분류 필터", ["전체", "대본", "질문지", "영상기획안", "촬영자료", "방송자료", "참고자료", "기타"])
    documents = repo.list_documents()
    if search:
        query = search.lower().strip()
        documents = [document for document in documents if query in " ".join(str(value) for value in document.values()).lower()]
    if category_filter != "전체":
        documents = [document for document in documents if document.get("category") == category_filter]
    if not documents:
        st.markdown('<div class="empty-state">조건에 맞는 자료가 없습니다.</div>', unsafe_allow_html=True)
        return
    for index, document in enumerate(documents):
        with st.expander(f"{human_date(document.get('created_at'))} · {document.get('title')} · {document.get('category')}"):
            st.caption(f"{document.get('department') or '진료과 미지정'} · {document.get('professor') or '교수 미지정'} · 업무 ID {document.get('task_id') or '연결 안 함'}")
            edited_content = st.text_area("본문 및 메모", value=document.get("content") or "", height=220, key=f"doc_content_{document['id']}_{index}")
            save_col, download_col, delete_col = st.columns(3)
            if save_col.button("수정 저장", key=f"doc_save_{document['id']}", width="stretch"):
                run_action(lambda item_id=str(document["id"]), value=edited_content: repo.update_document(item_id, content=value), "자료를 수정했습니다.")
            if document.get("file_name"):
                cache_key = f"document_download_{document['id']}"
                if download_col.button("파일 준비", key=f"doc_prepare_{document['id']}", width="stretch"):
                    try:
                        st.session_state[cache_key] = repo.document_bytes(document)
                    except DatabaseError as error:
                        st.error(str(error))
                if st.session_state.get(cache_key):
                    download_col.download_button("다운로드", data=st.session_state[cache_key], file_name=document["file_name"], mime=document.get("mime_type") or "application/octet-stream", key=f"doc_download_{document['id']}", width="stretch")
            else:
                download_col.download_button("TXT 다운로드", data=edited_content.encode("utf-8"), file_name=f"{document.get('title', 'document')}.txt", mime="text/plain", key=f"doc_text_download_{document['id']}", width="stretch")
            confirm = delete_col.checkbox("삭제 확인", key=f"doc_confirm_{document['id']}")
            if delete_col.button("삭제", disabled=not confirm, key=f"doc_delete_{document['id']}", width="stretch"):
                run_action(lambda item=document: repo.delete_document(item), "자료를 삭제했습니다.")


def settings_page() -> None:
    section_heading("SETTINGS", "⚙ 설정", "업무 유형·프로젝트·알람·체크리스트·업무 세트·문서 양식을 관리합니다.")
    if repo.persistent:
        st.success("Supabase가 연결되어 등록한 정보가 영구 저장됩니다.", icon="✅")
    else:
        st.warning("현재 체험 모드입니다. 입력 내용은 현재 세션에만 유지되며 GitHub 파일에는 저장되지 않습니다.", icon="🧪")
        st.code('SUPABASE_URL = "https://프로젝트.supabase.co"\nSUPABASE_KEY = "service-role-key"\nOPENAI_API_KEY = "선택사항"', language="toml")
    schema_path = BASE_DIR / "schema.sql"
    if not schema_path.is_file():
        schema_path = BASE_DIR / "supabase" / "schema.sql"
    if schema_path.is_file():
        st.download_button("Supabase 초기 설정 SQL 다운로드", data=schema_path.read_bytes(), file_name="schema.sql", mime="text/plain")

    category_tab, project_tab, reminder_tab, checklist_tab, task_template_tab, document_template_tab = st.tabs(
        ["업무 유형", "프로젝트", "알람", "퇴근 점검", "업무 세트", "문서 양식"]
    )
    with category_tab:
        rows = repo.list_categories()
        for row in rows:
            name_col, delete_col = st.columns([5, 1])
            name_col.write(row["name"])
            in_use = any(task.get("category") == row["name"] for task in repo.list_tasks())
            if delete_col.button("삭제", key=f"cat_delete_{row['id']}", disabled=in_use, help="사용 중인 유형은 삭제할 수 없습니다."):
                run_action(lambda item_id=str(row["id"]): repo.delete_category(item_id), "업무 유형을 삭제했습니다.")
        with st.form("add_category"):
            name = st.text_input("새 업무 유형", placeholder="예: 뉴스레터")
            if st.form_submit_button("＋ 업무 유형 추가") and name.strip():
                run_action(lambda: repo.add_category(name), "업무 유형을 추가했습니다.")

    with project_tab:
        for project in repo.list_projects():
            with st.container(border=True):
                st.write(f"**{project['name']}**")
                st.caption(project.get("description") or "설명 없음")
                in_use = any(task.get("project_id") == project["id"] for task in repo.list_tasks())
                if st.button("프로젝트 삭제", key=f"project_delete_{project['id']}", disabled=in_use):
                    run_action(lambda item_id=str(project["id"]): repo.delete_project(item_id), "프로젝트를 삭제했습니다.")
        with st.form("add_project"):
            project_name = st.text_input("프로젝트명")
            project_description = st.text_input("설명")
            if st.form_submit_button("＋ 프로젝트 추가") and project_name.strip():
                run_action(lambda: repo.add_project(project_name, project_description), "프로젝트를 추가했습니다.")

    with reminder_tab:
        for reminder in repo.list_reminders():
            enabled_col, title_col, delete_col = st.columns([1, 4, 1])
            enabled = enabled_col.checkbox("사용", value=bool(reminder.get("enabled")), key=f"rem_enabled_{reminder['id']}")
            if enabled != bool(reminder.get("enabled")):
                repo.update_reminder(str(reminder["id"]), enabled=enabled)
            title_col.write(f"**{str(reminder.get('reminder_time'))[:5]}** · {reminder['title']} · {reminder.get('repeat_type', 'weekday')}")
            if delete_col.button("삭제", key=f"rem_delete_{reminder['id']}"):
                run_action(lambda item_id=str(reminder["id"]): repo.delete_reminder(item_id), "알람을 삭제했습니다.")
        with st.form("add_reminder"):
            title = st.text_input("알람 내용")
            left, right = st.columns(2)
            reminder_time = left.time_input("시간", value=time(16, 0))
            repeat_type = right.selectbox("반복", ["weekday", "daily", "once"], format_func=lambda value: {"weekday": "평일", "daily": "매일", "once": "한 번"}[value])
            if st.form_submit_button("＋ 알람 추가") and title.strip():
                run_action(lambda: repo.add_reminder(title, reminder_time.strftime("%H:%M"), repeat_type), "알람을 추가했습니다.")

    with checklist_tab:
        for item in repo.list_checklists():
            with st.form(f"settings_check_{item['id']}"):
                title = st.text_input("항목", value=item["title"], key=f"settings_check_title_{item['id']}")
                enabled = st.checkbox("사용", value=bool(item.get("enabled", True)), key=f"settings_check_enabled_{item['id']}")
                save, remove = st.columns(2)
                if save.form_submit_button("저장", width="stretch"):
                    run_action(lambda item_id=str(item["id"]): repo.update_checklist(item_id, title=title, enabled=enabled), "점검 항목을 수정했습니다.")
                if remove.form_submit_button("삭제", width="stretch"):
                    run_action(lambda item_id=str(item["id"]): repo.delete_checklist(item_id), "점검 항목을 삭제했습니다.")

    with task_template_tab:
        for template in repo.list_task_templates():
            with st.expander(f"{template['name']} · {template['category']}"):
                for step in template.get("steps", []):
                    st.write(f"□ {step}")
                if st.button("업무 세트 삭제", key=f"tpl_delete_{template['id']}"):
                    run_action(lambda item_id=str(template["id"]): repo.delete_task_template(item_id), "업무 세트를 삭제했습니다.")
        with st.form("add_task_template"):
            name = st.text_input("업무 세트 이름")
            category = st.selectbox("기본 업무 유형", category_names())
            steps = st.text_area("세부업무 · 한 줄에 하나", height=150)
            if st.form_submit_button("＋ 업무 세트 저장") and name.strip():
                run_action(lambda: repo.add_task_template(name, category, steps.splitlines()), "업무 세트를 저장했습니다.")

    with document_template_tab:
        for template in repo.list_document_templates():
            with st.expander(f"{template['document_type']} · {template['name']}"):
                name = st.text_input("양식명", value=template["name"], key=f"doc_tpl_name_{template['id']}")
                document_type = st.text_input("문서 유형", value=template["document_type"], key=f"doc_tpl_type_{template['id']}")
                content = st.text_area("양식 본문", value=template["content"], height=260, key=f"doc_tpl_content_{template['id']}")
                save, remove = st.columns(2)
                if save.button("양식 수정 저장", key=f"doc_tpl_save_{template['id']}", width="stretch"):
                    run_action(lambda item_id=str(template["id"]): repo.update_document_template(item_id, name=name, document_type=document_type, content=content), "문서 양식을 수정했습니다.")
                if remove.button("양식 삭제", key=f"doc_tpl_delete_{template['id']}", width="stretch"):
                    run_action(lambda item_id=str(template["id"]): repo.delete_document_template(item_id), "문서 양식을 삭제했습니다.")
        with st.form("add_document_template"):
            name = st.text_input("새 양식명")
            document_type = st.text_input("문서 유형", placeholder="예: 교수 인터뷰 질문지")
            content = st.text_area("양식 본문", height=220)
            if st.form_submit_button("＋ 문서 양식 저장") and name.strip() and document_type.strip():
                run_action(lambda: repo.add_document_template(name, document_type, content), "문서 양식을 저장했습니다.")

    st.write("")
    backup = json.dumps(repo.export_bundle(), ensure_ascii=False, indent=2, default=str)
    st.download_button("전체 데이터 JSON 백업", data=backup, file_name=f"pr-work-backup-{TODAY.isoformat()}.json", mime="application/json")


PAGE_LABELS = {
    "오늘": "◉  오늘",
    "전체 업무": "▦  전체 업무",
    "콘텐츠 캘린더": "□  콘텐츠 캘린더",
    "대기·회신": "↗  대기·회신",
    "유튜브 실적": "▶  유튜브 실적",
    "AI 대본 작성": "✦  AI 대본 작성",
    "자료실": "▤  자료실",
    "설정": "⚙  설정",
}


with st.sidebar:
    render_sidebar_brand()
    st.markdown("---")
    menu = st.radio(
        "업무 메뉴",
        ["오늘", "전체 업무", "콘텐츠 캘린더", "대기·회신", "유튜브 실적", "AI 대본 작성", "자료실", "설정"],
        format_func=lambda value: PAGE_LABELS[value],
        label_visibility="collapsed",
    )
    st.markdown("---")
    if st.button("＋ 새 업무", type="primary", width="stretch"):
        request_create_task(TODAY)
    st.caption(f"저장 방식 · {repo.mode_label}")
    st.caption("GitHub → Streamlit 자동 배포")

show_flash()
reminder_pulse()

try:
    all_tasks = repo.list_tasks()
    if menu == "오늘":
        dashboard_page(all_tasks)
    elif menu == "전체 업무":
        all_tasks_page(all_tasks)
    elif menu == "콘텐츠 캘린더":
        calendar_page(all_tasks)
    elif menu == "대기·회신":
        waiting_page()
    elif menu == "유튜브 실적":
        content_records_page(all_tasks)
    elif menu == "AI 대본 작성":
        ai_script_page(all_tasks)
    elif menu == "자료실":
        documents_page(all_tasks)
    else:
        settings_page()
except DatabaseError as error:
    st.error(str(error))
    st.info("Supabase에서 schema.sql을 실행했는지, Streamlit Secrets의 URL과 키가 정확한지 확인해 주세요.")

if st.session_state.show_create_task:
    create_task_dialog()
elif st.session_state.show_task_detail and st.session_state.selected_task_id:
    task_detail_dialog(str(st.session_state.selected_task_id))
elif st.session_state.youtube_record_task_id:
    youtube_record_dialog(str(st.session_state.youtube_record_task_id))

st.markdown('<div class="foot-note">홍보 바다 · 업무와 기록을 하나의 흐름으로 관리합니다.</div>', unsafe_allow_html=True)
