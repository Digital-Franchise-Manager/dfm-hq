import { useMemo, useState } from "react";

type Section = "Overview" | "Competitions" | "Leagues" | "Fixtures" | "Live Match" | "Ladder" | "Newsroom" | "Awards" | "Roster" | "Market" | "Settings";
type Sport = "DFM" | "DRL";

const sections: { label: Section; icon: string; group: string }[] = [
  { label: "Overview", icon: "▦", group: "HQ" },
  { label: "Competitions", icon: "◈", group: "HQ" },
  { label: "Leagues", icon: "♧", group: "MANAGE" },
  { label: "Fixtures", icon: "▤", group: "MATCH CENTRE" },
  { label: "Live Match", icon: "◉", group: "MATCH CENTRE" },
  { label: "Ladder", icon: "↗", group: "MATCH CENTRE" },
  { label: "Newsroom", icon: "▧", group: "FRANCHISE" },
  { label: "Awards", icon: "✦", group: "FRANCHISE" },
  { label: "Roster", icon: "♙", group: "FRANCHISE" },
  { label: "Market", icon: "⇄", group: "FRANCHISE" },
  { label: "Settings", icon: "⚙", group: "SYSTEM" }
];

const descriptions: Record<Section, string> = {
  Overview: "Your command centre for every competition and franchise.",
  Competitions: "Choose a game mode and enter the competition hub.",
  Leagues: "Create a private league, join an existing league or manage your leagues.",
  Fixtures: "Round-by-round fixtures, match previews and results.",
  "Live Match": "Follow match-day action and live scoring when feeds are connected.",
  Ladder: "Track standings, form and movement across the competition.",
  Newsroom: "Competition updates, franchise announcements and match reports.",
  Awards: "Season honours, round awards and player recognition.",
  Roster: "Manage your squad, starting side and player availability.",
  Market: "Player movement and roster transactions for supported game modes.",
  Settings: "Manage your platform and competition preferences."
};

const modules: { title: string; detail: string; section: Section; tag: string }[] = [
  { title: "DML Classic Cup", detail: "Traditional fantasy competition", section: "Competitions", tag: "CLASSIC" },
  { title: "DML Draft Premiership", detail: "Franchise-based draft competition", section: "Competitions", tag: "DRAFT" },
  { title: "My Leagues", detail: "Create, join and manage leagues", section: "Leagues", tag: "LEAGUES" },
  { title: "Match Centre", detail: "Fixtures, live match and standings", section: "Fixtures", tag: "MATCHDAY" }
];

function BrandMark({ sport }: { sport: Sport }) {
  if (sport === "DRL") {
    return <img className="brand-shield" src="/assets/drl_official_logo.png" alt="Digital Rugby League shield" />;
  }
  return <div className="dfm-monogram" aria-label="Digital Franchise Manager">DFM<span>HQ</span></div>;
}


function PlatformSelector() {
  const [logoFailed, setLogoFailed] = useState(false);
  return (
    <main className="platform-selector">
      <div className="selector-edge-art" aria-hidden="true">
        <span className="selector-splash selector-splash-left" />
        <span className="selector-splash selector-splash-right" />
        <span className="selector-dots" />
      </div>
      <header className="selector-header">
        <div className="selector-wordmark"><span>DFM</span><small>DIGITAL FRANCHISE MANAGER</small></div>
        <span className="selector-status"><i /> PLATFORM GATEWAY</span>
      </header>
      <section className="selector-content">
        <p className="eyebrow"><span /> ONE PLATFORM. MULTIPLE SPORTS.</p>
        <h1>CHOOSE YOUR<br /><em>COMPETITION.</em></h1>
        <p className="selector-intro">Select a platform to enter its dedicated headquarters.</p>
        <a className="platform-option" href="https://drl.digitalfranchisemanager.com/" aria-label="Enter Digital Rugby League">
          <div className="platform-option-logo">
            {!logoFailed && <img src="/assets/drl_official_logo.png" alt="Digital Rugby League official shield" onError={() => setLogoFailed(true)} />}
            {logoFailed && <span className="platform-logo-fallback">DRL</span>}
          </div>
          <div className="platform-option-copy">
            <span className="section-kicker">AVAILABLE PLATFORM · 01</span>
            <h2>DIGITAL RUGBY LEAGUE</h2>
            <p>Enter DRL Competition HQ</p>
          </div>
          <span className="platform-option-arrow" aria-hidden="true">↗</span>
        </a>
        <p className="selector-footnote">MORE SPORTS AND COMPETITIONS WILL BE ADDED AS THEY BECOME AVAILABLE.</p>
      </section>
      <footer className="selector-footer"><span>DIGITAL FRANCHISE MANAGER</span><span>BUILT FOR THE NEXT GENERATION OF FANTASY SPORT</span></footer>
    </main>
  );
}

