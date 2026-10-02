import { trajectoryPreviewPath } from '../lib/canvasDrawing.js';

/** Row of numbered slots showing collected samples (signature thumbnails). */
export default function SamplePreview({ samples, total, kind, onRemoveLast }) {
  return (
    <div className="sample-preview">
      {Array.from({ length: total }).map((_, index) => {
        const sample = samples[index];
        return (
          <div key={index} className={`sample-slot ${sample ? 'filled' : ''}`}>
            {sample && kind === 'dynamic' ? (
              <svg viewBox="0 0 80 80" aria-label={`signature ${index + 1}`}>
                <path d={trajectoryPreviewPath(sample.points)} />
              </svg>
            ) : (
              <span>{sample ? '✋' : index + 1}</span>
            )}
          </div>
        );
      })}
      {samples.length > 0 && onRemoveLast && (
        <button type="button" className="link" onClick={onRemoveLast}>Remove last</button>
      )}
    </div>
  );
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * SamplePreview.jsx shows registration progress as numbered slots: a hand icon
 * for each captured gesture, a mirrored SVG thumbnail for each recorded air
 * signature, and a "Remove last" action to redo a bad capture.
 * ========================================================================== */
