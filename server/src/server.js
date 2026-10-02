import { createApp } from './app.js';
import { connectDatabase } from './config/database.js';
import env from './config/env.js';

async function start() {
  try {
    await connectDatabase();
  } catch (error) {
    console.error(`[db] could not connect to ${env.mongodbUri}: ${error.message}`);
    console.error('[db] start MongoDB (see README) and try again.');
    process.exit(1);
  }

  const app = createApp();

  app.listen(env.port, () => {
    console.log(`[api] AirAuth API listening on http://localhost:${env.port}`);
    console.log(`[api] ML service expected at ${env.mlServiceUrl}`);
  });
}

start();

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * server.js is the backend entry point (npm start / npm run dev): it connects
 * to MongoDB, exits with a helpful message if that fails, then starts the
 * Express app on PORT and logs where the ML service is expected.
 * ========================================================================== */
