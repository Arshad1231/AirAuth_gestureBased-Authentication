import env from '../config/env.js';
import AuthAttempt from '../models/AuthAttempt.js';
import BiometricProfile from '../models/BiometricProfile.js';
import LoginSession from '../models/LoginSession.js';
import User from '../models/User.js';
import { storeSamples } from '../services/biometricSampleStore.js';
import { mlService } from '../services/mlServiceClient.js';
import { createOpaqueToken, hashToken, issueAccessToken } from '../services/tokenService.js';
import AppError from '../utils/AppError.js';
import asyncHandler from '../utils/asyncHandler.js';
import { normaliseUsername, requireObject, requireString } from '../utils/validators.js';
import { REASON_MESSAGES, toPublicResult } from './verificationResult.js';

const STEP_STATIC = 'static_gesture';
const STEP_DYNAMIC = 'dynamic_signature';

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function lockedError(user) {
  return new AppError(423, 'ACCOUNT_LOCKED', 'Too many failed attempts. The account is temporarily locked.', {
    lockedUntil: user.lockUntil,
  });
}

async function loadSession(req, expectedStage) {
  const token = requireString(req.body.loginSessionId, 'loginSessionId');
  const session = await LoginSession.findOne({ tokenHash: hashToken(token) });

  if (!session || session.expiresAt < new Date()) {
    throw new AppError(401, 'LOGIN_SESSION_EXPIRED', 'Your login session expired. Please start again.');
  }

  if (session.stage !== expectedStage) {
    throw new AppError(409, 'WRONG_STEP', `This login session is waiting for step "${session.stage}".`, {
      expectedStep: session.stage,
    });
  }

  const user = await User.findById(session.user);
  if (!user || user.status !== 'active') {
    await session.deleteOne();
    throw new AppError(401, 'UNAUTHENTICATED', 'Account not available.');
  }

  if (user.isLocked()) {
    await session.deleteOne();
    throw lockedError(user);
  }

  const profile = await BiometricProfile.findOne({ user: user._id });
  if (!profile) {
    throw new AppError(404, 'USER_NOT_REGISTERED', 'No biometric profile found. Please register.');
  }

  return { session, user, profile };
}

async function logAttempt(req, user, step, result) {
  await AuthAttempt.create({
    user: user._id,
    username: user.username,
    step,
    accepted: Boolean(result.accepted),
    reason: result.reason,
    score: result.score,
    threshold: result.threshold,
    matchPercent: result.match_percent,
    modelVersion: result.model_version,
    ip: req.ip,
    userAgent: req.get('user-agent'),
  });
}

/** Count a failed step; lock the account and end the session if limits are hit. */
async function handleFailure(user, session, step) {
  session.attempts[step] += 1;

  user.failedAttempts += 1;
  if (user.failedAttempts >= env.lockoutThreshold) {
    user.lockUntil = new Date(Date.now() + env.lockoutMinutes * 60 * 1000);
    user.failedAttempts = 0;
  }
  await user.save();

  const attemptsRemaining = Math.max(env.maxAttemptsPerStep - session.attempts[step], 0);
  const sessionEnded = attemptsRemaining === 0 || user.isLocked();

  if (sessionEnded) {
    await session.deleteOne();
  } else {
    session.markModified('attempts');
    await session.save();
  }

  return { attemptsRemaining, sessionEnded, locked: user.isLocked(), lockedUntil: user.lockUntil };
}

// ---------------------------------------------------------------------------
// routes
// ---------------------------------------------------------------------------

/**
 * POST /api/auth/login/start   { username }
 * Opens a login session at Step 1.  Unknown users get USER_NOT_REGISTERED so
 * the client can redirect them to registration.
 */
