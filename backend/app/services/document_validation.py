"""Bounded document inspection in a disposable Linux process.

One validation entry point; original bytes are never rewritten. Format parsing
is not malware scanning, rendering, signature verification or OOXML certification.
The child has resource limits, not a separate UID/filesystem/network namespace.
"""

from dataclasses import asdict, dataclass
import io
import json
import logging
import os
from pathlib import Path
import posixpath
import re
import stat
import signal
import subprocess
import sys
import threading
import warnings
import struct
from urllib.parse import unquote, urlsplit
from xml.parsers import expat
import zipfile
import zlib


MIME_BY_EXTENSION = {
    '.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
}
_ALIASES = {'.pdf': {'application/x-pdf'}, '.jpg': {'image/jpg', 'image/pjpeg'},
            '.jpeg': {'image/jpg', 'image/pjpeg'}, '.png': {'image/x-png'}}
_GENERIC = {'', 'application/octet-stream', 'binary/octet-stream'}
_CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
_RELS = 'http://schemas.openxmlformats.org/package/2006/relationships'
_OFFICE = ('http://schemas.openxmlformats.org/officeDocument/2006/relationships',
           'http://purl.oclc.org/ooxml/officeDocument/relationships')
_WORD = ('http://schemas.openxmlformats.org/wordprocessingml/2006/main',
         'http://purl.oclc.org/ooxml/wordprocessingml/main')
_SHEET = ('http://schemas.openxmlformats.org/spreadsheetml/2006/main',
          'http://purl.oclc.org/ooxml/spreadsheetml/main')
_MAIN_TYPES = {
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml',
}
_SHEET_TYPES = {'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.chartsheet+xml'}


class DocumentValidationError(Exception):
    def __init__(self, code, detail='El contenido no corresponde a un formato documental permitido.', status=422):
        self.code, self.detail, self.status = code, detail, status
        super().__init__(detail)


@dataclass(frozen=True)
class InspectionLimits:
    entries: int = 2048
    directory_bytes: int = 4 * 1024 * 1024
    expanded_bytes: int = 100 * 1024 * 1024
    member_bytes: int = 32 * 1024 * 1024
    xml_bytes: int = 8 * 1024 * 1024
    xml_nodes: int = 100_000
    xml_depth: int = 64
    image_records: int = 4096
    image_pixels: int = 20_000_000
    image_dimension: int = 16_384
    image_decoded_bytes: int = 160 * 1024 * 1024
    pdf_pages: int = 1000
    pdf_objects: int = 100_000
    pdf_nodes: int = 200_000
    pdf_depth: int = 64
    pdf_operations: int = 100_000
    pdf_stream_bytes: int = 100 * 1024 * 1024
    worker_cpu_seconds: int = 3
    worker_seconds: int = 5
    worker_memory_bytes: int = 512 * 1024 * 1024


def load_limits():
    defaults = InspectionLimits()
    values = {}
    for name in defaults.__dataclass_fields__:
        variable = 'DOCUMENT_INSPECTION_' + name.upper()
        try:
            value = int(os.getenv(variable, str(getattr(defaults, name))))
        except ValueError as exc:
            raise RuntimeError(f'{variable} requiere un entero positivo') from exc
        if value <= 0:
            raise RuntimeError(f'{variable} requiere un entero positivo')
        # New processing budgets can be lowered, never silently made unbounded.
        if name in _PROCESSING_FIELDS and value > getattr(defaults, name):
            raise RuntimeError(f'{variable} excede el máximo de inspección')
        values[name] = value
    return InspectionLimits(**values)


def _reject(code='DOCUMENT_FORMAT_INVALID'):
    raise DocumentValidationError(code)


def _pdf_envelope(data):
    if not re.match(rb'%PDF-(?:1\.[0-7]|2\.0)(?:\r\n|\r|\n)', data[:16]):
        _reject()
    tail = re.search(rb'startxref[\x00\t\n\x0c\r ]+([0-9]{1,20})[\x00\t\n\x0c\r ]+%%EOF[\x00\t\n\x0c\r ]*\Z', data[-4096:])
    if tail is None:
        _reject()
    offset = int(tail.group(1))
    target = data[offset:offset + 64] if 0 < offset < len(data) else b''
    if not (re.match(rb'xref[\x00\t\n\x0c\r ]', target)
            or re.match(rb'[0-9]{1,10}\s+[0-9]{1,10}\s+obj(?:\s|<)', target)):
        _reject()


