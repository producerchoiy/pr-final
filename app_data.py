from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any


WORKFLOW_STATUSES = [
    "기획",
    "제작",
    "편집",
    "검토대기",
    "승인대기",
    "회신대기",
    "배포",
    "완료",
]
WAITING_STATUSES = {"회신대기", "승인대기", "검토대기"}
PRIORITIES = ["보통", "높음", "긴급"]
DEFAULT_CATEGORIES = [
    "유튜브",
    "촬영",
    "편집",
    "방송",
    "사진",
    "대본",
    "콘텐츠",
    "행사",
    "사무 업무",
    "기타",
]

DEFAULT_TASK_TEMPLATES = [
    {
        "id": "TPL-EVENT-PHOTO",
        "name": "행사 촬영 기본 세트",
        "category": "촬영",
        "steps": ["촬영", "촬영물 백업", "사진 선별", "사진 보정", "해당 부서 메일 전송", "포토앨범 업로드"],
    },
    {
        "id": "TPL-YOUTUBE",
        "name": "유튜브 인터뷰 기본 세트",
        "category": "유튜브",
        "steps": ["질문지 작성", "교수 일정 확정", "촬영", "영상 편집", "썸네일 제작", "팀장 검토", "교수 검토", "업로드"],
    },
]

DEFAULT_DOCUMENT_TEMPLATES = [
    {
        "id": "DOC-TPL-LG",
        "name": "LG헬로비전 인터뷰 양식",
        "document_type": "LG헬로비전",
        "content": "[방송 제목]\n\n[오프닝]\n\n[진행자 질문]\nQ1. \nQ2. \nQ3. \n\n[교수 답변 핵심]\n\n[생활 속 실천 팁]\n\n[클로징]",
    },
    {
        "id": "DOC-TPL-YTN",
        "name": "YTN 라디오 양식",
        "document_type": "YTN 라디오",
        "content": "[코너명]\n\n[오늘의 주제]\n\n[도입 멘트]\n\n[질문과 답변]\nQ1. \nA1. \n\n[청취자 주의사항]\n\n[마무리]",
    },
    {
        "id": "DOC-TPL-YOUTUBE",
        "name": "유튜브 교수 인터뷰 질문지",
        "document_type": "유튜브 인터뷰",
        "content": "[콘텐츠 제목]\n\n[시청자가 궁금해할 핵심 질문]\n1. \n2. \n3. \n\n[오해 바로잡기]\n\n[진료가 필요한 신호]\n\n[엔딩 한 문장]",
    },
    {
        "id": "DOC-TPL-SHORTS",
        "name": "쇼츠 질문지",
        "document_type": "쇼츠",
        "content": "[0~3초 후킹]\n\n[핵심 정보 3가지]\n1. \n2. \n3. \n\n[주의 문구]\n\n[마지막 행동 요청]",
    },
]


def _iso(day: date) -> str:
    return day.isoformat()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task(
    task_id: str,
    title: str,
    category: str,
    status: str,
    priority: str,
    deadline: date,
    execution_date: date,
    start_time: str,
    end_time: str,
    steps: list[tuple[str, bool]],
    **extra: Any,
) -> dict[str, Any]:
    first_pending = next((name for name, completed in steps if not completed), "완료")
    now = _timestamp()
    return {
        "task_id": task_id,
        "title": title,
        "category": category,
        "status": status,
        "priority": priority,
        "deadline": _iso(deadline),
        "execution_date": _iso(execution_date),
        "start_time": start_time,
        "end_time": end_time,
        "next_action": first_pending,
        "waiting_for": None,
        "waiting_type": None,
        "request_date": None,
        "followup_date": None,
        "description": "",
        "featured": False,
        "project_id": None,
        "created_at": now,
        "updated_at": now,
        "workflow_steps": [
            {"id": f"{task_id}-S{index:02d}", "task_id": task_id, "step_order": index, "title": name, "completed": completed}
            for index, (name, completed) in enumerate(steps, start=1)
        ],
        **extra,
    }


