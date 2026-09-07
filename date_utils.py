from __future__ import annotations

from calendar import monthcalendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


SEOUL = ZoneInfo("Asia/Seoul")


def korea_now() -> datetime:
    return datetime.now(SEOUL)


def week_end(day: date) -> date:
    return day + timedelta(days=6 - day.weekday())


def as_date(value: str | date | None, fallback: date | None = None) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return fallback or date.today()


def human_date(value: str | date | None, *, include_year: bool = False) -> str:
    day = as_date(value)
    return day.strftime("%Y.%m.%d") if include_year else f"{day.month}/{day.day}"


def human_datetime(value: str | None) -> str:
    if not value:
        return "미지정"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo:
            parsed = parsed.astimezone(SEOUL)
        return f"{parsed.month}/{parsed.day} {parsed.strftime('%H:%M')}"
    except ValueError:
        return str(value)


def calendar_weeks(year: int, month: int) -> list[list[int]]:
    return monthcalendar(year, month)
