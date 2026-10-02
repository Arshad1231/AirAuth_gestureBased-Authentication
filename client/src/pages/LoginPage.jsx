import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { authApi } from '../api/authApi.js';
import AirSignatureCapture from '../components/AirSignatureCapture.jsx';
import ResultCard from '../components/ResultCard.jsx';
import StaticGestureCapture from '../components/StaticGestureCapture.jsx';
import StepIndicator from '../components/StepIndicator.jsx';
import { useAuth } from '../context/AuthContext.jsx';

const STEPS = ['Account', 'Step 1 · Gesture', 'Step 2 · Air signature'];
const REDIRECT_SECONDS = 4;

export default function LoginPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { signIn } = useAuth();

  const [step, setStep] = useState(0);
  const [username, setUsername] = useState(params.get('username') || '');
  const [loginSessionId, setLoginSessionId] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [staticResult, setStaticResult] = useState(null);
  const [dynamicResult, setDynamicResult] = useState(null);
  const [notRegistered, setNotRegistered] = useState(false);
  const [redirectIn, setRedirectIn] = useState(REDIRECT_SECONDS);
  const [granted, setGranted] = useState(false);

  // Unregistered users are sent to registration automatically.
  useEffect(() => {
    if (!notRegistered) return undefined;
    if (redirectIn <= 0) {
      navigate(`/register?username=${encodeURIComponent(username)}`);
      return undefined;
    }
    const timer = setTimeout(() => setRedirectIn((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [notRegistered, redirectIn, navigate, username]);

  const restart = (message) => {
    setStep(0);
    setLoginSessionId('');
    setStaticResult(null);
    setDynamicResult(null);
    setError(message || '');
  };

  const handleApiError = (err) => {
    if (err.code === 'ACCOUNT_LOCKED') {
      const until = err.details?.lockedUntil ? new Date(err.details.lockedUntil).toLocaleTimeString() : 'later';
      restart(`Account temporarily locked after too many failed attempts. Try again after ${until}.`);
    } else if (err.code === 'LOGIN_SESSION_EXPIRED' || err.code === 'WRONG_STEP') {
      restart(err.message);
    } else {
      // CAPTURE_REJECTED etc.: the attempt did not count — just retry.
      setError(err.message);
    }
  };

  async function startLogin(event) {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      const response = await authApi.startLogin(username);
      setLoginSessionId(response.loginSessionId);
      setDisplayName(response.displayName);
      setStep(1);
    } catch (err) {
      if (err.code === 'USER_NOT_REGISTERED') {
        setNotRegistered(true);
        setRedirectIn(REDIRECT_SECONDS);
      } else {
        handleApiError(err);
      }
    } finally {
      setBusy(false);
    }
  }

  const handleFailure = (response, setResult) => {
    setResult(response.result);
    if (response.locked) {
      restart('Too many failed attempts — the account is now temporarily locked.');
    } else if (response.sessionEnded) {
      restart(`${response.message} No attempts left for this login — please start again.`);
    } else {
      setError(`${response.message} ${response.attemptsRemaining} attempt(s) left.`);
    }
  };

  const submitStaticGesture = useCallback(async (sample) => {
    setError('');
    setBusy(true);
    try {
      const response = await authApi.verifyStaticGesture(loginSessionId, sample);
      if (response.passed) {
        setStaticResult(response.result);
        setNotice(response.message);
        setStep(2);
      } else {
        handleFailure(response, setStaticResult);
      }
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  }, [loginSessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  const submitAirSignature = useCallback(async (sample) => {
    setError('');
    setNotice('');
    setBusy(true);
    try {
      const response = await authApi.verifyAirSignature(loginSessionId, sample);
      setDynamicResult(response.result);
      if (response.passed) {
        setGranted(true);
        signIn(response.token, response.user);
        setTimeout(() => navigate('/dashboard'), 2500);
      } else {
        handleFailure(response, setDynamicResult);
      }
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  }, [loginSessionId, navigate, signIn]); // eslint-disable-line react-hooks/exhaustive-deps

  if (notRegistered) {
    return (
      <div className="panel narrow center">
        <h2>“{username}” is not registered yet</h2>
        <p>You need to enroll your hand gesture and air signature before you can log in.</p>
        <p className="muted">Taking you to registration in {redirectIn}s…</p>
        <Link className="button primary" to={`/register?username=${encodeURIComponent(username)}`}>Register now</Link>
      </div>
    );
  }

  if (granted) {
    return (
      <div className="panel narrow center access granted">
        <h2>ACCESS GRANTED</h2>
        <p>Welcome back, {displayName}. Both factors verified.</p>
        <div className="result-pair">
          <ResultCard title="Step 1 · Gesture" result={staticResult} />
          <ResultCard title="Step 2 · Air signature" result={dynamicResult} />
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <h2>Log in</h2>
      <StepIndicator steps={STEPS} current={step} />
      {error && <p className="alert error">{error}</p>}
      {notice && !error && <p className="alert ok">{notice}</p>}

      {step === 0 && (
        <form className="form narrow" onSubmit={startLogin}>
          <label>
            Username
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username"
                   required minLength={3} maxLength={32} />
          </label>
          <button type="submit" className="primary" disabled={busy}>Continue</button>
          <p className="muted">New here? <Link to="/register">Create an account</Link></p>
        </form>
      )}

      {step === 1 && (
        <div className="step-grid">
          <div className="instructions">
            <h3>Hi {displayName} — show your secret gesture</h3>
            <p>Use the same hand and pose you registered. Hold it still until the capture finishes.</p>
            {busy && <p className="muted">Verifying gesture…</p>}
            <ResultCard title="Last attempt" result={staticResult} />
          </div>
          <StaticGestureCapture onCapture={submitStaticGesture} disabled={busy} buttonLabel="Verify gesture" />
        </div>
      )}

      {step === 2 && (
        <div className="step-grid">
          <div className="instructions">
            <h3>Now draw your signature in the air</h3>
            <p>Sign naturally with your index finger, then hold it still to finish.</p>
            {busy && <p className="muted">Verifying signature…</p>}
            <ResultCard title="Step 1 · Gesture" result={staticResult} />
            {dynamicResult && <ResultCard title="Last signature attempt" result={dynamicResult} />}
          </div>
          <AirSignatureCapture onCapture={submitAirSignature} disabled={busy} autoSubmit buttonLabel="Start signing" />
        </div>
      )}
    </div>
  );
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * LoginPage.jsx drives the two-step login:
 *   0 Account  username -> /login/start.  Unregistered users see a notice and
 *              are redirected to registration automatically.
 *   1 Step 1   capture the static gesture -> /login/static-gesture
 *   2 Step 2   draw the air signature    -> /login/air-signature
 * It shows a ResultCard for each verification, the attempts left, and handles
 * lockout / expired session by restarting.  When both steps pass it stores
 * the access token, shows ACCESS GRANTED with both scores and opens the
 * dashboard.
 * ========================================================================== */
