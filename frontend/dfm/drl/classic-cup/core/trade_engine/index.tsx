import React, { useState } from "react";

export function MarketplacePanel() {
  const [query, setQuery] = useState("");
  return <section className="drlcc-panel">
    <div className="drlcc-panel-heading"><span>CLASSIC CUP PLAYER ACQUISITION</span><h2>MARKETPLACE</h2></div>
    <label className="drlcc-search"><span>SEARCH PLAYERS</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Player name, club or position" /></label>
    <div className="drlcc-filter-row">
      <label>POSITION<select defaultValue=""><option value="">All positions</option><option>WFB</option><option>CTR</option><option>HLF</option><option>EDG</option><option>MID</option><option>HOK</option></select></label>
      <label>SORT BY<select defaultValue="price"><option value="price">Price</option><option value="average">Average points</option><option value="total">Total points</option></select></label>
    </div>
    <div className="drlcc-empty"><strong>PLAYER MARKET FEED NOT CONNECTED</strong><p>{query ? "No live search can be performed until the authenticated player-market feed is connected." : "Eligible players, positions, prices, average points and total points will appear here when the secured Classic marketplace service is connected."}</p></div>
  </section>;
}

export function TradeStatus() {
  return <p className="drlcc-inline-note">Swap and trade execution must be validated by the Classic squad, bank, lockout and trade engines before a roster change is confirmed.</p>;
}
