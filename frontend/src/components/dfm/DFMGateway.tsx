import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import SiteFooter from "../SiteFooter";
import { authService, type DfmUser } from "../../services/auth-service";

type Mode = "login" | "signup";
type Props = { children: ReactNode };

export default function DFMGateway({ children }: Props) {
  const [user, setUser] = useState<DfmUser | null>(null);
  const [checked, setChecked] = useState(false);
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const isDrl = window.location.hostname.toLowerCase() === "drl.digitalfranchisemanager.com";

  useEffect(() => {
    let active = true;
    authService.getSession()
      .then((session) => { if (active && session.authenticated && session.user?.id) setUser(session.user); })
      .catch(() => { if (active) setError("DFM authentication is temporarily unavailable."); })
      .finally(() => { if (active) setChecked(true); });
    return () => { active = false; };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (mode === "login") {
        await authService.login(email, password);
        const session = await authService.getSession();
        if (!session.authenticated || !session.user?.id) throw new Error("Your session could not be verified.");
        setUser(session.user);
      } else {
        const result = await authService.signup(email, password);
        if (result.confirmationRequired) {
          setNotice("Registration received. Check your email to confirm your DFM account, then sign in.");
          setMode("login");
        } else {
          const session = await authService.getSession();
          if (session.authenticated && session.user?.id) setUser(session.user);
          else setNotice("Registration completed. Please sign in.");
        }
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The request could not be completed.");
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    try {
      await authService.logout();
      setUser(null);
    } catch {
      setError("Logout could not be confirmed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (!checked) return <main className="dfm-auth-shell"><div className="dfm-auth-card"><span className="dfm-kicker">DIGITAL FRANCHISE MANAGER</span><h1>CHECKING<br/><em>SESSION.</em></h1><p>Securely checking your account.</p></div></main>;

  if (!user) return (
    <main className="dfm-auth-shell">
      <header className="dfm-auth-header"><div className="dfm-wordmark"><strong>DFM</strong><span>DIGITAL<br/>FRANCHISE<br/>MANAGER</span></div><span className="dfm-kicker">ONE PLATFORM. MULTIPLE SPORTS.</span></header>
      <section className="dfm-auth-card">
        <span className="dfm-kicker">{mode === "login" ? "ACCOUNT ACCESS" : "CREATE YOUR ACCOUNT"}</span>
        <h1>{mode === "login" ? <>WELCOME<br/><em>BACK.</em></> : <>JOIN<br/><em>DFM.</em></>}</h1>
        <p>{mode === "login" ? "Sign in to enter Digital Franchise Manager." : "Create your DFM account to establish your franchise."}</p>
        <form onSubmit={submit} className="dfm-auth-form">
          <label>Email address<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          {error && <p className="dfm-form-error" role="alert">{error}</p>}
          {notice && <p className="dfm-form-notice" role="status">{notice}</p>}
          <button type="submit" disabled={busy}>{busy ? "PLEASE WAIT…" : mode === "login" ? "SIGN IN" : "CREATE ACCOUNT"}</button>
        </form>
        <button className="dfm-mode-switch" type="button" onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(""); setNotice(""); }}>
          {mode === "login" ? "New to DFM? Create an account" : "Already registered? Sign in"}
        </button>
      </section>
      <SiteFooter/>
    </main>
  );

  if (isDrl) return <>{children}</>;

  return (
    <main className="dfm-hq-shell">
      <header className="dfm-hq-topbar">
        <div className="dfm-wordmark"><strong>DFM</strong><span>DIGITAL<br/>FRANCHISE<br/>MANAGER</span></div>
        <div className="dfm-account">
          <button className="dfm-profile-button" type="button" aria-label="Account menu" onClick={() => setNotice(notice ? "" : "account")}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 12a4.2 4.2 0 1 0 0-8.4A4.2 4.2 0 0 0 12 12Zm-7.2 8.4a7.2 7.2 0 0 1 14.4 0" /></svg>
          </button>
          {notice === "account" && <div className="dfm-account-menu"><span>{user.email}</span><button type="button" onClick={logout} disabled={busy}>Sign out</button></div>}
        </div>
      </header>
      <section className="dfm-hq-content">
        <p className="dfm-kicker">DIGITAL FRANCHISE MANAGER · HEADQUARTERS</p>
        <h1>YOUR<br/><em>PLATFORM.</em></h1>
        <p className="dfm-hq-intro">Choose a destination to continue.</p>
        <div className="dfm-module-grid">
          <a className="dfm-module" href="#franchise"><span>01 / FRANCHISE</span><strong>FRANCHISE HQ</strong><small>COMING SOON</small></a>
          <a className="dfm-module" href="#newsroom"><span>02 / MEDIA</span><strong>NEWSROOM</strong><small>PLATFORM UPDATES</small></a>
          <a className="dfm-module dfm-module-live" href="https://drl.digitalfranchisemanager.com/"><span>03 / SPORT</span><strong>DIGITAL RUGBY LEAGUE</strong><small>ENTER DRL HQ ↗</small></a>
          <a className="dfm-module" href="#drlw"><span>04 / SPORT</span><strong>DRLW</strong><small>COMING SOON</small></a>
        </div>
      </section>
      <SiteFooter/>
    </main>
  );
}
