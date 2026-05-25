"""Map ``SashActuator`` runtime signals to a STATUS_SPEC envelope.

A single helper that both ``GET /status`` and the ``/control/*`` precondition
gates call. Per ``ac-organic-lab/docs/STATUS_SPEC.md`` §6.2 the two
surfaces must never disagree about what is currently allowed - sharing one
helper makes that invariant fall out for free.

State derivation (mirrors what ``LegacyFumeHoodActuatorAdapter`` in
``ac-organic-lab`` was doing client-side, now authoritative on the device):

| ``is_moving`` | ``sash_position`` | ``equipment_status`` |
|---------------|-------------------|----------------------|
| ``True``      | any               | ``busy``             |
| ``False``     | ``1..5``          | ``ready``            |
| ``False``     | ``None``          | ``requires_init``    |

The device's own internal ``equipment_status`` (which after any ``/stop``
call reads ``"stopped"`` even when parked at a preset) is intentionally
ignored - it reflects "last command was stop", not operational state.
"""

from __future__ import annotations

import socket
import time
from datetime import datetime, timezone

from .claims import ClaimRegistry
from .models import (
    PROTOCOL_VERSION,
    ClaimedBy,
    ComponentStatus,
    EquipmentState,
    EquipmentStatus,
    MetricValue,
)


_PROCESS_START_TIME = time.monotonic()


def derive_state(actuator) -> tuple[EquipmentState, int | None, bool]:
    """Return ``(equipment_status, sash_position, is_moving)``.

    The single source of truth for state derivation. ``allowed_actions``
    and the ``/control/sash/*`` precondition gates both call this.
    """

    is_moving = bool(
        actuator.movement_thread is not None and actuator.movement_thread.is_alive()
    )
    position = actuator.get_current_position()
    if is_moving:
        return "busy", position, True
    if position is None:
        return "requires_init", None, False
    return "ready", position, False


def allowed_actions_for(state: EquipmentState) -> list[str]:
    """Skill names the device will currently honor.

    Mirrors the ``requires_states`` declared by the fume_hood entries in
    ``ac-organic-lab/skills/.../skill_catalog/fume_hood.py``.
    """

    if state == "ready":
        return ["sash.move", "sash.stop"]
    if state == "busy":
        return ["sash.stop"]
    if state == "requires_init":
        # Move pulses down looking for a hall sensor when position is unknown.
        return ["sash.move"]
    return []


def build_status(
    *,
    actuator,
    equipment_id: str,
    equipment_name: str,
    equipment_version: str | None,
    claims: ClaimRegistry,
    last_error=None,
) -> EquipmentStatus:
    state, position, is_moving = derive_state(actuator)
    allowed = allowed_actions_for(state)

    components: dict[str, ComponentStatus] = {
        "actuator": ComponentStatus(
            connected=True,
            state="moving" if is_moving else "idle",
        ),
        "sash": ComponentStatus(
            connected=True,
            state=f"position_{position}" if position is not None else "between_sensors",
            message=None if position is not None else "Sash not parked at a hall sensor",
        ),
    }

    metrics: dict[str, MetricValue] = {}
    if position is not None:
        metrics["sash_position"] = MetricValue(value=position, unit="preset")
    target = actuator.target_position if is_moving else None
    if target is not None:
        metrics["target_position"] = MetricValue(value=target, unit="preset")

    message = {
        "ready": f"Sash parked at position {position}",
        "busy": f"Moving sash{f' to position {target}' if target else ''}",
        "requires_init": "Sash between hall sensors - move to a preset to recover",
    }.get(state, "Hardware status unknown")

    required_actions: list[str] = ["sash.move"] if state == "requires_init" else []

    claimed_by: ClaimedBy | None = claims.snapshot()
    details: dict[str, object] = {"claimed_by": claimed_by.model_dump(mode="json") if claimed_by else None}

    return EquipmentStatus(
        protocol_version=PROTOCOL_VERSION,
        equipment_id=equipment_id,
        equipment_name=equipment_name,
        equipment_kind="fume_hood",
        equipment_version=equipment_version,
        host=socket.gethostname(),
        equipment_status=state,
        message=message,
        required_actions=required_actions,
        device_time=datetime.now(timezone.utc),
        uptime_seconds=time.monotonic() - _PROCESS_START_TIME,
        components=components,
        metrics=metrics,
        last_error=last_error,
        allowed_actions=allowed,
        details=details,
    )


__all__ = [
    "derive_state",
    "allowed_actions_for",
    "build_status",
]
