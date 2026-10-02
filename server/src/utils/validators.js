import AppError from './AppError.js';

const USERNAME_PATTERN = /^[a-z0-9_.-]{3,32}$/;

export function normaliseUsername(value) {
  const username = String(value || '').trim().toLowerCase();

  if (!USERNAME_PATTERN.test(username)) {
    throw new AppError(
      400,
      'INVALID_USERNAME',
      'Username must be 3-32 characters: letters, numbers, dot, dash or underscore.',
    );
  }

  return username;
}

export function requireArray(value, name, { min = 1, max = 50 } = {}) {
  if (!Array.isArray(value) || value.length < min || value.length > max) {
    throw new AppError(400, 'INVALID_PAYLOAD', `${name} must be an array of ${min}-${max} items.`);
  }
  return value;
}

export function requireObject(value, name) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new AppError(400, 'INVALID_PAYLOAD', `${name} is required.`);
  }
  return value;
}

export function requireString(value, name) {
  if (typeof value !== 'string' || !value) {
    throw new AppError(400, 'INVALID_PAYLOAD', `${name} is required.`);
  }
  return value;
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * validators.js contains small request-validation helpers: username
 * normalisation (lower-case, 3-32 safe characters) and presence/shape checks
 * for arrays, objects and strings.  Detailed biometric validation is done by
 * the ML service; these only reject obviously malformed requests early.
 * ========================================================================== */
