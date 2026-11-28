import React from "react";

export type RankingScope = "Club" | "State" | "AUS";

type RankingProps = {
  scope: RankingScope;
  onScopeChange: (scope: RankingScope) => void;
};

export function OverallRankingsPanel({ scope, onScopeChange }: RankingProps) {
  return <section className="drlcc-panel">
    <div className="drlcc-panel-heading"><span>ALL CLASSIC CUP PARTICIPANTS</span><h2>OVERALL RANKINGS</h2></div>
    <div className="drlcc-tabs" role="tablist" aria-label="Ranking scope">
      {(["Club", "State", "AUS"] as RankingScope[]).map((item) =>
        <button key={item} type="button" role="tab" aria-selected={scope === item}
          className={scope === item ? "is-active" : ""} onClick={() => onScopeChange(item)}>{item}</button>
      )}
    </div>
    <div className="drlcc-empty"><strong>{scope.toUpperCase()} RANKINGS NOT CONNECTED</strong><p>Rankings will include every eligible Classic Cup participant in the selected scope. No participant positions or scores are fabricated.</p></div>
  </section>;
}

export function LeagueLadderPanel() {
  return <section className="drlcc-panel">
    <div className="drlcc-panel-heading"><span>SELECTED LEAGUE</span><h2>LEAGUE LADDER</h2></div>
    <div className="drlcc-empty"><strong>LEAGUE STANDINGS NOT CONNECTED</strong><p>The ladder will rank members of this league only. It is separate from Club, State and AUS Overall Rankings.</p></div>
  </section>;
}
