import mongoose from 'mongoose';

const userSchema = new mongoose.Schema(
  {
    username: {
      type: String,
      required: true,
      unique: true,
      lowercase: true,
      trim: true,
      match: /^[a-z0-9_.-]{3,32}$/,
    },
    displayName: { type: String, trim: true, maxlength: 64 },

    status: { type: String, enum: ['active', 'disabled'], default: 'active' },

    // Security state
    failedAttempts: { type: Number, default: 0 },
    lockUntil: { type: Date, default: null },
    lastLoginAt: { type: Date, default: null },
  },
  { timestamps: true },
);

userSchema.methods.isLocked = function isLocked() {
  return Boolean(this.lockUntil && this.lockUntil > new Date());
};

userSchema.methods.toPublicJSON = function toPublicJSON() {
  return {
    id: this._id.toString(),
    username: this.username,
    displayName: this.displayName || this.username,
    status: this.status,
    createdAt: this.createdAt,
    lastLoginAt: this.lastLoginAt,
  };
};

export default mongoose.model('User', userSchema);

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * User.js is the account collection.  An account is identified by a unique,
 * lower-case username (no password - the two air gestures ARE the
 * credentials).  It tracks consecutive failed verification attempts and a
 * lockUntil timestamp for brute-force protection, plus the last successful
 * login.  toPublicJSON() is the only shape ever sent to the browser.
 * ========================================================================== */
