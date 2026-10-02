import { Router } from 'express';

import { getHealth } from '../controllers/systemController.js';

const router = Router();

router.get('/health', getHealth);

export default router;

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * systemRoutes.js mounts GET /api/system/health, the combined API / database /
 * ML-service status used by the client's status indicator.
 * ========================================================================== */