function DrlDashboard() {
  const [sport, setSport] = useState<Sport>("DRL");
  const [section, setSection] = useState<Section>("Overview");
  const [query, setQuery] = useState("");
  const [mobileMenu, setMobileMenu] = useState(false);

  const visibleSections = useMemo(
    () => sections.filter((item) => item.label.toLowerCase().includes(query.toLowerCase())),
    [query]
  );

  const navigate = (next: Section) => {
    setSection(next);
    setMobileMenu(false);
  };

  return (
    <div className={`site-shell ${sport === "DRL" ? "sport-drl" : "sport-dfm"}`}>
      <div className="edge-art" aria-hidden="true">
        <span className="paint-splash splash-one" />
        <span className="paint-splash splash-two" />
        <span className="paint-drip drip-one" />
        <span className="paint-drip drip-two" />
        <span className="hand-mark mark-x">×</span>
        <span className="hand-mark mark-o">○</span>
        <span className="hand-mark mark-x mark-x-two">×</span>
        <span className="edge-dots" />
      </div>

      <aside className={`sidebar ${mobileMenu ? "sidebar-open" : ""}`}>
        <div className="sidebar-brand">
          <BrandMark sport={sport} />
          <div className="brand-copy">
            <strong>{sport === "DRL" ? "DIGITAL" : "DIGITAL"}</strong>
            <strong>{sport === "DRL" ? "RUGBY LEAGUE" : "FRANCHISE"}</strong>
            {sport === "DFM" && <strong>MANAGER</strong>}
          </div>
        </div>

        <div className="sport-switch" role="group" aria-label="Select platform">
          <button className={sport === "DFM" ? "selected" : ""} onClick={() => { setSport("DFM"); navigate("Overview"); }}>DFM HQ</button>
          <button className={sport === "DRL" ? "selected" : ""} onClick={() => { setSport("DRL"); navigate("Overview"); }}>DRL</button>
        </div>

        <label className="nav-search">
          <span>⌕</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a section" aria-label="Find a section" />
          <kbd>/</kbd>
        </label>

        <nav className="main-nav" aria-label="Main navigation">
          {(["HQ", "MANAGE", "MATCH CENTRE", "FRANCHISE", "SYSTEM"] as const).map((group) => {
            const items = visibleSections.filter((item) => item.group === group);
            if (!items.length) return null;
            return <div className="nav-group" key={group}>
              <p className="nav-heading">{group}</p>
              {items.map((item) => (
                <button key={item.label} className={section === item.label ? "nav-item active" : "nav-item"} onClick={() => navigate(item.label)}>
                  <span className="nav-icon">{item.icon}</span><span>{item.label}</span>
                  {item.label === "Live Match" && <i className="live-dot" />}
                </button>
              ))}
            </div>;
          })}
          {visibleSections.length === 0 && <p className="no-results">No matching sections.</p>}
        </nav>
        <div className="sidebar-foot"><span className="status-pip" /> PLATFORM FOUNDATION <small>BUILD 0.1 · MOBILE FIRST</small></div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <button className="mobile-menu-button" onClick={() => setMobileMenu(!mobileMenu)} aria-label="Toggle navigation">☰</button>
          <div className="breadcrumb"><span>{sport === "DRL" ? "DIGITAL RUGBY LEAGUE" : "DIGITAL FRANCHISE MANAGER"}</span><b>/</b>{section.toUpperCase()}</div>
          <div className="topbar-right"><span className="connection-label"><i /> FOUNDATION MODE</span><button className="avatar-button" aria-label="Account">U</button></div>
        </header>

        <div className="content-wrap">
          <section className="welcome-row">
            <div>
              <p className="eyebrow"><span /> {sport === "DRL" ? "DRL COMPETITION HQ" : "MULTI-SPORT PLATFORM"}</p>
              <h1>{section === "Overview" ? <>OWN THE<br /><em>COMPETITION.</em></> : section.toUpperCase()}</h1>
              <p className="intro-copy">{descriptions[section]}</p>
            </div>
            <div className="hero-brand"><BrandMark sport={sport} /><span>{sport === "DRL" ? "DIGITAL RUGBY LEAGUE" : "DIGITAL FRANCHISE MANAGER"}</span></div>
          </section>

          {section === "Overview" ? (
            <>
              <div className="section-bar"><div><span className="section-kicker">YOUR PLATFORM</span><h2>COMMAND CENTRE</h2></div><span className="section-index">01 / 04</span></div>
              <div className="module-grid">
                {modules.map((module, index) => <button className="module-card" key={module.title} onClick={() => navigate(module.section)}>
                  <div className="module-top"><span>{module.tag}</span><b>0{index + 1}</b></div>
                  <div className="module-symbol">{["◈", "⬡", "♧", "▤"][index]}</div>
                  <h3>{module.title}</h3><p>{module.detail}</p><span className="module-open">OPEN MODULE <b>↗</b></span>
                </button>)}
              </div>

              <div className="section-bar lower-bar"><div><span className="section-kicker">SYSTEM STATUS</span><h2>BUILT TO EXPAND</h2></div></div>
              <div className="status-grid">
                <article className="status-card"><span className="status-number">01</span><div><strong>PLATFORM SHELL</strong><p>Responsive navigation and DFM / DRL identity switching.</p></div><span className="status-state">ACTIVE</span></article>
                <article className="status-card"><span className="status-number">02</span><div><strong>COMPETITION ENGINES</strong><p>Classic and Draft foundations remain separated in the repository.</p></div><span className="status-state">FOUNDATION</span></article>
                <article className="status-card"><span className="status-number">03</span><div><strong>LIVE DATA CONNECTIONS</strong><p>Player, league and match data require verified service integration.</p></div><span className="status-state pending">PENDING</span></article>
              </div>
            </>
          ) : (
            <section className="section-view">
              <div className="section-view-head"><span className="section-kicker">DFM / DRL WORKSPACE</span><span className="section-index">MODULE VIEW</span></div>
              <div className="empty-state">
                <div className="empty-symbol">{sections.find((item) => item.label === section)?.icon}</div>
                <p className="eyebrow">MODULE FOUNDATION</p>
                <h2>{section}</h2>
                <p>{descriptions[section]}</p>
                <div className="empty-divider" />
                <p className="implementation-note">The interface entry point is in place. Live records and actions will be enabled when the corresponding verified backend service and permissions are connected.</p>
                <button className="back-button" onClick={() => navigate("Overview")}>← BACK TO COMMAND CENTRE</button>
              </div>
            </section>
          )}

          <footer className="page-footer"><span>DFM HQ <b>×</b> DIGITAL RUGBY LEAGUE</span><span>BUILT FOR THE NEXT GENERATION OF FANTASY SPORT</span></footer>
        </div>
      </main>
      {mobileMenu && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileMenu(false)} />}
    </div>
  );
}

function App() {
  const hostname = window.location.hostname.toLowerCase();
  return hostname === "drl.digitalfranchisemanager.com" ? <DrlDashboard /> : <PlatformSelector />;
}

export default App;
