from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings


class SupabaseGateway:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=15)

    @property
    def auth_url(self) -> str:
        return f"{self.settings.supabase_url.rstrip('/')}/auth/v1"

    @property
    def rest_url(self) -> str:
        return f"{self.settings.supabase_url.rstrip('/')}/rest/v1"

    def _headers(self, token: str | None = None, service: bool = False) -> dict[str, str]:
        key = self.settings.supabase_service_role_key if service else self.settings.supabase_anon_key
        headers = {"apikey": key, "Content-Type": "application/json"}
        bearer = key if service else token
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        return headers

    async def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        response = await self.client.request(method, url, **kwargs)
        if response.is_error:
            detail = response.json().get("msg", response.text) if response.content else "Supabase request failed"
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
        return response.json() if response.content else None

    async def user(self, access_token: str) -> dict[str, Any]:
        return await self._request("GET", f"{self.auth_url}/user", headers=self._headers(access_token))

    async def entries(self, access_token: str, start: str, end: str) -> list[dict[str, Any]]:
        return await self._request("GET", f"{self.rest_url}/attendance_entries", headers=self._headers(access_token), params=[
            ("select", "work_date,status"), ("work_date", f"gte.{start}"), ("work_date", f"lte.{end}"), ("order", "work_date.asc"),
        ])

    async def upsert_entry(self, access_token: str, user_id: str, work_date: str, status_value: str) -> dict[str, Any]:
        data = await self._request("POST", f"{self.rest_url}/attendance_entries", headers={**self._headers(access_token), "Prefer": "resolution=merge-duplicates,return=representation"}, json={"user_id": user_id, "work_date": work_date, "status": status_value})
        return data[0]

    async def delete_entry(self, access_token: str, work_date: str) -> None:
        await self._request("DELETE", f"{self.rest_url}/attendance_entries", headers=self._headers(access_token), params={"work_date": f"eq.{work_date}"})

    async def cached_holidays(self, year: int) -> dict[str, Any] | None:
        data = await self._request("GET", f"{self.rest_url}/holiday_cache", headers=self._headers(service=True), params={"year": f"eq.{year}", "select": "holidays,expires_at"})
        return data[0] if data else None

    async def save_holidays(self, year: int, holidays: list[dict[str, Any]]) -> None:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        await self._request("POST", f"{self.rest_url}/holiday_cache", headers={**self._headers(service=True), "Prefer": "resolution=merge-duplicates"}, json={"year": year, "holidays": holidays, "expires_at": expires_at})
