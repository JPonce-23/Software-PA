"""Cooperative POSIX writer exclusion, retained even if a SQL connection dies.

Lock names are permanent protocol objects: never unlink/recreate them. Recovery
only opens existing locks and requires the durable inode identity registered by
the uploader. Legacy uploads have no such proof and must not be adopted.
"""
import fcntl
import os
import stat
import uuid
from pathlib import Path


class CoordinationError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _identity(fd):
    info = os.fstat(fd)
    return [info.st_dev, info.st_ino]


def _close_descriptors(descriptors):
    error = None
    for fd in descriptors:
        if fd is not None:
            try:
                os.close(fd)
            except OSError as exc:
                if error is None:
                    error = exc
    if error is not None:
        raise error


class WriterLease:
    def __init__(self, root, document_id, operation_id, *, create=False):
        if type(document_id) is not int or document_id <= 0 or not isinstance(operation_id, uuid.UUID):
            raise ValueError('Invalid writer identity')
        self.root = Path(root)
        self.name = f'{document_id}-{operation_id.hex}.lock'
        self.create = create
        self.root_fd = self.directory_fd = self.fd = None
        self.identity = None

    def __enter__(self):
        from .document_storage import _open_root, _directory_flags
        try:
            self.root_fd = _open_root(self.root)
            if os.fstat(self.root_fd).st_mode & 0o022:
                raise CoordinationError('UNTRUSTED_COORDINATION_ROOT')
            if self.create:
                try:
                    os.mkdir('.ss12-writers', 0o700, dir_fd=self.root_fd)
                except FileExistsError:
                    pass
            self.directory_fd = os.open('.ss12-writers', _directory_flags(), dir_fd=self.root_fd)
            info = os.fstat(self.directory_fd)
            if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise CoordinationError('UNTRUSTED_COORDINATION_DIRECTORY')
            self.fd = os.open(self.name, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC |
                              (os.O_CREAT if self.create else 0), 0o600, dir_fd=self.directory_fd)
            info = os.fstat(self.fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != 0
                    or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600):
                raise CoordinationError('UNTRUSTED_COORDINATION_FILE')
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise CoordinationError('ACTIVE_WRITER') from None
            self.identity = {'root': _identity(self.root_fd), 'directory': _identity(self.directory_fd),
                             'lock': _identity(self.fd)}
            if self.create:
                os.fsync(self.fd); os.fsync(self.directory_fd); os.fsync(self.root_fd)
            self.check()
            return self
        except BaseException:
            self.close()
            raise

    def check(self):
        from .document_storage import _open_root, _directory_flags
        root_fd = directory_fd = None
        try:
            if self.fd is None:
                raise CoordinationError('COORDINATION_CLOSED')
            root_fd = _open_root(self.root)
            directory_fd = os.open('.ss12-writers', _directory_flags(), dir_fd=root_fd)
            root_info, directory_info = os.fstat(root_fd), os.fstat(directory_fd)
            if root_info.st_mode & 0o022 or directory_info.st_uid != os.geteuid() or stat.S_IMODE(directory_info.st_mode) != 0o700:
                raise CoordinationError('COORDINATION_PERMISSIONS_CHANGED')
            entry = os.stat(self.name, dir_fd=directory_fd, follow_symlinks=False)
            if (self.identity != {'root': _identity(root_fd), 'directory': _identity(directory_fd),
                                  'lock': [entry.st_dev, entry.st_ino]}
                    or _identity(self.fd) != self.identity['lock'] or not stat.S_ISREG(entry.st_mode)
                    or entry.st_nlink != 1 or entry.st_size != 0 or entry.st_uid != os.geteuid()
                    or stat.S_IMODE(entry.st_mode) != 0o600):
                raise CoordinationError('COORDINATION_CHANGED')
        except OSError:
            raise CoordinationError('COORDINATION_CHANGED') from None
        finally:
            _close_descriptors((directory_fd, root_fd))

    def close(self):
        # Closing the owned descriptor releases flock; never remove its name.
        # Attempt every close even on an error. Never retry a descriptor number:
        # on Linux it may already have been released and reused by another thread.
        descriptors = []
        for field in ('fd', 'directory_fd', 'root_fd'):
            descriptors.append(getattr(self, field))
            setattr(self, field, None)
        _close_descriptors(descriptors)

    def __exit__(self, *args):
        self.close()
