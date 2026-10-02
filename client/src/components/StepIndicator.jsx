export default function StepIndicator({ steps, current }) {
  return (
    <ol className="steps">
      {steps.map((label, index) => {
        const state = index < current ? 'done' : index === current ? 'active' : 'todo';
        return (
          <li key={label} className={state}>
            <span className="step-number">{state === 'done' ? '✓' : index + 1}</span>
            {label}
          </li>
        );
      })}
    </ol>
  );
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * StepIndicator.jsx renders the horizontal progress tracker used by the
 * registration and login wizards (done / active / upcoming steps).
 * ========================================================================== */
