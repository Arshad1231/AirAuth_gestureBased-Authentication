import cors from 'cors';
import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';

import env from './config/env.js';
import { errorHandler, notFound } from './middleware/errorHandler.js';
import authRoutes from './routes/authRoutes.js';
import systemRoutes from './routes/systemRoutes.js';
import userRoutes from './routes/userRoutes.js';

export function createApp() {
  const app = express();

  app.set('trust proxy', 1);

  app.use(helmet());
  app.use(cors({ origin: env.clientOrigin }));
  app.use(express.json({ limit: '5mb' }));
  app.use(morgan(env.nodeEnv === 'production' ? 'combined' : 'dev'));

  app.use('/api/system', systemRoutes);
  app.use('/api/auth', authRoutes);
  app.use('/api/users', userRoutes);

  app.use(notFound);
  app.use(errorHandler);

  return app;
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * app.js builds the Express application: security headers (helmet), CORS for
 * the React client origin, a 5 MB JSON body limit (landmark/trajectory
 * payloads), request logging, the three route groups (/api/system,
 * /api/auth, /api/users) and the 404 + central error handlers.  It is kept
 * separate from server.js so it can be imported by tests without listening.
 * ========================================================================== */
