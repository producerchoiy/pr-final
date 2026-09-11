from __future__ import annotations

from datetime import time
from typing import Any


WORKFLOW_STATUSES = [
    "기획",
    "진행 중",
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


def initial_store() -> dict[str, list[dict[str, Any]]]:
    """Blank working store used when Supabase is not connected.

    Sample tasks are intentionally excluded so a deleted item can never be
    recreated merely because Streamlit reran or a browser session restarted.
    """
    return {
        "tasks": [],
        "task_steps": [],
        "projects": [],
        "categories": [
            {"id": f"CAT-{index:02d}", "name": name}
            for index, name in enumerate(DEFAULT_CATEGORIES, start=1)
        ],
        "task_templates": [dict(item) for item in DEFAULT_TASK_TEMPLATES],
        "reminders": [],
        "checklists": [],
        "content_records": [],
        "documents": [],
        "document_templates": [dict(item) for item in DEFAULT_DOCUMENT_TEMPLATES],
        "waiting_items": [],
        "task_status_history": [],
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
