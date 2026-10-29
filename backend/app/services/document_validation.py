"""Bounded format-envelope checks, NOT malware scanning or full format parsers.

No extraction, image decoding, PDF object traversal or network access. OOXML
uses stdlib ZIP/Expat with limits before ZIP indexing and during inspection.
"""

from dataclasses import dataclass
import io
import os
import posixpath
import re
import stat
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
        values[name] = value
    return InspectionLimits(**values)


def _reject(code='DOCUMENT_FORMAT_INVALID'):
    raise DocumentValidationError(code)


def _pdf(data):
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
    # Cross-reference/object/stream semantics, signatures and JS are not parsed.


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
    # IDAT/ancillary streams and pixels are deliberately not decompressed.


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
        self.overrides, self.relationships = {}, []
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
        for info in infos:
            summary = _XmlSummary(limits, nodes) if info.filename in required else None
            if summary: summaries[info.filename] = summary
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
            # Worksheet contents/embedded objects are CRC-checked, not schema parsed.


def validate_document(data, extension, client_mime, *, max_file_bytes, limits=None):
    extension = extension.lower()
    if extension not in MIME_BY_EXTENSION:
        _reject('DOCUMENT_EXTENSION')
    if not data or len(data) > max_file_bytes:
        raise DocumentValidationError('DOCUMENT_SIZE', 'Archivo vacío o demasiado grande', 413)
    limits = limits or load_limits()
    try:
        if extension == '.pdf': _pdf(data)
        elif extension == '.png': _png(data, limits)
        elif extension in ('.jpg', '.jpeg'): _jpeg(data, limits)
        else: _ooxml(data, extension, limits)
    except DocumentValidationError:
        raise
    except (zipfile.BadZipFile, zipfile.LargeZipFile, expat.ExpatError, zlib.error,
            ValueError, NotImplementedError, RuntimeError, EOFError, OSError) as exc:
        raise DocumentValidationError('DOCUMENT_FORMAT_INVALID') from exc
    canonical = MIME_BY_EXTENSION[extension]
    mime = (client_mime or '').split(';', 1)[0].strip().lower()
    permitted = _GENERIC | {canonical} | _ALIASES.get(extension, set())
    if extension in ('.docx', '.xlsx'): permitted |= {'application/zip', 'application/x-zip-compressed'}
    if mime not in permitted:
        raise DocumentValidationError('DOCUMENT_MIME_MISMATCH', 'El tipo MIME declarado es incompatible con el formato comprobado.')
    return canonical


def download_media_type():
    # No schema/provenance marker distinguishes a validated upload from a legacy
    # row with exactly the same MIME. Conservative for all versions, no rewrites.
    return 'application/octet-stream'