def _png(data, limits):
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        _reject()
    position, count, image_data, palette, color = 8, 0, False, False, None
    while position + 12 <= len(data):
        count += 1
        if count > limits.image_records:
            _reject('DOCUMENT_IMAGE_COMPLEXITY')
        size = int.from_bytes(data[position:position + 4], 'big')
        kind = data[position + 4:position + 8]
        end = position + 12 + size
        if end > len(data) or not all(65 <= c <= 90 or 97 <= c <= 122 for c in kind):
            _reject()
        payload = memoryview(data)[position + 8:position + 8 + size]
        crc = zlib.crc32(payload, zlib.crc32(kind)) & 0xffffffff
        if crc != int.from_bytes(data[end - 4:end], 'big'):
            _reject()
        if count == 1:
            if kind != b'IHDR' or size != 13:
                _reject()
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
            if (not 0 < width < 2**31 or not 0 < height < 2**31 or depth not in depths.get(color, set())
                    or compression != 0 or filtering != 0 or interlace not in (0, 1)):
                _reject()
        elif kind == b'IHDR':
            _reject()
        if kind == b'PLTE':
            if image_data or not size or size % 3 or size > 768:
                _reject()
            palette = True
        if kind == b'IDAT':
            if color == 3 and not palette:
                _reject()
            image_data = image_data or size > 0
        if kind == b'IEND':
            if size != 0 or end != len(data) or not image_data:
                _reject()
            return
        position = end
    _reject()


def _jpeg(data, limits):
    if not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9'):
        _reject()
    position, count, frame = 2, 0, False
    sof = {0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf}
    while position < len(data) - 2:
        count += 1
        if count > limits.image_records:
            _reject('DOCUMENT_IMAGE_COMPLEXITY')
        if data[position] != 0xff:
            _reject()
        while position < len(data) and data[position] == 0xff:
            position += 1
        if position + 3 > len(data):
            _reject()
        marker = data[position]
        position += 1
        if marker == 0x01:  # TEM has no length field.
            continue
        if marker in {0x00, 0xd8, 0xd9, *range(0xd0, 0xd8)}:
            _reject()
        size = int.from_bytes(data[position:position + 2], 'big')
        if size < 2 or position + size > len(data) - 2:
            _reject()
        if marker in sof:
            if size < 8 or data[position + 7] == 0 or size != 8 + 3 * data[position + 7]:
                _reject()
            if not int.from_bytes(data[position + 3:position + 5], 'big') or not int.from_bytes(data[position + 5:position + 7], 'big'):
                _reject()
            frame = True
        if marker == 0xda:  # Stop at SOS: no entropy decoding or scan traversal.
            if not frame or size < 6 or data[position + 2] == 0 or size != 6 + 2 * data[position + 2]:
                _reject()
            if position + size >= len(data) - 2:
                _reject()
            return
        position += size
    _reject()


def _zip_preflight(data, limits):
    """Bound/index the classic central directory before ZipFile allocates it.

    This does not replace zipfile: classic directory/EOCD only, no multipart,
    prefix or trailing containers. Local header extras are handled by zipfile.
    Count observed central records too, not just untrusted EOCD declarations.
    """
    eocd = data.rfind(b'PK\x05\x06', max(0, len(data) - 65557))
    if eocd < 0 or eocd + 22 > len(data) or not data.startswith(b'PK\x03\x04'):
        _reject('DOCUMENT_ZIP_INVALID')
    _, disk, start_disk, on_disk, entries, directory_size, offset, comment = struct.unpack_from('<4s4H2IH', data, eocd)
    if (disk or start_disk or entries != on_disk or entries == 65535 or directory_size == 0xffffffff
            or offset == 0xffffffff or eocd + 22 + comment != len(data) or offset + directory_size != eocd):
        _reject('DOCUMENT_ZIP_PROFILE')
    if entries > limits.entries or directory_size > limits.directory_bytes:
        _reject('DOCUMENT_ZIP_LIMIT')
    count, position = 0, offset
    while position < eocd:
        count += 1
        if count > limits.entries:
            _reject('DOCUMENT_ZIP_LIMIT')
        if position + 46 > eocd or data[position:position + 4] != b'PK\x01\x02':
            _reject('DOCUMENT_ZIP_INVALID')
        lengths = struct.unpack_from('<3H', data, position + 28)
        position += 46 + sum(lengths)
        if position > eocd:
            _reject('DOCUMENT_ZIP_INVALID')
    if count != entries or not count:
        _reject('DOCUMENT_ZIP_INVALID')


