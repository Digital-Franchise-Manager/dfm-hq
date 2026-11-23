import { useEffect, useMemo, useState } from "react";
import { supabase } from "../../utils/supabaseClient";
import "./DRLPlayerProfiles.css";

type PlayerStats = {
  appearances: number | null; tries: number | null; try_assists: number | null;
  points: number | null; tackles: number | null; tackle_efficiency: number | null;
  metres_gained: number | null; line_breaks: number | null; errors: number | null;
  penalties_conceded: number | null;
};
type AchievementCardCode = "state_of_origin_blue" | "state_of_origin_burgundy" | "gold" | "silver" | "bronze";
type PlayerProfile = {
  drl_player_id: number; first_name: string; last_name: string;
  team_name: string | null; position: string | null; photo_url: string | null;
  photo_alt: string | null; photo_kind?: "verified_action_photo" | null;
  career_appearances: number | null;
  achievement_cards: AchievementCardCode[];
  stats: PlayerStats | null;
};
type PlayerFeed = { season: number; players: PlayerProfile[]; source_status: "connected" | "unavailable" };
type SortKey = "points" | "tries" | "try_assists" | "tackles" | "metres_gained" | "line_breaks" | "appearances";
const statLabels: Array<{ key: keyof PlayerStats; label: string; suffix?: string }> = [
  { key: "appearances", label: "Season appearances" }, { key: "tries", label: "Tries" },
  { key: "try_assists", label: "Try assists" }, { key: "points", label: "Points" },
  { key: "tackles", label: "Tackles" }, { key: "tackle_efficiency", label: "Tackle efficiency", suffix: "%" },
  { key: "metres_gained", label: "Metres gained", suffix: "m" }, { key: "line_breaks", label: "Line breaks" },
  { key: "errors", label: "Errors" }, { key: "penalties_conceded", label: "Penalties conceded" }
];
const milestoneCards = [
  { code: "white", label: "0–49 NRL GAMES", className: "white", minimum: 0, rank: 10 },
  { code: "mint", label: "50–99 NRL GAMES", className: "mint", minimum: 50, rank: 9 },
  { code: "neon-lime", label: "100–149 NRL GAMES", className: "neon-lime", minimum: 100, rank: 8 },
  { code: "emerald", label: "150–299 NRL GAMES", className: "emerald", minimum: 150, rank: 7 },
  { code: "platinum", label: "300+ NRL GAMES", className: "platinum", minimum: 300, rank: 4 }
] as const;
const achievementCardDetails: Record<AchievementCardCode, { label: string; className: string; rank: number }> = {
  gold: { label: "1ST PLACE · GOLD", className: "gold", rank: 1 },
  silver: { label: "2ND PLACE · SILVER", className: "silver", rank: 2 },
  bronze: { label: "3RD PLACE · BRONZE", className: "bronze", rank: 3 },
  state_of_origin_blue: { label: "STATE OF ORIGIN · BLUE", className: "origin-blue", rank: 5 },
  state_of_origin_burgundy: { label: "STATE OF ORIGIN · BURGUNDY", className: "origin-burgundy", rank: 6 }
};
function displayStat(value: number | null | undefined, suffix = ""): string {
  return value === null || value === undefined ? "Not supplied" : `${value.toLocaleString()}${suffix}`;
}
function PlayerCardCollection({ player }: { player: PlayerProfile }) {
  if (player.career_appearances === null || player.career_appearances === undefined) {
    return <section className="drl-player-card-collection" aria-label="Player cards">
      <div className="drl-player-card-heading"><strong>PLAYER CARD COLLECTION</strong><span>CAREER TOTAL UNVERIFIED</span></div>
      <p className="drl-card-pending">Career appearance records have not been verified for this player. Milestone cards are withheld until an official career total is available.</p>
    </section>;
  }
  const earned = milestoneCards
    .filter((card) => player.career_appearances! >= card.minimum)
    .map((card) => ({ ...card, rank: card.rank }));
  const achievements = (player.achievement_cards ?? [])
    .filter((code): code is AchievementCardCode => code in achievementCardDetails)
    .map((code) => ({ code, ...achievementCardDetails[code] }));
  const cards = [...earned, ...achievements].sort((a, b) => a.rank - b.rank);
  return <section className="drl-player-card-collection" aria-label="Player card collection">
    <div className="drl-player-card-heading"><strong>PLAYER CARD COLLECTION</strong><span>{player.career_appearances.toLocaleString()} CAREER NRL GAMES</span></div>
    <div className="drl-player-card-grid">
      {cards.map((card) => <article key={card.code} className={`drl-milestone-card ${card.className}`}>
        <span className="drl-card-mark">DRL</span><strong>{card.label}</strong><small>{card.code === "white" || card.code === "mint" || card.code === "neon-lime" || card.code === "emerald" || card.code === "platinum" ? "CAREER MILESTONE" : "ACHIEVEMENT CARD"}</small>
      </article>)}
    </div>
    {cards.length === 0 && <p className="drl-card-pending">No verified milestone or achievement cards have been awarded.</p>}
  </section>;
}
function ActionPhoto({ player, compact = false }: { player: PlayerProfile; compact?: boolean }) {
  return player.photo_url && player.photo_kind === "verified_action_photo"
    ? <img className={compact ? "drl-player-action-photo compact" : "drl-player-action-photo"} src={player.photo_url} alt={player.photo_alt ?? `${player.first_name} ${player.last_name} in ${player.team_name ?? "club"} colours during match play`} loading="lazy" />
    : <div className={compact ? "drl-player-photo-fallback compact" : "drl-player-photo-fallback"} aria-label="Verified current-club action photo pending review"><span>PHOTO<br/>PENDING</span></div>;
}
export default function DRLPlayerProfiles() {
  const [season, setSeason] = useState("2026");
  const [players, setPlayers] = useState<PlayerProfile[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("points");
  const [sortDirection, setSortDirection] = useState<"desc" | "asc">("desc");
  const [loading, setLoading] = useState(false);
  const [feedError, setFeedError] = useState("The secure player service has not been connected yet.");

  useEffect(() => {
    const controller = new AbortController();
    async function loadPlayers() {
      setLoading(true); setFeedError("");
      try {
        if (!supabase) throw new Error("Secure sign-in is not configured on this environment.");
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        if (sessionError || !session?.access_token) throw new Error("Sign in to view player profiles.");
        const response = await fetch(`/api/drl/nrl/players?season=${encodeURIComponent(season)}`, {
          method: "GET", credentials: "same-origin",
          headers: { Accept: "application/json", Authorization: `Bearer ${session.access_token}` },
          signal: controller.signal
        });
        if (!response.ok) throw new Error(response.status === 401
          ? "Your sign-in session is missing or expired. Sign in again to view player profiles."
          : "The secure player service is currently unavailable.");
        const payload = await response.json() as PlayerFeed;
        if (payload.source_status !== "connected" || !Array.isArray(payload.players)) {
          throw new Error("Verified player data is not available for this season yet.");
        }
        setPlayers(payload.players);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setPlayers([]); setFeedError(error instanceof Error ? error.message : "Unable to load player profiles.");
      } finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void loadPlayers();
    return () => controller.abort();
  }, [season]);

  const visiblePlayers = useMemo(() => {
    const filtered = players.filter((player) =>
      `${player.first_name} ${player.last_name} ${player.team_name ?? ""}`.toLowerCase().includes(search.toLowerCase())
    );
    return filtered.sort((a, b) => {
      const left = a.stats?.[sortKey] ?? Number.NEGATIVE_INFINITY;
      const right = b.stats?.[sortKey] ?? Number.NEGATIVE_INFINITY;
      return (left - right) * (sortDirection === "desc" ? -1 : 1);
    });
  }, [players, search, sortKey, sortDirection]);
  const selected = players.find((player) => player.drl_player_id === selectedId) ?? null;

  return <section className="drl-player-profiles" aria-label="NRL player profiles">
    <div className="drl-player-toolbar">
      <label>SEASON<select value={season} onChange={(event) => { setSeason(event.target.value); setSelectedId(null); }}><option value="2026">2026 NRL season</option></select></label>
      <label className="drl-player-search">SEARCH PLAYERS<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Player or club name" /></label>
      <label>SORT BY<select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
        <option value="points">Points</option><option value="tries">Tries</option><option value="try_assists">Try assists</option>
        <option value="tackles">Tackles</option><option value="metres_gained">Metres gained</option>
        <option value="line_breaks">Line breaks</option><option value="appearances">Season appearances</option>
      </select></label>
      <button type="button" className="drl-sort-direction" onClick={() => setSortDirection((direction) => direction === "desc" ? "asc" : "desc")} aria-label="Toggle sort direction">{sortDirection === "desc" ? "HIGHEST FIRST ↓" : "LOWEST FIRST ↑"}</button>
    </div>
    {loading && <div className="drl-player-empty" role="status"><strong>LOADING PLAYER PROFILES</strong><p>Retrieving verified season records.</p></div>}
    {!loading && feedError && <div className="drl-player-empty" role="status"><strong>PLAYER DATA NOT CONNECTED</strong><p>{feedError}</p><small>The 588-player archive remains private. No placeholder statistics or unverified photographs are displayed.</small></div>}
    {!loading && !feedError && <div className="drl-player-layout">
      <div className="drl-player-list" aria-label="Player ranking results">
        <div className="drl-player-list-heading"><span>PLAYER</span><span>{sortKey.replaceAll("_", " ").toUpperCase()}</span></div>
        {visiblePlayers.map((player, index) => <button type="button" key={player.drl_player_id} className={selectedId === player.drl_player_id ? "drl-player-row selected" : "drl-player-row"} onClick={() => setSelectedId(player.drl_player_id)}>
          <span className="drl-player-rank">{index + 1}</span><ActionPhoto player={player} compact />
          <span className="drl-player-name"><strong>{player.first_name} {player.last_name}</strong><small>{player.team_name ?? "Current club not verified"} · {player.position ?? "Position not supplied"}</small></span>
          <strong className="drl-player-score">{displayStat(player.stats?.[sortKey])}</strong>
        </button>)}
        {visiblePlayers.length === 0 && <p className="drl-player-no-results">No matching players in the connected feed.</p>}
      </div>
      <aside className="drl-player-detail">
        {selected ? <>
          <div className="drl-player-profile-head"><ActionPhoto player={selected} />
            <div><span>2026 NRL PLAYER PROFILE</span><h2>{selected.first_name} {selected.last_name}</h2><p>{selected.team_name ?? "Current club not verified"} · {selected.position ?? "Position not supplied"}</p></div>
          </div>
          <PlayerCardCollection player={selected} />
          <div className="drl-player-stat-grid">{statLabels.map((stat) => <article key={stat.key}><span>{stat.label}</span><strong>{displayStat(selected.stats?.[stat.key], stat.suffix)}</strong></article>)}</div>
        </> : <div className="drl-player-empty"><strong>SELECT A PLAYER</strong><p>Choose a player to view their season profile, card collection and verified statistics.</p></div>}
      </aside>
    </div>}
  </section>;
}
