import BiometricProfile from '../models/BiometricProfile.js';
import User from '../models/User.js';
import { storeSamples } from '../services/biometricSampleStore.js';
import { mlService } from '../services/mlServiceClient.js';
import AppError from '../utils/AppError.js';
import asyncHandler from '../utils/asyncHandler.js';
import { normaliseUsername, requireArray } from '../utils/validators.js';

/**
 * POST /api/auth/check-user   { username }
 * Tells the client whether to start the login flow or the registration flow.
 */
export const checkUser = asyncHandler(async (req, res) => {
  const username = normaliseUsername(req.body.username);
  const user = await User.findOne({ username });

  if (!user) {
    return res.json({ username, registered: false });
  }

  const hasProfile = await BiometricProfile.exists({ user: user._id });

  return res.json({
    username,
    registered: Boolean(hasProfile),
    displayName: user.displayName || user.username,
    locked: user.isLocked(),
  });
});

/**
 * POST /api/auth/register
 * { username, displayName, staticSamples: [...], dynamicSamples: [...] }
 *
 * 1. validate input / username availability
 * 2. ML: build static-gesture template      (Step 1 factor)
 * 3. ML: build air-signature template       (Step 2 factor)
 * 4. save User + BiometricProfile (+ raw samples for research)
 */
export const register = asyncHandler(async (req, res) => {
  const username = normaliseUsername(req.body.username);
  const displayName = String(req.body.displayName || '').trim().slice(0, 64) || username;
  const staticSamples = requireArray(req.body.staticSamples, 'staticSamples', { min: 3, max: 15 });
  const dynamicSamples = requireArray(req.body.dynamicSamples, 'dynamicSamples', { min: 3, max: 25 });

  const existing = await User.findOne({ username });
  if (existing && (await BiometricProfile.exists({ user: existing._id }))) {
    throw new AppError(409, 'USERNAME_TAKEN', 'This username is already registered. Please log in.');
  }

  const enrollStep = async (step, call) => {
    try {
      return await call();
    } catch (error) {
      if (error instanceof AppError && error.code === 'CAPTURE_REJECTED') {
        error.details = { ...error.details, step };
      }
      throw error;
    }
  };

  const staticEnrollment = await enrollStep('static_gesture', () =>
    mlService.enrollStaticGesture(staticSamples));
  const dynamicEnrollment = await enrollStep('dynamic_signature', () =>
    mlService.enrollAirSignature(dynamicSamples));

  const user = existing || (await User.create({ username, displayName }));

  try {
    await BiometricProfile.create({
      user: user._id,
      staticTemplate: staticEnrollment.template,
      dynamicTemplate: dynamicEnrollment.template,
      staticHandedness: staticEnrollment.template.handedness,
      staticFeatureVersion: staticEnrollment.template.feature_version,
      dynamicFeatureVersion: dynamicEnrollment.template.feature_version,
      enrollmentReport: { static: staticEnrollment.report, dynamic: dynamicEnrollment.report },
    });
  } catch (error) {
    if (!existing) await User.deleteOne({ _id: user._id });
    throw error;
  }

  await storeSamples(user._id, 'static', 'enrollment', staticSamples);
  await storeSamples(user._id, 'dynamic', 'enrollment', dynamicSamples);

  res.status(201).json({
    message: 'Registration complete. You can now log in with your gesture and air signature.',
    user: user.toPublicJSON(),
    enrollment: {
      staticGesture: {
        samples: staticEnrollment.report.samples,
        handedness: staticEnrollment.report.handedness,
      },
      airSignature: {
        samples: dynamicEnrollment.report.samples,
        meanDuration: dynamicEnrollment.report.mean_duration,
      },
    },
  });
});

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * registrationController.js handles new users.
 *   checkUser  - reports whether a username is registered, so the client can
 *                route an unknown user to registration automatically.
 *   register   - validates the request, asks the ML service to build the
 *                static-gesture and air-signature templates (tagging any
 *                rejected capture with the step it belongs to so the UI can
 *                ask for that sample again), then stores the User and
 *                BiometricProfile atomically-enough (user removed if the
 *                profile cannot be saved) and keeps the raw captures for
 *                research if enabled.
 * ========================================================================== */
