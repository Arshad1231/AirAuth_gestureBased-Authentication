import { Navigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext.jsx';

export default function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * ProtectedRoute.jsx guards pages that require a completed two-step login,
 * redirecting anonymous visitors to /login.
 * ========================================================================== */
