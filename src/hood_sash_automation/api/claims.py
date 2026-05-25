"""Server-side claim/heartbeat/release for STATUS_SPEC v1.1.

A single in-process holder. The fume hood has one actuator and is operated
by at most one workflow at a time, so a single-slot holder is the right
fit. The model:

* ``claim(req)`` reserves the slot or raises :class:`ClaimConflict` (HTTP 409).
* Re-claim from the same ``session_id`` rotates the token and resets the TTL
  (idempotent per spec).
* ``heartbeat(token)`` refreshes the TTL or raises :class:`ClaimStale`
  (HTTP 401).
* ``release(token)`` is idempotent: unknown / stale token still returns
  ``None``.
* ``snapshot()`` returns the current ``ClaimedBy`` (or ``None``) for
  embedding into ``EquipmentStatus.details``.
* ``assert_holder(token)`` is called by ``/control/sash/*`` to enforce
  ``X-Claim-Token`` (HTTP 423 on miss / mismatch).

Concurrency: a single :class:`threading.Lock` guards every mutation. The
actuator's movement thread does not interact with this module - claim
state is independent of motion state.
"""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .models import ClaimedBy, ClaimRequest, ClaimResponse


# Heartbeat interval given to the client. Half the TTL so a single missed
# heartbeat is recoverable.
_HEARTBEAT_RATIO = 0.5


@dataclass
class _Holder:
    token: str
    owner: str
    session_id: str
    expires_at: datetime


class ClaimConflict(Exception):
    """A different session holds the claim. Maps to HTTP 409 in the API."""

    def __init__(self, claimed_by: ClaimedBy):
        super().__init__("claim held by another session")
        self.claimed_by = claimed_by


class ClaimStale(Exception):
    """Token is unknown or expired. Maps to HTTP 401 in the API."""


class ClaimRequired(Exception):
    """A protected /control/* endpoint was hit without a valid X-Claim-Token.

    Maps to HTTP 423 in the API.
    """

    def __init__(self, claimed_by: ClaimedBy | None):
        super().__init__("claim required")
        self.claimed_by = claimed_by


class ClaimRegistry:
    """In-process single-slot claim registry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._holder: _Holder | None = None

    # -- Public surface -----------------------------------------------------

    def claim(self, req: ClaimRequest) -> ClaimResponse:
        with self._lock:
            now = _utcnow()
            existing = self._evict_if_expired(now)

            if existing is not None and existing.session_id != req.session_id:
                raise ClaimConflict(self._holder_view(existing))

            token = secrets.token_urlsafe(24)
            expires_at = now + timedelta(seconds=req.ttl_s)
            self._holder = _Holder(
                token=token,
                owner=req.owner,
                session_id=req.session_id,
                expires_at=expires_at,
            )
            heartbeat_interval = max(2.0, req.ttl_s * _HEARTBEAT_RATIO)
            return ClaimResponse(
                claim_token=token,
                heartbeat_interval_s=heartbeat_interval,
                expires_at=expires_at,
            )

    def heartbeat(self, token: str | None, *, ttl_s: float = 30.0) -> datetime:
        if token is None:
            raise ClaimStale()
        with self._lock:
            now = _utcnow()
            self._evict_if_expired(now)
            holder = self._holder
            if holder is None or holder.token != token:
                raise ClaimStale()
            holder.expires_at = now + timedelta(seconds=ttl_s)
            return holder.expires_at

    def release(self, token: str | None) -> None:
        if token is None:
            return
        with self._lock:
            holder = self._holder
            if holder is not None and holder.token == token:
                self._holder = None

    def assert_holder(self, token: str | None) -> None:
        with self._lock:
            now = _utcnow()
            self._evict_if_expired(now)
            holder = self._holder
            if holder is None or token is None or holder.token != token:
                raise ClaimRequired(
                    self._holder_view(holder) if holder is not None else None
                )

    def snapshot(self) -> ClaimedBy | None:
        with self._lock:
            self._evict_if_expired(_utcnow())
            holder = self._holder
            return self._holder_view(holder) if holder is not None else None

    # -- Internals ----------------------------------------------------------

    def _evict_if_expired(self, now: datetime) -> _Holder | None:
        holder = self._holder
        if holder is None:
            return None
        if holder.expires_at <= now:
            self._holder = None
            return None
        return holder

    @staticmethod
    def _holder_view(holder: _Holder) -> ClaimedBy:
        return ClaimedBy(
            session_id=holder.session_id,
            owner=holder.owner,
            expires_at=holder.expires_at,
        )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "ClaimRegistry",
    "ClaimConflict",
    "ClaimStale",
    "ClaimRequired",
]
