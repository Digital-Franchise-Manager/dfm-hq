import type { Medal } from "./drlPlayerMedals";
import "./DRLPlayerCard.css";

export type DrlCardPlayer = {
  drl_player_id: number;
  first_name: string;
  last_name: string;
  team_name: string | null;
  primary_fantasy_position: string | null;
  eligible_fantasy_positions: string[];
  fantasy_points: number | null;
  nrl_career_appearances: number | null;
  origin_state: "NSW" | "QLD" | null;
  origin_minutes_played: number | null;
  photo_url: string | null;
  photo_alt: string | null;
};

type Props = {
  player: DrlCardPlayer;
  medal?: { medal: Medal; position: string } | null;
};

function appearanceTier(appearances: number | null): string {
  if (appearances === null || !Number.isFinite(appearances)) return "APPEARANCES PENDING";
  if (appearances >= 51) return "NEON LIME";
  if (appearances >= 25) return "MINT";
  return "WHITE";
}

export default function DRLPlayerCard({ player, medal }: Props) {
  const originQualified = (player.origin_state === "NSW" || player.origin_state === "QLD") &&
    typeof player.origin_minutes_played === "number" && player.origin_minutes_played > 0;
  const tier = appearanceTier(player.nrl_career_appearances);
  const classification = medal
    ? medal.medal
    : originQualified
      ? player.origin_state === "NSW" ? "STATE OF ORIGIN — NSW" : "STATE OF ORIGIN — QLD"
      : tier;

  const classificationClass = medal ? medal.medal.toLowerCase() : originQualified ? (player.origin_state === "NSW" ? "origin-nsw" : "origin-qld") : tier.toLowerCase().replaceAll(" ", "-");

  return (
    <article className={`drl-collectible-card drl-card-${classificationClass}`}
      data-player-id={player.drl_player_id}>
      <div className="drl-card-brand"><span>DRL</span><span>DIGITAL RUGBY LEAGUE</span></div>
      <div className="drl-card-photo">
        {player.photo_url
          ? <img src={player.photo_url} alt={player.photo_alt ?? `${player.first_name} ${player.last_name} in match action`} loading="lazy" />
          : <div className="drl-card-photo-pending">ACTION PHOTO<br />PENDING</div>}
      </div>
      <div className="drl-card-classification">{classification}</div>
      <h3>{player.first_name} {player.last_name}</h3>
      <p className="drl-card-club">{player.team_name ?? "CLUB PENDING"}</p>
      <div className="drl-card-meta">
        <span>PRIMARY: {player.primary_fantasy_position ?? "PENDING"}</span>
        <span>DPP: {player.eligible_fantasy_positions.length > 1 ? player.eligible_fantasy_positions.join(" / ") : "NO"}</span>
      </div>
      <div className="drl-card-score">
        <strong>{player.fantasy_points === null ? "—" : player.fantasy_points.toLocaleString()}</strong>
        <span>DRL FANTASY POINTS</span>
      </div>
      <footer>NRL CAREER GAMES: {player.nrl_career_appearances ?? "PENDING"}</footer>
    </article>
  );
}
