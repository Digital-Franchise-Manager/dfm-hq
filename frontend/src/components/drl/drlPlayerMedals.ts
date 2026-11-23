export const DRL_FANTASY_POSITIONS = ["HOK", "MID", "EDG", "HLF", "CTR", "WFB"] as const;
export type DrlFantasyPosition = typeof DRL_FANTASY_POSITIONS[number];
export type Medal = "GOLD" | "SILVER" | "BRONZE";

export interface MedalCandidate {
  drl_player_id: number;
  fantasy_points: number;
  primary_position: DrlFantasyPosition;
  eligible_positions: DrlFantasyPosition[];
}

export interface PositionalMedal {
  drl_player_id: number;
  position: DrlFantasyPosition;
  medal: Medal;
  fantasy_points: number;
  is_primary_position: boolean;
}

/**
 * Allocates three distinct medal recipients per fantasy position.
 * Primary-position claims are allocated across all six positions first.
 * Secondary-position claims then fill any remaining medal places.
 * A player can receive one medal maximum across the complete system.
 */
export function allocateDrlPositionalMedals(candidates: MedalCandidate[]): PositionalMedal[] {
  const valid = candidates.filter((player) =>
    Number.isSafeInteger(player.drl_player_id) &&
    Number.isFinite(player.fantasy_points) &&
    DRL_FANTASY_POSITIONS.includes(player.primary_position) &&
    player.eligible_positions.includes(player.primary_position) &&
    player.eligible_positions.every((position) => DRL_FANTASY_POSITIONS.includes(position))
  );

  const unique = new Map<number, MedalCandidate>();
  for (const player of valid) {
    if (!unique.has(player.drl_player_id)) unique.set(player.drl_player_id, player);
  }

  const awardedPlayers = new Set<number>();
  const awards: PositionalMedal[] = [];
  const medalOrder: Medal[] = ["GOLD", "SILVER", "BRONZE"];

  // Primary-position rankings always take precedence over secondary DPP claims.
  for (const position of DRL_FANTASY_POSITIONS) {
    const ranked = [...unique.values()]
      .filter((player) => player.primary_position === position)
      .sort((a, b) => b.fantasy_points - a.fantasy_points || a.drl_player_id - b.drl_player_id);
    let slot = 0;
    for (const player of ranked) {
      if (slot >= medalOrder.length) break;
      if (awardedPlayers.has(player.drl_player_id)) continue;
      awards.push({
        drl_player_id: player.drl_player_id,
        position,
        medal: medalOrder[slot++],
        fantasy_points: player.fantasy_points,
        is_primary_position: true
      });
      awardedPlayers.add(player.drl_player_id);
    }
  }

  // Secondary eligible positions can fill vacancies, but never duplicate a medal.
  for (const position of DRL_FANTASY_POSITIONS) {
    const ranked = [...unique.values()]
      .filter((player) => player.primary_position !== position && player.eligible_positions.includes(position))
      .sort((a, b) => b.fantasy_points - a.fantasy_points || a.drl_player_id - b.drl_player_id);
    const positionAwards = awards.filter((award) => award.position === position);
    let slot = positionAwards.length;
    for (const player of ranked) {
      if (slot >= medalOrder.length) break;
      if (awardedPlayers.has(player.drl_player_id)) continue;
      awards.push({
        drl_player_id: player.drl_player_id,
        position,
        medal: medalOrder[slot++],
        fantasy_points: player.fantasy_points,
        is_primary_position: false
      });
      awardedPlayers.add(player.drl_player_id);
    }
  }

  return awards.sort((a, b) =>
    DRL_FANTASY_POSITIONS.indexOf(a.position) - DRL_FANTASY_POSITIONS.indexOf(b.position) ||
    medalOrder.indexOf(a.medal) - medalOrder.indexOf(b.medal)
  );
}
