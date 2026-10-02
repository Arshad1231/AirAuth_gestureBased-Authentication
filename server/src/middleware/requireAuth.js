import User from '../models/User.js';
import { verifyAccessToken } from '../services/tokenService.js';
import AppError from '../utils/AppError.js';
import asyncHandler from '../utils/asyncHandler.js';

const requireAuth = asyncHandler(async (req, res, next) => {
  const header = req.get('authorization') || '';
  const [scheme, token] = header.split(' ');

  if (scheme !== 'Bearer' || !token) {
    throw new AppError(401, 'UNAUTHENTICATED', 'Please log in.');
  }

  let payload;
  try {
    payload = verifyAccessToken(token);
  } catch {
    throw new AppError(401, 'TOKEN_INVALID', 'Your session has expired. Please log in again.');
  }

  const user = await User.findById(payload.sub);
  if (!user || user.status !== 'active') {
    throw new AppError(401, 'UNAUTHENTICATED', 'Account not available.');
  }

  req.user = user;
  next();
});

export default requireAuth;

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * requireAuth.js protects routes that need a fully authenticated user (both
 * steps passed).  It validates the Bearer access token, loads the user and
 * attaches it as req.user; otherwise it responds 401.
 * ========================================================================== */
