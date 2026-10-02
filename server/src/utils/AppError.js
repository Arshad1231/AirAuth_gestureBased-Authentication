export default class AppError extends Error {
  constructor(status, code, message, details = undefined) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * AppError.js is the single error type thrown by controllers and services.
 * It carries an HTTP status, a stable machine-readable code (e.g.
 * USER_NOT_REGISTERED, ACCOUNT_LOCKED, CAPTURE_REJECTED) used by the React
 * client to decide what to show, a human message and optional details.
 * ========================================================================== */
