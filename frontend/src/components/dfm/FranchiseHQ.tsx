import { useState } from "react";
import "./FranchiseHQ.css";

type FranchiseSection = "Overview" | "Identity" | "Roster" | "Coaches Box" | "Newsroom" | "Settings";

const sections: { label: FranchiseSection; icon: string; note: string }[] = [
  { label: "Overview", icon: "▦", note: "Franchise command centre" },
  { label: "Identity", icon: "◇", note: "Brand and franchise identity" },
  { label: "Roster", icon: "♙", note: "Squad and player management" },
  { label: "Coaches Box", icon: "▣", note: "Franchise communication" },
  { label: "Newsroom", icon: "▧", note: "Franchise announcements" },
  { label: "Settings", icon: "⚙", note: "Franchise preferences" }
];

function NotConnected({ title, description }: { title: string; description: string }) {
  return <div className="fhq-empty">
    <span className="fhq-empty-mark">◇</span>
    <p className="fhq-kicker">DEVELOPMENT PLACEHOLDER</p>
    <h3>{title}</h3>
    <p>{description}</p>
    <span className="fhq-empty-status">SERVICE NOT CONNECTED</span>
  </div>;
}

function IdentityPreview() {
  const [primary, setPrimary] = useState("#C7FF00");
  const [secondary, setSecondary] = useState("#080908");
  const [tertiary, setTertiary] = useState("#FFFFFF");
  const [accent, setAccent] = useState("");
  const [primaryName, setPrimaryName] = useState("");
  const [secondaryName, setSecondaryName] = useState("");
  const [abbreviation, setAbbreviation] = useState("");
  const [logoType, setLogoType] = useState("Mascot");
  return <div className="fhq-identity-layout">
    <section className="fhq-panel">
      <div className="fhq-panel-heading"><div><p className="fhq-kicker">FRANCHISE BRANDING</p><h3>IDENTITY BUILDER</h3></div><span className="fhq-step">PREVIEW ONLY</span></div>
      <p className="fhq-help">The identity builder follows the existing franchise identity model. Values entered here are temporary browser preview data and are not saved.</p>
      <div className="fhq-field-grid">
        <label>PRIMARY NAME<input value={primaryName} maxLength={40} onChange={e=>setPrimaryName(e.target.value)} placeholder="e.g. Campbelltown"/></label>
        <label>SECONDARY NAME<input value={secondaryName} maxLength={40} onChange={e=>setSecondaryName(e.target.value)} placeholder="e.g. Crushers"/></label>
        <label>ABBREVIATION<input value={abbreviation} maxLength={4} onChange={e=>setAbbreviation(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g,""))} placeholder="3–4 characters"/></label>
        <label>LOGO STYLE<select value={logoType} onChange={e=>setLogoType(e.target.value)}><option>Mascot</option><option>Wordmark</option><option>Lettermark</option><option>Numerical</option><option>Geometrical</option><option>Geographical</option><option>Hybrid</option></select></label>
      </div>
      <div className="fhq-colour-grid">
        <label>PRIMARY COLOUR<input type="color" value={primary} onChange={e=>setPrimary(e.target.value)}/><code>{primary}</code></label>
        <label>SECONDARY COLOUR<input type="color" value={secondary} onChange={e=>setSecondary(e.target.value)}/><code>{secondary}</code></label>
        <label>TERTIARY COLOUR<input type="color" value={tertiary} onChange={e=>setTertiary(e.target.value)}/><code>{tertiary}</code></label>
        <label>ACCENT COLOUR<input type="color" value={accent || "#92958D"} onChange={e=>setAccent(e.target.value)}/><code>{accent || "OPTIONAL"}</code></label>
      </div>
      <div className="fhq-form-note">LOGO GENERATION, IDENTITY PACK STORAGE AND FINAL REGISTRATION WILL BE CONNECTED AFTER AUTHENTICATION IS IMPLEMENTED.</div>
    </section>
    <aside className="fhq-identity-preview">
      <p className="fhq-kicker">LIVE BRAND PREVIEW</p>
      <div className="fhq-preview-crest" style={{borderColor:accent || primary,background:secondary,color:primary}}>
        <span>{abbreviation || "TEAM"}</span>
      </div>
      <h3>{primaryName || "FRANCHISE NAME"}</h3>
      <p>{secondaryName || "FRANCHISE NICKNAME"}</p>
      <div className="fhq-preview-swatches"><i style={{background:primary}}/><i style={{background:secondary}}/><i style={{background:tertiary}}/>{accent&&<i style={{background:accent}}/>}</div>
      <span className="fhq-preview-style">{logoType.toUpperCase()} STYLE</span>
    </aside>
  </div>;
}

