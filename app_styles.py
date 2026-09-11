from __future__ import annotations

import base64
import os
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

from embedded_assets import FAMILY_DUO_B64, FAMILY_TABLE_B64, LITTLE_SISTER_B64, SEA_POEM_B64
from date_utils import human_date, human_datetime, korea_now


BASE_DIR = Path(__file__).parent
ASSET_DIR = Path(os.environ.get("PR_FLOW_ASSET_DIR", BASE_DIR / "assets"))


def _asset_b64(path: Path, fallback_b64: str) -> str:
    try:
        return base64.b64encode(path.read_bytes()).decode("ascii")
    except (FileNotFoundError, OSError):
        return fallback_b64


def _data_uri(path: Path, fallback_b64: str) -> str:
    return f"data:image/jpeg;base64,{_asset_b64(path, fallback_b64)}"


def inject_css() -> None:
    sea = _data_uri(ASSET_DIR / "sea_poem.jpeg", SEA_POEM_B64)
    sister = _data_uri(ASSET_DIR / "little_sister.jpeg", LITTLE_SISTER_B64)
    family_table = _data_uri(ASSET_DIR / "family_table.jpg", FAMILY_TABLE_B64)
    family_duo = _data_uri(ASSET_DIR / "family_duo.jpg", FAMILY_DUO_B64)
    st.markdown(
        f"""
        <style>
        @font-face {{
            font-family: 'Pretendard';
            font-weight: 100 900;
            font-style: normal;
            font-display: swap;
            src: url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/woff2/PretendardVariable.woff2') format('woff2-variations');
        }}
        :root {{
            --font-ui: 'SeoulNamsan', 'Pretendard', 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif;
            --navy-950: #102f3b;
            --navy-900: #153b49;
            --teal-700: #126b6d;
            --teal-600: #168083;
            --teal-100: #dcefee;
            --teal-50: #eff8f7;
            --gold-600: #b68222;
            --gold-100: #f8e9bd;
            --rose-600: #c8485e;
            --rose-100: #f9e5e9;
            --ink-900: #172a30;
            --ink-700: #40575d;
            --ink-500: #6b7f84;
            --line: #dce7e8;
            --surface: #ffffff;
            --canvas: #f4f8f8;
            --shadow-sm: 0 5px 18px rgba(17, 55, 63, .06);
            --shadow-md: 0 12px 34px rgba(17, 55, 63, .10);
        }}
        html {{ font-size: 16px; }}
        html, body, .stApp, [class*="css"], button, input, textarea, select {{
            font-family: var(--font-ui) !important;
            letter-spacing: -.012em;
        }}
        .stApp {{
            color: var(--ink-900);
            background:
                radial-gradient(circle at 92% 2%, rgba(22, 128, 131, .08), transparent 25rem),
                linear-gradient(180deg, #f8fbfb 0%, var(--canvas) 100%);
        }}
        [data-testid="stHeader"] {{ background: transparent; }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, var(--navy-900) 0%, var(--navy-950) 100%);
            border-right: 0;
        }}
        [data-testid="stSidebar"] * {{ color: #ffffff; }}
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] small {{ color: #d5e3e6 !important; }}
        [data-testid="stSidebar"] hr {{ border-color: rgba(255, 255, 255, .14); }}
        [data-testid="stSidebar"] .stRadio label {{
            min-height: 2.7rem;
            padding: .58rem .72rem;
            border-radius: 10px;
            font-size: .94rem;
            font-weight: 650;
            line-height: 1.45;
            transition: background-color .16s ease, transform .16s ease;
        }}
        [data-testid="stSidebar"] .stRadio label:hover {{
            background: rgba(255, 255, 255, .09);
            transform: translateX(2px);
        }}
        [data-testid="stSidebar"] .stButton button,
        [data-testid="stSidebar"] .stDownloadButton button {{
            color: #ffffff;
            border-color: rgba(255, 255, 255, .28);
            background: rgba(255, 255, 255, .08);
        }}
        [data-testid="stSidebar"] .stButton button[kind="primary"] {{
            color: var(--navy-950);
            border-color: #f3d98a;
            background: #f3d98a;
        }}
        .block-container {{
            max-width: 1480px;
            padding-top: 1.35rem;
            padding-bottom: 4rem;
        }}
        h1, h2, h3 {{
            color: var(--ink-900);
            letter-spacing: -.035em;
            line-height: 1.28;
        }}
        p, li, label {{ line-height: 1.68; }}
        .sidebar-brand {{
            position: relative;
            min-height: 132px;
            padding: 1rem;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, .24);
            border-radius: 16px;
            background-image: linear-gradient(120deg, rgba(9, 42, 52, .95), rgba(16, 66, 75, .67)), url('{sea}');
            background-position: center 40%;
            background-size: cover;
            box-shadow: 0 14px 30px rgba(5, 28, 35, .34);
        }}
        .sidebar-brand::after {{
            content: '';
            position: absolute;
            right: -2.2rem;
            bottom: -3rem;
            width: 8rem;
            height: 8rem;
            border: 1px solid rgba(255, 255, 255, .18);
            border-radius: 50%;
        }}
        .sidebar-brand .brand-label {{
            color: #f3d98a;
            font-size: .74rem;
            font-weight: 800;
            letter-spacing: .11em;
        }}
        .sidebar-brand h2 {{
            margin: .3rem 0 .25rem;
            color: #ffffff;
            font-size: 1.52rem;
            font-weight: 800;
        }}
        .sidebar-brand p {{
            max-width: 91%;
            margin: 0;
            color: #e3edef !important;
            font-size: .84rem;
            line-height: 1.6;
        }}
        .sidebar-memory {{
            display: flex;
            align-items: end;
            min-height: 72px;
            margin-top: .65rem;
            padding: .8rem;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, .18);
            border-radius: 14px;
            background-image: linear-gradient(90deg, rgba(9, 39, 47, .92), rgba(9, 39, 47, .42)), url('{family_table}');
            background-position: center 31%;
            background-size: cover;
        }}
        .sidebar-memory span {{
            color: #f6e7b6;
            font-size: .83rem;
            font-weight: 700;
            line-height: 1.5;
            text-shadow: 0 2px 10px rgba(0, 0, 0, .7);
        }}
        .app-heading {{
            display: flex;
            align-items: end;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1.1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--line);
        }}
        .app-heading .eyebrow {{
            color: var(--teal-700);
            font-size: .76rem;
            font-weight: 800;
            letter-spacing: .09em;
        }}
        .app-heading h1 {{
            margin: .22rem 0 .2rem;
            font-size: 2rem;
            font-weight: 850;
        }}
        .app-heading p {{
            margin: 0;
            color: var(--ink-700);
            font-size: .98rem;
        }}
        .heading-meta {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            justify-content: end;
            gap: .45rem;
            min-width: max-content;
        }}
        .date-badge, .mode-badge {{
            display: inline-flex;
            align-items: center;
            padding: .42rem .68rem;
            border: 1px solid var(--line);
            border-radius: 999px;
            font-size: .79rem;
            font-weight: 750;
        }}
        .date-badge {{ color: var(--ink-700); background: var(--surface); }}
        .mode-badge {{ color: var(--teal-700); background: var(--teal-50); }}
        .status-dot {{
            width: .48rem;
            height: .48rem;
            margin-right: .38rem;
            border-radius: 50%;
            background: #27966b;
            box-shadow: 0 0 0 3px rgba(39, 150, 107, .13);
        }}
        .section-kicker {{
            margin-top: .5rem;
            color: var(--teal-700);
            font-size: .74rem;
            font-weight: 800;
            letter-spacing: .1em;
        }}
        .section-title {{
            margin-top: .1rem;
            color: var(--ink-900);
            font-size: 1.34rem;
            font-weight: 800;
            line-height: 1.38;
        }}
        .section-desc {{
            max-width: 58rem;
            margin: .2rem 0 .85rem;
            color: var(--ink-500);
            font-size: .9rem;
            line-height: 1.65;
        }}
        [class*="st-key-stat_card_"] {{
            min-height: 118px;
            padding: .85rem .9rem .75rem;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: rgba(255, 255, 255, .94);
            box-shadow: var(--shadow-sm);
        }}
        [class*="st-key-stat_card_"] .stat-label {{
            color: var(--ink-700);
            font-size: .87rem;
            font-weight: 750;
        }}
        [class*="st-key-stat_card_"] .stat-note {{
            margin-top: .12rem;
            color: var(--ink-500);
            font-size: .77rem;
            line-height: 1.45;
        }}
        [class*="st-key-stat_card_"] .stButton button {{
            justify-content: flex-start;
            min-height: 2.45rem;
            margin-top: .35rem;
            padding: .25rem 0;
            border: 0;
            color: var(--teal-700);
            background: transparent;
            box-shadow: none;
            font-size: 1.42rem;
            font-weight: 850;
        }}
        [class*="st-key-stat_card_"] .stButton button:hover {{
            color: var(--navy-900);
            background: var(--teal-50);
        }}
        .stButton button, .stDownloadButton button {{
            min-height: 2.65rem;
            border-radius: 10px;
            font-size: .9rem;
            font-weight: 750;
            transition: border-color .15s ease, background-color .15s ease, transform .15s ease;
        }}
        .stButton button:hover, .stDownloadButton button:hover {{ transform: translateY(-1px); }}
        .stButton button[kind="primary"] {{
            border-color: var(--teal-700);
            background: var(--teal-700);
        }}
        div[data-baseweb="select"] > div,
        .stTextInput input, .stDateInput input, .stTimeInput input, .stTextArea textarea {{
            border-color: #cfdddf !important;
            border-radius: 10px !important;
            background: #ffffff !important;
            font-size: .94rem !important;
        }}
        div[data-baseweb="select"] > div:focus-within,
        .stTextInput input:focus, .stDateInput input:focus, .stTimeInput input:focus, .stTextArea textarea:focus {{
            border-color: var(--teal-600) !important;
            box-shadow: 0 0 0 3px rgba(22, 128, 131, .11) !important;
        }}
        [data-testid="stExpander"], [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: var(--line) !important;
            border-radius: 13px !important;
            background: rgba(255, 255, 255, .96);
        }}
        [data-testid="stMetric"] {{
            padding: .9rem 1rem;
            border: 1px solid var(--line);
            border-radius: 13px;
            background: var(--surface);
            box-shadow: var(--shadow-sm);
        }}
        [data-testid="stMetricValue"] {{ color: var(--navy-900); font-weight: 820; }}
        .schedule-row {{
            display: grid;
            grid-template-columns: 7.5rem minmax(0, 1fr);
            gap: .15rem .8rem;
            min-height: 80px;
            padding: .9rem 1rem;
            border: 1px solid var(--line);
            border-left: 4px solid var(--teal-600);
            border-radius: 12px;
            background: var(--surface);
            box-shadow: var(--shadow-sm);
        }}
        .schedule-row.urgent {{
            border-color: #efc9d0;
            border-left-color: var(--rose-600);
            background: #fffafb;
        }}
        .schedule-time {{
            grid-row: 1 / span 2;
            align-self: center;
            color: var(--teal-700);
            font-size: .91rem;
            font-weight: 820;
            font-variant-numeric: tabular-nums;
        }}
        .schedule-title {{
            overflow-wrap: anywhere;
            color: var(--ink-900);
            font-size: .98rem;
            font-weight: 780;
            line-height: 1.45;
        }}
        .schedule-next {{
            color: var(--ink-500);
            font-size: .83rem;
            line-height: 1.5;
        }}
        .task-card {{
            min-height: 160px;
            margin-bottom: .45rem;
            padding: 1rem;
            border: 1px solid var(--line);
            border-radius: 13px;
            background: var(--surface);
            box-shadow: var(--shadow-sm);
        }}
        .task-card.urgent {{
            border-color: #eab5bf;
            box-shadow: 0 8px 24px rgba(200, 72, 94, .09);
        }}
        .task-top {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: .65rem;
        }}
        .badges {{ display: flex; flex-wrap: wrap; gap: .32rem; }}
        .badge {{
            display: inline-flex;
            align-items: center;
            min-height: 1.65rem;
            padding: .18rem .5rem;
            border-radius: 999px;
            color: var(--teal-700);
            background: var(--teal-50);
            font-size: .75rem;
            font-weight: 750;
        }}
        .badge.pink {{ color: #ad354b; background: var(--rose-100); }}
        .badge.sun {{ color: #805d17; background: #fbf0d2; }}
        .task-id {{
            flex: none;
            padding-top: .22rem;
            color: #829498;
            font-size: .72rem;
            font-weight: 600;
            font-variant-numeric: tabular-nums;
        }}
        .task-title {{
            margin: .65rem 0 .55rem;
            overflow-wrap: anywhere;
            color: var(--ink-900);
            font-size: 1.02rem;
            font-weight: 800;
            line-height: 1.5;
        }}
        .next-action {{
            padding: .58rem .68rem;
            border: 1px solid #dcebea;
            border-radius: 9px;
            color: var(--ink-700);
            background: var(--teal-50);
            font-size: .86rem;
            line-height: 1.55;
        }}
        .next-action b {{ margin-right: .25rem; color: var(--teal-700); }}
        .task-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: .42rem 1rem;
            margin-top: .65rem;
            color: var(--ink-500);
            font-size: .79rem;
            line-height: 1.45;
        }}
        .task-meta b {{ margin-right: .2rem; color: var(--ink-700); }}
        .waiting-card {{
            margin-bottom: .45rem;
            padding: .95rem;
            border: 1px solid #ead9aa;
            border-radius: 12px;
            background: #fffdf6;
        }}
        .waiting-card .waiting-label {{
            color: var(--gold-600);
            font-size: .73rem;
            font-weight: 800;
            letter-spacing: .06em;
        }}
        .waiting-card strong {{
            display: block;
            margin-top: .2rem;
            color: var(--ink-900);
            font-size: 1rem;
            line-height: 1.45;
        }}
        .waiting-card p {{
            margin: .35rem 0 .55rem;
            color: var(--ink-700);
            font-size: .86rem;
            line-height: 1.6;
        }}
        .waiting-card small {{ color: #776b51; font-size: .77rem; line-height: 1.5; }}
        .flow-column {{
            min-height: 205px;
            padding: .9rem;
            border: 1px solid var(--line);
            border-top: 3px solid var(--teal-600);
            border-radius: 12px;
            background: var(--surface);
            box-shadow: var(--shadow-sm);
        }}
        .flow-column h3 {{ margin: 0 0 .65rem; font-size: .98rem; font-weight: 800; }}
        .flow-task {{
            padding: .62rem 0;
            border-top: 1px solid #e8eeee;
            font-size: .84rem;
            line-height: 1.5;
        }}
        .flow-task b {{ display: block; color: var(--ink-900); overflow-wrap: anywhere; }}
        .flow-task span {{ color: var(--ink-500); font-size: .76rem; }}
        .day-head {{
            margin-bottom: .28rem;
            text-align: center;
            color: var(--ink-500);
            font-size: .8rem;
            font-weight: 800;
        }}
        [class*="st-key-calendar_cell_"] {{
            min-height: 124px;
            padding: .5rem;
            border: 1px solid var(--line);
            border-radius: 11px;
            background: rgba(255, 255, 255, .72);
        }}
        [class*="st-key-calendar_cell_"] .stButton button {{
            min-height: 2rem;
            padding: .32rem .4rem;
            overflow: hidden;
            font-size: .75rem;
            text-align: left;
        }}
        .calendar-empty {{ min-height: 98px; }}
        .calendar-date {{
            margin-bottom: .28rem;
            color: var(--ink-700);
            font-size: .82rem;
            font-weight: 800;
        }}
        .empty-state {{
            padding: 1.7rem 1rem;
            border: 1px dashed #bed3d4;
            border-radius: 12px;
            color: var(--ink-500);
            background: rgba(255, 255, 255, .72);
            text-align: center;
            font-size: .91rem;
            line-height: 1.6;
        }}
        .sister-note {{
            display: flex;
            align-items: end;
            min-height: 176px;
            padding: 1rem 1.1rem;
            overflow: hidden;
            border-radius: 14px;
            color: #ffffff;
            background-image: linear-gradient(90deg, rgba(10, 54, 61, .96) 0%, rgba(10, 54, 61, .84) 48%, rgba(10, 54, 61, .18) 100%), url('{sister}');
            background-position: center 78%;
            background-size: cover;
            box-shadow: var(--shadow-md);
        }}
        .sister-note b, .family-closing b {{
            display: block;
            color: #f4dea0;
            font-size: 1.12rem;
            font-weight: 800;
            line-height: 1.45;
        }}
        .sister-note p {{
            max-width: 58%;
            margin: .35rem 0 0;
            color: #e7f0f1;
            font-size: .84rem;
            line-height: 1.6;
        }}
        .family-closing {{
            display: flex;
            align-items: end;
            min-height: 155px;
            margin-top: 1rem;
            padding: 1rem 1.2rem;
            border-radius: 14px;
            color: #ffffff;
            background-image: linear-gradient(90deg, rgba(12, 44, 53, .96) 0%, rgba(12, 44, 53, .78) 52%, rgba(12, 44, 53, .18) 100%), url('{family_duo}');
            background-position: center 43%;
            background-size: cover;
            box-shadow: var(--shadow-md);
        }}
        .family-closing p {{
            max-width: 50%;
            margin: .35rem 0 0;
            color: #e7f0f1;
            font-size: .84rem;
            line-height: 1.6;
        }}
        .foot-note {{
            padding-top: 2.3rem;
            color: #75888c;
            text-align: center;
            font-size: .78rem;
        }}
        @media (max-width: 900px) {{
            .block-container {{ padding: 1rem .8rem 3rem; }}
            .app-heading {{ align-items: flex-start; flex-direction: column; }}
            .heading-meta {{ justify-content: flex-start; min-width: 0; }}
            .schedule-row {{ grid-template-columns: 6.5rem minmax(0, 1fr); }}
        }}
        @media (max-width: 640px) {{
            html {{ font-size: 15px; }}
            .app-heading h1 {{ font-size: 1.72rem; }}
            .app-heading p {{ font-size: .92rem; }}
            .schedule-row {{ display: block; min-height: auto; padding: .8rem; }}
            .schedule-time {{ margin-bottom: .3rem; }}
            .task-card {{ min-height: auto; }}
            .task-top {{ display: block; }}
            .task-id {{ margin-top: .35rem; }}
            [class*="st-key-calendar_cell_"] {{ min-height: 84px; padding: .35rem; }}
            .calendar-empty {{ min-height: 66px; }}
            .sister-note p, .family-closing p {{ max-width: 78%; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-label">PR WORKFLOW</div>
            <h2>홍보 바다</h2>
            <p>업무, 일정, 회신과 기록을<br>하나의 흐름으로 관리합니다.</p>
        </div>
        <div class="sidebar-memory"><span>일과 삶을 함께 지키는 기록</span></div>
        """,
        unsafe_allow_html=True,
    )


