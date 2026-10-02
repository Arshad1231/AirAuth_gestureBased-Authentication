const asyncHandler = (handler) => (req, res, next) =>
  Promise.resolve(handler(req, res, next)).catch(next);

export default asyncHandler;

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * asyncHandler.js wraps async Express route handlers so a rejected promise is
 * forwarded to the central error handler instead of crashing the process
 * (Express 4 does not do this by itself).
 * ========================================================================== */
