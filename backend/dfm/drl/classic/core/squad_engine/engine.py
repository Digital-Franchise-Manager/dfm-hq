"""DRL Classic 21-player squad validation and emergency scoring.

Classic squads contain a positional starting XIII, four interchange players
and four emergency players. The starting XIII and interchange form the
scoring 17. An unavailable scoring player may be replaced by a nominated EMG;
when Auto Emergency is enabled, the first eligible available EMG in the
user-supplied emergency order is used. This is deliberately independent of
Draft Mode's squad and emergency rules.
"""
from __future__ import annotations

from collections.abc import Iterable

from backend.dfm.drl.core.player_positions import POSITIONAL_XIII, POSITION_CODES
from .models import (
    ClassicPlayer,
    ClassicReplacement,
    ClassicSquadScore,
    ClassicSquadSelection,
)

CLASSIC_ROSTER_SIZE = 21
CLASSIC_STARTING_SIZE = 13
CLASSIC_INTERCHANGE_SIZE = 4
CLASSIC_EMERGENCY_SIZE = 4
POSITIONAL_SLOTS = dict(POSITIONAL_XIII)


class ClassicSquadEngine:
    """Pure Classic roster rules; persistence and authorization stay outside."""

    @staticmethod
    def validate_squad(
        selection: ClassicSquadSelection, players: Iterable[ClassicPlayer]
    ) -> None:
        player_list = tuple(players)
        by_id = {player.player_id: player for player in player_list}
        if len(by_id) != len(player_list):
            raise ValueError("player records must have unique player_id values")

        roster = tuple(selection.roster_player_ids)
        interchange = tuple(selection.interchange_player_ids)
        emergencies = tuple(selection.emergency_player_ids)

        if len(roster) != CLASSIC_ROSTER_SIZE:
            raise ValueError("Classic squad must contain exactly 21 players")
        if len(set(roster)) != CLASSIC_ROSTER_SIZE:
            raise ValueError("roster_player_ids must not contain duplicates")
        if len(interchange) != CLASSIC_INTERCHANGE_SIZE:
            raise ValueError("Classic squad must contain exactly four interchange players")
        if len(set(interchange)) != CLASSIC_INTERCHANGE_SIZE:
            raise ValueError("interchange_player_ids must not contain duplicates")
        if len(emergencies) != CLASSIC_EMERGENCY_SIZE:
            raise ValueError("Classic squad must contain exactly four emergency players")
        if len(set(emergencies)) != CLASSIC_EMERGENCY_SIZE:
            raise ValueError("emergency_player_ids must not contain duplicates")
        if set(roster) != set(by_id):
            raise ValueError("player records must match the selected roster exactly")
        if not set(interchange).issubset(roster):
            raise ValueError("every interchange player must belong to the selected roster")
        if not set(emergencies).issubset(roster):
            raise ValueError("every emergency player must belong to the selected roster")
        if set(interchange).intersection(emergencies):
            raise ValueError("interchange and emergency players must be separate")

        if set(selection.starting_xiii) != set(POSITION_CODES):
            raise ValueError("starting_xiii must define all six canonical positions")

        starters: list[str] = []
        for position, required_slots in POSITIONAL_XIII:
            assigned = tuple(selection.starting_xiii[position])
            if len(assigned) != required_slots:
                raise ValueError(
                    f"{position} must contain exactly {required_slots} starting players"
                )
            for player_id in assigned:
                if player_id not in by_id:
                    raise ValueError(f"unknown starting player: {player_id}")
                if player_id in interchange or player_id in emergencies:
                    raise ValueError("a player cannot occupy more than one squad group")
                player = by_id[player_id]
                if player.selected_position != position:
                    raise ValueError(f"{player_id} must be assigned to {position}")
                if position not in player.eligible_positions:
                    raise ValueError(f"{player_id} is not eligible for {position}")
                starters.append(player_id)

        if len(starters) != CLASSIC_STARTING_SIZE or len(set(starters)) != CLASSIC_STARTING_SIZE:
            raise ValueError("starting XIII must contain 13 unique players")
        if set(starters).intersection(interchange) or set(starters).intersection(emergencies):
            raise ValueError("starting XIII, interchange and emergencies must be separate")
        if set(starters).union(interchange, emergencies) != set(roster):
            raise ValueError(
                "every roster player must be assigned to the starting XIII, interchange or emergencies"
            )

        assignments = dict(selection.emergency_assignments)
        if len(set(assignments.values())) != len(assignments):
            raise ValueError("an emergency player cannot replace multiple squad players")
        scoring_ids = set(starters).union(interchange)
        for unavailable_id, emergency_id in assignments.items():
            if unavailable_id not in scoring_ids:
                raise ValueError("emergency assignment target must be a starter or interchange player")
            if emergency_id not in emergencies:
                raise ValueError("emergency assignments must reference emergency players")
            target_position = by_id[unavailable_id].selected_position
            emergency = by_id[emergency_id]
            if emergency.selected_position != target_position:
                raise ValueError(
                    f"{emergency_id} must be selected at {target_position} for this emergency assignment"
                )
            if target_position not in emergency.eligible_positions:
                raise ValueError(f"{emergency_id} is not eligible for {target_position}")

    def score_squad(
        self,
        selection: ClassicSquadSelection,
        players: Iterable[ClassicPlayer],
        unavailable_player_ids: Iterable[str] = (),
    ) -> ClassicSquadScore:
        """Score the starting XIII plus interchange, applying EMG replacements.

        Manual assignments take precedence. If a nominated EMG is unavailable
        or already used, Auto Emergency may select the first available eligible
        EMG in the order supplied by emergency_player_ids. Each EMG can replace
        one unavailable player only.
        """
        player_list = tuple(players)
        self.validate_squad(selection, player_list)
        by_id = {player.player_id: player for player in player_list}
        unavailable = frozenset(unavailable_player_ids)
        unknown = unavailable.difference(by_id)
        if unknown:
            raise ValueError(f"unknown unavailable player IDs: {sorted(unknown)}")

        position_points = {position: 0.0 for position in POSITION_CODES}
        used_emergencies: set[str] = set()
        replacements: list[ClassicReplacement] = []
        manual = dict(selection.emergency_assignments)

        scoring_order = [
            player_id
            for position, _ in POSITIONAL_XIII
            for player_id in selection.starting_xiii[position]
        ] + list(selection.interchange_player_ids)

        for player_id in scoring_order:
            player = by_id[player_id]
            position = player.selected_position
            if player_id not in unavailable:
                position_points[position] += player.fantasy_points
                continue

            emergency_id = manual.get(player_id)
            automatic = False
            if emergency_id in unavailable or emergency_id in used_emergencies:
                emergency_id = None

            if emergency_id is None and selection.auto_emergency:
                emergency_id = next(
                    (
                        candidate_id
                        for candidate_id in selection.emergency_player_ids
                        if candidate_id not in unavailable
                        and candidate_id not in used_emergencies
                        and position in by_id[candidate_id].eligible_positions
                        and by_id[candidate_id].selected_position == position
                    ),
                    None,
                )
                automatic = emergency_id is not None

            if emergency_id is not None:
                used_emergencies.add(emergency_id)
                replacement = by_id[emergency_id]
                position_points[position] += replacement.fantasy_points
                replacements.append(
                    ClassicReplacement(
                        position=position,
                        unavailable_player_id=player_id,
                        replacement_player_id=emergency_id,
                        replacement_points=replacement.fantasy_points,
                        automatic=automatic,
                    )
                )

        unused = tuple(
            player_id
            for player_id in selection.emergency_player_ids
            if player_id not in used_emergencies
        )
        return ClassicSquadScore(
            total_points=sum(position_points.values()),
            position_points=position_points,
            replacements=tuple(replacements),
            unused_emergency_player_ids=unused,
        )
