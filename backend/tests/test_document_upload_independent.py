"""Reuse the upload regression after transactional catalog fixtures tear down."""
from .test_documents_dashboard import (
    test_document_version_is_immutable_and_downloadable as verify_document_version,
)


def test_existing_document_version_regression_isolated(
    client, admin_headers, api, target_domain,
):
    # Real sessions/commits preserve the independent upload transaction and
    # SHARE NOWAIT authorization fence, including the original duplicate and
    # byte-for-byte download assertions. No guard or lock is mocked.
    verify_document_version(client, admin_headers, api, target_domain)
