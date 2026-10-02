import { useCallback, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { authApi } from '../api/authApi.js';
import AirSignatureCapture from '../components/AirSignatureCapture.jsx';
import SamplePreview from '../components/SamplePreview.jsx';
import StaticGestureCapture from '../components/StaticGestureCapture.jsx';
import StepIndicator from '../components/StepIndicator.jsx';
import { AIR_SIGNATURE, STATIC_GESTURE } from '../config/captureConfig.js';

const STEPS = ['Account', 'Static gesture', 'Air signature', 'Finish'];

export default function RegisterPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const [step, setStep] = useState(0);
  const [username, setUsername] = useState(params.get('username') || '');
  const [displayName, setDisplayName] = useState('');
  const [staticSamples, setStaticSamples] = useState([]);
  const [dynamicSamples, setDynamicSamples] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [completed, setCompleted] = useState(null);

  const addStatic = useCallback((sample) => {
    setStaticSamples((current) => (current.length < STATIC_GESTURE.enrollSamples ? [...current, sample] : current));
  }, []);

  const addDynamic = useCallback((sample) => {
    setDynamicSamples((current) => (current.length < AIR_SIGNATURE.enrollSamples ? [...current, sample] : current));
  }, []);

  async function submitAccount(event) {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      const status = await authApi.checkUser(username);
      if (status.registered) {
        setError('This username is already registered. Please log in instead.');
        return;
      }
      setUsername(status.username);
      setStep(1);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitRegistration() {
    setError('');
    setBusy(true);
    try {
      const result = await authApi.register({ username, displayName, staticSamples, dynamicSamples });
      setCompleted(result);
    } catch (err) {
      if (err.code === 'CAPTURE_REJECTED') {
        // Send the user back to the step with the rejected sample and drop it.
        const index = err.details.sample_index;
        if (err.details.step === 'static_gesture') {
          setStaticSamples((s) => (Number.isInteger(index) ? s.filter((_, i) => i !== index) : []));
          setStep(1);
        } else {
          setDynamicSamples((s) => (Number.isInteger(index) ? s.filter((_, i) => i !== index) : []));
          setStep(2);
        }
      }
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (completed) {
    return (
      <div className="panel narrow center">
        <h2>Registration complete</h2>
        <p>
          {completed.enrollment.staticGesture.samples} gesture captures ({completed.enrollment.staticGesture.handedness} hand)
          and {completed.enrollment.airSignature.samples} air signatures were enrolled.
        </p>
        <button type="button" className="primary" onClick={() => navigate(`/login?username=${encodeURIComponent(username)}`)}>
          Log in now
        </button>
      </div>
    );
  }

  return (
    <div className="panel">
      <h2>Create your AirAuth account</h2>
      <StepIndicator steps={STEPS} current={step} />
      {error && <p className="alert error">{error}</p>}

      {step === 0 && (
        <form className="form narrow" onSubmit={submitAccount}>
          <label>
            Username
            <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. ayesha_k"
                   autoComplete="username" required minLength={3} maxLength={32} />
          </label>
          <label>
            Display name <span className="muted">(optional)</span>
            <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} maxLength={64} />
          </label>
          <button type="submit" className="primary" disabled={busy}>Continue</button>
          <p className="muted">Already registered? <Link to="/login">Log in</Link></p>
        </form>
      )}

      {step === 1 && (
        <div className="step-grid">
          <div className="instructions">
            <h3>Step 1 · Your secret hand gesture</h3>
            <ol>
              <li>Choose a hand pose only you know (e.g. thumb + ring finger up).</li>
              <li>Hold it still in front of the camera when the countdown ends.</li>
              <li>Repeat the <strong>same gesture</strong> {STATIC_GESTURE.enrollSamples} times, lowering your hand in between.</li>
              <li>Always use the same hand.</li>
            </ol>
            <SamplePreview samples={staticSamples} total={STATIC_GESTURE.enrollSamples} kind="static"
                           onRemoveLast={() => setStaticSamples((s) => s.slice(0, -1))} />
            <div className="row">
              <button type="button" onClick={() => setStep(0)}>Back</button>
              <button type="button" className="primary" disabled={staticSamples.length < STATIC_GESTURE.enrollSamples}
                      onClick={() => { setError(''); setStep(2); }}>
                Continue
              </button>
            </div>
          </div>
          <StaticGestureCapture onCapture={addStatic}
                                disabled={staticSamples.length >= STATIC_GESTURE.enrollSamples}
                                buttonLabel={`Capture gesture ${Math.min(staticSamples.length + 1, STATIC_GESTURE.enrollSamples)}/${STATIC_GESTURE.enrollSamples}`} />
        </div>
      )}

      {step === 2 && (
        <div className="step-grid">
          <div className="instructions">
            <h3>Step 2 · Your air signature</h3>
            <ol>
              <li>Point with your index finger and sign in the air, large and natural.</li>
              <li>Recording stops when you hold your finger still for a second.</li>
              <li>Sign the way you always would — speed and rhythm are part of your identity.</li>
              <li>Record {AIR_SIGNATURE.enrollSamples} signatures. More samples = more accurate.</li>
            </ol>
            <SamplePreview samples={dynamicSamples} total={AIR_SIGNATURE.enrollSamples} kind="dynamic"
                           onRemoveLast={() => setDynamicSamples((s) => s.slice(0, -1))} />
            <div className="row">
              <button type="button" onClick={() => setStep(1)}>Back</button>
              <button type="button" className="primary" disabled={dynamicSamples.length < AIR_SIGNATURE.enrollSamples}
                      onClick={() => { setError(''); setStep(3); }}>
                Continue
              </button>
            </div>
          </div>
          <AirSignatureCapture onCapture={addDynamic}
                               disabled={dynamicSamples.length >= AIR_SIGNATURE.enrollSamples}
                               buttonLabel={`Record signature ${Math.min(dynamicSamples.length + 1, AIR_SIGNATURE.enrollSamples)}/${AIR_SIGNATURE.enrollSamples}`} />
        </div>
      )}

      {step === 3 && (
        <div className="narrow">
          <h3>Ready to enroll</h3>
          <ul className="summary">
            <li>Username: <strong>{username}</strong></li>
            <li>Static gesture captures: <strong>{staticSamples.length}</strong></li>
            <li>Air signatures: <strong>{dynamicSamples.length}</strong></li>
          </ul>
          <p className="muted">
            The AI service now extracts key-point features from every capture, checks that they are consistent
            and builds your biometric templates.
          </p>
          <div className="row">
            <button type="button" onClick={() => setStep(2)} disabled={busy}>Back</button>
            <button type="button" className="primary" onClick={submitRegistration} disabled={busy}>
              {busy ? 'Building your profile…' : 'Create account'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * RegisterPage.jsx is the four-step registration wizard:
 *   0 Account        choose a username (checked against the backend)
 *   1 Static gesture capture the secret pose 5 times
 *   2 Air signature  record the air signature 8 times (with thumbnails)
 *   3 Finish         send everything to /api/auth/register
 * If the ML service rejects a specific capture (inconsistent or unusable),
 * that sample is removed and the user is taken back to the matching step to
 * redo it.  A ?username= query (from the login redirect) pre-fills the form.
 * ========================================================================== */
