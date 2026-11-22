import { useMemo, useState } from "react";
import "./DFMApplication.css";
import SiteFooter from "../SiteFooter";

type Page = "home" | "club-management" | "newsroom" | "drlw";
type ClubSection = "Overview" | "Franchise Progress" | "Season History" | "Asset Portfolio" | "Asset Development" | "Finances" | "Historical Recognition";
type AssetCategory = "Stadium & Grounds" | "Training & Academy" | "Hospitality" | "Accommodation" | "Administration" | "Transport" | "Medical" | "Recovery";

type AssetPath = {
  category: AssetCategory;
  levels: string[];
  max: 3 | 5;
  summary: string;
  benefit: string;
};

const classifications = [
  "Community Franchise",
  "Regional Franchise",
  "Championship Franchise",
  "National Franchise",
  "Premier Franchise"
];

const assetPaths: AssetPath[] = [
  { category: "Stadium & Grounds", max: 5, levels: ["Local Playing Field", "Community Sporting Ground", "Regional Stadium", "National Stadium", "Elite Stadium"], summary: "Match-day venue, playing surface, spectator capacity and event infrastructure.", benefit: "Match-day capacity and venue capability" },
  { category: "Training & Academy", max: 5, levels: ["Empty Training Field", "Club Training Grounds", "Professional Training Facility", "High Performance Centre", "Academy of Excellence"], summary: "Training space, equipment, coaching environment and player development infrastructure.", benefit: "Training capacity and development capability" },
  { category: "Hospitality", max: 5, levels: ["Local Pub", "Sports Bar", "Community Club", "Sports & Recreation Club", "Leagues Club"], summary: "A commercial hospitality venue that can grow with the sporting organisation.", benefit: "Hospitality services and potential operating income" },
  { category: "Accommodation", max: 5, levels: ["Local 1-Star Motel", "2-Star Motor Inn", "3-Star Hotel", "4-Star Premium Hotel", "5-Star Luxury Hotel"], summary: "Accommodation facilities that can serve visitors, members, teams and commercial guests.", benefit: "Room capacity and accommodation services" },
  { category: "Administration", max: 5, levels: ["Clubhouse", "Club Administration Building", "Regional Administration Centre", "Professional Franchise Headquarters", "Franchise HQ Office Building"], summary: "The organisation's administrative base, from a basic clubhouse to a dedicated headquarters.", benefit: "Administrative capacity and departmental workspace" },
  { category: "Transport", max: 3, levels: ["Team Van", "Club Minibus", "Team Coach"], summary: "Club-owned transport for players, staff and official team travel.", benefit: "Passenger capacity and transport capability" },
  { category: "Medical", max: 3, levels: ["First-Aid Room", "Club Treatment Centre", "Sports Medicine Centre"], summary: "Medical assessment and treatment facilities for players and staff.", benefit: "Medical service capability" },
  { category: "Recovery", max: 3, levels: ["Basic Recovery Room", "Recovery Suite", "Elite Recovery Centre"], summary: "Recovery and rehabilitation spaces supporting player welfare.", benefit: "Recovery and rehabilitation capability" }
];

const navItems: { label: ClubSection; icon: string; group: string }[] = [
  { label: "Overview", icon: "▦", group: "CLUB" },
  { label: "Franchise Progress", icon: "↗", group: "CLUB" },
  { label: "Season History", icon: "▤", group: "COMPETITION" },
  { label: "Historical Recognition", icon: "◇", group: "COMPETITION" },
  { label: "Asset Portfolio", icon: "▣", group: "PROPERTY & ASSETS" },
  { label: "Asset Development", icon: "⌂", group: "PROPERTY & ASSETS" },
  { label: "Finances", icon: "$", group: "MANAGEMENT" }
];

function StatusPanel({ title, copy }: { title: string; copy: string }) {
  return <div className="dfma-status-panel"><span className="dfma-status-mark">◇</span><p className="dfma-eyebrow">DESIGN FOUNDATION</p><h3>{title}</h3><p>{copy}</p><span className="dfma-status-label">FUNCTIONAL SERVICE DEFERRED</span></div>;
}

