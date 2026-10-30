"""SS-06 stage 2: real parsers, OS-bounded children, synthetic input, no DB."""
from dataclasses import asdict, replace
import io
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'backend/tests'), str(ROOT / 'tests/security')]
from app.services import document_validation as validator
from _document_samples import minimal_pdf, minimal_png, minimal_jpeg, png_chunk, package, office_parts
import test_document_validation as boundary


def corrupt_cases():
    png = b'\x89PNG\r\n\x1a\n'
    header = lambda width, height: png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    invalid_png = png + header(1, 1) + png_chunk(b'IDAT', b'not zlib') + png_chunk(b'IEND', b'')
    # Same valid compressed scanline as the fixture, but excessive IHDR dimensions.
    huge_png = minimal_png().replace(header(1, 1), header(100000, 100000))
    jpeg = minimal_jpeg(); length = int.from_bytes(jpeg[4:6], 'big')
    invalid_jpeg = jpeg[:2] + jpeg[4 + length:]
    xlsx = office_parts('xlsx'); xlsx['xl/worksheets/sheet1.xml'] = '<worksheet><broken>'
    docx = office_parts(); docx['word/styles.xml'] = '<styles><broken>'
    return [
        (b'%PDF-1.4\nxref\nfalse table\nstartxref\n9\n%%EOF\n', '.pdf'),
        (invalid_png, '.png'), (huge_png, '.png'), (invalid_jpeg, '.jpg'),
        (package(xlsx), '.xlsx'), (package(docx), '.docx'),
    ]


class DeepFormatTests(unittest.TestCase):
    def validate(self, data, extension, limits=None):
        return validator.validate_document(data, extension, None, max_file_bytes=25*1024**2, limits=limits)

    def test_six_reproduced_gaps_are_rejected_by_public_entry_point(self):
        for data, extension in corrupt_cases():
            with self.subTest(extension=extension), self.assertRaises(validator.DocumentValidationError) as caught:
                self.validate(data, extension)
            self.assertEqual(caught.exception.status, 422)

    def test_genuine_generated_images_baseline_and_progressive(self):
        from PIL import Image
        for format, extension, options in [('PNG', '.png', {}), ('JPEG', '.jpg', {}),
                                          ('JPEG', '.jpeg', {'progressive': True})]:
            with self.subTest(extension=extension, options=options):
                out = io.BytesIO(); Image.new('RGB', (8, 8), (25, 80, 150)).save(out, format=format, **options)
                self.assertEqual(self.validate(out.getvalue(), extension), validator.MIME_BY_EXTENSION[extension])

    def test_genuine_xlsx_with_styles_generated_by_openpyxl(self):
        from openpyxl import Workbook
        book = Workbook(); book.active['A1'] = 'SS06 synthetic legitimate workbook'
        out = io.BytesIO(); book.save(out); book.close()
        self.assertEqual(self.validate(out.getvalue(), '.xlsx'), validator.MIME_BY_EXTENSION['.xlsx'])

    def test_genuine_pdf_pages_and_compressed_content(self):
        from pypdf import PdfReader, PdfWriter
        writer = PdfWriter()
        writer.append(PdfReader(io.BytesIO(minimal_pdf())))
        writer.pages[0].compress_content_streams()
        writer.add_blank_page(width=72, height=72)
        out = io.BytesIO(); writer.write(out)
        self.assertEqual(self.validate(out.getvalue(), '.pdf'), 'application/pdf')
        with self.assertRaises(validator.DocumentValidationError) as caught:
            self.validate(out.getvalue(), '.pdf', replace(validator.InspectionLimits(), pdf_pages=1))
        self.assertEqual(caught.exception.code, 'DOCUMENT_PDF_LIMIT')

    def test_genuine_pdf_with_indirect_kids_array(self):
        from pypdf import PdfWriter
        from pypdf.generic import NameObject
        writer = PdfWriter(); writer.add_blank_page(width=72, height=72)
        pages = writer.root_object['/Pages']
        pages[NameObject('/Kids')] = writer._add_object(pages['/Kids'])
        output = io.BytesIO(); writer.write(output)
        self.assertEqual(self.validate(output.getvalue(), '.pdf'), 'application/pdf')

    def test_pdf_dangling_reference_page_cycle_and_false_count(self):
        # Same-size substitutions preserve the original xref offsets.
        pdf = minimal_pdf()
        for data in [pdf.replace(b'/Contents 5 0 R', b'/Contents 9 0 R'),
                     pdf.replace(b'/Kids [3 0 R]', b'/Kids [2 0 R]'),
                     pdf.replace(b'/Count 1', b'/Count 2')]:
            with self.subTest(), self.assertRaises(validator.DocumentValidationError):
                self.validate(data, '.pdf')

    def test_pdf_encrypted_documents_fail_closed(self):
        from pypdf import PdfWriter
        writer = PdfWriter(); writer.add_blank_page(width=72, height=72); writer.encrypt('synthetic')
        out = io.BytesIO(); writer.write(out)
        with self.assertRaises(validator.DocumentValidationError) as caught:
            self.validate(out.getvalue(), '.pdf')
        self.assertEqual(caught.exception.code, 'DOCUMENT_PDF_ENCRYPTED')

    def test_pdf_object_node_stream_and_operator_budgets(self):
        for field in ('pdf_objects', 'pdf_nodes', 'pdf_stream_bytes', 'pdf_operations', 'pdf_depth'):
            with self.subTest(field=field), self.assertRaises(validator.DocumentValidationError) as caught:
                self.validate(minimal_pdf(), '.pdf', replace(validator.InspectionLimits(), **{field: 1}))
            self.assertEqual(caught.exception.code, 'DOCUMENT_PDF_LIMIT')

    def test_image_pixel_dimension_decoded_bytes_and_animation_budgets(self):
        from PIL import Image
        out = io.BytesIO(); Image.new('RGB', (4, 4)).save(out, format='PNG')
        for kwargs in ({'image_pixels': 15}, {'image_dimension': 3}, {'image_decoded_bytes': 63}):
            with self.subTest(kwargs=kwargs), self.assertRaises(validator.DocumentValidationError):
                self.validate(out.getvalue(), '.png', replace(validator.InspectionLimits(), **kwargs))
        out = io.BytesIO()
        Image.new('RGB', (4, 4), 'red').save(out, format='PNG', save_all=True,
            append_images=[Image.new('RGB', (4, 4), 'blue')], duration=100)
        with self.assertRaises(validator.DocumentValidationError):
            self.validate(out.getvalue(), '.png')

    def test_every_secondary_xml_relationship_and_declared_xml_part_is_checked(self):
        for name in ('word/styles.xml', 'word/_rels/document.xml.rels', 'word/custom.part'):
            for payload in ('<unclosed>', '<!DOCTYPE x [<!ENTITY y "synthetic">]><x>&y;</x>'):
                with self.subTest(name=name, payload=payload):
                    parts = office_parts(); parts[name] = payload
                    if name.endswith('.part'):
                        parts['[Content_Types].xml'] = parts['[Content_Types].xml'].replace('</Types>',
                            '<Override PartName="/word/custom.part" ContentType="application/example+xml"/></Types>')
                    with self.assertRaises(validator.DocumentValidationError):
                        self.validate(package(parts), '.docx')

    def test_secondary_xml_uses_shared_nodes_and_per_part_byte_limits(self):
        parts = office_parts(); parts['word/styles.xml'] = '<styles>' + '<s/>'*100 + '</styles>'
        for changes in ({'xml_nodes': 30}, {'xml_bytes': 300}):
            with self.subTest(changes=changes), self.assertRaises(validator.DocumentValidationError) as caught:
                self.validate(package(parts), '.docx', replace(validator.InspectionLimits(), **changes))
            self.assertEqual(caught.exception.code, 'DOCUMENT_XML_LIMIT')

    def test_xml_sheet_root_is_not_just_any_well_formed_xml(self):
        parts = office_parts('xlsx'); parts['xl/worksheets/sheet1.xml'] = '<html/>'
        with self.assertRaises(validator.DocumentValidationError) as caught:
            self.validate(package(parts), '.xlsx')
        self.assertEqual(caught.exception.code, 'DOCUMENT_OOXML_TYPE')


