import mongoose from 'mongoose';

const biometricSampleSchema = new mongoose.Schema(
  {
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, index: true },
    kind: { type: String, enum: ['static', 'dynamic'], required: true },
    purpose: { type: String, enum: ['enrollment', 'login'], required: true },

    // Only meaningful for purpose = "login".
    accepted: { type: Boolean, default: null },
    score: { type: Number, default: null },

    // Raw capture exactly as sent by the browser (landmarks / trajectory).
    sample: { type: mongoose.Schema.Types.Mixed, required: true },
  },
  { timestamps: { createdAt: true, updatedAt: false } },
);

biometricSampleSchema.index({ kind: 1, createdAt: 1 });

export default mongoose.model('BiometricSample', biometricSampleSchema);

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * BiometricSample.js keeps the raw captures (hand landmarks for Step 1, the
 * fingertip trajectory for Step 2) from registration and login attempts,
 * labelled with their purpose and outcome.  They are written only when
 * STORE_RAW_SAMPLES=true and are exported by scripts/exportBiometricSamples.js
 * to retrain and recalibrate the ML models on real users.
 * ========================================================================== */
