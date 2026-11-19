"""Classic-only player lockout calculations and trade guards.

Classic rules:
- Captain and Vice-Captain lock at the first match kickoff for the round.
- Every player also locks one hour before their individual match.
- The earliest applicable deadline wins.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .models import LockoutDecision, LockoutReason, PlayerLockoutContext


class PlayerLockedError(ValueError):
    """Raised when a Classic trade includes a player who is locked."""

    def __init__(self, decision: LockoutDecision) -> None:
        self.decision = decision
        super().__init__(
            f"Classic player {decision.player_id!r} is locked "
            f"({decision.reason.value}) from {decision.lockout_at.isoformat()}."
        )


class ClassicLockoutEngine:
    """Enforces Classic lockout rules without importing Draft code."""

    mode = "classic"
    INDIVIDUAL_LOCKOUT_LEAD = timedelta(hours=1)

    @staticmethod
    def _require_aware(value: datetime, field_name: str) -> None:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be a timezone-aware datetime")

    def evaluate_player(
        self,
        *,
        player: PlayerLockoutContext,
        round_first_kickoff: datetime,
        now: datetime | None = None,
    ) -> LockoutDecision:
        if not player.player_id or not player.player_id.strip():
            raise ValueError("player_id is required")
        if player.is_captain and player.is_vice_captain:
            raise ValueError("a player cannot be both Captain and Vice-Captain")

        self._require_aware(player.match_kickoff, "match_kickoff")
        self._require_aware(round_first_kickoff, "round_first_kickoff")
        evaluated_at = now if now is not None else datetime.now(timezone.utc)
        self._require_aware(evaluated_at, "now")

        if player.match_kickoff < round_first_kickoff:
            raise ValueError("player match kickoff cannot precede the round's first kickoff")

        deadlines: list[tuple[datetime, LockoutReason]] = [
            (
                player.match_kickoff - self.INDIVIDUAL_LOCKOUT_LEAD,
                LockoutReason.INDIVIDUAL_MATCH,
            )
        ]
        if player.is_captain:
            deadlines.append((round_first_kickoff, LockoutReason.CAPTAIN_ROUND))
        elif player.is_vice_captain:
            deadlines.append((round_first_kickoff, LockoutReason.VICE_CAPTAIN_ROUND))

        lockout_at, reason = min(deadlines, key=lambda item: item[0])
        return LockoutDecision(
            player_id=player.player_id,
            is_locked=evaluated_at >= lockout_at,
            lockout_at=lockout_at,
            reason=reason,
            evaluated_at=evaluated_at,
        )

    def assert_player_tradeable(
        self,
        *,
        player: PlayerLockoutContext,
        round_first_kickoff: datetime,
        now: datetime | None = None,
    ) -> LockoutDecision:
        decision = self.evaluate_player(
            player=player,
            round_first_kickoff=round_first_kickoff,
            now=now,
        )
        if decision.is_locked:
            raise PlayerLockedError(decision)
        return decision

    def assert_trade_allowed(
        self,
        *,
        outgoing_player: PlayerLockoutContext,
        incoming_player: PlayerLockoutContext,
        round_first_kickoff: datetime,
        now: datetime | None = None,
    ) -> tuple[LockoutDecision, LockoutDecision]:
        """Guard both sides of a trade; neither locked player may be moved."""
        outgoing = self.assert_player_tradeable(
            player=outgoing_player,
            round_first_kickoff=round_first_kickoff,
            now=now,
        )
        incoming = self.assert_player_tradeable(
            player=incoming_player,
            round_first_kickoff=round_first_kickoff,
            now=now,
        )
        return outgoing, incoming
