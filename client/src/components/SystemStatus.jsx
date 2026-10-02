import { useEffect, useState } from 'react';

import { authApi } from '../api/authApi.js';

export default function SystemStatus() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    authApi.systemHealth().then(setHealth).catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="status-panel"><span className="dot bad" /> {error}</div>;
  if (!health) return <div className="status-panel muted">Checking system status…</div>;

  const ml = health.mlService || {};
  const models = ml.models || {};
  const modelLabel = (model) =>
    model?.available ? model.version : 'template matching only (model not trained)';

  return (
    <div className="status-panel">
      <div><span className="dot ok" /> API</div>
      <div><span className={`dot ${health.database === 'connected' ? 'ok' : 'bad'}`} /> MongoDB: {health.database}</div>
      <div><span className={`dot ${ml.status === 'ok' ? 'ok' : 'bad'}`} /> ML service: {ml.status || 'unknown'}</div>
      {ml.status === 'ok' && (
        <>
          <div className="muted">Step 1 model: {modelLabel(models.static_gesture)}</div>
          <div className="muted">Step 2 model: {modelLabel(models.dynamic_signature)}</div>
        </>
      )}
    </div>
  );
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * SystemStatus.jsx calls /api/system/health once and shows whether the API,
 * MongoDB and the ML service are up, plus which neural model version each
 * authentication step is using (or that it runs on template matching only).
 * ========================================================================== */