class _XmlSummary:
    """Bounded Expat metadata only; no tree, DTD, entities or resource loads."""
    def __init__(self, limits, nodes):
        self.root, self.body, self.sheets = None, False, []
        self.overrides, self.defaults, self.relationships = {}, {}, []
        self.depth, self.bytes, self.nodes, self.limits = 0, 0, nodes, limits
        self.stack = []
        self.parser = expat.ParserCreate(namespace_separator='}')
        if hasattr(self.parser, 'SetReparseDeferralEnabled'):
            self.parser.SetReparseDeferralEnabled(True)
        self.parser.StartElementHandler = self.start
        self.parser.EndElementHandler = self.end
        self.parser.StartDoctypeDeclHandler = self.forbidden
        self.parser.EntityDeclHandler = self.forbidden
        self.parser.ExternalEntityRefHandler = self.forbidden
        self.parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)

    def forbidden(self, *args):
        _reject('DOCUMENT_XML_DTD')

    def start(self, name, attrs):
        parent = self.stack[-1] if self.stack else None
        self.stack.append(name)
        self.depth += 1; self.nodes[0] += 1
        if self.depth > self.limits.xml_depth or self.nodes[0] > self.limits.xml_nodes or len(attrs) > 64:
            _reject('DOCUMENT_XML_LIMIT')
        if self.root is None:
            self.root = name
        if name == _CT + '}Override' and parent == _CT + '}Types':
            part = attrs.get('PartName')
            if part in self.overrides:
                _reject('DOCUMENT_OOXML_AMBIGUOUS')
            self.overrides[part] = attrs.get('ContentType')
        elif name == _CT + '}Default' and parent == _CT + '}Types':
            extension = attrs.get('Extension', '').lower()
            if not extension or extension in self.defaults:
                _reject('DOCUMENT_OOXML_AMBIGUOUS')
            self.defaults[extension] = attrs.get('ContentType', '')
        elif name == _RELS + '}Relationship' and parent == _RELS + '}Relationships':
            self.relationships.append(dict(attrs))
        elif name in {ns + '}body' for ns in _WORD} and self.depth == 2:
            self.body = True
        elif name in {ns + '}sheet' for ns in _SHEET} and parent in {ns + '}sheets' for ns in _SHEET} and self.depth == 3:
            self.sheets.append(next((attrs[ns + '}id'] for ns in _OFFICE if ns + '}id' in attrs), None))

    def end(self, name):
        self.depth -= 1
        self.stack.pop()

    def feed(self, block, final=False):
        self.bytes += len(block)
        if self.bytes > self.limits.xml_bytes:
            _reject('DOCUMENT_XML_LIMIT')
        self.parser.Parse(block, final)


