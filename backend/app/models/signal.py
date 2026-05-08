from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SignalIn(BaseModel):
    signal_id: UUID = Field(default_factory=uuid4)
    component_id: str = Field(..., min_length=1, max_length=255)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity_hint: str | None = None
    source: str
    metadata: dict = Field(default_factory=dict)