class RejectedBeforeStorageTests(unittest.TestCase):
    setUp = boundary.IntegrationBoundaryTests.setUp
    upload = boundary.IntegrationBoundaryTests.upload
    # Reuse the exact SS-06 service boundary fixture, not a second validator.
    def test_service_runs_validation_outside_the_event_loop_thread(self):
        import threading
        current = threading.get_ident(); observed = []
        def inspect(*args, **kwargs):
            observed.append(threading.get_ident())
            return validator.validate_document(*args, **kwargs)
        self.ns['validate_document'] = inspect
        self.upload(minimal_pdf())
        self.assertEqual(len(observed), 1)
        self.assertNotEqual(observed[0], current)

    def test_six_gaps_never_reach_staging_or_version_registration(self):
        self.ns['stage_document'] = MagicMock(side_effect=AssertionError('must not stage'))
        for data, extension in corrupt_cases():
            with self.subTest(extension=extension), self.assertRaises(boundary.HTTPError) as caught:
                self.upload(data, 'synthetic'+extension, validator.MIME_BY_EXTENSION[extension])
            self.assertEqual(caught.exception.status_code, 422)
        self.ns['stage_document'].assert_not_called()
        self.db.query.assert_not_called(); self.db.add.assert_not_called()
        self.db.flush.assert_not_called(); self.db.commit.assert_not_called()
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])