def _ooxml(data, extension, limits):
    _zip_preflight(data, limits)
    main = 'word/document.xml' if extension == '.docx' else 'xl/workbook.xml'
    required = {'[Content_Types].xml', '_rels/.rels', main}
    if extension == '.xlsx':
        required.add('xl/_rels/workbook.xml.rels')
    summaries, nodes, expanded = {}, [0], 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if len(infos) > limits.entries:
            _reject('DOCUMENT_ZIP_LIMIT')
        names, folded, declared = set(), set(), 0
        for info in infos:
            name, mode = info.filename, info.external_attr >> 16
            decoded = unquote(name)
            if (not name or info.orig_filename != name or '\\' in decoded or any(ord(c) < 32 or ord(c) == 127 for c in decoded)
                    or ':' in decoded or decoded.startswith('/')
                    or any(p in ('.', '..', '') for p in decoded.rstrip('/').split('/'))
                    or name in names or name.casefold() in folded
                    or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)
                    or stat.S_IFMT(mode) == stat.S_IFDIR and not name.endswith('/')):
                _reject('DOCUMENT_ZIP_PATH')
            names.add(name); folded.add(name.casefold())
            if info.flag_bits & 1 or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                _reject('DOCUMENT_ZIP_PROFILE')
            declared += info.file_size
            if info.file_size > limits.member_bytes or declared > limits.expanded_bytes:
                _reject('DOCUMENT_ZIP_LIMIT')
        if not required <= names:
            _reject('DOCUMENT_OOXML_PARTS')
        # Parse content types first so XML parts with non-.xml names also count.
        infos.sort(key=lambda info: info.filename != '[Content_Types].xml')
        roots = {}
        for info in infos:
            types = summaries.get('[Content_Types].xml')
            content_type = (types.overrides.get('/' + info.filename,
                types.defaults.get(info.filename.rsplit('.', 1)[-1].lower(), '')) if types else '')
            is_xml = (info.filename in required or info.filename.lower().endswith(('.xml', '.rels'))
                or content_type.endswith(('+xml', '/xml')))
            summary = _XmlSummary(limits, nodes) if is_xml else None
            if summary and info.filename in required: summaries[info.filename] = summary
            xml = bytearray() if summary else None
            observed = 0
            with archive.open(info) as stream:
                while block := stream.read(min(65536, limits.member_bytes - observed + 1,
                                                limits.expanded_bytes - expanded + 1)):
                    observed += len(block); expanded += len(block)
                    if observed > limits.member_bytes or expanded > limits.expanded_bytes:
                        _reject('DOCUMENT_ZIP_LIMIT')
                    if summary:
                        if len(xml) + len(block) > limits.xml_bytes:
                            _reject('DOCUMENT_XML_LIMIT')
                        xml.extend(block)
            if observed != info.file_size:
                _reject('DOCUMENT_ZIP_INVALID')
            if summary:
                # One bounded Parse avoids repeated incomplete-token reparsing
                # on older Expat builds; never concatenate the whole archive.
                summary.feed(bytes(xml), True)
                summary.parser = None
                roots[info.filename] = summary.root
                if info.filename.endswith('.rels') and summary.root != _RELS + '}Relationships':
                    _reject('DOCUMENT_OOXML_TYPE')
                if content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml':
                    if summary.root not in {ns + '}styles' for ns in _WORD}:
                        _reject('DOCUMENT_OOXML_TYPE')
        types, relations, content = (summaries['[Content_Types].xml'], summaries['_rels/.rels'], summaries[main])
        if (types.root != _CT + '}Types' or relations.root != _RELS + '}Relationships'
                or types.overrides.get('/' + main) != _MAIN_TYPES[extension]):
            _reject('DOCUMENT_OOXML_TYPE')
        office = [r for r in relations.relationships if r.get('Type') in {ns + '/officeDocument' for ns in _OFFICE}]
        if (len(office) != 1 or not office[0].get('Id') or office[0].get('TargetMode', 'Internal') != 'Internal'
                or office[0].get('Target') not in (main, '/' + main)):
            _reject('DOCUMENT_OOXML_RELATIONSHIP')
        if extension == '.docx':
            if content.root not in {ns + '}document' for ns in _WORD} or not content.body:
                _reject('DOCUMENT_OOXML_TYPE')
        else:
            rels = summaries['xl/_rels/workbook.xml.rels']
            if content.root not in {ns + '}workbook' for ns in _SHEET} or not content.sheets or rels.root != _RELS + '}Relationships':
                _reject('DOCUMENT_OOXML_TYPE')
            by_id = {}
            for rel in rels.relationships:
                if not rel.get('Id') or rel.get('Id') in by_id: _reject('DOCUMENT_OOXML_AMBIGUOUS')
                by_id[rel.get('Id')] = rel
            for sheet in content.sheets:
                if not sheet:
                    _reject('DOCUMENT_OOXML_RELATIONSHIP')
                rel = by_id.get(sheet, {})
                target = urlsplit(rel.get('Target', ''))
                name = posixpath.normpath(posixpath.join('xl', unquote(target.path))) if not target.path.startswith('/') else unquote(target.path).lstrip('/')
                if (rel.get('Type') not in {ns + suffix for ns in _OFFICE for suffix in ('/worksheet', '/chartsheet')}
                        or rel.get('TargetMode', 'Internal') != 'Internal' or target.scheme or target.netloc or target.query or target.fragment
                        or name not in names or types.overrides.get('/' + name) not in _SHEET_TYPES):
                    _reject('DOCUMENT_OOXML_RELATIONSHIP')
                expected = 'chartsheet' if types.overrides['/' + name].endswith('.chartsheet+xml') else 'worksheet'
                if roots.get(name) not in {ns + '}' + expected for ns in _SHEET}:
                    _reject('DOCUMENT_OOXML_TYPE')
            # Well-formed parts and selected roots, not complete OOXML schemas.
            # Embedded binaries/formulas/active content are not disinfected.


