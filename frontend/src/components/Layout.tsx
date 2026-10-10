import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { fetchHealth } from '../api';
import type { HealthStatus } from '../types';

export default function Layout() {
  const location = useLocation();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    const check = () => fetchHealth().then((status) => { if (active) { setHealth(status); setApiOnline(true); } }).catch(() => { if (active) { setHealth(null); setApiOnline(false); } });
    void check();
    const timer = window.setInterval(check, 30_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <header className="sticky top-0 z-20 border-b border-border bg-surface-raised/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-8">
            <Link to="/" className="flex items-center gap-3 text-text-primary" aria-label="Review Studio home">
              <span className="grid h-9 w-9 place-items-center rounded-lg border border-accent/30 bg-accent/10 font-mono text-sm font-bold text-accent">CR</span>
              <span><span className="block text-sm font-semibold tracking-tight">Review Studio</span><span className="hidden text-[10px] text-text-muted sm:block">AI code intelligence</span></span>
            </Link>
            <nav aria-label="Main navigation" className="flex h-16 items-center gap-1">
              <NavLink to="/" end className={({ isActive }) => `border-b-2 px-3 py-[22px] text-sm transition-colors ${isActive || location.pathname.startsWith('/reviews/') ? 'border-accent text-text-primary' : 'border-transparent text-text-secondary hover:text-text-primary'}`}>Reviews</NavLink>
              <NavLink to="/eval" className={({ isActive }) => `border-b-2 px-3 py-[22px] text-sm transition-colors ${isActive ? 'border-accent text-text-primary' : 'border-transparent text-text-secondary hover:text-text-primary'}`}>Evaluations</NavLink>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 text-xs text-text-secondary sm:flex" role="status" aria-live="polite">
              <span className={`h-2 w-2 rounded-full ${apiOnline === null ? 'bg-text-muted' : apiOnline ? 'bg-emerald-400' : 'bg-severity-critical'}`} />
              {apiOnline === null ? 'Connecting' : !apiOnline ? 'API unavailable' : health?.llm_providers.primary.configured || health?.llm_providers.fallback.configured ? 'AI configured' : 'Rules only · add an AI key'}
            </div>
            <Link to="/reviews/new" className="btn btn-primary">New review <span aria-hidden="true" className="ml-1.5">＋</span></Link>
          </div>
        </div>
      </header>
      <main className="flex-1"><Outlet /></main>
      <footer className="border-t border-border px-4 py-4 text-center text-xs text-text-muted">Review Studio <span className="mx-1">·</span> Local code review workspace</footer>
    </div>
  );
}
