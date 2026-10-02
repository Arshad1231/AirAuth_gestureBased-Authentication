import { useEffect, useRef, useState } from 'react';

import { CAMERA } from '../config/captureConfig.js';
import { clear, drawHand } from '../lib/canvasDrawing.js';
import { detectHand, loadHandLandmarker } from '../lib/handLandmarker.js';

/**
 * Live webcam view with MediaPipe hand tracking.
 *
 * props
 *   onFrame(frame)            called for every processed video frame with
 *                             { landmarks, handedness, score, timestamp, width, height }
 *   drawOverlay(ctx, frame)   optional extra drawing (e.g. signature ink)
 *   highlightLandmark         landmark index to emphasise (e.g. 8 = index tip)
 *   children                  HUD elements rendered on top of the video
 */
export default function CameraStage({ onFrame, drawOverlay, highlightLandmark = null, children }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const onFrameRef = useRef(onFrame);
  const drawOverlayRef = useRef(drawOverlay);
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  onFrameRef.current = onFrame;
  drawOverlayRef.current = drawOverlay;

  useEffect(() => {
    let cancelled = false;
    let animationId = 0;
    let stream = null;

    async function start() {
      try {
        setStatus('loading');
        const [landmarker, mediaStream] = await Promise.all([
          loadHandLandmarker(),
          navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: CAMERA.width }, height: { ideal: CAMERA.height }, facingMode: 'user' },
            audio: false,
          }),
        ]);

        stream = mediaStream;
        if (cancelled) {
          // Unmounted while starting (e.g. React StrictMode): release the camera.
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        const video = videoRef.current;
        video.srcObject = stream;
        await video.play();

        const canvas = canvasRef.current;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        setStatus('ready');

        let lastVideoTime = -1;

        const tick = () => {
          if (cancelled) return;

          if (video.readyState >= 2 && video.currentTime !== lastVideoTime) {
            lastVideoTime = video.currentTime;
            const now = performance.now();
            const frame = {
              ...detectHand(landmarker, video, now),
              timestamp: now / 1000,
              width: video.videoWidth,
              height: video.videoHeight,
            };

            const ctx = canvas.getContext('2d');
            clear(ctx);
            drawHand(ctx, frame.landmarks, { highlight: highlightLandmark });
            drawOverlayRef.current?.(ctx, frame);
            onFrameRef.current?.(frame);
          }

          animationId = requestAnimationFrame(tick);
        };

        animationId = requestAnimationFrame(tick);
      } catch (err) {
        if (cancelled) return;
        setStatus('error');
        setError(
          err?.name === 'NotAllowedError'
            ? 'Camera permission was denied. Allow camera access and reload the page.'
            : `Could not start the camera / hand tracker: ${err?.message || err}`,
        );
      }
    }

    start();

    return () => {
      cancelled = true;
      cancelAnimationFrame(animationId);
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [highlightLandmark]);

  return (
    <div className="camera-stage">
      <video ref={videoRef} className="mirrored" playsInline muted />
      <canvas ref={canvasRef} className="mirrored" />
      {status === 'loading' && <div className="camera-message">Starting camera and hand tracker…</div>}
      {status === 'error' && <div className="camera-message error">{error}</div>}
      {status === 'ready' && children}
    </div>
  );
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * CameraStage.jsx is the shared webcam + hand-tracking surface.  It loads the
 * MediaPipe hand landmarker and the camera in parallel, mirrors video and
 * overlay canvas for a natural selfie view, runs detection once per new video
 * frame in a requestAnimationFrame loop, draws the hand skeleton (plus any
 * caller overlay such as signature ink) and streams each frame's landmarks to
 * the parent through onFrame.  Callbacks are held in refs so the loop never
 * restarts on re-render; camera tracks are stopped on unmount.
 * ========================================================================== */
