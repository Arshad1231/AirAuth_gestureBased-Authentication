import { useCallback, useEffect, useRef, useState } from 'react';

import { STATIC_GESTURE } from '../config/captureConfig.js';
import CameraStage from './CameraStage.jsx';

/**
 * Step 1 capture: the user holds a static hand gesture; after a countdown
 * the component collects N frames of landmarks and returns one sample:
 *   { frames: [{ landmarks, handedness, score }], width, height }
 */
export default function StaticGestureCapture({ onCapture, disabled = false, buttonLabel = 'Capture gesture' }) {
  const [phase, setPhase] = useState('idle'); // idle | countdown | collecting
  const [countdown, setCountdown] = useState(0);
  const [handVisible, setHandVisible] = useState(false);
  const [message, setMessage] = useState('');
  const [progress, setProgress] = useState(0);

  const phaseRef = useRef('idle');
  const framesRef = useRef([]);
  const sizeRef = useRef({ width: 0, height: 0 });
  const collectStartRef = useRef(0);
  const handVisibleRef = useRef(false);

  const setPhaseBoth = (next) => {
    phaseRef.current = next;
    setPhase(next);
  };

  const begin = useCallback(() => {
    if (disabled || phaseRef.current !== 'idle') return;
    setMessage('');
    setCountdown(STATIC_GESTURE.countdownSeconds);
    setPhaseBoth('countdown');
  }, [disabled]);

  // Countdown timer
  useEffect(() => {
    if (phase !== 'countdown') return undefined;
    if (countdown <= 0) {
      framesRef.current = [];
      collectStartRef.current = performance.now();
      setProgress(0);
      setPhaseBoth('collecting');
      return undefined;
    }
    const timer = setTimeout(() => setCountdown((value) => value - 1), 1000);
    return () => clearTimeout(timer);
  }, [phase, countdown]);

  const handleFrame = useCallback(
    (frame) => {
      const visible = Boolean(frame.landmarks);
      if (visible !== handVisibleRef.current) {
        handVisibleRef.current = visible;
        setHandVisible(visible);
      }

      if (phaseRef.current !== 'collecting') return;

      sizeRef.current = { width: frame.width, height: frame.height };

      if (frame.landmarks) {
        framesRef.current.push({
          landmarks: frame.landmarks,
          handedness: frame.handedness,
          score: frame.score,
        });
        setProgress(framesRef.current.length / STATIC_GESTURE.framesPerCapture);
      }

      if (framesRef.current.length >= STATIC_GESTURE.framesPerCapture) {
        setPhaseBoth('idle');
        onCapture({ frames: framesRef.current, ...sizeRef.current });
        return;
      }

      if (performance.now() - collectStartRef.current > STATIC_GESTURE.collectTimeoutMs) {
        setPhaseBoth('idle');
        setMessage('Your hand was not visible long enough. Keep it inside the frame and try again.');
      }
    },
    [onCapture],
  );

  return (
    <div className="capture">
      <CameraStage onFrame={handleFrame}>
        <div className="hud">
          <span className={`pill ${handVisible ? 'ok' : 'warn'}`}>
            {handVisible ? 'Hand detected' : 'Show your hand'}
          </span>
          {phase === 'countdown' && <div className="countdown">{countdown || 'Hold!'}</div>}
          {phase === 'collecting' && (
            <div className="hud-bottom">
              <div className="meter"><div style={{ width: `${Math.round(progress * 100)}%` }} /></div>
              <span>Hold still…</span>
            </div>
          )}
        </div>
      </CameraStage>

      <div className="capture-actions">
        <button type="button" className="primary" onClick={begin} disabled={disabled || phase !== 'idle'}>
          {phase === 'idle' ? buttonLabel : 'Capturing…'}
        </button>
        {message && <p className="hint error">{message}</p>}
      </div>
    </div>
  );
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * StaticGestureCapture.jsx is the Step-1 capture widget.  It shows the camera
 * with a "hand detected" indicator, runs a short countdown so the user can
 * form the gesture, then collects 15 frames of 21 hand landmarks while the
 * pose is held (with a progress meter and timeout) and passes the resulting
 * sample to onCapture.  Used both for registration (5 captures) and login
 * (1 capture).
 * ========================================================================== */
