"""SS-06: synthetic files and isolated function bodies, no API/DB startup."""

import ast
import asyncio
from dataclasses import replace
import hashlib
import io
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import uuid
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'backend/tests'))
from app.services import document_validation as validator
from app.services import document_storage as storage
from _document_samples import minimal_pdf, minimal_png, minimal_jpeg, png_chunk, office_parts, package, CT, RELS, OFFICE


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True); self.env.start(); self.addCleanup(self.env.stop)
        self.limits = validator.load_limits()

    def validate(self, content, extension, mime=None, **kwargs):
        return validator.validate_document(content, extension, mime, max_file_bytes=1024 * 1024, **kwargs)

    def rejects(self, content, extension, code=None, **kwargs):
        with self.assertRaises(validator.DocumentValidationError) as caught:
            self.validate(content, extension, **kwargs)
        if code: self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.status, 422)

    def test_all_allowed_extensions_and_canonical_mime(self):
        for extension, content in [('.pdf', minimal_pdf()), ('.png', minimal_png()),
            ('.jpg', minimal_jpeg()), ('.jpeg', minimal_jpeg()),
            ('.docx', package(office_parts('docx'))), ('.xlsx', package(office_parts('xlsx')))]:
            self.assertEqual(self.validate(content, extension), validator.MIME_BY_EXTENSION[extension])
        self.assertEqual(set(validator.MIME_BY_EXTENSION), {'.pdf', '.docx', '.xlsx', '.jpg', '.jpeg', '.png'})

    def test_empty_and_total_size_rejection(self):
        for content, maximum in [(b'', 100), (minimal_pdf(), 1)]:
            with self.assertRaises(validator.DocumentValidationError) as caught:
                validator.validate_document(content, '.pdf', None, max_file_bytes=maximum)
            self.assertEqual(caught.exception.status, 413)

    def test_pdf_text_html_wrong_signature_missing_eof_xref_and_truncation(self):
        valid = minimal_pdf()
        for invalid in [b'plain text', b'<html>synthetic</html>', b'%PDF-1.4\nonly header\n%%EOF\n',
                        valid[:-6], valid.replace(b'startxref', b'not-an-xref'), valid + b'<html>trailing</html>',
                        re.sub(rb'startxref\n\d+', b'startxref\n99999999', valid)]:
            self.rejects(invalid, '.pdf')

    def test_pdf_genuine_incremental_update_and_forged_xref_stream(self):
        from pypdf import PdfWriter
        valid = minimal_pdf()
        writer = PdfWriter(io.BytesIO(valid), incremental=True)
        writer.add_metadata({'/Title': 'SS06 genuine incremental update'})
        output = io.BytesIO(); writer.write(output)
        self.assertEqual(self.validate(output.getvalue(), '.pdf'), 'application/pdf')
        # A pointer to an ordinary object is not a valid XRef stream.
        offset = valid.index(b'1 0 obj')
        wrapped = valid + f'\nstartxref\n{offset}\n%%EOF\n'.encode()
        self.rejects(wrapped, '.pdf')

    def test_png_truncation_crc_dimensions_and_arbitrary_signature_bytes(self):
        valid = minimal_png()
        corrupt = bytearray(valid); corrupt[30] ^= 1
        zero_dimensions = b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 0, 1, 8, 2, 0, 0, 0))
        for data in [valid[:8] + b'arbitrary', valid[:-1], bytes(corrupt), zero_dimensions,
                     valid + b'trailing', b'wrong' + valid]:
            self.rejects(data, '.png')

    def test_png_requires_idat_iend_and_indexed_palette(self):
        header = b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 3, 0, 0, 0))
        self.rejects(header + png_chunk(b'IEND', b''), '.png')
        self.rejects(header + png_chunk(b'IDAT', b'not decoded') + png_chunk(b'IEND', b''), '.png')

    def test_image_record_budget_and_invalid_config(self):
        self.rejects(minimal_png(), '.png', 'DOCUMENT_IMAGE_COMPLEXITY', limits=replace(self.limits, image_records=1))
        self.rejects(minimal_jpeg(), '.jpg', 'DOCUMENT_IMAGE_COMPLEXITY', limits=replace(self.limits, image_records=1))
        for value in ['0', '-1', 'invalid']:
            with patch.dict(os.environ, {'DOCUMENT_INSPECTION_ENTRIES': value}):
                with self.assertRaises(RuntimeError): validator.load_limits()

    def test_jpeg_invalid_segment_lengths_missing_frame_scan_and_eoi(self):
        valid = minimal_jpeg()
        for data in [b'\xff\xd8arbitrary\xff\xd9', valid[:-2], valid + b'junk', valid[:2] + b'\xff\xdb\x00\x01' + valid[8:],
                     valid.replace(b'\xff\xc0', b'\xff\xe0', 1), valid[:valid.index(b'\xff\xda')] + b'\xff\xd9']:
            self.rejects(data, '.jpg')

    def test_ooxml_transitional_strict_stored_and_deflated(self):
        for extension in ['docx', 'xlsx']:
            for strict in [False, True]:
                for compression in [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED]:
                    data = package(office_parts(extension, strict=strict), compression)
                    self.assertEqual(self.validate(data, '.' + extension), validator.MIME_BY_EXTENSION['.' + extension])

    def test_generic_zip_renamed_and_docx_xlsx_type_confusion(self):
        for extension in ['.docx', '.xlsx']:
            self.rejects(package({'hello.txt': 'synthetic'}), extension, 'DOCUMENT_OOXML_PARTS')
        self.rejects(package(office_parts('docx')), '.xlsx')
        self.rejects(package(office_parts('xlsx')), '.docx')

    def test_ooxml_missing_parts_wrong_root_main_content_type_and_macro_main(self):
        for target in ['[Content_Types].xml', '_rels/.rels', 'word/document.xml']:
            parts = office_parts(); del parts[target]
            self.rejects(package(parts), '.docx', 'DOCUMENT_OOXML_PARTS')
        for root in ['<html/>', '<word/>', '<document xmlns="urn:wrong"><body/></document>']:
            parts = office_parts(); parts['word/document.xml'] = root
            self.rejects(package(parts), '.docx', 'DOCUMENT_OOXML_TYPE')
        parts = office_parts(); parts['[Content_Types].xml'] = parts['[Content_Types].xml'].replace(
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml',
            'application/vnd.ms-word.document.macroEnabled.main+xml')
        self.rejects(package(parts), '.docx', 'DOCUMENT_OOXML_TYPE')

    def test_xlsx_sheet_links_must_resolve_to_declared_existing_internal_parts(self):
        for operation in ['missing', 'external', 'wrong_type', 'unknown_id', 'missing_id']:
            parts = office_parts('xlsx')
            if operation == 'missing': del parts['xl/worksheets/sheet1.xml']
            if operation == 'external': parts['xl/_rels/workbook.xml.rels'] = parts['xl/_rels/workbook.xml.rels'].replace(
                'Target="worksheets/sheet1.xml"', 'TargetMode="External" Target="https://qa.invalid/sheet.xml"')
            if operation == 'wrong_type': parts['xl/_rels/workbook.xml.rels'] = parts['xl/_rels/workbook.xml.rels'].replace('/worksheet"', '/not-a-sheet"')
            if operation == 'unknown_id': parts['xl/workbook.xml'] = parts['xl/workbook.xml'].replace('r:id="rId1"', 'r:id="missing"')
            if operation == 'missing_id': parts['xl/workbook.xml'] = parts['xl/workbook.xml'].replace('r:id="rId1"', '')
            self.rejects(package(parts), '.xlsx', 'DOCUMENT_OOXML_RELATIONSHIP')

    def test_office_root_relationship_external_or_ambiguous_rejected(self):
        for replacement in ['TargetMode="External" Target="https://qa.invalid/document.xml"', 'Target="other.xml"']:
            parts = office_parts(); parts['_rels/.rels'] = parts['_rels/.rels'].replace('Target="word/document.xml"', replacement)
            self.rejects(package(parts), '.docx', 'DOCUMENT_OOXML_RELATIONSHIP')

    def test_malformed_xml_and_dtd_entities_rejected_even_utf16(self):
        for text in ['<unclosed>', '<!DOCTYPE root [<!ENTITY x "small synthetic">]><root>&x;</root>',
                     '<!DOCTYPE root SYSTEM "file:///SS06_NOT_READ"><root/>']:
            for encoding in ['utf-8', 'utf-16']:
                parts = office_parts(); parts['word/document.xml'] = text.encode(encoding)
                with patch('builtins.open', side_effect=AssertionError('no external resource access')):
                    self.rejects(package(parts), '.docx')

    def test_xml_byte_node_depth_budgets(self):
        data = package(office_parts())
        for changes in [dict(xml_bytes=10), dict(xml_nodes=1), dict(xml_depth=1)]:
            self.rejects(data, '.docx', 'DOCUMENT_XML_LIMIT', limits=replace(self.limits, **changes))

    def test_zip_preflight_limits_before_zipfile_object_allocation(self):
        data = package(office_parts())
        for changes in [dict(entries=2), dict(directory_bytes=1)]:
            with patch.object(validator.zipfile, 'ZipFile', side_effect=AssertionError('must reject before indexing')):
                with self.assertRaises(validator.DocumentValidationError) as error:
                    validator._ooxml(data, '.docx', replace(self.limits, **changes))
                self.assertEqual(error.exception.code, 'DOCUMENT_ZIP_LIMIT')
        # Lie about declared entry count; observed central records still checked.
        forged = bytearray(data); end = forged.rfind(b'PK\x05\x06')
        struct.pack_into('<HH', forged, end + 8, 1, 1)
        with patch.object(validator.zipfile, 'ZipFile', side_effect=AssertionError('must reject before indexing')):
            with self.assertRaises(validator.DocumentValidationError) as error:
                validator._ooxml(bytes(forged), '.docx', self.limits)
            self.assertEqual(error.exception.code, 'DOCUMENT_ZIP_INVALID')

    def test_zip_profile_crc_truncation_prefix_trailing_data_and_zip64_rejected(self):
        data = package(office_parts(), zipfile.ZIP_STORED)
        bad_crc = bytearray(data)
        content = data.index(b'<Types'); bad_crc[content + 1] ^= 1
        encrypted = bytearray(data); central = encrypted.index(b'PK\x01\x02')
        flags = struct.unpack_from('<H', encrypted, central + 8)[0]; struct.pack_into('<H', encrypted, central + 8, flags | 1)
        zip64 = bytearray(data); end = zip64.rfind(b'PK\x05\x06'); struct.pack_into('<HH', zip64, end + 8, 65535, 65535)
        for value in [bytes(bad_crc), data[:-1], b'prefix' + data, data + b'trailing', bytes(encrypted), bytes(zip64)]:
            self.rejects(value, '.docx')

    def test_zip_paths_symlinks_duplicates_and_special_entries(self):
        for name in ['../escape', '/absolute', 'a/../escape', 'a\\escape', 'a/%2e%2e/escape', 'a/%5cescape', 'C:/file']:
            parts = office_parts(); parts[name] = 'synthetic'
            self.rejects(package(parts), '.docx', 'DOCUMENT_ZIP_PATH')
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            for name, value in office_parts().items(): archive.writestr(name, value)
            info = zipfile.ZipInfo('link'); info.create_system = 3; info.external_attr = (0o120777 << 16)
            archive.writestr(info, 'synthetic-target')
        self.rejects(output.getvalue(), '.docx', 'DOCUMENT_ZIP_PATH')
        parts = office_parts(); parts['WORD/document.xml'] = '<synthetic/>'
        self.rejects(package(parts), '.docx', 'DOCUMENT_ZIP_PATH')

    def test_declared_member_total_and_observed_extraction_limits(self):
        data = package(office_parts())
        for changes in [dict(member_bytes=1), dict(expanded_bytes=1)]:
            self.rejects(data, '.docx', 'DOCUMENT_ZIP_LIMIT', limits=replace(self.limits, **changes))
        infos = [zipfile.ZipInfo(name) for name in office_parts()]
        archive = MagicMock(); archive.__enter__.return_value = archive; archive.infolist.return_value = infos
        stream = io.BytesIO(b'xx'); archive.open.return_value = stream
        with patch.object(validator.zipfile, 'ZipFile', return_value=archive):
            with self.assertRaises(validator.DocumentValidationError) as error:
                validator._ooxml(data, '.docx', replace(self.limits, member_bytes=1))
            self.assertEqual(error.exception.code, 'DOCUMENT_ZIP_LIMIT')
        self.assertTrue(stream.closed); archive.__exit__.assert_called_once()

    def test_client_mime_generic_alias_normalization_and_mismatch(self):
        for mime in [None, '', 'application/octet-stream', 'binary/octet-stream', 'Application/PDF; charset=x', 'application/x-pdf']:
            self.assertEqual(self.validate(minimal_pdf(), '.pdf', mime), 'application/pdf')
        for mime in ['text/html', 'image/png', 'application/zip']:
            self.rejects(minimal_pdf(), '.pdf', 'DOCUMENT_MIME_MISMATCH', mime=mime)
        self.assertEqual(self.validate(package(office_parts()), '.docx', 'application/zip'), validator.MIME_BY_EXTENSION['.docx'])
        self.assertEqual(self.validate(minimal_jpeg(), '.jpeg', 'image/jpg'), 'image/jpeg')

    def test_real_pixel_decode_and_embedded_binary_limitation(self):
        # Correct framing/CRCs do not make an invalid pixel stream acceptable.
        data = b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
        data += png_chunk(b'IDAT', b'synthetic not zlib') + png_chunk(b'IEND', b'')
        self.rejects(data, '.png')
        # Ancillary Office binaries are checked for CRC/budget, not disarmed.
        parts = office_parts(); parts['word/embeddings/synthetic.bin'] = b'INERT SYNTHETIC EMBEDDED OBJECT'
        self.assertEqual(self.validate(package(parts), '.docx'), validator.MIME_BY_EXTENSION['.docx'])


