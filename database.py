from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import streamlit as st


class DatabaseError(RuntimeError):
    """Readable Supabase communication error."""


def secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, os.environ.get(name, default))
    except (FileNotFoundError, KeyError):
        value = os.environ.get(name, default)
    return str(value or "").strip()


class SupabaseClient:
    def __init__(self) -> None:
        self.url = secret("SUPABASE_URL").rstrip("/")
        self.key = secret("SUPABASE_KEY") or secret("SUPABASE_SERVICE_ROLE_KEY")

    @property
    def available(self) -> bool:
        return bool(self.url and self.key)

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(extra or {})
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, str] | None = None,
        payload: Any = None,
        headers: dict[str, str] | None = None,
        raw: bool = False,
    ) -> Any:
        if not self.available:
            raise DatabaseError("Supabase 연결 정보가 없습니다.")
        query = f"?{urlencode(params, safe='(),.*:')}" if params else ""
        body = payload if isinstance(payload, bytes) else (json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None)
        request = Request(
            f"{self.url}{endpoint}{query}",
            data=body,
            method=method,
            headers=self._headers(headers),
        )
        try:
            with urlopen(request, timeout=30) as response:
                data = response.read()
                if raw:
                    return data
                return json.loads(data.decode("utf-8")) if data else None
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise DatabaseError(f"Supabase 요청 실패 ({error.code}): {detail}") from error
        except URLError as error:
            raise DatabaseError("Supabase에 연결할 수 없습니다. URL과 네트워크를 확인해 주세요.") from error

    def select(
        self,
        table: str,
        *,
        filters: dict[str, str] | None = None,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        params = {"select": "*", **(filters or {})}
        if order:
            params["order"] = order
        return self._request("GET", f"/rest/v1/{quote(table)}", params=params) or []

    def insert(self, table: str, rows: dict[str, Any] | list[dict[str, Any]], *, upsert: bool = False) -> list[dict[str, Any]]:
        prefer = "resolution=merge-duplicates,return=representation" if upsert else "return=representation"
        return self._request("POST", f"/rest/v1/{quote(table)}", payload=rows, headers={"Prefer": prefer}) or []

    def update(self, table: str, filters: dict[str, str], changes: dict[str, Any]) -> list[dict[str, Any]]:
        return self._request(
            "PATCH",
            f"/rest/v1/{quote(table)}",
            params={"select": "*", **filters},
            payload=changes,
            headers={"Prefer": "return=representation"},
        ) or []

    def delete(self, table: str, filters: dict[str, str]) -> None:
        self._request("DELETE", f"/rest/v1/{quote(table)}", params=filters, headers={"Prefer": "return=minimal"})

    def upload(self, bucket: str, object_path: str, content: bytes, mime_type: str) -> str:
        encoded = "/".join(quote(part, safe="") for part in object_path.split("/"))
        self._request(
            "POST",
            f"/storage/v1/object/{quote(bucket, safe='')}/{encoded}",
            payload=content,
            headers={"Content-Type": mime_type, "x-upsert": "true"},
            raw=True,
        )
        return object_path

    def download(self, bucket: str, object_path: str) -> bytes:
        encoded = "/".join(quote(part, safe="") for part in object_path.split("/"))
        return self._request("GET", f"/storage/v1/object/authenticated/{quote(bucket, safe='')}/{encoded}", raw=True)

    def delete_object(self, bucket: str, object_path: str) -> None:
        self._request("DELETE", f"/storage/v1/object/{quote(bucket, safe='')}", payload={"prefixes": [object_path]})
