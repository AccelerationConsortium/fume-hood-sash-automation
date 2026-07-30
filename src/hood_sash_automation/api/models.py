"""STATUS_SPEC v1.2 Pydantic models for hood-sash-automation.

Wire-contract types are imported from the shared ``sdl-lab-contract`` package
and re-exported. Device-specific models (``MoveRequest``) remain local.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from sdl_lab_contract import (
    ClaimedBy,
    ClaimRejection,
    ClaimRequest,
    ClaimResponse,
    ComponentStatus,
    EquipmentKind,
    EquipmentState,
    EquipmentStatus,
    ErrorInfo,
    ErrorSeverity,
    HealthResponse,
    MetricValue,
    ProbeResponse,
)

PROTOCOL_VERSION = "1.2"


class MoveRequest(BaseModel):
    position: int = Field(ge=1, le=5, description="Sash preset position (1 closed - 5 fully open).")


__all__ = [
    "PROTOCOL_VERSION",
    "ClaimedBy",
    "ClaimRejection",
    "ClaimRequest",
    "ClaimResponse",
    "ComponentStatus",
    "EquipmentKind",
    "EquipmentState",
    "EquipmentStatus",
    "ErrorInfo",
    "ErrorSeverity",
    "HealthResponse",
    "MetricValue",
    "ProbeResponse",
    "MoveRequest",
]
