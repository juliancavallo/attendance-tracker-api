from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.dependencies import access_token, get_gateway
from app.schemas import AttendanceEntry, AttendanceWrite, Holiday
from app.services.supabase import SupabaseGateway


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=15) as client:
        app.state.gateway = SupabaseGateway(get_settings(), client)
        yield


app = FastAPI(title="Ofi 40% API", version="1.0.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/attendance", response_model=list[AttendanceEntry])
async def list_attendance(
    start: Annotated[date, Query(alias="from")], end: Annotated[date, Query(alias="to")],
    token: Annotated[str, Depends(access_token)], gateway: Annotated[SupabaseGateway, Depends(get_gateway)],
) -> list[dict]:
    if start > end:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="from must not be after to")
    return await gateway.entries(token, start.isoformat(), end.isoformat())


@app.put("/v1/attendance/{work_date}", response_model=AttendanceEntry)
async def put_attendance(
    work_date: date, payload: AttendanceWrite, token: Annotated[str, Depends(access_token)], gateway: Annotated[SupabaseGateway, Depends(get_gateway)],
) -> dict:
    user = await gateway.user(token)
    return await gateway.upsert_entry(token, user["id"], work_date.isoformat(), payload.status)


@app.delete("/v1/attendance/{work_date}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attendance(
    work_date: date, token: Annotated[str, Depends(access_token)], gateway: Annotated[SupabaseGateway, Depends(get_gateway)],
) -> Response:
    await gateway.delete_entry(token, work_date.isoformat())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/v1/holidays", response_model=list[Holiday])
async def holidays(year: int = Query(ge=2000, le=2100), gateway: SupabaseGateway = Depends(get_gateway)) -> list[dict]:
    cached = await gateway.cached_holidays(year)
    if cached and datetime.fromisoformat(cached["expires_at"].replace("Z", "+00:00")) > datetime.now(timezone.utc):
        return cached["holidays"]
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(f"https://api.argentinadatos.com/v1/feriados/{year}")
            response.raise_for_status()
            fetched = response.json()
    except httpx.HTTPError:
        if cached:
            return cached["holidays"]
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Holiday source unavailable")
    normalized = [{"fecha": item["fecha"], "nombre": item["nombre"], "tipo": item.get("tipo")} for item in fetched]
    await gateway.save_holidays(year, normalized)
    return normalized
