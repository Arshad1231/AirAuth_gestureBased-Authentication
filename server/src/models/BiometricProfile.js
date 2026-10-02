import mongoose from 'mongoose';

const biometricProfileSchema = new mongoose.Schema(
  {
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, unique: true },

    // Templates are produced and interpreted ONLY by the ML service.
    staticTemplate: { type: mongoose.Schema.Types.Mixed, required: true },
    dynamicTemplate: { type: mongoose.Schema.Types.Mixed, required: true },

    staticHandedness: { type: String },
    staticFeatureVersion: { type: String },
    dynamicFeatureVersion: { type: String },

    enrollmentReport: { type: mongoose.Schema.Types.Mixed },

    // Number of successful logins absorbed into the signature template.
    dynamicAdaptations: { type: Number, default: 0 },
  },
  { timestamps: true, minimize: false },
);

biometricProfileSchema.methods.toSummaryJSON = function toSummaryJSON() {
  return {
    staticHandedness: this.staticHandedness,
    staticSamples: this.staticTemplate?.feature_vectors?.length || 0,
    signatureSamples: this.dynamicTemplate?.trajectories?.length || 0,
    signatureEnrolled: this.dynamicTemplate?.enrolled_count || 0,
    dynamicAdaptations: this.dynamicAdaptations,
    featureVersions: {
      static: this.staticFeatureVersion,
      dynamic: this.dynamicFeatureVersion,
    },
    createdAt: this.createdAt,
    updatedAt: this.updatedAt,
  };
};

export default mongoose.model('BiometricProfile', biometricProfileSchema);

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * BiometricProfile.js stores one profile per user: the static-gesture
 * template (Step 1) and the air-signature template (Step 2) exactly as
 * returned by the ML service's /enroll endpoints, the enrollment quality
 * report and how many successful logins have been adapted into the signature
 * template.  The templates are never sent to the browser - only
 * toSummaryJSON() (counts, handedness, versions) is.
 * ========================================================================== */
