"""Descriptor-owned download, never a path-send or a later name-based reopen.

Published files are write-once by application protocol, not immutable to their
owner/another process with write access. Size/mtime checks detect ordinary
in-place changes but cannot guarantee a snapshot against a hostile same-UID
writer restoring metadata. No temporary copy, storage mutation, or SQL is used.
"""
import asyncio
from dataclasses import dataclass, field
from email.utils import formatdate
import errno
import hashlib
import hmac
import os
from pathlib import Path
import re
from secrets import token_hex
import stat
import threading
from urllib.parse import quote

from anyio import CancelScope
from fastapi import HTTPException
from starlette._utils import create_collapsing_task_group
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers
from starlette.requests import ClientDisconnect
from starlette.responses import FileResponse, MalformedRangeHeader, PlainTextResponse, RangeNotSatisfiable, Response

from .document_storage import DocumentStorageError, _directory_flags, _open_root

CHUNK_SIZE = 64 * 1024
MAX_RANGE_HEADER = 4096
MAX_RANGES = 16


class DownloadError(Exception):
    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__(code)  # Static code only, never an OS exception/path.


def download_root():
    # Unlike the upload helper, never resolve symlinks or mkdir during a read.
    root = Path(os.getenv('UPLOAD_ROOT', 'uploads'))
    return root if root.is_absolute() else Path.cwd() / root


def safe_filename(value):
    value = str(value or 'archivo').replace('\\', '/').split('/')[-1]
    value = ''.join('_' if ord(c) < 32 or ord(c) == 127 or c in '";' else c for c in value)
    return value.strip(' .')[:255] or 'archivo'


def _stamp(info):
    # Unlink/rename changes ctime/nlink without changing the held bytes. Permit
    # nlink=0 after opening so a name replacement still delivers the old inode.
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns


@dataclass
class VerifiedFile:
    fd: int | None = field(repr=False)
    info: object = field(repr=False)

    def check(self):
        if self.fd is None:
            raise DownloadError('DOCUMENT_DOWNLOAD_CLOSED', 503)
        try:
            current = os.fstat(self.fd)
        except OSError:
            raise DownloadError('DOCUMENT_DOWNLOAD_READ_FAILED', 503) from None
        if _stamp(current) != _stamp(self.info) or current.st_nlink > 1:
            raise DownloadError('DOCUMENT_DOWNLOAD_CHANGED')

    def read_at(self, offset, amount):
        try:
            self.check()
            data = os.pread(self.fd, min(amount, CHUNK_SIZE), offset)
            self.check()
            if len(data) != min(amount, CHUNK_SIZE):
                raise DownloadError('DOCUMENT_DOWNLOAD_CHANGED')
            return data
        except OSError:
            raise DownloadError('DOCUMENT_DOWNLOAD_READ_FAILED', 503) from None

    def close(self):
        if self.fd is not None:
            fd, self.fd = self.fd, None
            os.close(fd)  # Do not retry close on an ambiguously reused FD.


