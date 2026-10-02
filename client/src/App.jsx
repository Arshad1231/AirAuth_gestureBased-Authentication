import { Navigate, Route, Routes } from 'react-router-dom';

import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import HomePage from './pages/HomePage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * App.jsx declares the client routes inside the shared Layout:
 *   /           HomePage
 *   /register   RegisterPage  (enroll gesture + air signature)
 *   /login      LoginPage     (two-step verification)
 *   /dashboard  DashboardPage (protected - requires both steps)
 * Unknown paths redirect home.
 * ========================================================================== */
