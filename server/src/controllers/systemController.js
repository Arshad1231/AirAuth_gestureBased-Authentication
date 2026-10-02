import { databaseState } from '../config/database.js';
import { mlService } from '../services/mlServiceClient.js';
import asyncHandler from '../utils/asyncHandler.js';

/** GET /api/system/health */
export const getHealth = asyncHandler(async (req, res) => {
  let ml;
  try {
    ml = await mlService.health();
  } catch (error) {
    ml = { status: 'unavailable', error: error.message };
  }

  res.json({
    api: 'ok',
    database: databaseState(),
    mlService: ml,
  });
});

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * systemController.js reports the health of all three tiers for the UI's
 * status panel: the API itself, the MongoDB connection state and the ML
 * service (/health: loaded models, versions, thresholds, enrollment counts).
 * ========================================================================== */
