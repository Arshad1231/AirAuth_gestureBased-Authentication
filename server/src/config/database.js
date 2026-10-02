import mongoose from 'mongoose';

import env from './env.js';

export async function connectDatabase() {
  mongoose.set('strictQuery', true);

  await mongoose.connect(env.mongodbUri, {
    serverSelectionTimeoutMS: 8000,
  });

  console.log(`[db] connected to ${mongoose.connection.host}/${mongoose.connection.name}`);

  return mongoose.connection;
}

export function databaseState() {
  const states = ['disconnected', 'connected', 'connecting', 'disconnecting'];
  return states[mongoose.connection.readyState] || 'unknown';
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * database.js opens the Mongoose connection to MongoDB (failing fast after
 * 8 s if the server is unreachable) and reports the connection state for the
 * system health endpoint.
 * ========================================================================== */
