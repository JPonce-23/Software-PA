"""Private staging and no-replace publication on a trusted POSIX filesystem.

Published names are NEVER removed by compensation: DB commit can be ambiguous.
This is not a DB/filesystem transaction or protection from a compromised UID.
"""

import errno
import hashlib
import hmac
import logging
import os
from pathlib import Path
import re
import stat
import uuid

from ..safe_logging import DiagnosticEvent


class DocumentStorageError(Exception):
    def __init__(self, code, detail='No fue posible preparar o publicar el archivo documental.', status=409):
        self.code, self.detail, self.status = code, detail, status
        super().__init__(detail)


def storage_event(code, operation_id):
    # Only server-generated operation ID and static codes; never path/exception.
    event = DiagnosticEvent(category='document_storage', code=code, component='documents',
        correlation_id=operation_id, method=None, route=None, status=None, response_complete=None)
    logging.getLogger('ssalfer.diagnostics').error('document_storage',
        extra={'safe_event': event}, exc_info=False, stack_info=False)


def _identity(info):
    return info.st_dev, info.st_ino


def _io_code(error):
    return {errno.ENOSPC: 'DOCUMENT_STORAGE_FULL', errno.EDQUOT: 'DOCUMENT_STORAGE_QUOTA',
            errno.EACCES: 'DOCUMENT_STORAGE_PERMISSIONS', errno.EPERM: 'DOCUMENT_STORAGE_PERMISSIONS',
            errno.EXDEV: 'DOCUMENT_STORAGE_CROSS_DEVICE', errno.ELOOP: 'DOCUMENT_STORAGE_SYMLINK'}.get(
                error.errno, 'DOCUMENT_STORAGE_IO')


