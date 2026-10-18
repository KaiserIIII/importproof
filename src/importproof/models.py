"""Shared public limits and failure type."""
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_RESULT_BYTES = 16 * 1024 * 1024
MAX_FINDINGS = 2000
WORKER_SECONDS = 30


class AuditError(ValueError):
    """Invalid or unsupported input; must never be reported as equality."""
