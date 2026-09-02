from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class AttendanceWrite(BaseModel):
    status: Literal["office", "vacation"]


class AttendanceEntry(BaseModel):
    work_date: date
    status: Literal["office", "vacation"]


class Holiday(BaseModel):
    fecha: date
    nombre: str = Field(min_length=1)
    tipo: str | None = None
