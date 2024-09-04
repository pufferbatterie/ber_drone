import datetime
from email.policy import default
from typing import Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.ext.compiler import compiles

from sqlmodel import Field, SQLModel


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


@compiles(DateTime, "mysql")
def compile_datetime_mysql(type_, compiler, **kw):
    """https://stackoverflow.com/a/63704523"""
    return "DATETIME(3)"


class DronePosition(SQLModel, table=True):
    t: datetime.datetime = Field(default_factory=utcnow, primary_key=True)  # sa_column=Column(DATETIME(fsp=3))
    drone_id: str = Field(primary_key=True)
    latitude: float
    longitude: float
