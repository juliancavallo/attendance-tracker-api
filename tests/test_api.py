import asyncio

from fastapi.testclient import TestClient

from app.main import app, settings
from app.services.supabase import SupabaseGateway


class FakeGateway:
    async def user(self, token):
        return {"id": "26b74386-0b16-487b-908e-0ff06395aaaa", "email": "julian@example.com"}

    async def entries(self, token, start, end):
        return [{"work_date": start, "status": "office"}]

    async def upsert_entry(self, token, user_id, work_date, status_value):
        assert token == "valid"
        assert user_id == "26b74386-0b16-487b-908e-0ff06395aaaa"
        return {"work_date": work_date, "status": status_value}

    async def delete_entry(self, token, work_date):
        assert token == "valid"


def client_with_fake_gateway():
    client = TestClient(app)
    client.__enter__()
    app.state.gateway = FakeGateway()
    return client


def auth_headers(token="valid"):
    return {"Authorization": f"Bearer {token}"}


def test_attendance_requires_bearer_token():
    client = client_with_fake_gateway()
    try:
        response = client.get("/v1/attendance?from=2026-08-01&to=2026-08-31")
        assert response.status_code == 401
    finally:
        client.__exit__(None, None, None)


def test_attendance_is_read_using_bearer_token():
    client = client_with_fake_gateway()
    try:
        response = client.get("/v1/attendance?from=2026-08-01&to=2026-08-31", headers=auth_headers())
        assert response.status_code == 200
        assert response.json() == [{"work_date": "2026-08-01", "status": "office"}]
    finally:
        client.__exit__(None, None, None)


def test_attendance_write_uses_bearer_token_without_cookie_or_origin():
    client = client_with_fake_gateway()
    try:
        response = client.put("/v1/attendance/2026-08-31", headers=auth_headers(), json={"status": "office"})
        assert response.status_code == 200
        assert response.json() == {"work_date": "2026-08-31", "status": "office"}
    finally:
        client.__exit__(None, None, None)


def test_cors_accepts_authorization_header_from_configured_frontend():
    client = client_with_fake_gateway()
    try:
        response = client.options("/v1/attendance/2026-08-31", headers={
            "Origin": settings.origins[0],
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "authorization,content-type",
        })
        assert response.status_code == 200
        assert "authorization" in response.headers["access-control-allow-headers"].lower()
    finally:
        client.__exit__(None, None, None)


def test_service_requests_use_the_service_role_as_bearer_token():
    gateway = SupabaseGateway(settings)
    try:
        headers = gateway._headers(service=True)
        assert headers["Authorization"] == f"Bearer {settings.supabase_service_role_key}"
    finally:
        asyncio.run(gateway.client.aclose())
