import env from '../config/env.js';
import AppError from '../utils/AppError.js';

async function request(method, path, body) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), env.mlServiceTimeoutMs);

  let response;
  try {
    response = await fetch(`${env.mlServiceUrl}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', 'X-Service-Key': env.mlServiceApiKey },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (error) {
    throw new AppError(
      503,
      'ML_SERVICE_UNAVAILABLE',
      'The biometric verification service is not reachable. Is ml-service running?',
      { cause: error.name === 'AbortError' ? 'timeout' : error.message },
    );
  } finally {
    clearTimeout(timeout);
  }

  const payload = await response.json().catch(() => ({}));

  if (response.status === 422 && payload.error) {
    // The capture itself was unusable (too short, hand moved, ...): ask the user to retry.
    throw new AppError(422, 'CAPTURE_REJECTED', payload.error.message, {
      mlCode: payload.error.code,
      ...payload.error.details,
    });
  }

  if (!response.ok) {
    throw new AppError(502, 'ML_SERVICE_ERROR', 'The biometric service returned an error.', {
      status: response.status,
      detail: payload.detail,
    });
  }

  return payload;
}

export const mlService = {
  health: () => request('GET', '/health'),

  enrollStaticGesture: (samples) => request('POST', '/static/enroll', { samples }),
  verifyStaticGesture: (template, sample) => request('POST', '/static/verify', { template, sample }),

  enrollAirSignature: (samples) => request('POST', '/dynamic/enroll', { samples }),
  verifyAirSignature: (template, sample) => request('POST', '/dynamic/verify', { template, sample }),
};

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * mlServiceClient.js is the only code that talks to the Python ML service.
 * It sends JSON with the shared X-Service-Key, enforces a timeout and maps
 * failures to AppErrors: unreachable -> 503 ML_SERVICE_UNAVAILABLE, unusable
 * capture (ML 422) -> 422 CAPTURE_REJECTED with the ML message/details, any
 * other error -> 502.  mlService exposes health, enroll and verify calls for
 * both authentication steps.
 * ========================================================================== */