class HTTPError(Exception):
    def __init__(self, status_code, detail): self.status_code, self.detail = status_code, detail


class Version:
    id_documento = MagicMock(); hash_sha256 = MagicMock(); numero_version = MagicMock()
    def __init__(self, **kwargs): self.__dict__.update(kwargs)


def service_functions():
    tree = ast.parse((ROOT / 'backend/app/services/documents.py').read_text())
    names = {'store_version', '_safe_original_name', 'upload_root', 'safe_version_path'}
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    from starlette.concurrency import run_in_threadpool
    ns = dict(run_in_threadpool=run_in_threadpool, Path=Path, os=os, re=re, uuid=uuid, hashlib=hashlib, func=MagicMock(),
        ALLOWED_EXTENSIONS={'.pdf', '.docx', '.xlsx', '.jpg', '.jpeg', '.png'}, MAX_UPLOAD_BYTES=65536,
        models=SimpleNamespace(DocumentoVersion=Version), require_document_access=MagicMock(),
        set_audit_context=MagicMock(), HTTPException=HTTPError,
        DocumentStorageError=storage.DocumentStorageError, stage_document=storage.stage_document,
        storage_event=MagicMock(),
        DocumentValidationError=validator.DocumentValidationError, validate_document=validator.validate_document)
    future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[])), 'isolated_documents', 'exec'), ns)
    return ns


class IntegrationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(); self.addCleanup(self.directory.cleanup)
        self.env = patch.dict(os.environ, {'UPLOAD_ROOT': self.directory.name}, clear=True)
        self.env.start(); self.addCleanup(self.env.stop)
        self.ns = service_functions(); self.user = SimpleNamespace(id_usuario=3)
        self.db = MagicMock(); q = self.db.query.return_value
        q.filter.return_value = q; q.first.return_value = None; q.scalar.return_value = 0

    def upload(self, data, name='document.pdf', mime='application/pdf'):
        calls = []
        async def read(maximum): calls.append(maximum); return data[:maximum]
        result = asyncio.run(self.ns['store_version'](self.db, 7,
            SimpleNamespace(filename=name, content_type=mime, read=read), self.user))
        self.assertEqual(calls, [65537]); return result

    def test_canonical_mime_persisted_raw_bytes_sha_name_and_version_unchanged(self):
        data = minimal_pdf()
        result = self.upload(data, '../synthetic.pdf', 'application/octet-stream')
        self.assertEqual(result.tipo_mime, 'application/pdf')
        self.assertEqual(result.hash_sha256, hashlib.sha256(data).hexdigest())
        self.assertEqual(result.nombre_original, 'synthetic.pdf')
        self.assertEqual((result.numero_version, result.tamano_bytes), (1, len(data)))
        self.assertEqual((Path(self.directory.name) / result.ruta_almacenamiento).read_bytes(), data)
        self.ns['require_document_access'].assert_called_once_with(self.db, self.user, 7, mode='capture')
        self.db.commit.assert_called_once()

    def test_invalid_content_or_mime_rejected_before_version_lookup_or_file_write(self):
        for data, name, mime, status in [(b'<html>SS06 SYNTH PII</html>', 'fake.pdf', 'application/pdf', 422),
            (minimal_pdf(), 'fake.pdf', 'text/html', 422), (b'', 'empty.pdf', None, 413),
            (b'x' * 65537, 'large.pdf', 'application/pdf', 413), (b'x', 'bad.exe', None, 422)]:
            with self.subTest(name=name), self.assertRaises(HTTPError) as caught:
                self.upload(data, name, mime)
            self.assertEqual(caught.exception.status_code, status)
            self.assertNotIn('SS06 SYNTH PII', caught.exception.detail)
        self.db.query.assert_not_called(); self.db.add.assert_not_called(); self.db.commit.assert_not_called()
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    def test_authorization_precedes_read_validation_or_write(self):
        self.ns['require_document_access'].side_effect = HTTPError(403, 'denied')
        with self.assertRaises(HTTPError): self.upload(minimal_pdf())
        self.db.query.assert_not_called()
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    def test_duplicate_and_commit_failure_keep_existing_behavior(self):
        self.db.query.return_value.first.return_value = Version(id_documento=7)
        with self.assertRaises(HTTPError) as caught: self.upload(minimal_pdf())
        self.assertEqual(caught.exception.status_code, 409)
        self.db.query.return_value.first.return_value = None
        self.db.commit.side_effect = RuntimeError('SS06 SYNTH DRIVER DETAIL')
        with self.assertRaises(HTTPError) as caught: self.upload(minimal_pdf())
        self.assertEqual(caught.exception.status_code, 409)
        # SS-12: commit may already have succeeded when its response is lost.
        # Preserve the published file; only this operation's staging is cleaned.
        retained = list(Path(self.directory.name).rglob('*.pdf'))
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0].read_bytes(), minimal_pdf())
        self.assertEqual(list(Path(self.directory.name).rglob('.pending-*')), [])
        self.db.rollback.assert_called_once()

    def download(self, version, denied=False):
        tree = ast.parse((ROOT / 'backend/app/routers/documents.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'download_version')
        node.decorator_list = []
        ns = dict(Depends=lambda *args: None, get_db=None, auth=SimpleNamespace(RoleChecker=lambda roles: None),
            READ_ROLES=['admin', 'operador', 'visualizador', 'geografo'], HTTPException=HTTPError,
            models=SimpleNamespace(DocumentoVersion=Version), FileResponse=lambda *a, **kw: SimpleNamespace(args=a, kwargs=kw),
            service=SimpleNamespace(safe_version_path=MagicMock(return_value=Path('/tmp/synthetic-only'))),
            require_document_access=MagicMock(side_effect=HTTPError(403, 'denied') if denied else None),
            download_media_type=validator.download_media_type)
        future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[future, node], type_ignores=[])), 'isolated_download', 'exec'), ns)
        db = MagicMock(); db.get.return_value = version
        result = ns['download_version'](1, db=db, user=self.user)
        db.commit.assert_not_called()
        if version is not None: ns['require_document_access'].assert_called_once_with(db, self.user, version.id_documento)
        return result

    def test_new_and_legacy_downloads_never_use_unverified_mime_or_mutate_history(self):
        for mime in ['text/html', 'application/pdf', None, 'image/svg+xml', 'bad\r\nInjected: value']:
            version = Version(id_documento=7, nombre_original='original.pdf', tipo_mime=mime)
            before = vars(version).copy()
            response = self.download(version)
            self.assertEqual(response.kwargs['media_type'], 'application/octet-stream')
            self.assertEqual(response.kwargs['filename'], 'original.pdf')
            self.assertEqual(response.kwargs['content_disposition_type'], 'attachment')
            self.assertEqual(response.kwargs['headers'], {'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, no-store'})
            self.assertEqual(vars(version), before)

    def test_download_missing_and_denied_versions_keep_access_control(self):
        with self.assertRaises(HTTPError) as error: self.download(None)
        self.assertEqual(error.exception.status_code, 404)
        with self.assertRaises(HTTPError) as error: self.download(Version(id_documento=7), denied=True)
        self.assertEqual(error.exception.status_code, 403)

    def test_safe_path_and_allowed_extension_set_are_preserved(self):
        with self.assertRaises(HTTPError): self.ns['safe_version_path'](Version(ruta_almacenamiento='../outside.pdf'))
        self.assertNotIn('app.database', sys.modules); self.assertNotIn('app.main', sys.modules)


if __name__ == '__main__': unittest.main()