def open_verified(root, relative, document_id, expected_size, expected_sha, cancel):
    """One successful leaf open; no name-based read after descriptor validation."""
    if (type(document_id) is not int or document_id <= 0 or not isinstance(relative, str)
            or len(relative) > 4096 or '\\' in relative or '\x00' in relative):
        raise DownloadError('DOCUMENT_DOWNLOAD_PATH_INVALID', 404)
    parts = relative.split('/')
    if (len(parts) != 2 or parts[0] != str(document_id) or not parts[1]
            or any(p in ('.', '..') for p in parts) or parts[1].startswith('.')):
        raise DownloadError('DOCUMENT_DOWNLOAD_PATH_INVALID', 404)
    if (type(expected_size) is not int or expected_size < 0 or not isinstance(expected_sha, str)
            or re.fullmatch('[0-9a-f]{64}', expected_sha) is None):
        raise DownloadError('DOCUMENT_DOWNLOAD_METADATA_INVALID')
    if not hasattr(os, 'pread') or not hasattr(os, 'O_NONBLOCK'):
        raise DownloadError('DOCUMENT_DOWNLOAD_UNSUPPORTED', 503)
    root_fd = document_fd = leaf_fd = None
    try:
        root = Path(root)
        if (not root.is_absolute() or '..' in root.parts or '\x00' in str(root)
                or len(root.parts) < 2 or len(root.parts) > 64):
            raise DownloadError('DOCUMENT_DOWNLOAD_PATH_INVALID', 404)
        if cancel.is_set():
            raise DownloadError('DOCUMENT_DOWNLOAD_CANCELLED', 503)
        root_fd = _open_root(root)
        if os.fstat(root_fd).st_mode & stat.S_IWOTH:
            raise DownloadError('DOCUMENT_DOWNLOAD_PATH_INVALID', 404)
        document_fd = os.open(parts[0], _directory_flags(), dir_fd=root_fd)
        if os.fstat(document_fd).st_mode & stat.S_IWOTH:
            raise DownloadError('DOCUMENT_DOWNLOAD_PATH_INVALID', 404)
        before = os.stat(parts[1], dir_fd=document_fd, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise DownloadError('DOCUMENT_DOWNLOAD_PATH_INVALID', 404)
        leaf_fd = os.open(parts[1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                          dir_fd=document_fd)
        info = os.fstat(leaf_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1 or _stamp(info) != _stamp(before):
            raise DownloadError('DOCUMENT_DOWNLOAD_CHANGED')
        if info.st_size != expected_size:
            raise DownloadError('DOCUMENT_DOWNLOAD_SIZE_MISMATCH')
        verified = VerifiedFile(leaf_fd, info)
        checksum, offset = hashlib.sha256(), 0
        while offset < expected_size:
            if cancel.is_set():
                raise DownloadError('DOCUMENT_DOWNLOAD_CANCELLED', 503)
            block = verified.read_at(offset, min(CHUNK_SIZE, expected_size - offset))
            checksum.update(block); offset += len(block)
        verified.check()
        if not hmac.compare_digest(checksum.hexdigest(), expected_sha):
            raise DownloadError('DOCUMENT_DOWNLOAD_HASH_MISMATCH')
        leaf_fd = None  # Ownership transfers only after the whole-file check.
        return verified
    except DocumentStorageError:
        raise DownloadError('DOCUMENT_DOWNLOAD_PATH_INVALID', 404) from None
    except OSError as error:
        status = 404 if error.errno in (errno.ENOENT, errno.ENOTDIR, errno.ELOOP) else 503
        raise DownloadError('DOCUMENT_DOWNLOAD_UNAVAILABLE', status) from None
    finally:
        for fd in (leaf_fd, document_fd, root_fd):
            if fd is not None:
                os.close(fd)


async def _worker(function, *args, cancel=None, dispose=None):
    """Never close/reuse an FD while a cancelled thread still reads it."""
    task = asyncio.create_task(run_in_threadpool(function, *args))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        if cancel is not None:
            cancel.set()
        with CancelScope(shield=True):
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if not task.cancelled() and task.exception() is None and dispose is not None:
                await _worker(dispose, task.result())
        raise


class DescriptorDownloadResponse(Response):
    """Owned FD lifecycle spans opening, headers, ranges and disconnect/error.

    Only FileResponse's pure range/multipart helpers are reused (pinned Starlette
    1.3.1). No FileResponse instance, pathsend, anyio.open_file or second open.
    """
    def __init__(self, *, relative, document_id, size, sha256, filename, root=None):
        self._spec = (download_root() if root is None else root, relative, document_id, size, sha256)
        self.filename = safe_filename(filename)
        quoted = quote(self.filename)
        disposition = (f"attachment; filename*=utf-8''{quoted}" if quoted != self.filename
                       else f'attachment; filename="{self.filename}"')
        super().__init__(content=b'', media_type='application/octet-stream', headers={
            'Content-Disposition': disposition, 'X-Content-Type-Options': 'nosniff',
            'Cache-Control': 'private, no-store', 'Accept-Ranges': 'bytes'})

    def _ranges(self, scope, size):
        request = Headers(scope=scope)
        value, conditional = request.get('range'), request.get('if-range')
        if value is None or (conditional is not None and conditional not in
                            (self.headers['etag'], self.headers['last-modified'])):
            return [(0, size)], False
        if len(value) > MAX_RANGE_HEADER or len(value.split(',')) > MAX_RANGES:
            raise MalformedRangeHeader('Range request exceeds bounded limits')
        ranges = FileResponse._parse_range_header(value, size)
        if any(end <= start for start, end in ranges):
            raise MalformedRangeHeader('Range start must precede end')
        return ranges, True

    async def _serve(self, scope, send):
        owned, started = None, False
        cancel = threading.Event()
        async def transmit(message):
            nonlocal started
            try:
                await send(message)
            except OSError:
                raise ClientDisconnect() from None
            if message['type'] == 'http.response.start':
                started = True
        try:
            owned = await _worker(open_verified, *self._spec, cancel,
                                  cancel=cancel, dispose=lambda value: value.close())
            await _worker(owned.check)
            size = owned.info.st_size
            self.headers['content-length'] = str(size)
            self.headers['last-modified'] = formatdate(owned.info.st_mtime, usegmt=True)
            tag = f'{owned.info.st_mtime}-{size}'.encode()
            self.headers['etag'] = '"' + hashlib.md5(tag, usedforsecurity=False).hexdigest() + '"'
            try:
                ranges, partial = self._ranges(scope, size)
            except (MalformedRangeHeader, RangeNotSatisfiable) as error:
                status = 416 if isinstance(error, RangeNotSatisfiable) else 400
                headers = {'X-Content-Type-Options':'nosniff', 'Cache-Control':'private, no-store'}
                if status == 416:
                    headers['Content-Range'] = f'bytes */{size}'
                response = PlainTextResponse(error.content if status == 400 else '',
                                             status_code=status, headers=headers)
                if scope['method'].upper() == 'HEAD':
                    response.body = b''
                await response(scope, None, transmit)
                return
            headers = dict(self.headers)
            boundary = generator = None
            if partial and len(ranges) == 1:
                start, end = ranges[0]
                headers['content-range'] = f'bytes {start}-{end-1}/{size}'
                headers['content-length'] = str(end-start)
            elif partial:
                boundary = token_hex(13)
                length, generator = FileResponse.generate_multipart(self, ranges, boundary, size,
                                                                    'application/octet-stream')
                headers['content-type'] = f'multipart/byteranges; boundary={boundary}'
                headers['content-length'] = str(length)
            response = Response(b'', status_code=206 if partial else 200, headers=headers)
            await transmit({'type':'http.response.start','status':response.status_code,'headers':response.raw_headers})
            if scope['method'].upper() != 'HEAD':
                for start, end in ranges:
                    if generator is not None:
                        await transmit({'type':'http.response.body','body':generator(start,end),'more_body':True})
                    while start < end:
                        block = await _worker(owned.read_at, start, min(CHUNK_SIZE, end-start))
                        start += len(block)
                        await transmit({'type':'http.response.body','body':block,'more_body':True})
                    if generator is not None:
                        await transmit({'type':'http.response.body','body':b'\r\n','more_body':True})
                if boundary is not None:
                    await transmit({'type':'http.response.body','body':f'--{boundary}--'.encode(),'more_body':True})
                await _worker(owned.check)
            await transmit({'type':'http.response.body','body':b'','more_body':False})
        except DownloadError as error:
            if started:
                # Headers cannot be replaced with JSON after transmission starts.
                raise RuntimeError('DOCUMENT_DOWNLOAD_INTERRUPTED') from None
            detail = ('Archivo no encontrado' if error.status == 404 else
                      'El archivo no coincide con la versión registrada' if error.status == 409 else
                      'No fue posible leer el archivo documental')
            raise HTTPException(error.status, detail) from None
        finally:
            cancel.set()
            if owned is not None:
                with CancelScope(shield=True):
                    await _worker(owned.close)

    async def __call__(self, scope, receive, send):
        # Monitor disconnect even during initial hashing, for ASGI 2.0 and 2.4.
        async with create_collapsing_task_group() as group:
            async def transfer():
                try:
                    await self._serve(scope, send)
                finally:
                    group.cancel_scope.cancel()
            async def disconnect():
                while True:
                    if (await receive())['type'] == 'http.disconnect':
                        group.cancel_scope.cancel()
                        return
            group.start_soon(transfer)
            group.start_soon(disconnect)
