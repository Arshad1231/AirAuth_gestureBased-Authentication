import AppError from '../utils/AppError.js';

export function notFound(req, res) {
  res.status(404).json({ error: { code: 'NOT_FOUND', message: `No route for ${req.method} ${req.path}` } });
}

// eslint-disable-next-line no-unused-vars
export function errorHandler(error, req, res, next) {
  if (error instanceof AppError) {
    return res.status(error.status).json({
      error: { code: error.code, message: error.message, details: error.details },
    });
  }

  if (error.type === 'entity.too.large') {
    return res.status(413).json({ error: { code: 'PAYLOAD_TOO_LARGE', message: 'Request is too large.' } });
  }

  if (error instanceof SyntaxError && 'body' in error) {
    return res.status(400).json({ error: { code: 'INVALID_JSON', message: 'Malformed JSON body.' } });
  }

  if (error.code === 11000) {
    return res.status(409).json({ error: { code: 'DUPLICATE', message: 'That record already exists.' } });
  }

  console.error('[error]', error);
  return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Unexpected server error.' } });
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * errorHandler.js turns every failure into the API's uniform error shape
 * { error: { code, message, details } }: AppErrors keep their status/code,
 * oversized and malformed JSON bodies get 413/400, Mongo duplicate keys get
 * 409 and anything unexpected is logged and returned as a generic 500.
 * notFound() handles unknown routes.
 * ========================================================================== */