def validate_document(data, extension, client_mime, *, max_file_bytes, limits=None):
    extension = extension.lower()
    if extension not in MIME_BY_EXTENSION:
        _reject('DOCUMENT_EXTENSION')
    if not data or len(data) > max_file_bytes:
        raise DocumentValidationError('DOCUMENT_SIZE', 'Archivo vacío o demasiado grande', 413)
    limits = limits or load_limits()
    canonical = MIME_BY_EXTENSION[extension]
    mime = (client_mime or '').split(';', 1)[0].strip().lower()
    permitted = _GENERIC | {canonical} | _ALIASES.get(extension, set())
    if extension in ('.docx', '.xlsx'): permitted |= {'application/zip', 'application/x-zip-compressed'}
    if mime not in permitted:
        raise DocumentValidationError('DOCUMENT_MIME_MISMATCH', 'El tipo MIME declarado es incompatible con el formato comprobado.')
    _inspect_in_process(data, extension, limits)
    return canonical


def download_media_type():
    # No schema/provenance marker distinguishes a validated upload from a legacy
    # row with exactly the same MIME. Conservative for all versions, no rewrites.
    return 'application/octet-stream'


# Fixed exit codes are the only child output: no attacker-controlled diagnostics,
# pickle, stdout accumulation or parser exception details reach the API/logs.
_WORKER_CODES = (
    'DOCUMENT_FORMAT_INVALID', 'DOCUMENT_IMAGE_COMPLEXITY', 'DOCUMENT_ZIP_INVALID',
    'DOCUMENT_ZIP_PROFILE', 'DOCUMENT_ZIP_LIMIT', 'DOCUMENT_ZIP_PATH',
    'DOCUMENT_OOXML_PARTS', 'DOCUMENT_XML_LIMIT', 'DOCUMENT_XML_DTD',
    'DOCUMENT_OOXML_AMBIGUOUS', 'DOCUMENT_OOXML_TYPE', 'DOCUMENT_OOXML_RELATIONSHIP',
    'DOCUMENT_IMAGE_LIMIT', 'DOCUMENT_PDF_LIMIT', 'DOCUMENT_PDF_ENCRYPTED',
    'DOCUMENT_PROCESS_LIMIT',
)
_PROCESSING_FIELDS = frozenset(InspectionLimits.__dataclass_fields__) - {
    'entries', 'directory_bytes', 'expanded_bytes', 'member_bytes',
    'xml_bytes', 'xml_nodes', 'xml_depth', 'image_records',
}
# Per interpreter, immediate refusal instead of an unbounded work queue. Each
# ASGI process/replica has its own cap; aggregate deployment capacity needs QA.
_INSPECTION_SLOTS = threading.BoundedSemaphore(2)


def _image(data, extension, limits):
    from PIL import Image, ImageFile

    Image.MAX_IMAGE_PIXELS = limits.image_pixels
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    expected = 'PNG' if extension == '.png' else 'JPEG'
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(data), formats=[expected]) as image:
            width, height = image.size
            if (image.format != expected or getattr(image, 'n_frames', 1) != 1
                    or max(width, height) > limits.image_dimension
                    or width * height > limits.image_pixels
                    or width * height * max(4, len(image.getbands())) > limits.image_decoded_bytes):
                _reject('DOCUMENT_IMAGE_LIMIT')
            image.verify()
        # verify() deliberately does not decode pixels. Reopen and decode all.
        with Image.open(io.BytesIO(data), formats=[expected]) as image:
            image.load()


