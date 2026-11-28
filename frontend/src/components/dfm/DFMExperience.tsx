import { useState } from "react";
import SiteFooter from "../SiteFooter";
import "./DFMExperience.css";

type Page = "Newsroom" | "HQ Overview" | "Digital Rugby League" | "Franchise HQ" | "Competition" | "Coach's Box" | "Roster" | "Fixture" | "Standings" | "Marketplace" | "Classic Cup" | "Draft Premiership" | "Club Management" | "DRLW";
type ClubSection = "Overview" | "Progression" | "Assets" | "Stadium & Grounds" | "Training & Academy" | "Hospitality" | "Accommodation" | "Administration" | "Transport" | "Medical & Recovery" | "Finances";
const nav = [
  { label: "Newsroom" as Page, icon: "▤", group: "DFM HQ" },
  { label: "Franchise HQ" as Page, icon: "▣", group: "DFM HQ" },
  { label: "Digital Rugby League" as Page, icon: "◈", group: "DFM HQ" }
];
const clubNav: ClubSection[] = ["Overview", "Progression", "Assets", "Stadium & Grounds", "Training & Academy", "Hospitality", "Accommodation", "Administration", "Transport", "Medical & Recovery", "Finances"];
const ranks = ["Community Franchise", "Regional Franchise", "Championship Franchise", "National Franchise", "Premier Franchise"];
const assets = [
  { title: "Hospitality", start: "Local Pub", end: "Leagues Club", levels: 5, text: "Develop club hospitality and commercial operations." },
  { title: "Training & Academy", start: "Empty Training Field", end: "Academy of Excellence", levels: 5, text: "Build from basic training grounds to elite player development." },
  { title: "Accommodation", start: "Local 1-Star Motel", end: "Luxury 5-Star Hotel", levels: 5, text: "Develop accommodation and hospitality capacity." },
  { title: "Administration", start: "Clubhouse", end: "Franchise HQ Office Building", levels: 5, text: "Grow club administration into a professional headquarters." }
];
function Status({ children }: { children: string }) { return <span className="dfme-status">{children}</span>; }
function Heading({ eyebrow, title, text }: { eyebrow: string; title: string; text: string }) {
  return <div className="dfme-page-heading"><div><p className="dfme-eyebrow">{eyebrow}</p><h1>{title}</h1><p>{text}</p></div></div>;
}
function AssetCards({ filter, onOpen }: { filter?: string; onOpen: (section: ClubSection) => void }) {
  return <div className="dfme-asset-grid">{assets.filter((asset) => !filter || asset.title === filter).map((asset) => <article className="dfme-asset-card" key={asset.title}>
    <div className="dfme-card-top"><span>{asset.title}</span><Status>{`${asset.levels} LEVELS`}</Status></div>
    <h3>{asset.start}</h3><div className="dfme-upgrade-track"><span>LEVEL 1</span><i/><span>LEVEL {asset.levels}</span></div>
    <h4>{asset.end}</h4><p>{asset.text}</p>
    <button onClick={() => onOpen(asset.title as ClubSection)}>OPEN ASSET CATEGORY ↗</button>
  </article>)}</div>;
}
function ClubManagement({ onBack }: { onBack: () => void }) {
  const [section, setSection] = useState<ClubSection>("Overview");
  const [menuOpen, setMenuOpen] = useState(false);
  const choose = (next: ClubSection) => { setSection(next); setMenuOpen(false); };
  let content;
  if (section === "Overview") content = <>
    <div className="dfme-club-banner"><div><p className="dfme-eyebrow">CLUB OWNERSHIP & MANAGEMENT</p><h2>BUILD YOUR<br/><em>SPORTING LEGACY.</em></h2><p>Acquire sporting and commercial assets, develop facilities and grow your franchise through real-world competition seasons.</p></div><div className="dfme-club-seal">CLUB<br/>MANAGEMENT</div></div>
    <div className="dfme-stat-grid"><article><span>FRANCHISE CLASSIFICATION</span><strong>COMMUNITY FRANCHISE</strong><small>Standard starting classification</small></article><article><span>SEASON PROGRESSION</span><strong>NOT CONNECTED</strong><small>Sport-specific season records</small></article><article><span>ASSET PORTFOLIO</span><strong>NOT CONNECTED</strong><small>Owned properties and facilities</small></article></div>
    <div className="dfme-section-title"><div><p className="dfme-eyebrow">DEVELOPMENT PORTFOLIO</p><h3>BUILD YOUR ORGANISATION</h3></div><button onClick={() => choose("Assets")}>VIEW ALL ASSETS ↗</button></div>
    <AssetCards onOpen={choose}/>
    <div className="dfme-note"><strong>FOUNDING FRANCHISE RECOGNITION</strong><p>Eligible teams with competition participation dating back to 2019 may receive verified historical season credits and award points. Historical records and allocations are not yet connected.</p></div>
  </>;
  else if (section === "Progression") content = <>
    <Heading eyebrow="CLUB DEVELOPMENT / CLASSIFICATION" title="FRANCHISE PROGRESSION" text="Each completed season advances the franchise by one rank in that sport. Every sport maintains its own independent progression."/>
    <div className="dfme-rank-list">{ranks.map((rank, index) => <article key={rank}><span className="dfme-rank-number">0{index + 1}</span><div><h3>{rank}</h3><p>{index === 0 ? "Starting classification for new franchises." : index === 4 ? "Highest classification. Further seasons continue earning development rewards." : "Earned through completed seasons in the relevant sport."}</p></div>{index === 0 && <Status>START</Status>}</article>)}</div>
    <div className="dfme-note"><strong>SEASON RULE</strong><p>One completed season in one sport equals one progression rank in that sport. Rank is capped at Premier Franchise. Additional seasons at the maximum rank continue to earn development rewards.</p></div>
    <div className="dfme-note"><strong>HISTORICAL FOUNDING FRANCHISES</strong><p>Only select teams from the competition's history since 2019 qualify for retrospective verification. Their historical seasons and award points are handled separately from new-franchise progression.</p></div>
  </>;
  else if (section === "Assets") content = <><Heading eyebrow="PROPERTY / FACILITIES / COMMERCIAL" title="ASSET PORTFOLIO" text="Every asset has its own independent upgrade pathway. Asset types may have three or five levels depending on their nature."/><AssetCards onOpen={choose}/><div className="dfme-note"><strong>OTHER PLANNED ASSET CATEGORIES</strong><p>Stadiums and sporting grounds, team transport, medical facilities, recovery centres and additional commercial properties. Their individual upgrade stages will be defined in their asset specifications.</p></div></>;
  else if (["Training & Academy", "Hospitality", "Accommodation", "Administration"].includes(section)) content = <><Heading eyebrow="ASSET CATEGORY / DEVELOPMENT" title={section.toUpperCase()} text={section === "Training & Academy" ? "Develop training infrastructure from an empty field to an Academy of Excellence through five independent asset levels." : section === "Hospitality" ? "Build hospitality from a Local Pub through staged upgrades to a Leagues Club." : section === "Accommodation" ? "Develop accommodation from a local 1-star motel to a luxury 5-star hotel." : "Grow club administration from a clubhouse into a dedicated Franchise HQ office building."}/><AssetCards filter={section} onOpen={choose}/></>;
  else if (section === "Stadium & Grounds") content = <Heading eyebrow="ASSET CATEGORY" title="STADIUM & GROUNDS" text="Purchase and develop home grounds, stadium capacity, playing surfaces and match-day facilities. Individual asset levels and upgrade requirements will be specified before functionality is connected."/>;
  else if (section === "Transport") content = <Heading eyebrow="ASSET CATEGORY" title="TEAM TRANSPORT" text="Purchase and upgrade team transport, including team buses and support vehicles. The individual asset pathway will be specified separately."/>;
  else if (section === "Medical & Recovery") content = <Heading eyebrow="ASSET CATEGORY" title="MEDICAL & RECOVERY" text="Develop medical, sports science, rehabilitation and recovery infrastructure. Each asset will have an independently defined three- or five-level pathway."/>;
  else content = <Heading eyebrow="CLUB OPERATIONS" title="FINANCES" text="The financial management interface will present available funds, operating income, expenses, asset purchase costs, upgrade costs and maintenance when the financial service is built. No balances or prices are fabricated in this design preview."/>;
  return <main className="dfme-club-shell">
    <header className="dfme-topbar"><button className="dfme-back" onClick={onBack}>← DFM HQ</button><div className="dfme-topbar-label">CLUB OWNERSHIP <b>& MANAGEMENT</b></div><Status>DESIGN MODE</Status><button className="dfme-menu" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle club management navigation">☰</button></header>
    <div className="dfme-club-layout"><aside className={menuOpen ? "dfme-club-nav open" : "dfme-club-nav"}><div className="dfme-club-nav-head">CLUB MANAGEMENT</div>{clubNav.map((item) => <button key={item} className={section === item ? "active" : ""} onClick={() => choose(item)}>{item}</button>)}<div className="dfme-nav-foot">FRANCHISE CLASSIFICATION<br/><strong>COMMUNITY FRANCHISE</strong></div></aside><section className="dfme-club-main"><div className="dfme-breadcrumb">DFM HQ <span>/</span> CLUB MANAGEMENT <span>/</span> {section.toUpperCase()}</div>{content}<div className="dfme-disclaimer">DESIGN FOUNDATION ONLY · NO LIVE FRANCHISE RECORDS, ASSETS OR FINANCIAL DATA CONNECTED</div></section></div><SiteFooter/>
  </main>;
}
export default function DFMExperience({ onEnterDigitalRugbyLeague }: { onEnterDigitalRugbyLeague: () => void }) {
  const [page, setPage] = useState<Page>("HQ Overview");
  const [menuOpen, setMenuOpen] = useState(false);
  const [newsTab, setNewsTab] = useState("Platform");
  const [competitionTab, setCompetitionTab] = useState("DML Classic Cup");
  const [competitionRound, setCompetitionRound] = useState("1");
  const [playerRound, setPlayerRound] = useState("1");
  const [coachRound, setCoachRound] = useState("1");
  const [marketCategory, setMarketCategory] = useState("Franchise-to-Franchise");
  const navigate = (next: Page) => { if (next === "Digital Rugby League") { setMenuOpen(false); onEnterDigitalRugbyLeague(); return; } setPage(next); setMenuOpen(false); if (next === "Classic Cup" || next === "Draft Premiership") setCompetitionTab("Competition Overview"); };
  if (page === "Club Management") return <ClubManagement onBack={() => navigate("HQ Overview")}/>;
  const descriptions: Record<Page, string> = {
    "Competition": "Your competition hub for Digital Franchise Manager.",
    "Coach's Box": "Franchise coaching communication and discussion.",
    "Roster": "Manage franchise players and squad selection.",
    "Fixture": "View competition fixtures by round.",
    "Standings": "Competition, player and coach standings with independent round selection.",
    "Marketplace": "Franchise-to-Franchise transfers, Restricted Free Agents and Free Agents.",
    "HQ Overview": "Your central headquarters for DFM news, your franchise workspace and Digital Rugby League.",
    "Digital Rugby League": "Enter the Digital Rugby League sport environment. Classic Cup and Draft Premiership are available only after entering DRL.",
    "Classic Cup": "Traditional fantasy competition workspace. Competition setup, league entry and management destinations are mapped here.",
    "Draft Premiership": "Franchise-based draft competition workspace. League setup, roster, fixture, ladder and market destinations are mapped here.",
    "Club Management": "Own, develop and manage your sporting organisation.",
    "Newsroom": "Platform announcements, competition updates, team news and franchise publications.",
    "DRLW": "Digital Rugby League Women's — dedicated sport environment.",
    "Franchise HQ": "This destination is closed and unavailable while its future scope is being defined."
  };
  const title = page === "HQ Overview" ? "ONE PLATFORM. MULTIPLE SPORTS." : page.toUpperCase();
  return <main className="dfme-shell">
    <header className="dfme-header"><button className="dfme-mobile-toggle" onClick={() => setMenuOpen(!menuOpen)} aria-label="Open DFM navigation">☰</button><div className="dfme-wordmark"><strong>DIGITAL</strong><strong>FRANCHISE</strong><strong>MANAGER</strong></div><span className="dfme-header-label">HEADQUARTERS</span><button className="dfme-account" aria-label="Account profile" title="Account profile"><span/></button></header>
    {menuOpen && <button className="dfme-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)}/>}
    <aside className={menuOpen ? "dfme-sidebar open" : "dfme-sidebar"}><p className="dfme-side-title">DFM HEADQUARTERS</p>{["DFM HQ"].map((group) => { const links = nav.filter((item) => item.group === group); return links.length ? <div className="dfme-nav-group" key={group}><p>{group}</p>{links.map((item) => <button key={item.label} className={page === item.label ? "active" : ""} onClick={() => navigate(item.label)}><span>{item.icon}</span>{item.label === "Newsroom" ? "DFM News and Updates" : item.label === "Franchise HQ" ? "My Franchise HQ" : item.label}{item.label === "Franchise HQ" && <small>CLOSED</small>}</button>)}</div> : null; })}<div className="dfme-sidebar-foot">DIGITAL FRANCHISE MANAGER<br/><small>MOBILE-FIRST APPLICATION FLOW</small></div></aside>
    <section className="dfme-main"><div className="dfme-content"><div className="dfme-breadcrumb">DIGITAL FRANCHISE MANAGER <span>/</span> {page.toUpperCase()}</div><Heading eyebrow="DIGITAL FRANCHISE MANAGER / HEADQUARTERS" title={title} text={descriptions[page]}/>
      {page === "HQ Overview" && <><div className="dfme-destination-grid"><button onClick={() => navigate("Newsroom")}><span>01 / PLATFORM MEDIA</span><strong>DFM NEWS AND UPDATES</strong><small>PLATFORM ANNOUNCEMENTS & UPDATES ↗</small></button><button className="dfme-featured" onClick={() => navigate("Franchise HQ")}><span>02 / YOUR FRANCHISE</span><strong>MY FRANCHISE HQ</strong><small>OPEN YOUR CENTRAL FRANCHISE WORKSPACE ↗</small></button><button onClick={() => navigate("Digital Rugby League")}><span>03 / SPORT</span><strong>DIGITAL RUGBY LEAGUE</strong><small>ENTER THE DRL DEPARTMENT ↗</small></button></div></>}

      {page === "Classic Cup" && <div className="dfme-flow-panel"><div className="dfme-flow-card"><span>CLASSIC CUP</span><h2>COMPETITION HUB</h2><p>Traditional fantasy competition entry point.</p><Status>DESIGN FOUNDATION</Status></div><div className="dfme-flow-links">{["Competition Overview","My Team / Roster","Overall Rankings","Leagues","Create League","Join a League","My Leagues","Awards","Settings"].map((item) => <button className={competitionTab===item?"selected":""} key={item} onClick={() => setCompetitionTab(item)}>{item}<b>↗</b></button>)}</div>{competitionTab==="My Leagues" && <div className="dfme-flow-links dfme-subflow">{["Fixture","Standings","Awards","League Settings"].map((item) => <button key={item} onClick={() => setCompetitionTab(item)}>{item}<b>↗</b></button>)}</div>}<div className="dfme-empty"><span>CLASSIC CUP / {competitionTab.toUpperCase()}</span><h2>{competitionTab.toUpperCase()}</h2><p>This screen is mapped in the application flow. Competition records and actions will be connected in a later functional development phase.</p><Status>DESIGN FOUNDATION</Status></div><div className="dfme-note"><strong>LEAGUE FLOW</strong><p>My Leagues leads to the selected league's fixture, standings, awards and settings. Live Match is reserved for an active live event. Live data and league actions are not connected in this phase.</p></div></div>}
      {page === "Draft Premiership" && <div className="dfme-flow-panel"><div className="dfme-flow-card"><span>DRAFT PREMIERSHIP</span><h2>FRANCHISE COMPETITION HUB</h2><p>Draft-based fantasy competition entry point.</p><Status>DESIGN FOUNDATION</Status></div><div className="dfme-flow-links">{["Competition Overview","My Roster","Leagues","Create League","Join a League","My Leagues","Market — Face to Face","Market — Restricted Free Agent","Market — Free Agent","Awards","Settings"].map((item) => <button className={competitionTab===item?"selected":""} key={item} onClick={() => setCompetitionTab(item)}>{item}<b>↗</b></button>)}</div>{competitionTab==="My Leagues" && <div className="dfme-flow-links dfme-subflow">{["Fixture","Standings","Awards","League Settings"].map((item) => <button key={item} onClick={() => setCompetitionTab(item)}>{item}<b>↗</b></button>)}</div>}<div className="dfme-empty"><span>DRAFT PREMIERSHIP / {competitionTab.toUpperCase()}</span><h2>{competitionTab.toUpperCase()}</h2><p>This screen is mapped in the application flow. Competition records, draft rosters and market actions will be connected in a later functional development phase.</p><Status>DESIGN FOUNDATION</Status></div><div className="dfme-note"><strong>COMPETITION CONTEXT</strong><p>Fixture, standings and awards are presented within the selected league. Live Match appears only when a live event is active. The market contains Face to Face, Restricted Free Agent and Free Agent sections. No live market or player data is loaded.</p></div></div>}
      {page === "Competition" && <div className="dfme-flow-panel"><div className="dfme-flow-card"><span>COMPETITION</span><h2>COMPETITION HUB</h2><p>Access the competition workspace.</p><Status>DESIGN FOUNDATION</Status></div><div className="dfme-flow-links">{["DML Classic Cup","DML Draft Premiership"].map((item) => <button className={competitionTab===item?"selected":""} key={item} onClick={() => setCompetitionTab(item)}>{item}<b>↗</b></button>)}</div><div className="dfme-empty"><span>COMPETITION / {competitionTab.toUpperCase()}</span><h2>{competitionTab.toUpperCase()}</h2><p>Competition configuration and records will be connected in a later development phase.</p><Status>DESIGN FOUNDATION</Status></div></div>}
      {page === "Coach's Box" && <div className="dfme-empty"><span>COACH'S BOX</span><h2>COACH COMMUNICATION</h2><p>Franchise coaching discussions will be available when the secured service is connected.</p><Status>AWAITING SERVICE</Status></div>}
      {page === "Roster" && <div className="dfme-empty"><span>ROSTER</span><h2>FRANCHISE ROSTER</h2><p>Player selection and squad management will appear when the authorised roster service is connected.</p><Status>AWAITING SERVICE</Status></div>}
      {page === "Fixture" && <div className="dfme-empty"><span>FIXTURE</span><h2>COMPETITION FIXTURES</h2><p>Round fixtures will appear when official competition data is connected. No fixtures or results are fabricated.</p><Status>AWAITING DATA</Status></div>}
      {page === "Standings" && <div className="dfme-flow-panel"><div className="dfme-standings-grid">
        <section className="dfme-standings-card"><div className="dfme-card-top"><span>COMPETITION</span><Status>{`ROUND ${competitionRound}`}</Status></div><label>SELECT ROUND<select value={competitionRound} onChange={e=>setCompetitionRound(e.target.value)}>{Array.from({length:30},(_,i)=><option key={i+1} value={String(i+1)}>Round {i+1}</option>)}</select></label><p>Competition standings will appear when official ladder data is connected.</p></section>
        <section className="dfme-standings-card"><div className="dfme-card-top"><span>PLAYERS</span><Status>{`ROUND ${playerRound}`}</Status></div><label>SELECT ROUND<select value={playerRound} onChange={e=>setPlayerRound(e.target.value)}>{Array.from({length:30},(_,i)=><option key={i+1} value={String(i+1)}>Round {i+1}</option>)}</select></label><p>Player standings will appear when verified statistics are connected.</p></section>
        <section className="dfme-standings-card"><div className="dfme-card-top"><span>COACHES</span><Status>{`ROUND ${coachRound}`}</Status></div><label>SELECT ROUND<select value={coachRound} onChange={e=>setCoachRound(e.target.value)}>{Array.from({length:30},(_,i)=><option key={i+1} value={String(i+1)}>Round {i+1}</option>)}</select></label><p>Coach standings will appear when official coach data is connected.</p></section>
      </div><div className="dfme-note"><strong>STANDINGS DATA</strong><p>Each section has its own independent round selector. No ladder positions, player statistics or coach results are invented.</p></div></div>}
      {page === "Marketplace" && <div className="dfme-flow-panel"><div className="dfme-tabs">{["Franchise-to-Franchise","Restricted Free Agent","Free Agents"].map((tab)=><button className={marketCategory===tab?"selected":""} key={tab} onClick={()=>setMarketCategory(tab)}>{tab}</button>)}</div><div className="dfme-empty"><span>MARKETPLACE / {marketCategory.toUpperCase()}</span><h2>{marketCategory.toUpperCase()}</h2><p>{marketCategory==="Franchise-to-Franchise"?"Transfers negotiated directly between franchises will be listed here.":marketCategory==="Restricted Free Agent"?"Restricted free agents and their signing process will be displayed here.":"Available free agents eligible for recruitment will be displayed here."}</p><Status>MARKET DATA NOT CONNECTED</Status></div></div>}
      {page === "Newsroom" && <div className="dfme-flow-panel"><div className="dfme-tabs">{["Platform","Competitions","Teams","Transfers"].map((tab) => <button className={newsTab === tab ? "selected" : ""} key={tab} onClick={() => setNewsTab(tab)}>{tab}</button>)}</div><div className="dfme-empty"><span>NEWSROOM / {newsTab.toUpperCase()}</span><h2>PUBLICATION FEED NOT CONNECTED</h2><p>This destination is ready for published articles and announcements. No sample stories or invented results are displayed.</p><Status>AWAITING CONTENT SERVICE</Status></div></div>}
      {page === "DRLW" && <div className="dfme-empty"><span>DIGITAL RUGBY LEAGUE WOMEN'S</span><h2>SPORT ENVIRONMENT FOUNDATION</h2><p>The DRLW destination is mapped. Its competition rules, engines, player data and dedicated interface will be implemented as a separate sport experience.</p><Status>DESIGN FOUNDATION</Status></div>}
      {page === "Franchise HQ" && <div className="dfme-empty"><span>DFM / FRANCHISE HQ</span><h2>DESTINATION CLOSED</h2><p>Franchise HQ remains closed and inactive by instruction. No registration, identity builder, roster or franchise administration workflow is available.</p><Status>CLOSED</Status></div>}
    </div><SiteFooter/></section>
  </main>;
}