export default function FranchiseHQ({ onExit }: { onExit: () => void }) {
  const [section, setSection] = useState<FranchiseSection>("Overview");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const select = (next: FranchiseSection) => { setSection(next); setDrawerOpen(false); };
  const descriptions: Record<FranchiseSection,string> = {
    Overview: "Your franchise command centre. Build your identity, manage your squad and coordinate your coaching staff.",
    Identity: "Establish your franchise name, colours, brand direction and identity pack.",
    Roster: "Manage your squad, player positions, availability and roster decisions.",
    "Coaches Box": "A dedicated communication space for franchise coaches and authorised staff.",
    Newsroom: "Publish franchise announcements, team news and official updates.",
    Settings: "Manage franchise preferences and administrative controls."
  };
  let content;
  if (section === "Identity") content = <IdentityPreview/>;
  else if (section === "Overview") content = <div className="fhq-overview">
    <div className="fhq-welcome"><p className="fhq-kicker">FRANCHISE MANAGEMENT</p><h2>BUILD YOUR<br/><em>FRANCHISE.</em></h2><p>{descriptions[section]}</p></div>
    <div className="fhq-stat-grid">
      <div><span>FRANCHISE IDENTITY</span><strong>NOT REGISTERED</strong><small>Setup service pending</small></div>
      <div><span>ROSTER</span><strong>NOT CONNECTED</strong><small>Player service pending</small></div>
      <div><span>COACHING STAFF</span><strong>NOT CONNECTED</strong><small>Membership service pending</small></div>
    </div>
    <div className="fhq-action-grid">
      <button onClick={()=>select("Identity")}><span>01 / BRAND</span><strong>FRANCHISE IDENTITY</strong><small>Preview the identity builder</small><b>↗</b></button>
      <button onClick={()=>select("Roster")}><span>02 / SQUAD</span><strong>ROSTER MANAGEMENT</strong><small>Open roster workspace</small><b>↗</b></button>
      <button onClick={()=>select("Coaches Box")}><span>03 / STAFF</span><strong>COACHES BOX</strong><small>Open coaching workspace</small><b>↗</b></button>
      <button onClick={()=>select("Newsroom")}><span>04 / MEDIA</span><strong>FRANCHISE NEWSROOM</strong><small>Open publication workspace</small><b>↗</b></button>
    </div>
    <div className="fhq-notice"><strong>DEVELOPMENT MODE</strong><p>Franchise records, players and staff are not loaded. This interface does not create or modify database records.</p></div>
  </div>;
  else if (section === "Roster") content = <NotConnected title="ROSTER WORKSPACE" description="Roster management will connect to the DRL Classic and Draft roster engines. No player records are currently loaded into this interface."/>;
  else if (section === "Coaches Box") content = <NotConnected title="COACHES BOX" description="Coach membership, permissions and private franchise conversations require the future authenticated membership service."/>;
  else if (section === "Newsroom") content = <NotConnected title="FRANCHISE NEWSROOM" description="Franchise announcements and publication tools will be added after the content and permissions model is implemented."/>;
  else content = <NotConnected title="FRANCHISE SETTINGS" description="Franchise ownership, administration and competition lock controls will be connected after the secure account and membership model is implemented."/>;
  return <main className="fhq-shell">
    <header className="fhq-topbar">
      <button className="fhq-menu-toggle" onClick={()=>setDrawerOpen(!drawerOpen)} aria-label="Toggle franchise navigation">☰</button>
      <button className="fhq-back" onClick={onExit}>← DFM HQ</button>
      <div className="fhq-topbar-title">FRANCHISE <b>HEADQUARTERS</b></div>
      <span className="fhq-mode">DESIGN MODE</span>
    </header>
    {drawerOpen&&<button className="fhq-scrim" aria-label="Close navigation" onClick={()=>setDrawerOpen(false)}/>}
    <div className="fhq-layout">
      <aside className={drawerOpen?"fhq-sidebar open":"fhq-sidebar"}>
        <div className="fhq-side-brand"><span>DFM</span><strong>FRANCHISE HQ</strong></div>
        <nav>{sections.map(item=><button key={item.label} className={section===item.label?"active":""} onClick={()=>select(item.label)}><span>{item.icon}</span>{item.label}</button>)}</nav>
        <div className="fhq-sidebar-foot">FRANCHISE WORKSPACE<br/><small>AUTHENTICATION DEFERRED</small></div>
      </aside>
      <section className="fhq-content">
        <div className="fhq-page-heading"><div><p className="fhq-kicker">DFM / FRANCHISE HQ</p><h1>{section.toUpperCase()}</h1><p>{descriptions[section]}</p></div><span className="fhq-page-index">0{sections.findIndex(x=>x.label===section)+1} / 06</span></div>
        {content}
        <footer className="fhq-footer"><span>DIGITAL FRANCHISE MANAGER</span><button onClick={onExit}>RETURN TO DFM HQ ↗</button></footer>
      </section>
    </div>
  </main>;
}
