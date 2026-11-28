import React from "react";

export type ClassicPlayer = {
  id: string;
  name: string;
  club: string;
  position: string;
  price?: number;
  average?: number;
  totalPoints?: number;
};

type RosterPanelProps = {
  onPlayerSelect: (player: ClassicPlayer) => void;
};

const startingSlots = [
  ["WFB", 3], ["CTR", 2], ["HLF", 2], ["EDG", 2], ["MID", 3], ["HOK", 1]
] as const;

function EmptySlot({ label, onClick }: { label: string; onClick: () => void }) {
  return <button type="button" className="drlcc-roster-slot" onClick={onClick} disabled>
    <span>{label}</span><strong>PLAYER DATA PENDING</strong><small>Awaiting connected roster</small>
  </button>;
}

export function RosterPanel({ onPlayerSelect }: RosterPanelProps) {
  const openUnavailableProfile = () => {
    // No player profile is fabricated when the authenticated roster feed is absent.
  };
  void onPlayerSelect;
  return <section className="drlcc-panel">
    <div className="drlcc-panel-heading"><span>21-PLAYER SQUAD</span><h2>MY ROSTER</h2></div>
    <div className="drlcc-roster-group">
      <div className="drlcc-group-heading"><h3>STARTING 13</h3><span>13 POSITIONS</span></div>
      <div className="drlcc-roster-grid">{startingSlots.flatMap(([position, count]) =>
        Array.from({ length: count }, (_, index) =>
          <EmptySlot key={position + index} label={position + " " + (index + 1)} onClick={openUnavailableProfile} />
        )
      )}</div>
    </div>
    <div className="drlcc-roster-group">
      <div className="drlcc-group-heading"><h3>INTERCHANGE</h3><span>4 PLAYERS</span></div>
      <div className="drlcc-roster-grid drlcc-roster-grid-four">{Array.from({ length: 4 }, (_, index) =>
        <EmptySlot key={"INT" + index} label={"INT " + (index + 1)} onClick={openUnavailableProfile} />
      )}</div>
    </div>
    <div className="drlcc-roster-group">
      <div className="drlcc-group-heading"><h3>EMERGENCIES</h3><span>4 PLAYERS</span></div>
      <div className="drlcc-roster-grid drlcc-roster-grid-four">{Array.from({ length: 4 }, (_, index) =>
        <EmptySlot key={"EMG" + index} label={"EMG " + (index + 1)} onClick={openUnavailableProfile} />
      )}</div>
    </div>
    <div className="drlcc-empty drlcc-empty-compact"><strong>ROSTER SERVICE NOT CONNECTED</strong><p>Your authenticated 21-player roster will load here. Player records, prices and scoring are not replaced with sample data.</p></div>
  </section>;
}

export function PlayerProfilePanel({ player }: { player?: ClassicPlayer }) {
  const actions = [{ key: "S", label: "Swap" }, { key: "T", label: "Trade" }, { key: "C", label: "Captain" }, { key: "VC", label: "Vice Captain" }];
  return <section className="drlcc-panel">
    <div className="drlcc-panel-heading"><span>ROSTER MANAGEMENT</span><h2>PLAYER PROFILE</h2></div>
    {player ? <div className="drlcc-player-profile">
      <h3>{player.name}</h3><p>{player.club} · {player.position}</p>
      <div className="drlcc-player-metrics"><span>PRICE <b>{player.price === undefined ? "—" : "$" + player.price}</b></span><span>AVERAGE <b>{player.average ?? "—"}</b></span><span>TOTAL <b>{player.totalPoints ?? "—"}</b></span></div>
      <div className="drlcc-player-actions">{actions.map((action) => <button type="button" key={action.key} disabled title="Player action service not connected"><b>{action.key}</b><span>{action.label}</span></button>)}</div>
    </div> : <div className="drlcc-player-profile">
      <div className="drlcc-empty"><strong>NO PLAYER SELECTED</strong><p>Choose a player from your connected roster to view their profile and available actions.</p></div>
      <div className="drlcc-player-actions">{actions.map((action) => <button type="button" key={action.key} disabled title="Available when a roster player is loaded"><b>{action.key}</b><span>{action.label}</span></button>)}</div>
    </div>}
  </section>;
}