def render_app_heading(mode_label: str) -> None:
    now = korea_now()
    weekday = "월화수목금토일"[now.weekday()]
    st.markdown(
        f"""
        <div class="app-heading">
            <div>
                <div class="eyebrow">COMMUNICATIONS WORKSPACE</div>
                <h1>홍보 업무 통합 관리</h1>
                <p>기억에 의존하지 않고, 다음 행동과 일정을 기준으로 업무를 관리합니다.</p>
            </div>
            <div class="heading-meta">
                <span class="date-badge">{now.year}년 {now.month}월 {now.day}일 {weekday}요일</span>
                <span class="mode-badge"><span class="status-dot"></span>{escape(mode_label)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_heading(kicker: str, title: str, description: str = "") -> None:
    st.markdown(
        f'<div class="section-kicker">{escape(kicker)}</div><div class="section-title">{escape(title)}</div><div class="section-desc">{escape(description)}</div>',
        unsafe_allow_html=True,
    )


def task_card(task: dict[str, Any]) -> str:
    urgent = " urgent" if task.get("priority") == "긴급" else ""
    priority_class = "pink" if task.get("priority") == "긴급" else "sun"
    waiting = f" · {escape(str(task.get('waiting_for')))} 회신 대기" if task.get("waiting_for") else ""
    return f"""
    <div class="task-card{urgent}">
        <div class="task-top">
            <div class="badges">
                <span class="badge">{escape(str(task.get('category', '기타')))}</span>
                <span class="badge {priority_class}">{escape(str(task.get('priority', '보통')))}</span>
                <span class="badge">{escape(str(task.get('status', '기획')))}</span>
            </div>
            <div class="task-id">{escape(str(task.get('task_id', '')))}</div>
        </div>
        <div class="task-title">{escape(str(task.get('title', '')))}</div>
        <div class="next-action"><b>다음 행동</b> {escape(str(task.get('next_action') or '지정이 필요합니다.'))}</div>
        <div class="task-meta">
            <span><b>마감</b>{human_date(task.get('deadline'))}</span>
            <span><b>실행</b>{human_date(task.get('execution_date'))} {escape(str(task.get('start_time') or '')[:5])}{waiting}</span>
        </div>
    </div>
    """


def schedule_row(task: dict[str, Any]) -> str:
    urgent = " urgent" if task.get("priority") == "긴급" else ""
    repeat_labels = {"daily": "매일", "weekday": "평일", "weekly": "매주", "none": "반복 없음"}
    repeat_label = repeat_labels.get(str(task.get("repeat_type") or "none"), "반복 없음")
    reminder = "알람 끔"
    if task.get("reminder_enabled", True):
        minutes = int(task.get("reminder_minutes_before", 0) or 0)
        reminder = "시작 알람" if minutes == 0 else f"{minutes}분 전 알람"
    return f"""
    <div class="schedule-row{urgent}">
        <div class="schedule-time">{escape(str(task.get('start_time') or '--:--')[:5])}–{escape(str(task.get('end_time') or '--:--')[:5])}</div>
        <div class="schedule-title">{escape(str(task.get('title', '')))}</div>
        <div class="schedule-next">다음 행동 · {escape(str(task.get('next_action') or '지정이 필요합니다.'))}<br>{escape(repeat_label)} · {escape(reminder)}</div>
    </div>
    """


def waiting_card(item: dict[str, Any]) -> str:
    task = item.get("task") or {}
    return f"""
    <div class="waiting-card">
        <div class="waiting-label">WAITING FOR RESPONSE</div>
        <strong>{escape(str(item.get('waiting_for') or '대상이 지정되지 않았습니다.'))}</strong>
        <p>{escape(str(task.get('title') or '연결된 업무'))}<br>{escape(str(item.get('waiting_type') or '회신'))}을 기다리고 있습니다.</p>
        <small>요청 {human_datetime(item.get('requested_at'))} · 재확인 {human_datetime(item.get('followup_at'))}</small>
    </div>
    """


def render_sister_note() -> None:
    st.markdown(
        '<div class="sister-note"><div><b>퇴근 전 최종 확인</b><p>오늘의 기록을 정리하면 내일 해야 할 일이 더 분명해집니다.</p></div></div>',
        unsafe_allow_html=True,
    )


def render_family_closing() -> None:
    st.markdown(
        '<div class="family-closing"><div><b>오늘 업무를 정리했습니다.</b><p>미완료 업무에는 다음 행동과 실행 시간을 지정하고 일과를 마무리하세요.</p></div></div>',
        unsafe_allow_html=True,
    )
