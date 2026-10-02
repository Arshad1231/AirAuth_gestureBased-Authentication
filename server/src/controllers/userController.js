import AuthAttempt from '../models/AuthAttempt.js';
import BiometricProfile from '../models/BiometricProfile.js';
import BiometricSample from '../models/BiometricSample.js';
import LoginSession from '../models/LoginSession.js';
import User from '../models/User.js';
import asyncHandler from '../utils/asyncHandler.js';

/** GET /api/users/me */
export const getMe = asyncHandler(async (req, res) => {
  const profile = await BiometricProfile.findOne({ user: req.user._id });

  res.json({
    user: req.user.toPublicJSON(),
    biometricProfile: profile ? profile.toSummaryJSON() : null,
  });
});

/** GET /api/users/me/attempts?limit=20 */
export const getMyAttempts = asyncHandler(async (req, res) => {
  const limit = Math.min(Math.max(Number(req.query.limit) || 20, 1), 100);

  const attempts = await AuthAttempt.find({ user: req.user._id })
    .sort({ createdAt: -1 })
    .limit(limit);

  res.json({ attempts: attempts.map((attempt) => attempt.toPublicJSON()) });
});

/** DELETE /api/users/me — remove the account and ALL biometric data. */
export const deleteMe = asyncHandler(async (req, res) => {
  const userId = req.user._id;

  await Promise.all([
    BiometricProfile.deleteMany({ user: userId }),
    BiometricSample.deleteMany({ user: userId }),
    AuthAttempt.deleteMany({ user: userId }),
    LoginSession.deleteMany({ user: userId }),
  ]);
  await User.deleteOne({ _id: userId });

  res.json({ message: 'Your account and all biometric data were deleted.' });
});

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * userController.js serves the authenticated dashboard: the user's public
 * profile with a biometric-profile summary (no templates), their recent
 * authentication attempts, and a "delete my data" endpoint that removes the
 * account together with templates, raw samples, logs and open sessions.
 * ========================================================================== */
