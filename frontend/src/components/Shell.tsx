import { Activity, ArrowUpRight, ClipboardCheck, FileText, Gauge, LayoutDashboard, Menu, Settings2, ShieldAlert, X } from 'lucide-react';
import { useState } from 'react';
import { Link, NavLink, Outlet, useParams } from 'react-router-dom';
import { activeSiteId, activeSiteName } from '../api';
import { Brand } from './Brand';

export function Shell() {
  const [open, setOpen] = useState(false);
  const siteId = activeSiteId();
  const siteName = activeSiteName();
  const items = [
    { to: '/', label: 'Heat check', icon: Gauge, end: true },
    { to: '/setup', label: 'Site setup', icon: Settings2 },
    ...(siteId ? [
      { to: `/dashboard/${siteId}`, label: 'Shift overview', icon: LayoutDashboard },
      { to: `/compliance/${siteId}`, label: 'Compliance', icon: ClipboardCheck },
      { to: `/ledger/${siteId}`, label: 'Heat ledger', icon: Activity },
      { to: '/rulebooks', label: 'Rulebook desk', icon: FileText },
    ] : []),
    { to: '/replay', label: 'Replay demo', icon: ShieldAlert },
  ];
  const close = () => setOpen(false);
  return (
    <div className="app-frame">
      <aside className={`sidebar${open ? ' sidebar--open' : ''}`}>
        <div className="sidebar__top"><Brand /><button className="icon-btn mobile-close" onClick={close} aria-label="Close navigation"><X size={20} /></button></div>
        <div className="site-switcher">
          <span className="eyebrow">CURRENT WORKSPACE</span>
          <div className="site-switcher__row"><span className="site-indicator" /><div><strong>{siteName ?? 'Public heat desk'}</strong><small>{siteId ? 'Supervisor access · this session' : 'No site selected'}</small></div></div>
        </div>
        <nav className="nav-list" aria-label="Main navigation">
          <span className="eyebrow nav-list__label">OPERATIONS</span>
          {items.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} onClick={close} className={({ isActive }) => `nav-link${isActive ? ' nav-link--active' : ''}`}>
              <Icon size={18} strokeWidth={1.8} /><span>{label}</span>{label === 'Heat check' && <span className="nav-mini">PUBLIC</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__bottom">
          <div className="safety-note"><span className="safety-note__icon"><ShieldAlert size={17} /></span><div><strong>Decision support</strong><p>Demo estimates are not field measurements or medical advice.</p></div></div>
          <div className="sidebar__meta"><span>SHIFT SHIELD · BUILD 0.1</span><span className="online-dot" /> DEMO MODE</div>
        </div>
      </aside>
      {open && <button className="sidebar-backdrop" onClick={close} aria-label="Close navigation overlay" />}
      <div className="main-column">
        <header className="topbar">
          <button className="icon-btn mobile-menu" onClick={() => setOpen(true)} aria-label="Open navigation"><Menu size={22} /></button>
          <div className="topbar__status"><span className="pulse-dot" /><span>HEAT MONITORING</span><i /> <span>15-MINUTE PLAN</span></div>
          <div className="topbar__right"><span className="topbar__date">FIELD OPERATIONS</span><Link className="topbar__action" to={siteId ? `/dashboard/${siteId}` : '/setup'}>{siteId ? 'View shift' : 'Create site'}<ArrowUpRight size={15} /></Link></div>
        </header>
        <main className="page-wrap"><Outlet /></main>
        <footer className="page-footer"><span>SHIFT SHIELD <i>·</i> HEAT SAFETY WITH PROOF OF REST</span><span>Threshold chart transcription pending professional review. Follow official local guidance.</span></footer>
      </div>
    </div>
  );
}
