import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { authApi } from '../api/authApi.js';
import { useAuth } from '../context/AuthContext.jsx';

const STEP_LABELS = { static_gesture: 'Gesture', dynamic_signature: 'Air signature' };

export default function DashboardPage() {
  const navigate = useNavigate();
  const { token, signOut } = useAuth();
  const [profile, setProfile] = useState(null);
  const [attempts, setAttempts] = useState([]);
  const [error, setError] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    Promise.all([authApi.me(token), authApi.myAttempts(token, 25)])
      .then(([me, history]) => {
        setProfile(me);
        setAttempts(history.attempts);
      })
      .catch((err) => {
        if (err.status === 401) {
          signOut();
          navigate('/login');
        } else {
          setError(err.message);
        }
      });
  }, [token, signOut, navigate]);

  async function deleteAccount() {
    try {
      await authApi.deleteMe(token);
      signOut();
      navigate('/');
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <div className="panel"><p className="alert error">{error}</p></div>;
  if (!profile) return <div className="panel muted">Loading your secure area…</div>;

  const { user, biometricProfile: bio } = profile;
  const failedByOthers = attempts.filter((a) => !a.accepted).length;

  return (
    <div className="dashboard">
      <section className="panel vault">
        <h2>Secure vault</h2>
        <p>
          Welcome, <strong>{user.displayName}</strong>. You reached this page by passing both the static gesture
          and the air-signature check.
        </p>
        <div className="stat-row">
          <div className="stat"><span>Last login</span><strong>{user.lastLoginAt ? new Date(user.lastLoginAt).toLocaleString() : '—'}</strong></div>
          <div className="stat"><span>Registered</span><strong>{new Date(user.createdAt).toLocaleDateString()}</strong></div>
          <div className="stat"><span>Failed attempts (recent)</span><strong>{failedByOthers}</strong></div>
        </div>
      </section>

      {bio && (
        <section className="panel">
          <h3>Your biometric profile</h3>
          <div className="stat-row">
            <div className="stat"><span>Gesture hand</span><strong>{bio.staticHandedness}</strong></div>
            <div className="stat"><span>Gesture captures</span><strong>{bio.staticSamples}</strong></div>
            <div className="stat"><span>Signatures in template</span><strong>{bio.signatureSamples}</strong></div>
            <div className="stat"><span>Adapted from logins</span><strong>{bio.dynamicAdaptations}</strong></div>
          </div>
          <p className="muted">
            Your signature template learns from confident successful logins (up to 20 signatures), so it keeps
            up with small changes in how you sign.
          </p>
        </section>
      )}

      <section className="panel">
        <h3>Authentication history</h3>
        {attempts.length === 0 ? (
          <p className="muted">No attempts yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Time</th><th>Step</th><th>Result</th><th>Match</th><th>Reason</th></tr>
              </thead>
              <tbody>
                {attempts.map((attempt) => (
                  <tr key={attempt.id}>
                    <td>{new Date(attempt.createdAt).toLocaleString()}</td>
                    <td>{STEP_LABELS[attempt.step]}</td>
                    <td className={attempt.accepted ? 'ok-text' : 'bad-text'}>{attempt.accepted ? 'accepted' : 'rejected'}</td>
                    <td>{attempt.matchPercent != null ? `${attempt.matchPercent.toFixed(1)}%` : '—'}</td>
                    <td className="muted">{attempt.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel danger-zone">
        <h3>Privacy</h3>
        {confirmDelete ? (
          <div className="row">
            <span>Delete your account, templates and all stored captures permanently?</span>
            <button type="button" className="danger" onClick={deleteAccount}>Yes, delete everything</button>
            <button type="button" onClick={() => setConfirmDelete(false)}>Cancel</button>
          </div>
        ) : (
          <button type="button" className="danger" onClick={() => setConfirmDelete(true)}>Delete my account and biometric data</button>
        )}
      </section>
    </div>
  );
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * DashboardPage.jsx is the protected "secure vault" shown after a successful
 * two-step login.  It loads the user's profile and biometric-profile summary
 * (hand used, number of gesture captures and signatures, adaptations), lists
 * recent authentication attempts with their match scores, and offers a
 * confirmed "delete my account and biometric data" action.  An expired token
 * sends the user back to login.
 * ========================================================================== */
