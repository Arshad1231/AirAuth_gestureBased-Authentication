import dotenv from 'dotenv';

dotenv.config();

const number = (value, fallback) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const env = {
  port: number(process.env.PORT, 5000),
  nodeEnv: process.env.NODE_ENV || 'development',

  mongodbUri: process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/airauth',

  jwtSecret: process.env.JWT_SECRET || 'dev-only-secret-change-me',
  jwtExpiresIn: process.env.JWT_EXPIRES_IN || '1h',

  mlServiceUrl: (process.env.ML_SERVICE_URL || 'http://127.0.0.1:8000').replace(/\/$/, ''),
  mlServiceApiKey: process.env.ML_SERVICE_API_KEY || 'dev-ml-service-key',
  mlServiceTimeoutMs: number(process.env.ML_SERVICE_TIMEOUT_MS, 30000),

  clientOrigin: process.env.CLIENT_ORIGIN || 'http://localhost:5173',

  loginSessionMinutes: number(process.env.LOGIN_SESSION_MINUTES, 5),
  maxAttemptsPerStep: number(process.env.MAX_ATTEMPTS_PER_STEP, 3),
  lockoutThreshold: number(process.env.LOCKOUT_THRESHOLD, 5),
  lockoutMinutes: number(process.env.LOCKOUT_MINUTES, 15),

  storeRawSamples: (process.env.STORE_RAW_SAMPLES || 'true') === 'true',
};

if (env.nodeEnv === 'production' && env.jwtSecret === 'dev-only-secret-change-me') {
  throw new Error('JWT_SECRET must be set in production.');
}

export default env;

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * env.js loads server/.env with dotenv and exposes one typed, defaulted config
 * object (port, MongoDB URI, JWT settings, ML service URL/key/timeout, CORS
 * origin, login-security policy, raw-sample storage flag).  It refuses to
 * start in production with the default JWT secret.
 * ========================================================================== */
