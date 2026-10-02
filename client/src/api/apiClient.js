const BASE_URL = import.meta.env.VITE_API_URL || '';

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details || {};
  }
}

export async function apiRequest(path, { method = 'GET', body, token } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', 'Cannot reach the AirAuth server. Is the backend running?');
  }

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = payload.error || {};
    throw new ApiError(
      response.status,
      error.code || 'HTTP_ERROR',
      error.message || `Request failed (${response.status})`,
      error.details,
    );
  }

  return payload;
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * apiClient.js is the client's single HTTP helper.  It sends JSON (with an
 * optional Bearer token) to the backend - through the Vite /api proxy in
 * development or VITE_API_URL in production - and converts the backend's
 * { error: { code, message, details } } responses and network failures into
 * ApiError objects that pages can branch on by code.
 * ========================================================================== */
