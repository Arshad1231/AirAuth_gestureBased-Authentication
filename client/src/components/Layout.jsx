import { Link, NavLink, Outlet } from 'react-router-dom';

import { useAuth } from '../context/AuthContext.jsx';

export default function Layout() {
  const { isAuthenticated, user, signOut } = useAuth();

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark">✋</span> AirAuth
        </Link>
        <nav>
          {isAuthenticated ? (
            <>
              <NavLink to="/dashboard">{user?.displayName}</NavLink>
              <button type="button" className="link" onClick={signOut}>Log out</button>
            </>
          ) : (
            <>
              <NavLink to="/login">Log in</NavLink>
              <NavLink to="/register">Register</NavLink>
            </>
          )}
        </nav>
      </header>

      <main className="content">
        <Outlet />
      </main>

      <footer className="footer muted">
        Two-step air authentication · static hand gesture + dynamic air signature · demo system
      </footer>
    </div>
  );
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * Layout.jsx is the page frame shared by every route: top bar with the brand
 * and auth-aware navigation (Log in / Register, or the user's name and Log
 * out), the routed page content via <Outlet/>, and a footer.
 * ========================================================================== */
