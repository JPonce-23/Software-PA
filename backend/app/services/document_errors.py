"""Stable upload errors. Values are public constants, never request metadata."""
from fastapi import HTTPException

HEADER = "X-Document-Error-Code"
DOCUMENT_DUPLICATE = "DOCUMENT_DUPLICATE"
DOCUMENT_IDEMPOTENCY_CONFLICT = "DOCUMENT_IDEMPOTENCY_CONFLICT"
DOCUMENT_RECONCILIATION_REQUIRED = "DOCUMENT_RECONCILIATION_REQUIRED"
DOCUMENT_OPERATION_PENDING = "DOCUMENT_OPERATION_PENDING"
DOCUMENT_OPERATION_REJECTED = "DOCUMENT_OPERATION_REJECTED"
DOCUMENT_INTEGRITY_CONFLICT = "DOCUMENT_INTEGRITY_CONFLICT"
DOCUMENT_REQUEST_CONFLICT = "DOCUMENT_REQUEST_CONFLICT"
REJECTED_CODES = frozenset({DOCUMENT_DUPLICATE, DOCUMENT_OPERATION_REJECTED,
    DOCUMENT_INTEGRITY_CONFLICT, DOCUMENT_REQUEST_CONFLICT})
CODES = REJECTED_CODES | {DOCUMENT_IDEMPOTENCY_CONFLICT,
    DOCUMENT_RECONCILIATION_REQUIRED, DOCUMENT_OPERATION_PENDING}


def document_error(status, detail, code, *, headers=None):
    if code not in CODES:
        raise ValueError("Unknown public document error code")
    return HTTPException(status, detail, headers={**(headers or {}), HEADER: code})


def error_code(error):
    code = (getattr(error, "headers", None) or {}).get(HEADER)
    if code in CODES:
        return code
    # Only this exact PostgreSQL UNIQUE constraint proves content duplication.
    # Neither driver messages nor other integrity failures identify a duplicate.
    original = getattr(error, "orig", None)
    if getattr(original, "pgcode", None) == "23505" and \
            getattr(getattr(original, "diag", None), "constraint_name", None) == "uq_documento_hash":
        return DOCUMENT_DUPLICATE
    return None
