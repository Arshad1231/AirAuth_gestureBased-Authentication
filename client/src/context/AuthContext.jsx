import { createContext, useCallback, useContext, useMemo, useState } from 'react';

const STORAGE_KEY = 'airauth.session';
const AuthContext = createContext(null);

function readStoredSession() {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY)) || null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(readStoredSession);

  const signIn = useCallback((token, user) => {
    const next = { token, user };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setSession(next);
  }, []);

  const signOut = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY);
    setSession(null);
  }, []);

  const value = useMemo(
    () => ({
      token: session?.token || null,
      user: session?.user || null,
      isAuthenticated: Boolean(session?.token),
      signIn,
      signOut,
    }),
    [session, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>');
  return context;
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * AuthContext.jsx keeps the authenticated session (access token + public user)
 * in React context and sessionStorage, so it survives page reloads but not
 * closing the tab.  signIn() is called only after BOTH authentication steps
 * pass; signOut() clears it.  useAuth() gives components access.
 * ========================================================================== */
