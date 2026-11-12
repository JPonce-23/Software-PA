"""Real POSIX/ASGI download, SQL/auth doubles only; no DB, Docker or dotenv."""
import asyncio
from contextlib import ExitStack
import errno
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock,patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'tests/security'))
from _document_service_support import document_service
service=document_service()
from app.services import document_download as download
from fastapi import HTTPException
from fastapi.testclient import TestClient
from _document_download_support import download_app


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='ss12-download-')
        self.addCleanup(self.directory.cleanup);self.root=Path(self.directory.name)
        (self.root/'7').mkdir(mode=0o700)
        self.path=self.root/'7/0001-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.pdf'
        self.content=b'SS12 binary\x00\xff synthetic bytes'
        self.path.write_bytes(self.content)
        self.rel=str(self.path.relative_to(self.root))

    def response(self,**changes):
        args=dict(root=self.root,relative=self.rel,document_id=7,size=len(self.content),
                  sha256=hashlib.sha256(self.content).hexdigest(),filename='synthetic.pdf')
        args.update(changes);return download.DescriptorDownloadResponse(**args)

    async def collect_async(self,response=None,method='GET',headers=None,send_hook=None,spec='2.4',extensions=None):
        response=response or self.response();messages=[]
        async def send(message):
            if send_hook is not None:await send_hook(message)
            messages.append(message)
        async def receive():
            await asyncio.Event().wait()
        scope={'type':'http','asgi':{'version':'3.0','spec_version':spec},'method':method,
               'path':'/download','headers':[(k.lower().encode(),v.encode()) for k,v in (headers or {}).items()],
               'extensions':extensions or {}}
        await response(scope,receive,send)
        return messages

    def collect(self,*args,**kwargs):return asyncio.run(self.collect_async(*args,**kwargs))
    def body(self,messages):return b''.join(m.get('body',b'') for m in messages if m['type']=='http.response.body')
    def headers(self,messages):return dict(messages[0]['headers'])
    def track_open(self):
        original=download.open_verified;opened=[]
        def open_file(*args):
            value=original(*args);opened.append((value,value.fd));return value
        context=patch.object(download,'open_verified',side_effect=open_file)
        self.addCleanup(context.stop);context.start();return opened
    def assert_closed(self,opened):
        self.assertTrue(opened)
        for value,fd in opened:
            self.assertIsNone(value.fd)
            with self.assertRaises(OSError):os.fstat(fd)

    def test_legitimate_bytes_headers_and_closed_descriptor(self):
        opened=self.track_open();messages=self.collect()
        self.assertEqual(self.body(messages),self.content);self.assertEqual(messages[0]['status'],200)
        headers=self.headers(messages)
        self.assertEqual(headers[b'content-type'],b'application/octet-stream')
        self.assertEqual(headers[b'content-disposition'],b'attachment; filename="synthetic.pdf"')
        self.assertEqual(headers[b'x-content-type-options'],b'nosniff')
        self.assertEqual(headers[b'cache-control'],b'private, no-store')
        self.assertEqual(int(headers[b'content-length']),len(self.content))
        self.assertEqual(headers[b'accept-ranges'],b'bytes');self.assertIn(b'etag',headers)
        self.assertIn(b'last-modified',headers);self.assert_closed(opened)

    def test_substitution_after_verified_open_streams_original_inode(self):
        original=download.open_verified;opened=[]
        def replace_name(*args):
            value=original(*args);opened.append((value,value.fd))
            other=self.root/'replacement';other.write_bytes(b'SUBSTITUTED SYNTHETIC BYTES')
            os.replace(other,self.path);return value
        with patch.object(download,'open_verified',side_effect=replace_name):messages=self.collect()
        self.assertEqual(self.body(messages),self.content)
        self.assertEqual(self.path.read_bytes(),b'SUBSTITUTED SYNTHETIC BYTES');self.assert_closed(opened)

    def test_substitution_immediately_after_leaf_open_cannot_change_held_bytes(self):
        original=os.open;done=False;count=0
        def opening(path,*args,**kwargs):
            nonlocal done,count
            fd=original(path,*args,**kwargs)
            if str(path)==self.path.name:
                count+=1
                if not done:
                    done=True;other=self.root/'replacement';other.write_bytes(b'OTHER')
                    os.replace(other,self.path)
            return fd
        with patch.object(download.os,'open',side_effect=opening):messages=self.collect()
        self.assertEqual(count,1);self.assertEqual(self.body(messages),self.content)

    def test_streaming_never_reopens_leaf_or_uses_pathsend_extension(self):
        real=os.open;count=0
        def opening(path,flags,*a,**kw):
            nonlocal count
            if str(path)==self.path.name:count+=1
            return real(path,flags,*a,**kw)
        with patch.object(download.os,'open',side_effect=opening):
            messages=self.collect(extensions={'http.response.pathsend':{}})
        self.assertEqual(count,1);self.assertFalse(any(m['type']=='http.response.pathsend' for m in messages))

    def test_final_symlink_and_hardlink_are_rejected_without_reading(self):
        other=self.root/'private';other.write_bytes(self.content);self.path.unlink()
        for link in ('symlink','hardlink'):
            with self.subTest(link=link):
                if self.path.exists() or self.path.is_symlink():self.path.unlink()
                if link=='symlink':self.path.symlink_to(other)
                else:os.link(other,self.path)
                with patch.object(download.os,'pread',wraps=os.pread) as read:
                    with self.assertRaises(HTTPException) as error:self.collect()
                    self.assertEqual(error.exception.status_code,404);read.assert_not_called()

    def test_symlink_document_or_root_ancestor_is_rejected(self):
        moved=self.root/'moved';(self.root/'7').rename(moved);(self.root/'7').symlink_to(moved,target_is_directory=True)
        with self.assertRaises(HTTPException) as error:self.collect()
        self.assertEqual(error.exception.status_code,404)
        alias=self.root/'alias';alias.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(HTTPException):self.collect(self.response(root=alias))

    def test_absolute_traversal_wrong_document_nul_and_staging_are_rejected(self):
        paths=['/etc/passwd','../private','7/../private','8/file.pdf','7//file','7/.pending-x/payload','7/hidden\\file','7/\x00']
        for relative in paths:
            with self.subTest(relative=relative),patch.object(download.os,'pread') as read:
                with self.assertRaises(HTTPException) as error:self.collect(self.response(relative=relative))
                self.assertEqual(error.exception.status_code,404);read.assert_not_called()

    def test_missing_root_is_not_created_and_missing_file_is_404(self):
        self.path.unlink()
        with self.assertRaises(HTTPException) as error:self.collect()
        self.assertEqual(error.exception.status_code,404)
        missing=self.root/'does-not-exist'
        with self.assertRaises(HTTPException):self.collect(self.response(root=missing))
        self.assertFalse(missing.exists())

    def test_wrong_size_hash_and_metadata_fail_before_headers(self):
        for values in [dict(size=len(self.content)+1),dict(sha256='f'*64),dict(size=0),dict(sha256='bad')]:
            with self.subTest(values=values),self.assertRaises(HTTPException) as error:
                self.collect(self.response(**values))
            self.assertEqual(error.exception.status_code,409)

    def test_empty_historical_version_allowed_by_baseline_keeps_get_head_and_416(self):
        self.content=b'';self.path.write_bytes(b'')
        for method in ['GET','HEAD']:
            messages=self.collect(method=method)
            self.assertEqual(messages[0]['status'],200);self.assertEqual(self.body(messages),b'')
            self.assertEqual(self.headers(messages)[b'content-length'],b'0')
        messages=self.collect(headers={'Range':'bytes=0-0'})
        self.assertEqual(messages[0]['status'],416)
        self.assertEqual(self.headers(messages)[b'content-range'],b'bytes */0')

    def test_fifo_and_directory_rejected_without_blocking_read(self):
        self.path.unlink();os.mkfifo(self.path)
        with self.assertRaises(HTTPException):self.collect()
        self.path.unlink();self.path.mkdir()
        with self.assertRaises(HTTPException):self.collect()

    def test_read_error_is_sanitized_and_all_opened_fds_close(self):
        real_open=os.open;fds=[]
        def opening(*a,**kw):
            fd=real_open(*a,**kw);fds.append(fd);return fd
        with patch.object(download.os,'open',side_effect=opening),patch.object(download.os,'pread',side_effect=OSError(errno.EIO,'private path SECRET')):
            with self.assertRaises(HTTPException) as error:self.collect()
        self.assertEqual(error.exception.status_code,503);self.assertNotIn('SECRET',str(error.exception))
        for fd in set(fds):
            with self.assertRaises(OSError):os.fstat(fd)

    def test_head_full_and_range_no_body_preserve_content_lengths(self):
        for headers,status,length in [({},200,len(self.content)),({'Range':'bytes=1-3'},206,3)]:
            with self.subTest(headers=headers):
                opened=self.track_open();messages=self.collect(method='HEAD',headers=headers)
                self.assertEqual(self.body(messages),b'');self.assertEqual(messages[0]['status'],status)
                self.assertEqual(int(self.headers(messages)[b'content-length']),length);self.assert_closed(opened)

    def test_valid_range_closed_open_suffix_oversized_suffix(self):
        for value,wanted in [('bytes=1-3',self.content[1:4]),('bytes=4-',self.content[4:]),
                            ('bytes=-4',self.content[-4:]),('bytes=-999',self.content)]:
            with self.subTest(value=value):
                messages=self.collect(headers={'Range':value})
                self.assertEqual(messages[0]['status'],206);self.assertEqual(self.body(messages),wanted)
                self.assertEqual(int(self.headers(messages)[b'content-length']),len(wanted))

    def test_multiple_ranges_and_head_have_exact_multipart_length(self):
        for method in ['GET','HEAD']:
            with self.subTest(method=method):
                messages=self.collect(method=method,headers={'Range':'bytes=0-2,8-11'})
                self.assertEqual(messages[0]['status'],206)
                headers=self.headers(messages);self.assertIn(b'multipart/byteranges',headers[b'content-type'])
                if method=='GET':
                    body=self.body(messages);self.assertEqual(len(body),int(headers[b'content-length']))
                    self.assertIn(self.content[0:3],body);self.assertIn(self.content[8:12],body)
                    self.assertIn(b'Content-Range: bytes 0-2/',body)
                else:self.assertEqual(self.body(messages),b'')

    def test_overlapping_ranges_merge_like_starlette(self):
        messages=self.collect(headers={'Range':'bytes=0-4,2-8'})
        self.assertEqual(self.body(messages),self.content[:9]);self.assertEqual(self.headers(messages)[b'content-range'],f'bytes 0-8/{len(self.content)}'.encode())

    def test_unsatisfiable_and_malformed_ranges_close_fds(self):
        for value,status in [('bytes=9999-',416),('bytes=-0',416),('bad',400),('items=0-1',400),
                             ('bytes=5-3',400),('bytes=5-4',400),('bytes=',400),('bytes=0-1,'*30,400)]:
            with self.subTest(value=value):
                opened=self.track_open();messages=self.collect(headers={'Range':value})
                self.assertEqual(messages[0]['status'],status)
                if status==416:self.assertEqual(self.headers(messages)[b'content-range'],f'bytes */{len(self.content)}'.encode())
                self.assert_closed(opened)

    def test_if_range_etag_date_and_mismatch(self):
        full=self.collect();headers=self.headers(full)
        for conditional in [headers[b'etag'].decode(),headers[b'last-modified'].decode(),'"mismatch"']:
            messages=self.collect(headers={'Range':'bytes=0-2','If-Range':conditional})
            expected=self.content if conditional=='"mismatch"' else self.content[:3]
            self.assertEqual(self.body(messages),expected)

    def test_malformed_range_text_is_preserved_and_head_omits_body(self):
        messages=self.collect(headers={'Range':'wrong'})
        self.assertEqual(messages[0]['status'],400)
        self.assertEqual(self.body(messages),b'Malformed range header.')
        head=self.collect(method='HEAD',headers={'Range':'wrong'})
        self.assertEqual(self.body(head),b'')
        self.assertEqual(self.headers(head)[b'content-length'],str(len(b'Malformed range header.')).encode())

    def test_same_inode_change_before_headers_is_not_sent(self):
        original=download.open_verified
        def changed(*args):
            value=original(*args);self.path.write_bytes(b'x'*len(self.content));return value
        with patch.object(download,'open_verified',side_effect=changed),self.assertRaises(HTTPException) as error:self.collect()
        self.assertEqual(error.exception.status_code,409)

    def test_same_inode_change_during_stream_aborts_before_changed_block(self):
        self.content=b'a'*(download.CHUNK_SIZE*3);self.path.write_bytes(self.content);opened=self.track_open();sent=[]
        async def mutate(message):
            if message['type']=='http.response.body' and message.get('body') and not sent:
                sent.append(message['body']);self.path.write_bytes(b'b'*len(self.content))
        with self.assertRaisesRegex(RuntimeError,'DOCUMENT_DOWNLOAD_INTERRUPTED'):
            self.collect(send_hook=mutate)
        self.assertEqual(sent,[self.content[:download.CHUNK_SIZE]]);self.assert_closed(opened)

    def test_disconnect_send_error_closes_fd(self):
        opened=self.track_open()
        async def disconnected(message):raise OSError('synthetic transport disconnect')
        with self.assertRaises(download.ClientDisconnect):self.collect(send_hook=disconnected)
        self.assert_closed(opened)

    def test_read_error_after_headers_aborts_safely_and_closes_fd(self):
        opened=self.track_open();real=os.pread;calls=0
        def fail(*args):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError(errno.EIO,'private path SECRET')
            return real(*args)
        with patch.object(download.os,'pread',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'^DOCUMENT_DOWNLOAD_INTERRUPTED$'):self.collect()
        self.assert_closed(opened)

    def test_asgi_receive_disconnect_during_body_closes_fd_for_both_specs(self):
        for spec in ['2.0','2.4']:
            with self.subTest(spec=spec):
                opened=self.track_open()
                async def run():
                    entered=asyncio.Event()
                    async def send(message):
                        if message['type']=='http.response.body' and message.get('body'):
                            entered.set();await asyncio.sleep(1)
                    async def receive():await entered.wait();return {'type':'http.disconnect'}
                    await self.response()({'type':'http','method':'GET','headers':[],'asgi':{'spec_version':spec}},receive,send)
                asyncio.run(run());self.assert_closed(opened)

    def test_cancel_during_open_drains_thread_and_closes_transferred_fd(self):
        entered,release=threading.Event(),threading.Event();opened=[];original=download.open_verified
        def delayed(*args):
            value=original(*args);opened.append((value,value.fd));entered.set()
            if not release.wait(5):raise AssertionError('synthetic gate timeout')
            return value
        async def run():
            task=asyncio.create_task(self.collect_async())
            try:
                for _ in range(500):
                    if entered.is_set():break
                    await asyncio.sleep(.005)
                self.assertTrue(entered.is_set());task.cancel();await asyncio.sleep(.01)
                self.assertFalse(task.done())
            finally:release.set()
            with self.assertRaises(asyncio.CancelledError):await task
        with patch.object(download,'open_verified',side_effect=delayed):asyncio.run(run())
        self.assert_closed(opened)

    def test_cancel_during_chunk_read_never_closes_inflight_descriptor(self):
        opened=self.track_open();entered,release=threading.Event(),threading.Event()
        original=download.VerifiedFile.read_at;count=0
        def delayed(value,*args):
            nonlocal count
            count+=1
            if count==2:
                entered.set()
                if not release.wait(5):raise AssertionError('synthetic read gate timeout')
                os.fstat(value.fd)
            return original(value,*args)
        async def run():
            task=asyncio.create_task(self.collect_async())
            try:
                for _ in range(500):
                    if entered.is_set():break
                    await asyncio.sleep(.005)
                self.assertTrue(entered.is_set());task.cancel();await asyncio.sleep(.01)
                self.assertFalse(task.done())
            finally:release.set()
            with self.assertRaises(asyncio.CancelledError):await task
        with patch.object(download.VerifiedFile,'read_at',side_effect=delayed,autospec=True):asyncio.run(run())
        self.assert_closed(opened)

    def test_two_simultaneous_downloads_use_distinct_fds(self):
        opened=[];original=download.open_verified;barrier=threading.Barrier(2)
        def concurrent(*args):
            value=original(*args);opened.append((value,value.fd));barrier.wait(timeout=3);return value
        async def run():return await asyncio.gather(self.collect_async(),self.collect_async())
        with patch.object(download,'open_verified',side_effect=concurrent):results=asyncio.run(run())
        self.assertEqual([self.body(x) for x in results],[self.content]*2)
        self.assertEqual(len(opened),2);self.assertNotEqual(opened[0][1],opened[1][1]);self.assert_closed(opened)

    def test_blocking_read_hash_and_close_run_off_event_loop(self):
        main=threading.get_ident();threads=[];original=os.pread
        def read(*args):threads.append(threading.get_ident());return original(*args)
        with patch.object(download.os,'pread',side_effect=read):self.collect()
        self.assertTrue(threads);self.assertNotIn(main,threads)

    def test_storage_has_no_mutating_calls_and_legacy_name_remains_downloadable(self):
        with ExitStack() as stack:
            for name in ['write','unlink','remove','mkdir','rmdir','rename','replace','chmod','truncate','link','symlink']:
                stack.enter_context(patch.object(download.os,name,side_effect=AssertionError('storage mutation forbidden')))
            messages=self.collect()
        self.assertEqual(self.body(messages),self.content)


