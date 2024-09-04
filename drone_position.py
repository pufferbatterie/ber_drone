import datetime
from email.policy import default
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class DronePosition(SQLModel, table=True):
    t: datetime.datetime = Field(default_factory=utcnow, primary_key=True)
    drone_id: str = Field(primary_key=True)
    latitude: float
    lonitude: float
