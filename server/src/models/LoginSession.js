import mongoose from 'mongoose';

const loginSessionSchema = new mongoose.Schema(
  {
    // SHA-256 of the opaque session token held by the browser.
    tokenHash: { type: String, required: true, unique: true },
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },

    // State machine:  static_gesture --(pass)--> dynamic_signature --(pass)--> done
    stage: {
      type: String,
      enum: ['static_gesture', 'dynamic_signature'],
      default: 'static_gesture',
    },

    attempts: {
      static_gesture: { type: Number, default: 0 },
      dynamic_signature: { type: Number, default: 0 },
    },

    staticResult: { type: mongoose.Schema.Types.Mixed, default: null },

    ip: String,
    userAgent: String,

    // MongoDB deletes the document automatically once this time passes.
    expiresAt: { type: Date, required: true, index: { expireAfterSeconds: 0 } },
  },
  { timestamps: true },
);

export default mongoose.model('LoginSession', loginSessionSchema);

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * LoginSession.js is the server-side state of an in-progress two-step login.
 * The browser only holds a random token; the database stores its hash, the
 * user, the current stage (Step 1 static gesture -> Step 2 air signature) and
 * per-step attempt counters.  Step 2 can only be attempted once Step 1 has
 * moved the session forward, so steps cannot be skipped.  A TTL index removes
 * expired sessions automatically.
 * ========================================================================== */