class EndpointASGITests(unittest.TestCase):
    def setUp(self):
        self.fixture=DownloadTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.version=SimpleNamespace(id_documento_version=1,id_documento=7,ruta_almacenamiento=self.fixture.rel,
            tamano_bytes=len(self.fixture.content),hash_sha256=hashlib.sha256(self.fixture.content).hexdigest(),
            nombre_original='original.pdf',tipo_mime='text/html')
        self.db=MagicMock();self.db.get.return_value=self.version;self.allowed=True
        self.actor=SimpleNamespace(id_usuario=3,rol='visualizador')
        def database():yield self.db
        from fastapi import Header
        def actor(authorization:str|None=Header(default=None)):
            if authorization!='Bearer synthetic':raise HTTPException(401,'No autorizado')
            return self.actor
        def access(db,user,document):
            self.assertEqual(document,7)
            if not self.allowed:raise HTTPException(403,'Sin acceso documental')
        self.app=download_app(service.models,database,actor,access)
        env=patch.dict(os.environ,{'UPLOAD_ROOT':str(self.fixture.root)});env.start();self.addCleanup(env.stop)
        self.client=TestClient(self.app);self.addCleanup(self.client.close)
        self.url='/documentos/versiones/1/descarga';self.headers={'Authorization':'Bearer synthetic'}

    def test_actual_get_endpoint_binary_and_security_headers_without_sql_writes(self):
        before=vars(self.version).copy();response=self.client.get(self.url,headers=self.headers)
        self.assertEqual(response.status_code,200);self.assertEqual(response.content,self.fixture.content)
        self.assertEqual(response.headers['content-type'],'application/octet-stream')
        self.assertEqual(response.headers['cache-control'],'private, no-store')
        self.assertEqual(response.headers['x-content-type-options'],'nosniff')
        self.assertEqual(vars(self.version),before)
        for name in ['commit','flush','add','delete','execute']:getattr(self.db,name).assert_not_called()

    def test_head_and_range_are_exposed_on_actual_route(self):
        head=self.client.head(self.url,headers=self.headers)
        self.assertEqual(head.status_code,200);self.assertEqual(head.content,b'')
        self.assertEqual(head.headers['content-length'],str(len(self.fixture.content)))
        part=self.client.get(self.url,headers={**self.headers,'Range':'bytes=1-3'})
        self.assertEqual(part.status_code,206);self.assertEqual(part.content,self.fixture.content[1:4])
        self.assertEqual(self.client.get(self.url,headers={**self.headers,'Range':'bytes=999-'}).status_code,416)

    def test_unauthenticated_missing_and_revoked_access_deny_before_storage(self):
        with patch.object(download,'open_verified') as opening:
            self.assertEqual(self.client.get(self.url).status_code,401)
            self.allowed=False;self.assertEqual(self.client.get(self.url,headers=self.headers).status_code,403)
            self.db.get.return_value=None;self.assertEqual(self.client.get(self.url,headers=self.headers).status_code,404)
            opening.assert_not_called()

    def test_corrupt_file_response_is_generic_json_without_storage_details(self):
        self.fixture.path.write_bytes(b'wrong')
        response=self.client.get(self.url,headers=self.headers)
        self.assertEqual(response.status_code,409)
        for secret in [str(self.fixture.root),self.fixture.rel,self.version.hash_sha256]:self.assertNotIn(secret,response.text)

    def test_header_filename_is_sanitized_and_unicode_is_encoded(self):
        self.version.nombre_original='../../private\\caf\u00e9\r\n".pdf'
        response=self.client.get(self.url,headers=self.headers)
        self.assertEqual(response.status_code,200)
        disposition=response.headers['content-disposition']
        self.assertTrue(disposition.startswith('attachment; filename*='));self.assertNotIn('\r',disposition)
        self.assertNotIn('private',disposition);self.assertNotIn('%0D',disposition.upper())


if __name__=='__main__':unittest.main(verbosity=2)
