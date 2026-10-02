class BiometricInputError(ValueError):
    """
    Raised when a captured sample cannot be used (too short, hand not
    held still, inconsistent enrollment, ...).  The API layer converts it
    into an HTTP 422 response whose message is shown to the user.
    """

    def __init__(self, message, code="invalid_sample", details=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# errors.py defines BiometricInputError, the single exception type used for
# "the user should retry the capture" situations.  It carries a short
# machine-readable code (e.g. "unstable_pose", "too_short") plus optional
# details, which app/main.py turns into a structured 422 JSON error.
# =============================================================================