export const startLogin = asyncHandler(async (req, res) => {
  const username = normaliseUsername(req.body.username);
  const user = await User.findOne({ username });

  if (!user || !(await BiometricProfile.exists({ user: user._id }))) {
    throw new AppError(404, 'USER_NOT_REGISTERED', 'This user is not registered yet. Please register first.', {
      username,
    });
  }

  if (user.isLocked()) throw lockedError(user);

  const { token, tokenHash } = createOpaqueToken();
  const expiresAt = new Date(Date.now() + env.loginSessionMinutes * 60 * 1000);

  await LoginSession.create({
    tokenHash,
    user: user._id,
    ip: req.ip,
    userAgent: req.get('user-agent'),
    expiresAt,
  });

  res.json({
    loginSessionId: token,
    nextStep: STEP_STATIC,
    expiresAt,
    displayName: user.displayName || user.username,
    maxAttemptsPerStep: env.maxAttemptsPerStep,
  });
});

/**
 * POST /api/auth/login/static-gesture   { loginSessionId, sample }
 * Step 1: verify the static hand gesture.  Success advances the session.
 */
export const verifyStaticGesture = asyncHandler(async (req, res) => {
  const sample = requireObject(req.body.sample, 'sample');
  const { session, user, profile } = await loadSession(req, STEP_STATIC);

  const result = await mlService.verifyStaticGesture(profile.staticTemplate, sample);

  await logAttempt(req, user, STEP_STATIC, result);
  await storeSamples(user._id, 'static', 'login', [sample], result);

  if (!result.accepted) {
    const failure = await handleFailure(user, session, STEP_STATIC);
    return res.json({
      passed: false,
      message: REASON_MESSAGES[result.reason] || 'Gesture not recognised.',
      result: toPublicResult(result),
      ...failure,
    });
  }

  session.stage = STEP_DYNAMIC;
  session.staticResult = { score: result.score, at: new Date() };
  await session.save();

  return res.json({
    passed: true,
    nextStep: STEP_DYNAMIC,
    message: 'Gesture verified. Now draw your signature in the air.',
    result: toPublicResult(result),
  });
});

/**
 * POST /api/auth/login/air-signature   { loginSessionId, sample }
 * Step 2: verify the air signature.  Only reachable after Step 1 passed.
 * Success issues the access token and adapts the signature template.
 */
export const verifyAirSignature = asyncHandler(async (req, res) => {
  const sample = requireObject(req.body.sample, 'sample');
  const { session, user, profile } = await loadSession(req, STEP_DYNAMIC);

  const result = await mlService.verifyAirSignature(profile.dynamicTemplate, sample);

  await logAttempt(req, user, STEP_DYNAMIC, result);
  await storeSamples(user._id, 'dynamic', 'login', [sample], result);

  if (!result.accepted) {
    const failure = await handleFailure(user, session, STEP_DYNAMIC);
    return res.json({
      passed: false,
      message: REASON_MESSAGES[result.reason] || 'Signature not recognised.',
      result: toPublicResult(result),
      ...failure,
    });
  }

  if (result.template_update) {
    profile.dynamicTemplate = result.template_update;
    profile.dynamicAdaptations += 1;
    profile.markModified('dynamicTemplate');
    await profile.save();
  }

  user.failedAttempts = 0;
  user.lockUntil = null;
  user.lastLoginAt = new Date();
  await user.save();
  await session.deleteOne();

  return res.json({
    passed: true,
    message: 'Access granted.',
    token: issueAccessToken(user),
    user: user.toPublicJSON(),
    result: toPublicResult(result),
  });
});

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * loginController.js implements the two-step login state machine:
 *   startLogin          username -> opaque login-session token at Step 1
 *                       (USER_NOT_REGISTERED for unknown users, 423 if locked)
 *   verifyStaticGesture Step 1: ML verifies the hand gesture against the
 *                       stored template; success moves the session to Step 2
 *   verifyAirSignature  Step 2: only accepted for sessions that passed Step 1;
 *                       success resets counters, applies the ML template
 *                       adaptation, deletes the session and issues the JWT
 * Every attempt is written to AuthAttempt (and raw captures optionally kept).
 * Failures count against per-step attempt limits and a per-account lockout.
 * Unusable captures (ML 422) do not count as failed attempts.
 * ========================================================================== */
