"""Draft squad validation and emergency-substitution engine.

A squad contains 17 or 19 unique players: a positional XIII plus four or six
bench players. Manual EMG assignments take precedence. Auto Emergency fills
remaining vacancies with the lowest-scoring eligible unused bench player.
DNP and bye players are both represented as unavailable player IDs.
"""
from __future__ import annotations
from collections.abc import Iterable
from backend.dfm.drl.core.player_positions import POSITIONAL_XIII, POSITION_CODES
from .models import DraftPlayer, Replacement, SquadScore, SquadSelection

VALID_SQUAD_SIZES = frozenset((17, 19))
MAX_EMERGENCY_ASSIGNMENTS = 4
POSITIONAL_SLOTS = dict(POSITIONAL_XIII)

class SquadEngine:
    """Pure Draft roster rules; persistence and authorization stay outside."""

    @staticmethod
    def validate_squad(selection: SquadSelection, players: Iterable[DraftPlayer]) -> None:
        player_list = tuple(players)
        by_id = {player.player_id: player for player in player_list}
        if len(by_id) != len(player_list):
            raise ValueError("player records must have unique player_id values")
        roster = tuple(selection.roster_player_ids)
        bench = tuple(selection.bench_player_ids)
        if len(roster) not in VALID_SQUAD_SIZES:
            raise ValueError("Draft squad must contain exactly 17 or 19 players")
        if len(set(roster)) != len(roster):
            raise ValueError("roster_player_ids must not contain duplicates")
        if len(set(bench)) != len(bench):
            raise ValueError("bench_player_ids must not contain duplicates")
        if len(bench) != len(roster) - 13:
            raise ValueError("bench size must be four for a 17-player squad or six for a 19-player squad")
        if set(roster) != set(by_id):
            raise ValueError("player records must match the selected roster exactly")
        if not set(bench).issubset(roster):
            raise ValueError("every bench player must belong to the selected roster")
        if set(selection.starting_xiii) != set(POSITION_CODES):
            raise ValueError("starting_xiii must define all six canonical positions")

        starters = []
        for position, required_slots in POSITIONAL_XIII:
            assigned = tuple(selection.starting_xiii[position])
            if len(assigned) != required_slots:
                raise ValueError(f"{position} must contain exactly {required_slots} starting players")
            for player_id in assigned:
                if player_id not in by_id:
                    raise ValueError(f"unknown starting player: {player_id}")
                if player_id in bench:
                    raise ValueError("a player cannot be both a starter and a bench player")
                player = by_id[player_id]
                if player.selected_position != position:
                    raise ValueError(f"{player_id} must be assigned to {position} for this round")
                if position not in player.eligible_positions:
                    raise ValueError(f"{player_id} is not eligible for {position}")
                starters.append(player_id)

        if len(starters) != 13 or len(set(starters)) != 13:
            raise ValueError("starting XIII must contain 13 unique players")
        if set(starters).intersection(bench):
            raise ValueError("starting XIII and bench must be mutually exclusive")
        if set(starters).union(bench) != set(roster):
            raise ValueError("every roster player must be assigned to the starting XIII or bench")

        assignments = dict(selection.emergency_assignments)
        if len(assignments) > MAX_EMERGENCY_ASSIGNMENTS:
            raise ValueError("a maximum of four emergency assignments is permitted")
        if len(set(assignments.values())) != len(assignments):
            raise ValueError("a bench player cannot be assigned to multiple emergency positions")
        for position, player_id in assignments.items():
            if position not in POSITIONAL_SLOTS:
                raise ValueError(f"invalid emergency position: {position}")
            if player_id not in bench:
                raise ValueError("emergency assignments must reference bench players")
            player = by_id[player_id]
            if player.selected_position != position or position not in player.eligible_positions:
                raise ValueError(f"{player_id} must be assigned and eligible for emergency position {position}")

    def score_squad(self, selection: SquadSelection, players: Iterable[DraftPlayer],
                    unavailable_player_ids: Iterable[str] = ()) -> SquadScore:
        """Score starters and replace DNP/bye vacancies according to EMG rules.

        Manual EMG assignments always take precedence. If none is available
        for a vacancy, Auto Emergency optionally selects the lowest-scoring
        eligible unused bench player. A bench player can replace only once.
        """
        player_list = tuple(players)
        self.validate_squad(selection, player_list)
        by_id = {player.player_id: player for player in player_list}
        unavailable = frozenset(unavailable_player_ids)
        unknown = unavailable.difference(by_id)
        if unknown:
            raise ValueError(f"unknown unavailable player IDs: {sorted(unknown)}")

        used_bench: set[str] = set()
        replacements: list[Replacement] = []
        starting_points: dict[str, float] = {}
        manual = dict(selection.emergency_assignments)

        for position, _ in POSITIONAL_XIII:
            position_total = 0.0
            for starter_id in selection.starting_xiii[position]:
                if starter_id not in unavailable:
                    position_total += by_id[starter_id].fantasy_points
                    continue
                replacement_id = manual.get(position)
                automatic = False
                if replacement_id in unavailable or replacement_id in used_bench:
                    replacement_id = None
                if replacement_id is None and selection.auto_emergency:
                    candidates = [
                        by_id[player_id] for player_id in selection.bench_player_ids
                        if player_id not in unavailable and player_id not in used_bench
                        and position in by_id[player_id].eligible_positions
                        and by_id[player_id].selected_position == position
                    ]
                    if candidates:
                        chosen = min(candidates, key=lambda player: (player.fantasy_points, player.player_id))
                        replacement_id = chosen.player_id
                        automatic = True
                if replacement_id is not None:
                    used_bench.add(replacement_id)
                    replacement = by_id[replacement_id]
                    position_total += replacement.fantasy_points
                    replacements.append(Replacement(position, starter_id, replacement_id,
                                                     replacement.fantasy_points, automatic))
            starting_points[position] = position_total

        unused = tuple(player_id for player_id in selection.bench_player_ids if player_id not in used_bench)
        return SquadScore(sum(starting_points.values()), starting_points, tuple(replacements), unused)
