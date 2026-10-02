import env from '../config/env.js';
import BiometricSample from '../models/BiometricSample.js';

/**
 * Persist raw captures for future retraining (only when STORE_RAW_SAMPLES=true).
 * Failures are logged but never break registration or login.
 */
export async function storeSamples(userId, kind, purpose, samples, outcome = {}) {
  if (!env.storeRawSamples || !samples?.length) return;

  try {
    await BiometricSample.insertMany(
      samples.map((sample) => ({
        user: userId,
        kind,
        purpose,
        accepted: outcome.accepted ?? null,
        score: outcome.score ?? null,
        sample,
      })),
    );
  } catch (error) {
    console.warn('[samples] could not store raw samples:', error.message);
  }
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * biometricSampleStore.js saves raw static-gesture / air-signature captures
 * with their purpose (enrollment or login) and outcome into the
 * BiometricSample collection when research storage is enabled.  Storage is
 * best-effort so it can never block a user from registering or logging in.
 * ========================================================================== */
