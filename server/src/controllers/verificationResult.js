/**
 * Reduce an ML verification result to what the browser may see.
 * Templates (including template_update) and raw distances never leave
 * the server.
 */
export function toPublicResult(result) {
  const components = {};
  for (const [name, value] of Object.entries(result.components || {})) {
    components[name] = value.normalised;
  }

  return {
    step: result.step,
    accepted: Boolean(result.accepted),
    reason: result.reason,
    score: result.score,
    threshold: result.threshold,
    matchPercent: result.match_percent,
    components,
    quality: result.quality,
  };
}

export const REASON_MESSAGES = {
  match: 'Verified.',
  gesture_mismatch: 'The hand gesture did not match your registered gesture.',
  wrong_hand: 'Use the same hand you registered with.',
  signature_mismatch: 'The air signature did not match your registered signature.',
  replay_suspected: 'This capture looks like a replay of stored data and was rejected.',
};

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * verificationResult.js converts the ML service's verification response into
 * the public shape returned to the React client (decision, reason, fused
 * score, threshold, match %, normalised component scores, capture quality),
 * deliberately dropping templates and raw distances.  REASON_MESSAGES maps
 * each decision reason to a user-facing explanation.
 * ========================================================================== */
