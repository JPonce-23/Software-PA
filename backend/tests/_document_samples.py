"""Small synthetic format fixtures; stdlib only, no application/DB imports."""

import io
import struct
import zipfile
import zlib


def minimal_pdf(label='Software PA QA'):
    label = label.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    text = f'BT /F1 8 Tf 5 30 Td ({label}) Tj ET'.encode('ascii')
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length ' + str(len(text)).encode() + b' >>\nstream\n' + text + b'\nendstream']
    result = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'); offsets = [0]
    for index, body in enumerate(objects, 1):
        offsets.append(len(result)); result.extend(f'{index} 0 obj\n'.encode() + body + b'\nendobj\n')
    start = len(result)
    result.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]: result.extend(f'{offset:010} 00000 n \n'.encode())
    result.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode())
    return bytes(result)


def png_chunk(kind, content):
    return struct.pack('>I', len(content)) + kind + content + struct.pack('>I', zlib.crc32(kind + content) & 0xffffffff)


def minimal_png():
    return (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
        + png_chunk(b'IDAT', zlib.compress(b'\x00\xff\x00\x00')) + png_chunk(b'IEND', b''))


def minimal_jpeg():
    # Baseline grayscale 1x1: one all-zero DCT block, Huffman codes DC0/EOB0,
    # entropy bits 00 padded with 1s. Decoded by Pillow in the isolated SS-06 worker tests.
    def segment(marker, payload): return bytes([255, marker]) + struct.pack('>H', len(payload) + 2) + payload
    counts = b'\x01' + b'\x00' * 15
    return (b'\xff\xd8' + segment(0xdb, b'\x00' + b'\x01' * 64)
        + segment(0xc0, b'\x08\x00\x01\x00\x01\x01\x01\x11\x00')
        + segment(0xc4, b'\x00' + counts + b'\x00' + b'\x10' + counts + b'\x00')
        + segment(0xda, b'\x01\x01\x00\x00\x3f\x00') + b'\x3f\xff\xd9')


CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
RELS = 'http://schemas.openxmlformats.org/package/2006/relationships'
OFFICE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
WORD = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
SHEET = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def office_parts(extension='docx', *, strict=False):
    word = 'http://purl.oclc.org/ooxml/wordprocessingml/main' if strict else WORD
    sheet = 'http://purl.oclc.org/ooxml/spreadsheetml/main' if strict else SHEET
    office = 'http://purl.oclc.org/ooxml/officeDocument/relationships' if strict else OFFICE
    main = 'word/document.xml' if extension == 'docx' else 'xl/workbook.xml'
    main_type = ('application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'
                 if extension == 'docx' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml')
    extra = ('<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
             if extension == 'xlsx' else '')
    parts = {
        '[Content_Types].xml': f'<Types xmlns="{CT}"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/{main}" ContentType="{main_type}"/>{extra}</Types>',
        '_rels/.rels': f'<Relationships xmlns="{RELS}"><Relationship Id="rId1" Type="{office}/officeDocument" Target="{main}"/></Relationships>',
    }
    if extension == 'docx':
        parts[main] = f'<w:document xmlns:w="{word}"><w:body><w:p><w:r><w:t>SS06 SYNTH QA</w:t></w:r></w:p></w:body></w:document>'
    else:
        parts[main] = f'<workbook xmlns="{sheet}" xmlns:r="{office}"><sheets><sheet name="QA" sheetId="1" r:id="rId1"/></sheets></workbook>'
        parts['xl/_rels/workbook.xml.rels'] = f'<Relationships xmlns="{RELS}"><Relationship Id="rId1" Type="{office}/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
        parts['xl/worksheets/sheet1.xml'] = f'<worksheet xmlns="{sheet}"><sheetData/></worksheet>'
    return parts


def package(parts, compression=zipfile.ZIP_DEFLATED):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=compression) as archive:
        for name, content in parts.items(): archive.writestr(name, content)
    return output.getvalue()
