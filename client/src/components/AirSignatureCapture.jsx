import { useCallback, useEffect, useRef, useState } from 'react';

import { AIR_SIGNATURE, INDEX_FINGER_TIP } from '../config/captureConfig.js';
import { drawTrajectory } from '../lib/canvasDrawing.js';
import CameraStage from './CameraStage.jsx';

const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);

/**
 * Step 2 capture: the user draws their signature in the air with the index
 * fingertip.  Recording stops automatically when the finger rests, the hand
 * leaves the frame, the time limit is reached, or the user presses Done /
 * Space.  Returns one sample: { points: [[t, x, y, z], ...], width, height }.
 */
export default function AirSignatureCapture({
  onCapture,
  disabled = false,
  autoSubmit = false,
  buttonLabel = 'Start drawing',
}) {
  const [phase, setPhase] = useState('idle'); // idle | countdown | recording | review
  const [countdown, setCountdown] = useState(0);
  const [handVisible, setHandVisible] = useState(false);
  const [message, setMessage] = useState('');
  const [elapsed, setElapsed] = useState(0);

  const phaseRef = useRef('idle');
  const pointsRef = useRef([]);
  const sizeRef = useRef({ width: 0, height: 0 });
  const trackRef = useRef({});
  const handVisibleRef = useRef(false);

  const setPhaseBoth = (next) => {
    phaseRef.current = next;
    setPhase(next);
  };

  const finishRecording = useCallback(
    (reason) => {
      if (phaseRef.current !== 'recording') return;

      const points = pointsRef.current;
      const duration = points.length ? points[points.length - 1][0] : 0;

      if (points.length < 15 || duration < AIR_SIGNATURE.minSeconds || !trackRef.current.moved) {
        setPhaseBoth('idle');
        setMessage('The signature was too short. Press start and draw your full signature.');
        return;
      }

      const sample = { points, ...sizeRef.current };

      if (autoSubmit) {
        setPhaseBoth('idle');
        onCapture(sample);
      } else {
        setPhaseBoth('review');
        setMessage(reason === 'timeout' ? 'Time limit reached.' : '');
      }
    },
    [autoSubmit, onCapture],
  );

  const begin = useCallback(() => {
    if (disabled || phaseRef.current !== 'idle') return;
    pointsRef.current = [];
    setMessage('');
    setCountdown(AIR_SIGNATURE.countdownSeconds);
    setPhaseBoth('countdown');
  }, [disabled]);

  // Countdown
  useEffect(() => {
    if (phase !== 'countdown') return undefined;
    if (countdown <= 0) {
      pointsRef.current = [];
      trackRef.current = { start: null, lastSeen: null, anchor: null, anchorTime: null, path: 0, moved: false };
      setElapsed(0);
      setPhaseBoth('recording');
      return undefined;
    }
    const timer = setTimeout(() => setCountdown((value) => value - 1), 1000);
    return () => clearTimeout(timer);
  }, [phase, countdown]);

  // Space bar: start / stop
  useEffect(() => {
    const onKey = (event) => {
      if (event.code !== 'Space' || event.target.tagName === 'INPUT') return;
      event.preventDefault();
      if (phaseRef.current === 'idle') begin();
      else if (phaseRef.current === 'recording') finishRecording('manual');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [begin, finishRecording]);

  const handleFrame = useCallback(
    (frame) => {
      const visible = Boolean(frame.landmarks);
      if (visible !== handVisibleRef.current) {
        handVisibleRef.current = visible;
        setHandVisible(visible);
      }

      if (phaseRef.current !== 'recording') return;

      const track = trackRef.current;
      const now = frame.timestamp;
      sizeRef.current = { width: frame.width, height: frame.height };
      if (track.start === null) track.start = now;
      const t = now - track.start;

      if (frame.landmarks) {
        const tip = frame.landmarks[INDEX_FINGER_TIP];
        const previous = pointsRef.current[pointsRef.current.length - 1];
        if (previous) track.path += distance([previous[1], previous[2]], tip);
        if (track.path > 0.05) track.moved = true;

        pointsRef.current.push([Number(t.toFixed(4)), tip[0], tip[1], tip[2]]);
        track.lastSeen = t;

        if (!track.anchor || distance(track.anchor, tip) > AIR_SIGNATURE.stillRadius) {
          track.anchor = tip;
          track.anchorTime = t;
        }
      }

      setElapsed(t);

      const restedTooLong = track.moved && track.anchorTime !== null
        && t - track.anchorTime > AIR_SIGNATURE.stillSeconds && t > AIR_SIGNATURE.minSeconds;
      const handLost = track.moved && track.lastSeen !== null && t - track.lastSeen > AIR_SIGNATURE.lostHandSeconds;

      if (restedTooLong || handLost) finishRecording('auto');
      else if (t > AIR_SIGNATURE.maxSeconds) finishRecording('timeout');
    },
    [finishRecording],
  );

  const drawOverlay = useCallback((ctx) => {
    if (phaseRef.current === 'recording' || phaseRef.current === 'review') {
      drawTrajectory(ctx, pointsRef.current);
    }
  }, []);

  const accept = () => {
    setPhaseBoth('idle');
    onCapture({ points: pointsRef.current, ...sizeRef.current });
  };

  return (
    <div className="capture">
      <CameraStage onFrame={handleFrame} drawOverlay={drawOverlay} highlightLandmark={INDEX_FINGER_TIP}>
        <div className="hud">
          <span className={`pill ${handVisible ? 'ok' : 'warn'}`}>
            {handVisible ? 'Index finger tracked' : 'Show your hand'}
          </span>
          {phase === 'countdown' && <div className="countdown">{countdown || 'Draw!'}</div>}
          {phase === 'recording' && (
            <div className="hud-bottom">
              <span className="recording-dot" /> Recording {elapsed.toFixed(1)}s — rest your finger to finish
            </div>
          )}
        </div>
      </CameraStage>

      <div className="capture-actions">
        {phase === 'review' ? (
          <>
            <button type="button" className="primary" onClick={accept} disabled={disabled}>
              Use this signature
            </button>
            <button type="button" onClick={() => { setPhaseBoth('idle'); setMessage(''); }}>
              Redo
            </button>
          </>
        ) : phase === 'recording' ? (
          <button type="button" className="primary" onClick={() => finishRecording('manual')}>
            Done (Space)
          </button>
        ) : (
          <button type="button" className="primary" onClick={begin} disabled={disabled || phase !== 'idle'}>
            {phase === 'idle' ? `${buttonLabel} (Space)` : 'Get ready…'}
          </button>
        )}
        {message && <p className="hint">{message}</p>}
      </div>
    </div>
  );
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * AirSignatureCapture.jsx is the Step-2 capture widget.  After a countdown it
 * records the index-fingertip (landmark 8) position and timestamp for every
 * frame, drawing the live ink trail on the camera overlay.  Recording ends
 * automatically when the finger rests for ~1 s, the hand leaves the frame
 * after drawing, or 12 s pass - or manually via the Done button / Space bar.
 * Too-short attempts are rejected locally.  In review mode the user can keep
 * or redo the signature; with autoSubmit (login) it is sent immediately.
 * ========================================================================== */
