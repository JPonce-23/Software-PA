"""Journal double for the pre-existing POSIX/session unit regressions. No SQL."""
import hashlib
import json
from types import SimpleNamespace
import uuid
from unittest.mock import MagicMock


class JournalDouble:
    key = staticmethod(lambda value: uuid.uuid4() if value is None else uuid.UUID(str(value)))

    def __init__(self):
        self.reserve = MagicMock(side_effect=self.ticket)
        self.staged = MagicMock()
        self.confirm = MagicMock()
        self.failed = MagicMock(return_value=None)

    @staticmethod
    def ticket(sessions, document, actor, key, metadata, authorize, **kwargs):
        operation_id = uuid.uuid4()
        return SimpleNamespace(id=operation_id, key=key, document_id=document,
            actor_id=actor, fingerprint=hashlib.sha256(json.dumps(metadata,sort_keys=True).encode()).hexdigest(),
            path=f"{document}/op-{operation_id.hex}{metadata['extension']}")

    @staticmethod
    def decorate(version, ticket, *, replayed):
        version._idempotency_key=str(ticket.key)
        version._upload_operation_id=str(ticket.id)
        version._idempotency_replayed=replayed
        return version
