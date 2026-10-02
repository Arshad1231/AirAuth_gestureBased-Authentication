import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Forward API calls to the Express backend during development.
      '/api': 'http://localhost:5000',
    },
  },
});

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * vite.config.js configures the Vite dev server for the React client on port
 * 5173 and proxies every /api request to the Express backend on port 5000, so
 * the browser talks to a single origin during development (no CORS issues,
 * and camera access works on localhost).
 * ========================================================================== */
