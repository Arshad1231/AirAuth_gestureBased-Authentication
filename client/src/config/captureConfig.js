// Must match the version in package.json (WASM runtime is loaded from the CDN).
const TASKS_VISION_VERSION = '0.10.14';

export const MEDIAPIPE = {
  wasmUrl: `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${TASKS_VISION_VERSION}/wasm`,
  modelUrl:
    'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
  minConfidence: 0.6,
};

export const CAMERA = { width: 1280, height: 720 };

export const STATIC_GESTURE = {
  enrollSamples: 5,        // captures of the same gesture at registration
  framesPerCapture: 15,    // hand frames averaged into one capture
  countdownSeconds: 3,
  collectTimeoutMs: 4000,
};

export const AIR_SIGNATURE = {
  enrollSamples: 8,        // research data: 5 -> EER ~18 %, 10 -> ~8 %
  countdownSeconds: 3,
  maxSeconds: 12,
  minSeconds: 0.8,
  stillRadius: 0.012,      // normalised image units
  stillSeconds: 1.0,       // auto-stop after the finger rests this long
  lostHandSeconds: 0.7,    // auto-stop if the hand disappears after drawing
};

export const INDEX_FINGER_TIP = 8;

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * captureConfig.js holds every client-side capture parameter in one place:
 * MediaPipe WASM/model URLs, camera resolution, how many static-gesture and
 * air-signature samples registration collects, frames per gesture capture,
 * countdowns and the auto-stop rules for air signatures (finger still / hand
 * lost / time limit).
 * ========================================================================== */
