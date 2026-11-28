import React, { useState } from "react";
import { AwardsPanel } from "./core/awards_engine";
import { LeagueLadderPanel, OverallRankingsPanel, type RankingScope } from "./core/ladder_engine";
import { LockoutNotice } from "./core/lockout_engine";
import { LeagueNewsPanel } from "./core/newsroom";
import { PlayerProfilePanel, RosterPanel } from "./core/squad_engine";
import { MarketplacePanel, TradeStatus } from "./core/trade_engine";
import "./DRLClassicCup.css";

type Screen = "dashboard" | "roster" | "marketplace" | "rankings" | "leagues" | "active-leagues" | "create-league" | "join-leagues" | "league";
type LeagueTab = "news" | "chatroom" | "roster" | "fixture" | "ladder" | "marketplace";

type Props = { onExit: () => void };

const leagueTabs: { id: LeagueTab; label: string }[] = [
  { id: "news", label: "League News" },
  { id: "chatroom", label: "Chatroom (Coaches Box)" },
  { id: "roster", label: "Roster" },
  { id: "fixture", label: "Fixture" },
  { id: "ladder", label: "Ladder" },
  { id: "marketplace", label: "Marketplace" }
];

export default function DRLClassicCup({ onExit }: Props) {
  const [screen, setScreen] = useState<Screen>("dashboard");
  const [leagueTab, setLeagueTab] = useState<LeagueTab>("news");
  const [rankingScope, setRankingScope] = useState<RankingScope>("AUS");
  const [leagueName, setLeagueName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [leagueSearch, setLeagueSearch] = useState("");
  const [notice, setNotice] = useState("");

  const navigate = (next: Screen) => { setNotice(""); setScreen(next); };
  const openLeaguePreview = () => { setLeagueTab("news"); navigate("league"); };
  const goBack = () => {
    if (screen === "dashboard") { onExit(); return; }
    if (screen === "active-leagues" || screen === "create-league" || screen === "join-leagues") { navigate("leagues"); return; }
    if (screen === "league") { navigate("active-leagues"); return; }
    navigate("dashboard");
  };

  const header = <header className="drlcc-header">
    <button type="button" className="drlcc-back" onClick={goBack}>
      <span aria-hidden="true">←</span>{screen === "dashboard" ? "DRL DASHBOARD" : screen === "active-leagues" || screen === "create-league" || screen === "join-leagues" ? "LEAGUES" : screen === "league" ? "ACTIVE LEAGUES" : "CLASSIC CUP HOME"}
    </button>
    <div className="drlcc-brand"><span>DRL</span><strong>CLASSIC CUP</strong></div>
    <span className="drlcc-season">CLASSIC COMPETITION</span>
  </header>;

  let content: React.ReactNode;

  if (screen === "dashboard") {
    content = <>
      <section className="drlcc-hero"><div><span className="drlcc-kicker">DIGITAL RUGBY LEAGUE</span><h1>CLASSIC <em>CUP.</em></h1><p>Your Classic Cup team, player market, rankings and leagues.</p></div><div className="drlcc-hero-mark">CC</div></section>
      <div className="drlcc-dashboard-grid">
        <button type="button" className="drlcc-destination" onClick={() => navigate("roster")}><span>01 / TEAM MANAGEMENT</span><strong>ROSTER</strong><small>Manage your 21-player squad</small><b>OPEN ROSTER ↗</b></button>
        <button type="button" className="drlcc-destination" onClick={() => navigate("marketplace")}><span>02 / PLAYER ACQUISITION</span><strong>MARKETPLACE</strong><small>Research eligible Classic players</small><b>OPEN MARKETPLACE ↗</b></button>
        <button type="button" className="drlcc-destination" onClick={() => navigate("rankings")}><span>03 / PLATFORM COMPETITION</span><strong>OVERALL RANKINGS</strong><small>Club · State · AUS</small><b>VIEW RANKINGS ↗</b></button>
        <button type="button" className="drlcc-destination drlcc-destination-featured" onClick={() => navigate("leagues")}><span>04 / LEAGUE MANAGEMENT</span><strong>LEAGUES</strong><small>Active, create and join leagues</small><b>MANAGE LEAGUES ↗</b></button>
      </div>
    </>;
  } else if (screen === "roster") {
    content = <><div className="drlcc-page-title"><span>CLASSIC CUP / TEAM MANAGEMENT</span><h1>MY ROSTER</h1><p>Starting 13 · Interchange 4 · Emergencies 4</p></div><div className="drlcc-two-column"><RosterPanel onPlayerSelect={() => setNotice("Player details require the connected roster feed.")} /><PlayerProfilePanel /></div><LockoutNotice context="Swap and trade actions" /><TradeStatus /></>;
  } else if (screen === "marketplace") {
    content = <><div className="drlcc-page-title"><span>CLASSIC CUP / PLAYER ACQUISITION</span><h1>MARKETPLACE</h1><p>Search and compare eligible players before making a roster decision.</p></div><MarketplacePanel /><LockoutNotice context="Marketplace acquisitions" /></>;
  } else if (screen === "rankings") {
    content = <><div className="drlcc-page-title"><span>CLASSIC CUP / COMPETITION</span><h1>OVERALL RANKINGS</h1><p>All participating Classic Cup users, organised by ranking scope.</p></div><OverallRankingsPanel scope={rankingScope} onScopeChange={setRankingScope} /></>;
  } else if (screen === "leagues") {
    content = <><div className="drlcc-page-title"><span>CLASSIC CUP / LEAGUE MANAGEMENT</span><h1>LEAGUES</h1><p>Manage your Classic Cup league participation.</p></div><div className="drlcc-dashboard-grid drlcc-league-options">
      <button type="button" className="drlcc-destination" onClick={() => navigate("active-leagues")}><span>01 / YOUR COMPETITIONS</span><strong>ACTIVE LEAGUES</strong><small>View leagues you currently belong to</small><b>VIEW ACTIVE LEAGUES ↗</b></button>
      <button type="button" className="drlcc-destination" onClick={() => navigate("create-league")}><span>02 / COMMISSIONER</span><strong>CREATE LEAGUES</strong><small>Set up a new Classic Cup league</small><b>CREATE A LEAGUE ↗</b></button>
      <button type="button" className="drlcc-destination" onClick={() => navigate("join-leagues")}><span>03 / FIND A COMPETITION</span><strong>JOIN LEAGUES</strong><small>Find an eligible public or private league</small><b>FIND A LEAGUE ↗</b></button>
    </div></>;
  } else if (screen === "active-leagues") {
    content = <><div className="drlcc-page-title"><span>CLASSIC CUP / LEAGUES</span><h1>ACTIVE LEAGUES</h1><p>Your current Classic Cup league memberships.</p></div><div className="drlcc-empty"><strong>ACTIVE LEAGUE SERVICE NOT CONNECTED</strong><p>Your existing league memberships will be listed here after the authenticated league service is connected. No sample leagues are shown.</p><button type="button" className="drlcc-secondary-button" onClick={openLeaguePreview}>PREVIEW LEAGUE WORKSPACE</button><small>Preview only — this does not create or join a league.</small></div></>;
  } else if (screen === "create-league") {
    content = <><div className="drlcc-page-title"><span>CLASSIC CUP / LEAGUES</span><h1>CREATE LEAGUES</h1><p>Configure a new Classic Cup league.</p></div><form className="drlcc-form" onSubmit={(event) => { event.preventDefault(); setNotice("League creation is not connected. No league has been created or saved."); }}>
      <label>LEAGUE NAME<input value={leagueName} onChange={(event) => setLeagueName(event.target.value)} placeholder="Enter league name" required maxLength={60} /></label>
      <label>LEAGUE PRIVACY<select defaultValue="private"><option value="private">Private</option><option value="public">Public</option></select></label>
      <p className="drlcc-inline-note">League creation requires the authenticated Classic Cup league service. This form is a UI workflow preview and does not save data.</p>
      <button type="submit" className="drlcc-primary-button" disabled={!leagueName.trim()}>CONTINUE TO LEAGUE SETUP</button>
    </form>{notice && <p className="drlcc-feedback" role="status">{notice}</p>}</>;
  } else if (screen === "join-leagues") {
    content = <><div className="drlcc-page-title"><span>CLASSIC CUP / LEAGUES</span><h1>JOIN LEAGUES</h1><p>Find a public league or enter an invitation code for a private league.</p></div><form className="drlcc-form" onSubmit={(event) => { event.preventDefault(); setNotice("League discovery and joining are not connected. No membership has been created."); }}>
      <label>LEAGUE SEARCH<input value={leagueSearch} onChange={(event) => setLeagueSearch(event.target.value)} placeholder="Search public leagues" /></label>
      <label>INVITATION CODE<input value={joinCode} onChange={(event) => setJoinCode(event.target.value)} placeholder="Enter private league code" maxLength={32} /></label>
      <p className="drlcc-inline-note">League discovery and membership changes require the authenticated Classic Cup league service. No league data is fabricated.</p>
      <button type="submit" className="drlcc-primary-button" disabled={!joinCode.trim() && !leagueSearch.trim()}>CONTINUE</button>
    </form>{notice && <p className="drlcc-feedback" role="status">{notice}</p>}</>;
  } else {
    content = <><div className="drlcc-page-title"><span>CLASSIC CUP / LEAGUE WORKSPACE PREVIEW</span><h1>LEAGUE DASHBOARD</h1><p>League-specific facilities. Roster and Marketplace open the same shared Classic Cup modules.</p></div>
      <nav className="drlcc-league-tabs" aria-label="League navigation">{leagueTabs.map((tab) => <button type="button" key={tab.id} className={leagueTab === tab.id ? "is-active" : ""} onClick={() => setLeagueTab(tab.id)}>{tab.label}</button>)}</nav>
      {leagueTab === "news" && <LeagueNewsPanel />}
      {leagueTab === "chatroom" && <section className="drlcc-panel"><div className="drlcc-panel-heading"><span>LEAGUE COMMUNICATION</span><h2>CHATROOM / COACHES BOX</h2></div><div className="drlcc-empty"><strong>CHAT SERVICE NOT CONNECTED</strong><p>League members' conversations and announcements will appear here when the secured Coaches Box service is connected.</p></div></section>}
      {leagueTab === "roster" && <><div className="drlcc-two-column"><RosterPanel onPlayerSelect={() => setNotice("Player details require the connected roster feed.")} /><PlayerProfilePanel /></div><LockoutNotice context="League roster actions" /></>}
      {leagueTab === "fixture" && <section className="drlcc-panel"><div className="drlcc-panel-heading"><span>SELECTED LEAGUE</span><h2>FIXTURE</h2></div><div className="drlcc-empty"><strong>FIXTURE SERVICE NOT CONNECTED</strong><p>League matchups and round schedules will appear here when the fixture service is connected.</p></div></section>}
      {leagueTab === "ladder" && <LeagueLadderPanel />}
      {leagueTab === "marketplace" && <MarketplacePanel />}
      {notice && <p className="drlcc-feedback" role="status">{notice}</p>}
    </>;
  }

  return <div className="drlcc-app">
    {header}
    <main className="drlcc-main">
      <div className="drlcc-content">{content}</div>
      <footer className="drlcc-footer"><span>DIGITAL RUGBY LEAGUE</span><span>CLASSIC CUP</span><button type="button" onClick={onExit}>RETURN TO DRL DASHBOARD</button></footer>
    </main>
  </div>;
}
