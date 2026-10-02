import crypto from 'node:crypto';

import jwt from 'jsonwebtoken';

import env from '../config/env.js';

export function issueAccessToken(user) {
  return jwt.sign(
    { sub: user._id.toString(), username: user.username, amr: ['static_gesture', 'air_signature'] },
    env.jwtSecret,
    { expiresIn: env.jwtExpiresIn, issuer: 'airauth' },
  );
}

export function verifyAccessToken(token) {
  return jwt.verify(token, env.jwtSecret, { issuer: 'airauth' });
}

export function createOpaqueToken() {
  const token = crypto.randomBytes(32).toString('hex');
  return { token, tokenHash: hashToken(token) };
}

export function hashToken(token) {
  return crypto.createHash('sha256').update(String(token)).digest('hex');
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * tokenService.js handles all tokens:
 *   issueAccessToken / verifyAccessToken  JWT issued only after BOTH steps
 *                                         pass (amr claim lists the factors)
 *   createOpaqueToken / hashToken         random login-session tokens; only
 *                                         the SHA-256 hash is stored in Mongo
 * ========================================================================== */
