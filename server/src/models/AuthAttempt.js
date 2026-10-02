import mongoose from 'mongoose';

const authAttemptSchema = new mongoose.Schema(
  {
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', index: true },
    username: { type: String, index: true },

    step: { type: String, enum: ['static_gesture', 'dynamic_signature'], required: true },
    accepted: { type: Boolean, required: true },
    reason: String,

    score: Number,
    threshold: Number,
    matchPercent: Number,
    modelVersion: String,

    ip: String,
    userAgent: String,
  },
  { timestamps: { createdAt: true, updatedAt: false } },
);

authAttemptSchema.methods.toPublicJSON = function toPublicJSON() {
  return {
    id: this._id.toString(),
    step: this.step,
    accepted: this.accepted,
    reason: this.reason,
    score: this.score,
    threshold: this.threshold,
    matchPercent: this.matchPercent,
    createdAt: this.createdAt,
  };
};

export default mongoose.model('AuthAttempt', authAttemptSchema);

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * AuthAttempt.js is the audit log: one document per verification attempt of
 * either step, with the decision, reason, fused score, threshold, match
 * percentage, model version and client IP / user agent.  The dashboard shows
 * a user their own recent attempts (including failed ones by others).
 * ========================================================================== */