def demo_store(today: date | None = None) -> dict[str, list[dict[str, Any]]]:
    today = today or date.today()
    tasks = [
        _task(
            f"TASK-{today.strftime('%Y%m%d')}-001",
            "감염내과 정경화 교수 독감 인터뷰",
            "유튜브",
            "편집",
            "높음",
            today + timedelta(days=3),
            today,
            "14:00",
            "15:30",
            [("영상 편집", True), ("썸네일 제작", False), ("팀장 검토", False), ("교수 검토", False), ("업로드", False)],
            description="독감 유행 전 정확한 예방 정보를 전달하는 교수 인터뷰",
            featured=True,
        ),
        _task(
            f"TASK-{today.strftime('%Y%m%d')}-002",
            "입원생활안내 추가 수정",
            "콘텐츠",
            "검토대기",
            "높음",
            today,
            today,
            "10:00",
            "11:30",
            [("수정사항 반영", True), ("병동 파트장 검토", False), ("최종본 배포", False)],
            waiting_for="병동 파트장",
            waiting_type="검토",
            request_date=f"{today.isoformat()}T11:20:00",
            followup_date=f"{today.isoformat()}T16:00:00",
            featured=True,
        ),
        _task(
            f"TASK-{today.strftime('%Y%m%d')}-003",
            "암병원 개소 행사 촬영",
            "촬영",
            "제작",
            "긴급",
            today,
            today,
            "13:00",
            "14:00",
            [("촬영", False), ("촬영물 백업", False), ("사진 선별", False), ("부서 메일 전송", False), ("포토앨범 업로드", False)],
            project_id="PROJECT-001",
            next_action="촬영 동선 최종 확인",
        ),
        _task(
            f"TASK-{today.strftime('%Y%m%d')}-004",
            "LG헬로비전 교수 일정 재확인",
            "방송",
            "회신대기",
            "보통",
            today + timedelta(days=4),
            today,
            "09:30",
            "10:00",
            [("교수 일정 문의", True), ("촬영일 확정", False), ("기자에게 결과 전달", False)],
            waiting_for="김OO 교수",
            waiting_type="일정 회신",
            request_date=f"{(today - timedelta(days=2)).isoformat()}T14:20:00",
            followup_date=f"{today.isoformat()}T15:00:00",
        ),
        _task(
            f"TASK-{today.strftime('%Y%m%d')}-005",
            "10월 유튜브 주제 선정",
            "유튜브",
            "기획",
            "보통",
            today + timedelta(days=6),
            today + timedelta(days=1),
            "09:00",
            "10:00",
            [("검색 수요 확인", False), ("후보 주제 정리", False), ("출연 교수 검토", False)],
        ),
        _task(
            f"TASK-{today.strftime('%Y%m%d')}-006",
            "LG헬로비전 인터뷰 업로드",
            "방송",
            "배포",
            "높음",
            today + timedelta(days=2),
            today + timedelta(days=2),
            "16:00",
            "16:30",
            [("영상 최종 확인", True), ("업로드", False), ("링크 공유", False)],
            featured=True,
        ),
    ]
    return {
        "tasks": tasks,
        "projects": [{"id": "PROJECT-001", "name": "암병원 개소 행사", "description": "행사 촬영과 후속 배포 업무"}],
        "categories": [{"id": f"CAT-{index:02d}", "name": name} for index, name in enumerate(DEFAULT_CATEGORIES, start=1)],
        "task_templates": DEFAULT_TASK_TEMPLATES.copy(),
        "reminders": [
            {"id": "REM-001", "title": "일일업무보고 작성", "reminder_time": "16:00", "repeat_type": "weekday", "enabled": True},
            {"id": "REM-002", "title": "스튜디오 불 끄기", "reminder_time": "16:30", "repeat_type": "weekday", "enabled": True},
            {"id": "REM-003", "title": "촬영물 백업 여부 확인", "reminder_time": "17:00", "repeat_type": "weekday", "enabled": True},
        ],
        "checklists": [
            {"id": "CHK-001", "title": "촬영물 백업 및 각 부서 메일 전송", "enabled": True, "checked_on": None},
            {"id": "CHK-002", "title": "16:00 일일업무보고 작성", "enabled": True, "checked_on": None},
            {"id": "CHK-003", "title": "16:30 스튜디오 불 끄기", "enabled": True, "checked_on": None},
        ],
        "content_records": [],
        "documents": [],
        "document_templates": DEFAULT_DOCUMENT_TEMPLATES.copy(),
    }


def parse_time(value: str | time | None, default: time = time(9, 0)) -> time:
    if isinstance(value, time):
        return value
    if value:
        try:
            return time.fromisoformat(str(value)[:5])
        except ValueError:
            pass
    return default


def first_pending_step(steps: list[dict[str, Any]]) -> str:
    ordered = sorted(steps, key=lambda item: int(item.get("step_order", 0)))
    return next((str(step["title"]) for step in ordered if not step.get("completed")), "완료")
