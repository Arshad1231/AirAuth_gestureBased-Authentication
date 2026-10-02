import { apiRequest } from './apiClient.js';

export const authApi = {
  systemHealth: () => apiRequest('/api/system/health'),

  checkUser: (username) => apiRequest('/api/auth/check-user', { method: 'POST', body: { username } }),

  register: ({ username, displayName, staticSamples, dynamicSamples }) =>
    apiRequest('/api/auth/register', {
      method: 'POST',
      body: { username, displayName, staticSamples, dynamicSamples },
    }),

  startLogin: (username) => apiRequest('/api/auth/login/start', { method: 'POST', body: { username } }),

  verifyStaticGesture: (loginSessionId, sample) =>
    apiRequest('/api/auth/login/static-gesture', { method: 'POST', body: { loginSessionId, sample } }),

  verifyAirSignature: (loginSessionId, sample) =>
    apiRequest('/api/auth/login/air-signature', { method: 'POST', body: { loginSessionId, sample } }),

  me: (token) => apiRequest('/api/users/me', { token }),
  myAttempts: (token, limit = 20) => apiRequest(`/api/users/me/attempts?limit=${limit}`, { token }),
  deleteMe: (token) => apiRequest('/api/users/me', { method: 'DELETE', token }),
};

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * authApi.js lists every backend endpoint the React app uses: system health,
 * username check, registration, the three login calls (start, Step 1 static
 * gesture, Step 2 air signature) and the protected dashboard calls (profile,
 * attempt history, delete account).
 * ========================================================================== */
