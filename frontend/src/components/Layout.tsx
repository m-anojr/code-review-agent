import { Link, Outlet, useLocation } from 'react-router-dom';

export default function Layout() {
  const location = useLocation();
  
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border bg-surface-raised">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/" className="text-text-primary font-medium tracking-tight">
              Code Review Agent
            </Link>
            <nav className="flex gap-4">
              <Link
                to="/"
                className={`text-sm ${
                  location.pathname === '/' || location.pathname.startsWith('/reviews')
                    ? 'text-text-primary'
                    : 'text-text-secondary hover:text-text-primary transition-colors'
                }`}
              >
                Reviews
              </Link>
              <Link
                to="/eval"
                className={`text-sm ${
                  location.pathname === '/eval'
                    ? 'text-text-primary'
                    : 'text-text-secondary hover:text-text-primary transition-colors'
                }`}
              >
                Eval
              </Link>
            </nav>
          </div>
          <div>
            <Link to="/reviews/new" className="btn btn-primary">
              New Review
            </Link>
          </div>
        </div>
      </header>
      <main className="flex-1 overflow-hidden flex flex-col">
        <Outlet />
      </main>
    </div>
  );
}