@unittest.skipUnless(sys.platform == 'linux', 'Linux resource isolation required')
class ProcessIsolationTests(unittest.TestCase):
    def test_real_child_uses_clean_environment_and_does_not_parse_in_parent(self):
        import resource
        before = (resource.getrlimit(resource.RLIMIT_AS), resource.getrlimit(resource.RLIMIT_CPU))
        popen = subprocess.Popen
        with patch.dict(os.environ, {'SS06_SYNTHETIC_SECRET': 'must-not-be-inherited'}), \
             patch.object(validator, '_inspect_document', side_effect=AssertionError('parent parser forbidden')), \
             patch.object(validator.subprocess, 'Popen', wraps=popen) as launch:
            self.assertEqual(validator.validate_document(minimal_pdf(), '.pdf', None, max_file_bytes=65536), 'application/pdf')
        self.assertEqual(before, (resource.getrlimit(resource.RLIMIT_AS), resource.getrlimit(resource.RLIMIT_CPU)))
        args, kwargs = launch.call_args
        self.assertEqual(args[0][1:3], ['-I', '-B'])
        self.assertEqual(set(kwargs['env']), {'PATH', 'LANG', 'LC_ALL'})
        self.assertTrue(kwargs['close_fds']); self.assertTrue(kwargs['start_new_session'])
        self.assertEqual(kwargs['cwd'], '/')
        self.assertEqual(kwargs['stdout'], subprocess.DEVNULL)
        self.assertEqual(kwargs['stderr'], subprocess.DEVNULL)

    def test_two_slots_bound_admission_and_release_after_failures(self):
        gate = validator._INSPECTION_SLOTS
        gate.acquire(); gate.acquire()
        try:
            with patch.object(validator.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
                with self.assertRaises(validator.DocumentValidationError) as caught:
                    validator.validate_document(minimal_pdf(), '.pdf', None, max_file_bytes=65536)
            self.assertEqual((caught.exception.code, caught.exception.status), ('DOCUMENT_INSPECTION_BUSY', 503))
        finally:
            gate.release(); gate.release()
        with patch.object(validator.subprocess, 'Popen', side_effect=OSError('synthetic private path')):
            with self.assertRaises(validator.DocumentValidationError) as caught:
                validator.validate_document(minimal_pdf(), '.pdf', None, max_file_bytes=65536)
        self.assertEqual(caught.exception.status, 503)
        self.assertNotIn('private path', caught.exception.detail)
        self.assertTrue(gate.acquire(blocking=False)); self.assertTrue(gate.acquire(blocking=False))
        gate.release(); gate.release()

    def test_wall_deadline_kills_and_reaps_a_real_stalled_child(self):
        popen = subprocess.Popen; children = []
        def stalled(args, **kwargs):
            child = popen([sys.executable, '-I', '-B', '-c', 'import time; time.sleep(60)'], **kwargs)
            children.append(child); return child
        with patch.object(validator.subprocess, 'Popen', side_effect=stalled):
            with self.assertRaises(validator.DocumentValidationError) as caught:
                validator.validate_document(minimal_pdf(), '.pdf', None, max_file_bytes=65536,
                    limits=replace(validator.InspectionLimits(), worker_seconds=1))
        self.assertEqual(caught.exception.code, 'DOCUMENT_PROCESS_LIMIT')
        self.assertEqual(children[0].returncode, -signal.SIGKILL)
        self.assertIsNotNone(children[0].poll())

    def resource_probe(self, body):
        limits = replace(validator.InspectionLimits(), worker_cpu_seconds=1, worker_memory_bytes=128*1024**2)
        # Replace only the child format callback; exercise the production OS
        # limit setup and exception mapping with small deterministic probes.
        script = f"""import runpy,sys,json
ns=runpy.run_path({str(Path(validator.__file__).resolve())!r})
sys.argv=['worker','--inspect-worker','.pdf','1',{json.dumps(asdict(limits))!r}]
def probe(*args):
{body}
ns['_worker_main'].__globals__['_inspect_document']=probe
raise SystemExit(ns['_worker_main']())
"""
        return subprocess.run([sys.executable, '-I', '-B', '-c', script], input=b'x',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, env={'PATH':os.defpath}, start_new_session=True)

    def test_os_limits_are_effective_before_the_parser(self):
        child = self.resource_probe("""    import resource
    assert resource.getrlimit(resource.RLIMIT_CPU)==(1,1)
    assert resource.getrlimit(resource.RLIMIT_AS)==(128*1024**2,128*1024**2)
    assert resource.getrlimit(resource.RLIMIT_FSIZE)==(0,0)
    assert resource.getrlimit(resource.RLIMIT_CORE)==(0,0)
    assert resource.getrlimit(resource.RLIMIT_NOFILE)==(64,64)""")
        self.assertEqual((child.returncode, child.stdout, child.stderr), (0,b'',b''))

    def test_os_memory_limit_causes_controlled_rejection(self):
        child = self.resource_probe('    bytearray(256*1024**2)')
        self.assertEqual(child.returncode, 20 + validator._WORKER_CODES.index('DOCUMENT_PROCESS_LIMIT'))

    def test_os_cpu_limit_terminates_busy_parser(self):
        child = self.resource_probe('    while True: pass')
        self.assertIn(child.returncode, (-signal.SIGKILL, -signal.SIGXCPU))

    def test_processing_configuration_is_positive_and_cannot_raise_hard_budgets(self):
        for value in ('0','-1','invalid','6'):
            with self.subTest(value=value), patch.dict(os.environ, {'DOCUMENT_INSPECTION_WORKER_SECONDS':value}):
                with self.assertRaises(RuntimeError): validator.load_limits()


if __name__ == '__main__': unittest.main()
