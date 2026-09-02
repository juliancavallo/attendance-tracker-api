# Ofi 40% API

API FastAPI para el frontend estático de Ofi 40%.

## Ejecución local

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Para pruebas locales, definí `DEVELOPMENT=true` y agregá el origen exacto del frontend local a `FRONTEND_ORIGINS`.

## Contrato de la API

- `GET /v1/attendance?from=YYYY-MM-DD&to=YYYY-MM-DD`
- `PUT /v1/attendance/YYYY-MM-DD` — `{ "status": "office" | "vacation" }`
- `DELETE /v1/attendance/YYYY-MM-DD`
- `GET /v1/holidays?year=YYYY`

Las solicitudes autenticadas deben incluir `Authorization: Bearer <access_token>`. El frontend obtiene y refresca ese token mediante Supabase Auth; no se acepta `user_id` desde el cliente.

## Pruebas

```powershell
pytest
```
