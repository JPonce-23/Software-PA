"""Bound complete report reads and CSV staging without a database dependency."""

import csv
from dataclasses import dataclass
import io
import math
import os
import tempfile
import time


CSV_COLUMNS = ("id_proyecto", "anio", "indicador", "programado", "realizado",
               "cantidad", "superficie_ha", "monto")
ADVANCE_COLUMNS = ("id_proyecto", "id_entidad", "ambito", "tipo_cop_operativo",
                   "tipo_convenio", "destino_superficie", "anio", "mes", "trimestre",
                   "indicador", "programado", "realizado", "cantidad", "superficie_ha", "monto")
SNAPSHOT_COLUMNS = ("id_proyecto", "id_entidad", "ambito", "indicador",
                    "tipo_cop_operativo", "destino_superficie", "cantidad", "superficie_ha", "monto")
CSV_CHUNK_BYTES = 64 * 1024


class ReportLimitError(Exception):
    def __init__(self, code, detail, status=413):
        self.code, self.detail, self.status = code, detail, status
        super().__init__(detail)


@dataclass(frozen=True)
class ReportLimits:
    rows: int
    csv_bytes: int
    batch_rows: int
    build_seconds: float | None


def load_limits() -> ReportLimits:
    values = []
    for name, default in (("REPORT_MAX_ROWS", 10_000),
                          ("REPORT_EXPORT_MAX_BYTES", 16 * 1024 * 1024),
                          ("REPORT_FETCH_BATCH_ROWS", 250)):
        try:
            value = int(os.getenv(name, str(default)))
        except ValueError as exc:
            raise RuntimeError(f"{name} requiere un entero positivo") from exc
        if value <= 0:
            raise RuntimeError(f"{name} requiere un entero positivo")
        values.append(value)
    if values[2] > 1000:
        raise RuntimeError("REPORT_FETCH_BATCH_ROWS no puede exceder 1000")
    seconds = os.getenv("REPORT_EXPORT_BUILD_TIMEOUT_SECONDS", "").strip()
    if seconds:
        try:
            seconds = float(seconds)
        except ValueError as exc:
            raise RuntimeError("REPORT_EXPORT_BUILD_TIMEOUT_SECONDS requiere segundos positivos") from exc
        if not math.isfinite(seconds) or seconds <= 0:
            raise RuntimeError("REPORT_EXPORT_BUILD_TIMEOUT_SECONDS requiere segundos positivos")
    return ReportLimits(*values, seconds or None)


def iter_result_rows(result, limits, *, already_read=0, deadline=None, clock=time.monotonic):
    """The caller owns/closes result. No all()/fetchall() or per-batch SELECT."""
    count = already_read
    while True:
        check_deadline(deadline, clock)
        batch = result.fetchmany(min(limits.batch_rows, limits.rows - count + 1))
        check_deadline(deadline, clock)
        if not batch:
            return
        for row in batch:
            count += 1
            if count > limits.rows:
                raise ReportLimitError("REPORT_ROW_LIMIT", "El reporte excede el límite de filas; acote los filtros.")
            yield row


def read_complete_rows(db, query, limits, *, already_read=0):
    remaining = limits.rows - already_read
    result = db.execute(query.limit(remaining + 1).statement,
        execution_options={"yield_per": limits.batch_rows, "stream_results": True,
                           "max_row_buffer": limits.batch_rows})
    try:
        return list(iter_result_rows(result, limits, already_read=already_read))
    finally:
        result.close()


def snapshot_key(row):
    """Existing leading sort plus every remaining identity dimension, NULL last."""
    return tuple((value is None, value) for value in (
        row.id_proyecto, row.indicador, row.id_entidad, row.ambito,
        row.tipo_cop_operativo, row.destino_superficie))


def csv_cell(value):
    # Only exported strings change. Numeric negatives/Decimals remain numeric.
    if isinstance(value, str) and (value.startswith(("\t", "\r", "\n"))
            or value.lstrip(" \t\r\n\ufeff").startswith(("=", "+", "-", "@", "＝", "＋", "－", "＠"))):
        return "'" + value
    return value


def check_deadline(deadline, clock=time.monotonic):
    if deadline is not None and clock() >= deadline:
        raise ReportLimitError("REPORT_BUILD_TIMEOUT", "La exportación excedió el tiempo de preparación permitido.", 504)


def build_csv(result, limits, *, deadline=None, clock=time.monotonic, file_factory=tempfile.TemporaryFile):
    """Private unnamed disk file. At most one serialized row is in memory.

    Stage completely before sending HTTP 200 so limits cannot masquerade as a
    successful truncated CSV. The caller closes result; response owns the file.
    """
    output = file_factory(mode="w+b")
    size = 0
    line = io.StringIO(newline="")
    writer = csv.writer(line)

    def write_row(values):
        nonlocal size
        check_deadline(deadline, clock)
        line.seek(0)
        line.truncate(0)
        writer.writerow(values)
        encoded = line.getvalue().encode("utf-8")
        size += len(encoded)
        if size > limits.csv_bytes:
            raise ReportLimitError("REPORT_CSV_BYTE_LIMIT", "La exportación excede el límite de bytes; acote los filtros.")
        output.write(encoded)

    try:
        write_row(CSV_COLUMNS)
        for row in iter_result_rows(result, limits, deadline=deadline, clock=clock):
            values = [getattr(row, name) for name in CSV_COLUMNS]
            # A UTF-8 CSV cannot fit a string with more characters than its
            # entire byte budget. Reject before escaping/duplicating that cell.
            if any(isinstance(value, str) and len(value) > limits.csv_bytes for value in values):
                raise ReportLimitError("REPORT_CSV_BYTE_LIMIT", "La exportación excede el límite de bytes; acote los filtros.")
            write_row(csv_cell(value) for value in values)
        check_deadline(deadline, clock)
        output.seek(0)
        return output
    except BaseException:
        output.close()
        raise
    finally:
        line.close()


def file_chunks(output):
    try:
        while chunk := output.read(CSV_CHUNK_BYTES):
            yield chunk
    finally:
        output.close()
