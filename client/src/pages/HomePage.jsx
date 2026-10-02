import { Link } from 'react-router-dom';

import SystemStatus from '../components/SystemStatus.jsx';
import { useAuth } from '../context/AuthContext.jsx';

export default function HomePage() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="home">
      <section className="hero">
        <h1>Sign in with your hands — no password.</h1>
        <p className="lead">
          AirAuth verifies you in two steps using only your webcam: a secret <strong>hand gesture</strong>,
          then your personal <strong>signature drawn in the air</strong>. AI models check both the shape and
          the way you move.
        </p>
        <div className="hero-actions">
          {isAuthenticated ? (
            <Link className="button primary" to="/dashboard">Go to dashboard</Link>
          ) : (
            <>
              <Link className="button primary" to="/login">Log in</Link>
              <Link className="button" to="/register">Create an account</Link>
            </>
          )}
        </div>
      </section>

      <section className="cards">
        <article className="card">
          <h3>Step 1 · Static gesture</h3>
          <p>
            Hold your secret hand pose. 21 hand key-points are turned into joint angles, fingertip
            distances and hand geometry, then compared by a template matcher and a neural embedding network.
          </p>
        </article>
        <article className="card">
          <h3>Step 2 · Air signature</h3>
          <p>
            Draw your signature in the air with your index finger. The trajectory&apos;s shape, speed and
            rhythm are compared with DTW, behavioural statistics and a Conv1D + BiGRU embedding network.
          </p>
        </article>
        <article className="card">
          <h3>Privacy by design</h3>
          <p>
            Video never leaves your browser — only hand coordinates are sent. You can delete your account and
            all biometric data at any time.
          </p>
        </article>
      </section>

      <SystemStatus />
    </div>
  );
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * HomePage.jsx is the landing page: explains the two authentication steps and
 * the privacy model, links to login / registration (or the dashboard when
 * already signed in) and shows the live system status panel.
 * ========================================================================== */
