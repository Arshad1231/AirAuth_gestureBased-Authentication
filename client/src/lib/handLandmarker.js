import { FilesetResolver, HandLandmarker } from '@mediapipe/tasks-vision';

import { MEDIAPIPE } from '../config/captureConfig.js';

let landmarkerPromise = null;

async function create(delegate) {
  const vision = await FilesetResolver.forVisionTasks(MEDIAPIPE.wasmUrl);

  return HandLandmarker.createFromOptions(vision, {
    baseOptions: { modelAssetPath: MEDIAPIPE.modelUrl, delegate },
    runningMode: 'VIDEO',
    numHands: 1,
    minHandDetectionConfidence: MEDIAPIPE.minConfidence,
    minHandPresenceConfidence: MEDIAPIPE.minConfidence,
    minTrackingConfidence: MEDIAPIPE.minConfidence,
  });
}

/** Load the MediaPipe hand landmarker once (GPU, falling back to CPU). */
export function loadHandLandmarker() {
  if (!landmarkerPromise) {
    landmarkerPromise = create('GPU')
      .catch(() => create('CPU'))
      .catch((error) => {
        landmarkerPromise = null;
        throw error;
      });
  }
  return landmarkerPromise;
}

/**
 * Run detection on the current video frame and return a plain object:
 *   { landmarks: [[x,y,z] * 21] | null, handedness, score }
 */
export function detectHand(landmarker, video, timestampMs) {
  const result = landmarker.detectForVideo(video, timestampMs);
  const hand = result.landmarks?.[0];

  if (!hand) return { landmarks: null, handedness: null, score: 0 };

  const category = (result.handedness || result.handednesses)?.[0]?.[0];

  return {
    landmarks: hand.map((point) => [point.x, point.y, point.z]),
    handedness: category?.categoryName || 'Unknown',
    score: category?.score ?? 0,
  };
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * handLandmarker.js wraps MediaPipe Tasks Vision.  loadHandLandmarker() lazily
 * creates a single shared HandLandmarker in VIDEO mode (one hand, GPU with CPU
 * fallback) so every capture component reuses the same model.  detectHand()
 * runs it on a video frame and converts the result into the plain
 * 21 x [x, y, z] + handedness format the backend and ML service expect.
 * ========================================================================== */