function ClubManagement({ onBack }: { onBack: () => void }) {
  const [section, setSection] = useState<ClubSection>("Overview");
  const [selectedAsset, setSelectedAsset] = useState<AssetCategory>("Stadium & Grounds");
  const [mobileNav, setMobileNav] = useState(false);
  const activeAsset = useMemo(() => assetPaths.find((asset) => asset.category === selectedAsset) ?? assetPaths[0]!, [selectedAsset]);
  const selectSection = (next: ClubSection) => { setSection(next); setMobileNav(false); };
  const sectionCopy: Record<ClubSection, string> = {
    Overview: "Your sporting organisation's command centre. Develop your franchise, build facilities and manage its commercial operations.",
    "Franchise Progress": "Each completed season in a sport advances that sport's franchise classification by one rank.",
    "Season History": "A separate season record is maintained for every sport. Historical participation can be reviewed for eligible founding franchises.",
    "Historical Recognition": "Founding franchises that participated in the competition from 2019 may be eligible for verified historical progression and award credits.",
    "Asset Portfolio": "Review the property, facilities and equipment owned by your sporting organisation.",
    "Asset Development": "Choose an asset category and inspect its independent upgrade pathway. Each asset has its own maximum level.",
    Finances: "Manage club funds, operating income, expenditure, maintenance and development investment."
  };

  let content;
  if (section === "Overview") content = <div className="dfma-overview">
    <div className="dfma-feature-banner"><div><p className="dfma-eyebrow">CLUB OWNERSHIP & MANAGEMENT</p><h2>BUILD YOUR<br/><em>SPORTING EMPIRE.</em></h2><p>Start with a Community Franchise and develop a sporting organisation through seasons, facilities and sound management.</p></div><div className="dfma-rank-stamp"><span>STARTING CLASSIFICATION</span><strong>01</strong><b>COMMUNITY<br/>FRANCHISE</b></div></div>
    <div className="dfma-rule-grid">
      <article><span>01 / PROGRESSION</span><strong>1 SEASON = 1 RANK</strong><p>Progression is recorded independently for each sport.</p></article>
      <article><span>02 / ASSETS</span><strong>3 OR 5 LEVELS</strong><p>Every asset has its own upgrade pathway and maximum level.</p></article>
      <article><span>03 / OWNERSHIP</span><strong>YOUR STRATEGY</strong><p>Choose which properties and facilities to acquire and develop.</p></article>
    </div>
    <div className="dfma-section-title"><div><p className="dfma-eyebrow">MANAGEMENT WORKSPACE</p><h3>YOUR CLUB OPERATIONS</h3></div></div>
    <div className="dfma-action-grid">
      <button onClick={() => selectSection("Franchise Progress")}><span>01 / CLASSIFICATION</span><strong>FRANCHISE PROGRESS</strong><small>View the five franchise ranks</small><b>↗</b></button>
      <button onClick={() => selectSection("Asset Portfolio")}><span>02 / OWNERSHIP</span><strong>ASSET PORTFOLIO</strong><small>Review owned club assets</small><b>↗</b></button>
      <button onClick={() => selectSection("Asset Development")}><span>03 / DEVELOPMENT</span><strong>UPGRADE FACILITIES</strong><small>Explore asset development paths</small><b>↗</b></button>
      <button onClick={() => selectSection("Historical Recognition")}><span>04 / FOUNDING CLUBS</span><strong>HISTORICAL RECOGNITION</strong><small>Review the 2019 founding-club pathway</small><b>↗</b></button>
    </div>
    <p className="dfma-design-note">DESIGN PREVIEW ONLY · No franchise records, purchases, balances or historical points are loaded or saved.</p>
  </div>;
  else if (section === "Franchise Progress") content = <section className="dfma-content-panel"><div className="dfma-section-title"><div><p className="dfma-eyebrow">FIVE-CLASSIFICATION PATHWAY</p><h3>FRANCHISE PROGRESSION</h3></div><span className="dfma-chip">ONE SEASON / ONE RANK</span></div><div className="dfma-classification-list">{classifications.map((name, index) => <div className="dfma-classification-row" key={name}><span className="dfma-rank-number">0{index + 1}</span><div><strong>{name}</strong><small>{index === 0 ? "Starting classification for new franchises" : index === 4 ? "Highest classification" : `Reached after completing ${index} recognised season(s) in that sport`}</small></div>{index === 0 && <span className="dfma-chip">START</span>}</div>)}</div><div className="dfma-info-strip"><strong>Independent sport records</strong><p>Rugby league, soccer and other supported sports each maintain their own season count and franchise classification. A season in one sport does not advance another sport.</p></div></section>;
  else if (section === "Season History") content = <div className="dfma-two-column"><StatusPanel title="SEASON RECORDS NOT CONNECTED" copy="The screen structure is ready for season-by-season participation records, results and progression history. No historical seasons are being assumed."/><div className="dfma-content-panel"><p className="dfma-eyebrow">PROGRESSION RULE</p><h3>ONE COMPLETED SEASON</h3><p className="dfma-panel-copy">Each officially recognised completed season in an individual sport advances that franchise by one rank, up to Premier Franchise. Further seasons at the maximum rank may continue to earn development rewards.</p><div className="dfma-mini-flow"><span>SEASON COMPLETED</span><b>→</b><span>RANK +1</span></div></div></div>;
  else if (section === "Historical Recognition") content = <div className="dfma-two-column"><div className="dfma-content-panel"><p className="dfma-eyebrow">FOUNDING FRANCHISE PATHWAY</p><h3>RECOGNISING THE JOURNEY SINCE 2019</h3><p className="dfma-panel-copy">Select founding franchises that participated in the competition from 2019 may have eligible historical seasons and achievements reviewed.</p><ul className="dfma-check-list"><li>Verify participating franchise identity.</li><li>Confirm each completed historical season.</li><li>Validate premierships, grand finals and recognised awards.</li><li>Calculate historical progression and award credits.</li><li>Apply approved credits to eligible club development.</li></ul></div><StatusPanel title="HISTORICAL RECORDS AWAITING VERIFICATION" copy="No teams, seasons, achievements or award-point balances have been imported or calculated."/><div className="dfma-info-strip dfma-full-width"><strong>Historical credits are not ordinary season progression.</strong><p>Verified historical seasons can establish a founding franchise's starting position. Historical award points remain a separate reward balance that can be allocated to eligible development.</p></div></div>;
  else if (section === "Asset Portfolio") content = <div className="dfma-content-panel"><div className="dfma-section-title"><div><p className="dfma-eyebrow">OWNERSHIP REGISTER</p><h3>ASSET PORTFOLIO</h3></div><span className="dfma-chip">NO LIVE ASSETS</span></div><p className="dfma-panel-copy">Your purchased properties and facilities will be listed here once asset ownership is implemented. The catalogue below shows the planned asset classes, not owned items.</p><div className="dfma-asset-category-grid">{assetPaths.map((asset) => <button key={asset.category} className={selectedAsset === asset.category ? "selected" : ""} onClick={() => { setSelectedAsset(asset.category); setSection("Asset Development"); }}><span>{asset.max} LEVELS</span><strong>{asset.category}</strong><small>{asset.levels[0]} → {asset.levels[asset.levels.length - 1]}</small></button>)}</div></div>;
  else if (section === "Asset Development") content = <div className="dfma-content-panel"><div className="dfma-section-title"><div><p className="dfma-eyebrow">ASSET UPGRADE CATALOGUE</p><h3>ASSET DEVELOPMENT</h3></div><span className="dfma-chip">DESIGN PREVIEW</span></div><div className="dfma-asset-layout"><nav className="dfma-asset-nav" aria-label="Asset categories">{assetPaths.map((asset) => <button key={asset.category} className={selectedAsset === asset.category ? "selected" : ""} onClick={() => setSelectedAsset(asset.category)}>{asset.category}<span>{asset.max}</span></button>)}</nav><section className="dfma-asset-detail"><div className="dfma-asset-detail-head"><div><p className="dfma-eyebrow">{activeAsset.category.toUpperCase()}</p><h4>{activeAsset.levels[0]}</h4></div><span className="dfma-chip">{activeAsset.max} LEVELS</span></div><p className="dfma-panel-copy">{activeAsset.summary}</p><div className="dfma-upgrade-path">{activeAsset.levels.map((level, index) => <div className="dfma-upgrade-step" key={level}><span>LEVEL {index + 1}</span><strong>{level}</strong>{index < activeAsset.levels.length - 1 && <i aria-hidden="true">↓</i>}</div>)}</div><div className="dfma-info-strip"><strong>Development benefit</strong><p>{activeAsset.benefit}. Actual costs, operating expenses, prerequisites and performance effects will be defined during the functional systems phase.</p></div></section></div></div>;
  else content = <div className="dfma-two-column"><StatusPanel title="FINANCIAL SERVICE NOT CONNECTED" copy="No fictional account balance, revenue, expenditure or profit figures are displayed."/><div className="dfma-content-panel"><p className="dfma-eyebrow">FINANCIAL MANAGEMENT DESIGN</p><h3>MANAGE THE CLUB'S MONEY</h3><ul className="dfma-check-list"><li>Club funds and development points.</li><li>Match-day and competition income.</li><li>Commercial property income.</li><li>Asset purchase and upgrade costs.</li><li>Staffing, operating and maintenance expenses.</li></ul></div></div>;

  return <main className="dfma-club-shell">
    <header className="dfma-club-topbar"><button className="dfma-menu-button" onClick={() => setMobileNav(!mobileNav)} aria-label="Toggle club management navigation">☰</button><button className="dfma-back-button" onClick={onBack}>← DFM HQ</button><div className="dfma-topbar-title">CLUB OWNERSHIP <b>& MANAGEMENT</b></div><span className="dfma-mode-label">DESIGN PHASE</span></header>
    {mobileNav && <button className="dfma-mobile-scrim" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
    <div className="dfma-club-layout"><aside className={mobileNav ? "dfma-sidebar open" : "dfma-sidebar"}><div className="dfma-side-brand"><span>DFM</span><strong>CLUB MANAGEMENT</strong></div><nav>{["CLUB", "COMPETITION", "PROPERTY & ASSETS", "MANAGEMENT"].map((group) => <div className="dfma-nav-group" key={group}><p>{group}</p>{navItems.filter((item) => item.group === group).map((item) => <button key={item.label} className={section === item.label ? "active" : ""} onClick={() => selectSection(item.label)}><span>{item.icon}</span>{item.label}</button>)}</div>)}</nav><div className="dfma-sidebar-foot">DFM · CLUB OWNERSHIP<br/><small>FUNCTIONAL SERVICES DEFERRED</small></div></aside><section className="dfma-club-content"><div className="dfma-page-heading"><div><p className="dfma-eyebrow">DFM / CLUB OWNERSHIP & MANAGEMENT</p><h1>{section.toUpperCase()}</h1><p>{sectionCopy[section]}</p></div><span className="dfma-page-count">0{navItems.findIndex((item) => item.label === section) + 1} / 07</span></div>{content}<footer className="dfma-club-footer"><span>DIGITAL FRANCHISE MANAGER</span><span>CLUB OWNERSHIP & MANAGEMENT · DESIGN FOUNDATION</span></footer><SiteFooter/></section></div>
  </main>;
}

export default function DFMApplication() {
  const [page, setPage] = useState<Page>("home");
  const [menuOpen, setMenuOpen] = useState(false);
  const go = (next: Page) => { setPage(next); setMenuOpen(false); };
  if (page === "club-management") return <ClubManagement onBack={() => go("home")} />;
  if (page === "newsroom") return <main className="dfma-hq-shell"><header className="dfma-hq-topbar"><button className="dfma-menu-button" onClick={() => setMenuOpen(!menuOpen)} aria-label="Open DFM navigation">☰</button><a className="dfma-wordmark" href="/" onClick={(event) => { event.preventDefault(); go("home"); }}>DIGITAL<br/>FRANCHISE<br/>MANAGER</a><span className="dfma-topbar-label">NEWSROOM</span></header>{menuOpen && <button className="dfma-mobile-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}{menuOpen && <nav className="dfma-hq-drawer"><button onClick={() => go("home")}>DFM HQ</button><button onClick={() => go("club-management")}>CLUB MANAGEMENT</button></nav>}<section className="dfma-hq-content"><p className="dfma-eyebrow">DFM / NEWSROOM</p><h1>PLATFORM<br/><em>NEWSROOM.</em></h1><div className="dfma-status-panel"><p className="dfma-eyebrow">PUBLICATION SYSTEM</p><h3>NEWS FEED NOT CONNECTED</h3><p>The Newsroom destination is established. Articles, announcements and publication tools will be added in a later functional milestone. No sample stories or fabricated announcements are displayed.</p></div><button className="dfma-return-button" onClick={() => go("home")}>← BACK TO DFM HQ</button></section><SiteFooter/></main>;
  if (page === "drlw") return <main className="dfma-hq-shell"><header className="dfma-hq-topbar"><button className="dfma-menu-button" onClick={() => setMenuOpen(!menuOpen)} aria-label="Open DFM navigation">☰</button><a className="dfma-wordmark" href="/" onClick={(event) => { event.preventDefault(); go("home"); }}>DIGITAL<br/>FRANCHISE<br/>MANAGER</a><span className="dfma-topbar-label">DIGITAL RUGBY LEAGUE WOMEN'S</span></header>{menuOpen && <><button className="dfma-mobile-scrim" aria-label="Close DFM navigation" onClick={() => setMenuOpen(false)} /><nav className="dfma-hq-drawer"><button onClick={() => go("home")}>DFM HQ</button><button onClick={() => go("club-management")}>CLUB MANAGEMENT</button></nav></>}<section className="dfma-hq-content"><p className="dfma-eyebrow">DFM / WOMEN'S RUGBY LEAGUE</p><h1>DIGITAL RUGBY<br/><em>LEAGUE WOMEN'S.</em></h1><div className="dfma-status-panel"><p className="dfma-eyebrow">SPORT ENVIRONMENT</p><h3>DRLW INTERFACE FOUNDATION</h3><p>The women's rugby league destination is reserved in the application flow. Competition screens and sporting data will be added as the DRLW interface is designed. No fixtures, teams or results are fabricated.</p></div><button className="dfma-return-button" onClick={() => go("home")}>← BACK TO DFM HQ</button></section><SiteFooter/></main>;
  return <main className="dfma-hq-shell"><header className="dfma-hq-topbar"><button className="dfma-menu-button" onClick={() => setMenuOpen(!menuOpen)} aria-label="Open DFM navigation">☰</button><a className="dfma-wordmark" href="/" onClick={(event) => { event.preventDefault(); go("home"); }}>DIGITAL<br/>FRANCHISE<br/>MANAGER</a><span className="dfma-topbar-label">HEADQUARTERS</span></header>{menuOpen && <><button className="dfma-mobile-scrim" aria-label="Close DFM navigation" onClick={() => setMenuOpen(false)} /><nav className="dfma-hq-drawer"><button onClick={() => go("home")}>DFM HQ</button><button onClick={() => go("club-management")}>CLUB OWNERSHIP & MANAGEMENT</button><button onClick={() => go("newsroom")}>NEWSROOM</button><a href="https://drl.digitalfranchisemanager.com/">DIGITAL RUGBY LEAGUE ↗</a><button onClick={() => go("drlw")}>DIGITAL RUGBY LEAGUE WOMEN'S</button></nav></>}<section className="dfma-hq-content"><p className="dfma-eyebrow">DIGITAL FRANCHISE MANAGER · HEADQUARTERS</p><h1>ONE PLATFORM.<br/><em>MULTIPLE SPORTS.</em></h1><p className="dfma-hq-intro">Select a destination to enter its dedicated environment.</p><div className="dfma-destination-grid"><button className="dfma-destination-card dfma-destination-primary" onClick={() => go("club-management")}><span>01 / MANAGEMENT SIMULATION</span><strong>CLUB OWNERSHIP<br/>& MANAGEMENT</strong><small>BUILD AND DEVELOP YOUR SPORTING ORGANISATION ↗</small></button><button className="dfma-destination-card dfma-destination-closed" disabled aria-disabled="true"><span>02 / FRANCHISE WORKSPACE</span><strong>FRANCHISE HQ</strong><small>CLOSED · DEVELOPMENT DEFERRED</small></button><button className="dfma-destination-card" onClick={() => go("newsroom")}><span>03 / MEDIA</span><strong>NEWSROOM</strong><small>PLATFORM UPDATES ↗</small></button><a className="dfma-destination-card dfma-destination-live" href="https://drl.digitalfranchisemanager.com/"><span>04 / SPORT</span><strong>DIGITAL RUGBY LEAGUE</strong><small>ENTER DRL HEADQUARTERS ↗</small></a><button className="dfma-destination-card" onClick={() => go("drlw")}><span>05 / SPORT</span><strong>DIGITAL RUGBY LEAGUE WOMEN'S</strong><small>OPEN DRLW ENVIRONMENT ↗</small></button></div><div className="dfma-hq-footnote"><span>DFM · DIGITAL FRANCHISE MANAGER</span><span>APPLICATION FLOW · MOBILE FIRST</span></div></section><SiteFooter/></main>;
}