def _pdf(data, limits):
    from pypdf import PdfReader
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, StreamObject

    _pdf_envelope(data)

    class RejectRepair(logging.Handler):
        def emit(self, record):
            _reject()  # pypdf can repair even in strict mode; reject warnings.

    logger = logging.getLogger('pypdf')
    handler = RejectRepair(level=logging.WARNING)
    logger.addHandler(handler)
    try:
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            _reject('DOCUMENT_PDF_ENCRYPTED')
        root = reader.trailer['/Root']
        if not isinstance(root, DictionaryObject) or root.get('/Type') != '/Catalog' or '/Pages' not in root:
            _reject()
        # Verify the page tree before pypdf flattens it: /Parent backreferences
        # are legal, but cycles/shared nodes in /Kids and false /Count are not.
        page_nodes = set()

        def pages(ref, parent=None, depth=0):
            if depth > limits.pdf_depth or len(page_nodes) >= limits.pdf_objects:
                _reject('DOCUMENT_PDF_LIMIT')
            node = ref.get_object()
            if not isinstance(node, DictionaryObject) or id(node) in page_nodes:
                _reject()
            page_nodes.add(id(node))
            if parent is not None and ('/Parent' not in node or node['/Parent'] is not parent):
                _reject()
            if node.get('/Type') == '/Page':
                return 1
            if node.get('/Type') != '/Pages' or '/Kids' not in node or not isinstance(node['/Kids'], ArrayObject):
                _reject()
            count = 0
            for child in node['/Kids']:
                count += pages(child, node, depth + 1)
                if count > limits.pdf_pages:
                    _reject('DOCUMENT_PDF_LIMIT')
            if node.get('/Count') != count:
                _reject()
            return count

        count = pages(root.raw_get('/Pages'))
        if not 0 < count <= limits.pdf_pages:
            _reject('DOCUMENT_PDF_LIMIT')
        # These indexed-object APIs are covered against the exact pypdf pin.
        references = []
        for generation, entries in reader.xref.items():
            for number in entries:
                if number and not reader.xref_free_entry.get(generation, {}).get(number, False):
                    references.append(IndirectObject(number, generation, reader))
                    if len(references) > limits.pdf_objects:
                        _reject('DOCUMENT_PDF_LIMIT')
        for number in reader.xref_objStm:
            references.append(IndirectObject(number, 0, reader))
            if len(references) > limits.pdf_objects:
                _reject('DOCUMENT_PDF_LIMIT')
        seen, containers, nodes, expanded = set(), set(), 0, 0
        stack = [(ref, 0) for ref in references] + [(reader.trailer, 0)]
        while stack:
            obj, depth = stack.pop()
            if isinstance(obj, IndirectObject):
                key = obj.idnum, obj.generation
                if key in seen:
                    continue
                indexed = (obj.idnum in reader.xref.get(obj.generation, {})
                    and not reader.xref_free_entry.get(obj.generation, {}).get(obj.idnum, False))
                if not indexed and not (obj.generation == 0 and obj.idnum in reader.xref_objStm):
                    _reject()
                seen.add(key)
                if len(seen) > limits.pdf_objects:
                    _reject('DOCUMENT_PDF_LIMIT')
                stack.append((obj.get_object(), depth + 1))
                continue
            nodes += 1
            if nodes > limits.pdf_nodes or depth > limits.pdf_depth:
                _reject('DOCUMENT_PDF_LIMIT')
            if isinstance(obj, (DictionaryObject, ArrayObject)):
                if id(obj) in containers:
                    continue
                containers.add(id(obj))
                if isinstance(obj, StreamObject):
                    # Decoders may allocate before this length check. RLIMIT_AS,
                    # CPU and the parent's deadline are the hard outer defense.
                    expanded += len(obj.get_data())
                    if expanded > limits.pdf_stream_bytes:
                        _reject('DOCUMENT_PDF_LIMIT')
                children = obj.values() if isinstance(obj, DictionaryObject) else obj
                for child in children:
                    stack.append((child, depth + 1))
                    if len(stack) > limits.pdf_nodes:
                        _reject('DOCUMENT_PDF_LIMIT')
        operations = 0
        if len(reader.pages) != count:
            _reject()
        for page in reader.pages:
            box = page.mediabox
            import math
            if not all(math.isfinite(float(value)) for value in box) or box.width <= 0 or box.height <= 0:
                _reject()
            contents = page.get_contents()
            if contents is not None:
                operations += len(contents.operations)
                if operations > limits.pdf_operations:
                    _reject('DOCUMENT_PDF_LIMIT')
    finally:
        logger.removeHandler(handler)


