import { Router } from 'express';

import { startLogin, verifyAirSignature, verifyStaticGesture } from '../controllers/loginController.js';
import { checkUser, register } from '../controllers/registrationController.js';
import { authLimiter, verifyLimiter } from '../middleware/rateLimiters.js';

const router = Router();

router.use(authLimiter);

router.post('/check-user', checkUser);
router.post('/register', register);

router.post('/login/start', startLogin);
router.post('/login/static-gesture', verifyLimiter, verifyStaticGesture);
router.post('/login/air-signature', verifyLimiter, verifyAirSignature);

export default router;

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * authRoutes.js mounts the public authentication API under /api/auth:
 *   POST /check-user               is this username registered?
 *   POST /register                 enroll gesture + air signature
 *   POST /login/start              open a login session (Step 1)
 *   POST /login/static-gesture     verify Step 1
 *   POST /login/air-signature      verify Step 2 -> access token
 * All routes are IP rate-limited; the two verification routes more strictly.
 * ========================================================================== */
