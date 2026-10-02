import { Router } from 'express';

import { deleteMe, getMe, getMyAttempts } from '../controllers/userController.js';
import requireAuth from '../middleware/requireAuth.js';

const router = Router();

router.use(requireAuth);

router.get('/me', getMe);
router.get('/me/attempts', getMyAttempts);
router.delete('/me', deleteMe);

export default router;

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * userRoutes.js mounts the protected dashboard API under /api/users (Bearer
 * token required): profile summary, authentication history and account /
 * biometric-data deletion.
 * ========================================================================== */
