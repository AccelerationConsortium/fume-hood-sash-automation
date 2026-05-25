"""STATUS_SPEC v1.1 Pydantic models.

Vendored from ``ac-organic-lab/docs/STATUS_SPEC.md``. Once the spec has
shipped on 3+ device repos, this module is the migration target for the
shared ``lab-status-contract`` package.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


PROTOCOL_VERSION = "1.1"


EquipmentKind = Literal[
    "solid_doser",
    "liquid_handler",
    "press",
    "fume_hood",
    "robot_arm",
    "environmental_sensor",
    "hplc",
    "plate_reader",
    "plate_sealer",
    "plate_stacker",
    "shaker",
    "camera",
    "smart_plug",
    "power_strip",
    "other",
]


EquipmentState = Literal[
    "ready",
    "busy",
    "requires_init",
    "degraded",
    "dry_run",
    "error",
    "e_stop",
    "unknown",
]


class ComponentStatus(BaseModel):
    connected: bool
    state: str
    message: str | None = None
    last_event_at: datetime | None = None


class MetricValue(BaseModel):
    value: float | int | str | bool
    unit: str | None = None
    timestamp: datetime | None = None


class ErrorInfo(BaseModel):
    code: str | None = None
    message: str
    severity: Literal["info", "warning", "error", "critical"]
    timestamp: datetime


class ClaimedBy(BaseModel):
    session_id: str
    owner: str
    expires_at: datetime


class EquipmentStatus(BaseModel):
    protocol_version: str = PROTOCOL_VERSION

    equipment_id: str
    equipment_name: str
    equipment_kind: EquipmentKind
    equipment_version: str | None = None
    host: str | None = None

    equipment_status: EquipmentState
    message: str | None = None
    required_actions: list[str] = Field(default_factory=list)

    device_time: datetime
    uptime_seconds: float | None = None

    components: dict[str, ComponentStatus] = Field(default_factory=dict)
    metrics: dict[str, MetricValue] = Field(default_factory=dict)
    last_error: ErrorInfo | None = None

    allowed_actions: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ProbeResponse(BaseModel):
    equipment_id: str
    equipment_name: str
    protocol_version: str


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"


class ClaimRequest(BaseModel):
    owner: str
    session_id: str
    ttl_s: float = Field(default=30.0, ge=1.0, le=300.0)


class ClaimResponse(BaseModel):
    claim_token: str
    heartbeat_interval_s: float
    expires_at: datetime


class ClaimRejection(BaseModel):
    detail: str
    claimed_by: ClaimedBy | None = None
    retry_after_s: float | None = None


class MoveRequest(BaseModel):
    position: int = Field(ge=1, le=5, description="Sash preset position (1 closed - 5 fully open).")


__all__ = [
    "PROTOCOL_VERSION",
    "EquipmentKind",
    "EquipmentState",
    "ComponentStatus",
    "MetricValue",
    "ErrorInfo",
    "ClaimedBy",
    "EquipmentStatus",
    "ProbeResponse",
    "HealthResponse",
    "ClaimRequest",
    "ClaimResponse",
    "ClaimRejection",
    "MoveRequest",
]
