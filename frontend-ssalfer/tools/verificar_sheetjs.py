"""Verify vendored SheetJS against its pinned official archive, without executing it."""
import argparse
import hashlib
import io
from pathlib import Path
import ssl
import tarfile
from urllib.request import Request, urlopen

URL = "https://cdn.sheetjs.com/xlsx-0.20.3/xlsx-0.20.3.tgz"
ARCHIVE_SHA256 = "8dc73fc3b00203e72d176e85b50938627c7b086e607c682e8d3c22c02bb99fe8"
MAX_ARCHIVE = 8 * 1024 * 1024
FILES = {
    "package/dist/xlsx.mini.min.js": "xlsx-0.20.3.mini.min.js",
    "package/LICENSE": "SheetJS-LICENSE.txt",
}
ROOT = Path(__file__).resolve().parents[2]


def verify(archive, vendor):
    if len(archive) > MAX_ARCHIVE or hashlib.sha256(archive).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("ARCHIVO_OFICIAL_NO_COINCIDE")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
        for member_name, filename in FILES.items():
            member = package.getmember(member_name)
            if not member.isfile() or member.size > MAX_ARCHIVE:
                raise ValueError("CONTENIDO_OFICIAL_INVALIDO")
            with package.extractfile(member) as source:
                expected = source.read(MAX_ARCHIVE + 1)
            local = vendor / filename
            if local.is_symlink() or not local.is_file() or local.stat().st_size != len(expected):
                raise ValueError("COPIA_LOCAL_NO_COINCIDE")
            if local.read_bytes() != expected:
                raise ValueError("COPIA_LOCAL_NO_COINCIDE")
    return len(FILES)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Previously downloaded official archive; no network")
    args = parser.parse_args()
    try:
        if args.archive:
            with args.archive.open("rb") as source:
                archive = source.read(MAX_ARCHIVE + 1)
        else:
            request = Request(URL, headers={"User-Agent": "SSALFER-vendor-verifier/1.0", "Accept": "application/octet-stream"})
            with urlopen(request, timeout=30, context=ssl.create_default_context()) as response:
                if not response.geturl().startswith("https://cdn.sheetjs.com/"):
                    raise ValueError("ORIGEN_NO_PERMITIDO")
                archive = response.read(MAX_ARCHIVE + 1)
        count = verify(archive, ROOT / "frontend-ssalfer/js/vendor")
    except Exception:
        print("SHEETJS_NO_VERIFICADO: no se pudo comprobar el paquete oficial o la copia local.")
        return 1
    print(f"SHEETJS_VERIFICADO: {count} archivos coinciden con la distribucion oficial 0.20.3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
