const COMPONENT_LABELS = {
  template: 'Key-point template',
  embedding: 'Neural embedding',
  dtw: 'Trajectory (DTW)',
  global: 'Rhythm & timing',
};

/**
 * Shows one verification decision with its match score and the per-
 * component normalised distances (1.0 = the user's typical variation).
 */
export default function ResultCard({ title, result, message }) {
  if (!result) return null;

  const accepted = result.accepted;

  return (
    <div className={`result-card ${accepted ? 'granted' : 'denied'}`}>
      <div className="result-header">
        <strong>{title}</strong>
        <span className="result-badge">{accepted ? 'MATCH' : 'NO MATCH'}</span>
      </div>

      {message && <p>{message}</p>}

      {typeof result.matchPercent === 'number' && (
        <>
          <div className="meter large">
            <div style={{ width: `${result.matchPercent}%` }} />
            <span className="meter-threshold" title="decision threshold" />
          </div>
          <p className="muted">
            Match {result.matchPercent.toFixed(1)}%
            {result.score != null && ` · score ${result.score.toFixed(3)} / threshold ${result.threshold.toFixed(3)}`}
          </p>
        </>
      )}

      {result.components && Object.keys(result.components).length > 0 && (
        <ul className="components">
          {Object.entries(result.components).map(([name, value]) => (
            <li key={name}>
              <span>{COMPONENT_LABELS[name] || name}</span>
              <span className="mono">{value.toFixed(2)}×</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * ResultCard.jsx visualises a verification result: MATCH / NO MATCH badge,
 * a match-percentage bar with the decision threshold marked at 50 %, the
 * fused score versus threshold and each AI component's distance expressed in
 * multiples of the user's own natural variation.
 * ========================================================================== */