def _directory_flags():
    if not all(hasattr(os, flag) for flag in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_CLOEXEC')):
        raise DocumentStorageError('DOCUMENT_STORAGE_UNSUPPORTED', status=503)
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def _open_root(root):
    root = Path(root)
    if not root.is_absolute() or len(root.parts) <= 1 or '..' in root.parts:
        raise DocumentStorageError('DOCUMENT_STORAGE_ROOT_INVALID')
    fd = os.open('/', _directory_flags())
    try:
        for part in root.parts[1:]:
            child = os.open(part, _directory_flags(), dir_fd=fd)
            os.close(fd); fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


class StagedDocument:
    def __init__(self, root, document_id, content, digest):
        if type(document_id) is not int or document_id <= 0:
            raise DocumentStorageError('DOCUMENT_STORAGE_ID_INVALID')
        self.root, self.document_name = Path(root), str(document_id)
        self.content, self.digest = content, digest
        self.operation_id = uuid.uuid4().hex
        self.stage_name = '.pending-' + self.operation_id
        self.root_fd = self.document_fd = self.stage_fd = self.file_fd = None
        self.stage_identity = self.file_identity = None
        self.created_stage = False
        self.published_name = None

    def __enter__(self):
        try:
            self.root_fd = _open_root(self.root)
            if os.fstat(self.root_fd).st_mode & stat.S_IWOTH:
                raise DocumentStorageError('DOCUMENT_STORAGE_PUBLIC_ROOT')
            try:
                os.mkdir(self.document_name, mode=0o700, dir_fd=self.root_fd)
            except FileExistsError:
                pass
            self.document_fd = os.open(self.document_name, _directory_flags(), dir_fd=self.root_fd)
            if os.fstat(self.document_fd).st_mode & stat.S_IWOTH:
                raise DocumentStorageError('DOCUMENT_STORAGE_PUBLIC_DIRECTORY')
            # mkdir is exclusive. On collision, never adopt/delete that directory.
            try:
                os.mkdir(self.stage_name, mode=0o700, dir_fd=self.document_fd)
            except FileExistsError as exc:
                raise DocumentStorageError('DOCUMENT_STAGING_COLLISION') from exc
            self.created_stage = True
            stage_entry = os.stat(self.stage_name, dir_fd=self.document_fd, follow_symlinks=False)
            if not stat.S_ISDIR(stage_entry.st_mode):
                raise DocumentStorageError('DOCUMENT_STAGING_CHANGED')
            self.stage_identity = _identity(stage_entry)
            self.stage_fd = os.open(self.stage_name, _directory_flags(), dir_fd=self.document_fd)
            if _identity(os.fstat(self.stage_fd)) != self.stage_identity:
                raise DocumentStorageError('DOCUMENT_STAGING_CHANGED')
            self.file_fd = os.open('payload', os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                mode=0o600, dir_fd=self.stage_fd)
            self.file_identity = _identity(os.fstat(self.file_fd))
            remaining = memoryview(self.content)
            while remaining:
                written = os.write(self.file_fd, remaining[:65536])
                if written <= 0:
                    raise OSError(errno.EIO, 'Incomplete document write')
                remaining = remaining[written:]
            os.fsync(self.file_fd)
            os.lseek(self.file_fd, 0, os.SEEK_SET)
            observed, checksum = 0, hashlib.sha256()
            while block := os.read(self.file_fd, min(65536, len(self.content) - observed + 1)):
                observed += len(block)
                if observed > len(self.content):
                    raise DocumentStorageError('DOCUMENT_STORAGE_SIZE_CHANGED')
                checksum.update(block)
            if observed != len(self.content) or not hmac.compare_digest(checksum.hexdigest(), self.digest):
                raise DocumentStorageError('DOCUMENT_STORAGE_HASH_MISMATCH')
            os.fsync(self.stage_fd)
            return self
        except OSError as exc:
            storage_event(_io_code(exc), self.operation_id)
            self.close()
            raise DocumentStorageError('DOCUMENT_STORAGE_IO', status=507) from exc
        except BaseException:
            self.close()
            raise

    def publish(self, name):
        try:
            self._publish(name)
        except OSError as exc:
            storage_event(_io_code(exc), self.operation_id)
            raise DocumentStorageError('DOCUMENT_STORAGE_IO', status=507) from exc

    def _publish(self, name):
        if self.published_name is not None:
            raise DocumentStorageError('DOCUMENT_STORAGE_ALREADY_PUBLISHED')
        match = re.fullmatch(r'([0-9]{4,})-[0-9a-f]{32}\.(?:pdf|docx|xlsx|jpe?g|png)', name)
        if not match or int(match.group(1)) <= 0:
            raise DocumentStorageError('DOCUMENT_STORAGE_NAME_INVALID')
        current = os.stat(self.document_name, dir_fd=self.root_fd, follow_symlinks=False)
        if not stat.S_ISDIR(current.st_mode) or _identity(current) != _identity(os.fstat(self.document_fd)):
            raise DocumentStorageError('DOCUMENT_STORAGE_DIRECTORY_CHANGED')
        source = os.stat('payload', dir_fd=self.stage_fd, follow_symlinks=False)
        if not stat.S_ISREG(source.st_mode) or _identity(source) != self.file_identity:
            raise DocumentStorageError('DOCUMENT_STORAGE_SOURCE_CHANGED')
        try:
            os.link('payload', name, src_dir_fd=self.stage_fd, dst_dir_fd=self.document_fd, follow_symlinks=False)
        except FileExistsError as exc:
            raise DocumentStorageError('DOCUMENT_STORAGE_COLLISION') from exc
        # From here on, retain the final entry, even if verification/fsync/DB fails.
        self.published_name = name
        published = os.stat(name, dir_fd=self.document_fd, follow_symlinks=False)
        if not stat.S_ISREG(published.st_mode) or _identity(published) != self.file_identity:
            raise DocumentStorageError('DOCUMENT_STORAGE_PUBLISHED_CHANGED')
        os.fsync(self.document_fd)
        os.fsync(self.root_fd)  # Persist a newly created document directory too.

    def close(self):
        failure = self.created_stage and self.stage_identity is None
        # Pin the inode until unlink completes; never delete an entry that was
        # substituted. Do not scan/rmtree a directory or unlink any published name.
        if self.file_fd is not None and self.stage_fd is not None:
            try:
                entry = os.stat('payload', dir_fd=self.stage_fd, follow_symlinks=False)
                if stat.S_ISREG(entry.st_mode) and _identity(entry) == self.file_identity:
                    os.unlink('payload', dir_fd=self.stage_fd)
                else:
                    failure = True
            except FileNotFoundError:
                pass
            except OSError:
                failure = True
        for attribute in ('file_fd',):
            fd = getattr(self, attribute)
            if fd is not None:
                setattr(self, attribute, None)
                try: os.close(fd)
                except OSError: failure = True
        if self.created_stage and self.stage_identity is not None and self.document_fd is not None:
            try:
                entry = os.stat(self.stage_name, dir_fd=self.document_fd, follow_symlinks=False)
                if stat.S_ISDIR(entry.st_mode) and _identity(entry) == self.stage_identity:
                    os.rmdir(self.stage_name, dir_fd=self.document_fd)
                    os.fsync(self.document_fd)
                else:
                    failure = True
            except FileNotFoundError:
                pass
            except OSError:
                failure = True
        for attribute in ('stage_fd', 'document_fd', 'root_fd'):
            fd = getattr(self, attribute)
            if fd is not None:
                setattr(self, attribute, None)
                try: os.close(fd)
                except OSError: failure = True
        if failure:
            storage_event('DOCUMENT_STAGING_CLEANUP_INCOMPLETE', self.operation_id)

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def stage_document(root, document_id, content, digest):
    return StagedDocument(root, document_id, content, digest)