def _inspect_document(data, extension, limits):
    """Child-only format dispatch; never call with untrusted data in the API."""
    if extension == '.pdf':
        _pdf(data, limits)
    elif extension == '.png':
        _png(data, limits)
        _image(data, extension, limits)
    elif extension in ('.jpg', '.jpeg'):
        _jpeg(data, limits)
        _image(data, extension, limits)
    else:
        _ooxml(data, extension, limits)


def _stop_worker(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.communicate()  # reap and close stdin even on cancellation/timeout


def _inspect_in_process(data, extension, limits):
    if sys.platform != 'linux':
        raise DocumentValidationError('DOCUMENT_INSPECTION_UNAVAILABLE', status=503)
    defaults = InspectionLimits()
    for field in _PROCESSING_FIELDS:
        value = getattr(limits, field)
        if type(value) is not int or not 0 < value <= getattr(defaults, field):
            raise RuntimeError('Presupuesto de procesamiento documental inválido')
    if not _INSPECTION_SLOTS.acquire(blocking=False):
        raise DocumentValidationError('DOCUMENT_INSPECTION_BUSY', status=503)
    try:
        # No shell, inherited application environment, output pipes, temporary
        # input files or unsafe preexec_fn in a threaded ASGI process.
        try:
            process = subprocess.Popen(
                [sys.executable, '-I', '-B', str(Path(__file__).resolve()),
                 '--inspect-worker', extension, str(len(data)), json.dumps(asdict(limits))],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env={'PATH': os.defpath, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'},
                cwd='/', close_fds=True, start_new_session=True,
            )
        except OSError as exc:
            raise DocumentValidationError('DOCUMENT_INSPECTION_UNAVAILABLE', status=503) from exc
        try:
            process.communicate(input=data, timeout=limits.worker_seconds)
        except subprocess.TimeoutExpired:
            _stop_worker(process)
            _reject('DOCUMENT_PROCESS_LIMIT')
        except BaseException:
            _stop_worker(process)
            raise
        if process.returncode == 0:
            return
        if 20 <= process.returncode < 20 + len(_WORKER_CODES):
            _reject(_WORKER_CODES[process.returncode - 20])
        if process.returncode < 0:
            _reject('DOCUMENT_PROCESS_LIMIT')
        raise DocumentValidationError('DOCUMENT_INSPECTION_UNAVAILABLE', status=503)
    finally:
        _INSPECTION_SLOTS.release()


def _worker_main():
    try:
        import resource
        if len(sys.argv) != 5 or sys.argv[1] != '--inspect-worker':
            return 2
        extension, size = sys.argv[2], int(sys.argv[3])
        limits = InspectionLimits(**json.loads(sys.argv[4]))
        if extension not in MIME_BY_EXTENSION or size <= 0:
            return 2
        # Apply hard OS limits BEFORE reading input or importing either parser.
        # Respect stricter inherited limits instead of trying to raise them.
        for kind, ceiling in ((resource.RLIMIT_AS, limits.worker_memory_bytes),
                (resource.RLIMIT_CPU, limits.worker_cpu_seconds),
                (resource.RLIMIT_FSIZE, 0), (resource.RLIMIT_CORE, 0), (resource.RLIMIT_NOFILE, 64)):
            _, hard = resource.getrlimit(kind)
            value = ceiling if hard == resource.RLIM_INFINITY else min(ceiling, hard)
            resource.setrlimit(kind, (value, value))
    except (ImportError, OSError, ValueError, TypeError):
        return 2  # cannot enforce resource isolation: fail closed
    try:
        data = sys.stdin.buffer.read(size + 1)
        if len(data) != size:
            _reject()
        _inspect_document(data, extension, limits)
        return 0
    except DocumentValidationError as exc:
        return 20 + _WORKER_CODES.index(exc.code)
    except ImportError:
        return 2  # missing pinned dependency is an operational failure
    except MemoryError:
        return 20 + _WORKER_CODES.index('DOCUMENT_PROCESS_LIMIT')
    except Exception:
        return 20  # no exception text, filenames or document data escape


if __name__ == '__main__':
    raise SystemExit(_worker_main())
