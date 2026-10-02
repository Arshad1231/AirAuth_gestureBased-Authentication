import rateLimit from 'express-rate-limit';

const message = (text) => ({ error: { code: 'RATE_LIMITED', message: text } });

// Registration + login endpoints (per IP).
export const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 100,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  message: message('Too many authentication requests. Try again in a few minutes.'),
});

// Biometric verification is expensive and the main brute-force target.
export const verifyLimiter = rateLimit({
  windowMs: 5 * 60 * 1000,
  limit: 30,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  message: message('Too many verification attempts. Slow down.'),
});

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * rateLimiters.js defines per-IP request limits: a general limit for all
 * /api/auth routes and a stricter one for the two verification endpoints,
 * complementing the per-account lockout implemented in loginController.js.
 * ========================================================================== */
