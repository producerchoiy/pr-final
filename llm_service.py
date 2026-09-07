from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from database import secret


class LLMError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(secret("OPENAI_API_KEY"))


def _extract_text(response: dict[str, Any]) -> str:
    if response.get("output_text"):
        return str(response["output_text"])
    parts: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(str(content["text"]))
    return "\n".join(parts).strip()


def generate_script(
    *,
    template: str,
    document_type: str,
    professor: str,
    department: str,
    topic: str,
    reference: str,
    length: str,
    tone: str,
) -> str:
    api_key = secret("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("OPENAI_API_KEY가 설정되지 않았습니다.")
    model = secret("OPENAI_MODEL", "gpt-5-mini")
    prompt = f"""당신은 대학병원 홍보실의 숙련된 방송·영상 작가입니다.
아래 기존 문서 양식의 제목, 순서, 구성을 유지하여 새 원고를 작성하세요.
의학 정보는 참고자료 안에서만 사용하고 근거가 불명확한 수치나 치료 효과를 만들어내지 마세요.
환자가 이해하기 쉬운 자연스러운 한국어를 사용하세요.

[문서 유형]
{document_type}

[교수 / 진료과]
{department} {professor}

[주제]
{topic}

[원하는 길이]
{length}

[톤]
{tone}

[기존 양식]
{template}

[참고자료]
{reference or '제공된 참고자료 없음. 사실 확인이 필요한 부분은 [확인 필요]로 표시할 것.'}
"""
    payload = {
        "model": model,
        "input": prompt,
        "reasoning": {"effort": "low"},
        "text": {"verbosity": "medium"},
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise LLMError(f"AI 요청 실패 ({error.code}): {detail}") from error
    except URLError as error:
        raise LLMError("AI 서비스에 연결할 수 없습니다.") from error
    output = _extract_text(result)
    if not output:
        raise LLMError("AI 응답에서 원고를 찾지 못했습니다.")
    return output
