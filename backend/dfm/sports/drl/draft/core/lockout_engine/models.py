"""Typed inputs and decisions for the independent Draft lockout engine."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class LockoutReason(str, Enum):
    INDIVIDUAL_MATCH = "individual_match_lockout"
    CAPTAIN_ROUND = "captain_round_lockout"
    VICE_CAPTAIN_ROUND = "vice_captain_round_lockout"
    EMERGENCY_ROUND = "emergency_round_lockout"


@dataclass(frozen=True, slots=True)
class PlayerLockoutContext:
    player_id: str
    match_kickoff: datetime
    is_captain: bool = False
    is_vice_captain: bool = False
    is_emergency: bool = False


@dataclass(frozen=True, slots=True)
class LockoutDecision:
    player_id: str
    is_locked: bool
    lockout_at: datetime
    reason: LockoutReason
    evaluated_at: datetime
