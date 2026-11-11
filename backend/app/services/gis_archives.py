"""ZIP/Shapefile extraction into a private directory owned by this attempt."""
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath

from .gis_ingestion import IngestionError
from .gis_limits import load_limits


def extract_shapefile_zip(path: Path) -> Path:
    limits = load_limits()
    destination = path.with_suffix('')
    # Deliberately outside try: never remove a pre-existing directory on failure.
    try:
        destination.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise IngestionError('ZIP_DESTINO_EXISTENTE', 'El directorio de extracción ya existe.') from exc
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > limits.zip_entries:
                raise IngestionError('LIMITE_ZIP_ENTRADAS', 'El ZIP excede el limite de entradas.')
            declared = 0
            for info in entries:
                member = PurePosixPath(info.filename.replace('\\', '/'))
                mode = stat.S_IFMT(info.external_attr >> 16)
                if (member.is_absolute() or '..' in member.parts or not member.parts
                        or ':' in member.parts[0] or '\x00' in info.filename
                        or mode not in (0, stat.S_IFREG, stat.S_IFDIR)):
                    raise IngestionError('ZIP_NO_SEGURO', 'ZIP no seguro.')
                if info.file_size > limits.zip_member_bytes:
                    raise IngestionError('LIMITE_ZIP_MIEMBRO', 'Un archivo ZIP excede el limite expandido individual.')
                declared += info.file_size
                if declared > limits.zip_total_bytes:
                    raise IngestionError('LIMITE_ZIP_TOTAL', 'ZIP expandido demasiado grande.')
            total = 0
            for info in entries:
                if info.is_dir():
                    continue
                member = PurePosixPath(info.filename.replace('\\', '/'))
                target = (destination / Path(*member.parts)).resolve()
                if destination.resolve() not in target.parents:
                    raise IngestionError('ZIP_NO_SEGURO', 'ZIP no seguro.')
                target.parent.mkdir(parents=True, exist_ok=True)
                size = 0
                with archive.open(info) as source, target.open('xb') as output:
                    while True:
                        chunk = source.read(min(64 * 1024, limits.zip_member_bytes - size + 1,
                                                limits.zip_total_bytes - total + 1))
                        if not chunk:
                            break
                        size += len(chunk)
                        total += len(chunk)
                        if size > limits.zip_member_bytes or total > limits.zip_total_bytes:
                            raise IngestionError('LIMITE_ZIP_BYTES', 'La extracción ZIP excede el presupuesto real de bytes.')
                        output.write(chunk)
                if size != info.file_size:
                    raise IngestionError('ZIP_TAMANO_INCONSISTENTE', 'El tamaño extraído no coincide con el ZIP.')
        shapes = list(destination.rglob('*.shp'))
        if len(shapes) != 1:
            raise IngestionError('ZIP_SHAPEFILE_INVALIDO', 'El ZIP debe contener exactamente un dataset Shapefile.')
        return shapes[0]
    except BaseException as exc:
        shutil.rmtree(destination)
        if isinstance(exc, (OSError, zipfile.BadZipFile, RuntimeError)) and not isinstance(exc, IngestionError):
            raise IngestionError('ZIP_INVALIDO', 'No fue posible extraer el ZIP.') from exc
        raise
