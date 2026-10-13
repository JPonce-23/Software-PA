"""CPU-only synthetic before/after benchmark; never connects to PostgreSQL.

Run in the isolated test container, passing a snapshot of Entrega 1 before the
final corrections. Timings exclude GDAL, disk I/O and SQL/JSONB persistence.
"""

import argparse
from contextlib import contextmanager
import gc
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
from time import perf_counter
from types import SimpleNamespace as N


def load_previous(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def diagnostic_module(module):
    name = "app.services.gis_diagnostics"
    previous = sys.modules[name]
    sys.modules[name] = module
    try:
        yield
    finally:
        sys.modules[name] = previous


class MemorySession:
    def __init__(self):
        self.rows = []

    def add(self, row):
        self.rows.append(row)

    def add_all(self, rows):
        self.rows.extend(rows)

    def flush(self):
        pass


def dataset(destinations, nuclei_count, textual):
    nuclei = [(N(id_proyecto_nucleo=i + 1), N(id_nucleo=i + 1,
        nombre_nucleo="Núcleo sintético", fuente_datos="RAN_PHINA_CATALOGO_NUCLEOS",
        id_nucleo_fuente=f"RAN-{i}", municipio=N(nombre="M", entidad=N(nombre="E")),
        tipo_tenencia=N(nombre="Ejido")), None) for i in range(nuclei_count)]
    universe = [(*nuclei[i % nuclei_count][:2], N(id_parcela=i + 1, no_parcela=str(i // nuclei_count + 1)))
                for i in range(destinations)]
    identity = {"N__CLEO_AG": "Núcleo sintético", "municipio": "M", "estado": "E", "TIPO_N__CL": "Ejido"} if textual else {"cve_unica_nucleo": "RAN-0"}
    return nuclei, universe, {**identity, "PARCELA": "00016", "Num_parcela": "000016", "no_parcela": "0000016"}


def timed(callback, repetitions):
    samples = []
    gc.collect()
    for _ in range(repetitions):
        start = perf_counter()
        callback()
        samples.append(perf_counter() - start)
    return {"median_seconds": statistics.median(samples), "samples_seconds": samples}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    options = parser.parse_args()
    if options.repetitions < 1:
        parser.error("repetitions debe ser positivo")
    if any(os.getenv(key) != value for key, value in (
        ("APP_ENV", "test"), ("DB_NAME", "software_pa_test"), ("TEST_ALLOW_DATABASE", "software_pa_test"))):
        parser.error("Sólo se ejecuta con configuración explícita de pruebas")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app import models
    from app.database import engine
    from app.services import gis_diagnostics as current_diagnostics, gis_reconciliation as current_matching
    from sqlalchemy import event

    def forbid_sql(*args, **kwargs):
        raise AssertionError("El benchmark no debe ejecutar SQL")
    event.listen(engine, "before_cursor_execute", forbid_sql)
    baseline_services = options.baseline_dir / "backend/app/services"
    old_diagnostics = load_previous("app.services._diagnostics_before", baseline_services / "gis_diagnostics.py")
    old_matching = load_previous("app.services._matching_before", baseline_services / "gis_reconciliation.py")
    # Keep matching operations, model construction and result serialization real;
    # replace only the database-bound geometry lookup and unit-of-work writes.
    old_matching.geometry_hash = current_matching.geometry_hash = lambda *args: None
    output = {"methodology": "CPU synthetic; median; no SQL/GDAL; one warm-up; before=Entrega 1 snapshot", "repetitions": options.repetitions, "scenarios": []}
    for features, destinations, nuclei_count, textual in (
        (200, 1000, 40, False), (200, 1000, 40, True), (500, 2000, 80, True),
    ):
        nuclei, universe, properties = dataset(destinations, nuclei_count, textual)
        before = old_diagnostics.matching_diagnostic(properties, universe, nuclei, [], parcel=True)
        after = current_diagnostics.matching_diagnostic(properties, universe, nuclei, [], parcel=True)
        assert before == after
        def diagnostics(module):
            for _ in range(features):
                value = module.matching_diagnostic(properties, universe, nuclei, [], parcel=True)
                assert value == after
        def processing(matching, diagnostic):
            results = []
            with diagnostic_module(diagnostic):
                for i in range(features):
                    session = MemorySession()
                    feature = N(id_importacion_feature=i + 1)
                    matching.build_candidates(session, N(tipo_objetivo="parcela_gpkg", id_importacion=1, mapeo={}),
                        feature, properties, universe, N(id_usuario=1), cycle=N(id_ciclo=1), nucleus_universe=nuclei)
                    candidates = [(c.id_proyecto_nucleo, c.id_parcela, c.criterio, c.clasificacion, tuple(c.coincidencias))
                        for c in session.rows if isinstance(c, models.ImportacionFeatureCandidato)]
                    result = next(c for c in session.rows if isinstance(c, models.ImportacionConciliacionResultado))
                    results.append((feature.estado_conciliacion, candidates, result.diagnostico))
            return results
        expected = processing(old_matching, old_diagnostics)
        assert processing(current_matching, current_diagnostics) == expected
        measurements = {}
        for name, callback in (
            ("diagnostic_before", lambda: diagnostics(old_diagnostics)),
            ("diagnostic_after", lambda: diagnostics(current_diagnostics)),
            ("processing_before", lambda: processing(old_matching, old_diagnostics)),
            ("processing_after", lambda: processing(current_matching, current_diagnostics)),
        ):
            measurements[name] = timed(callback, options.repetitions)
        output["scenarios"].append({"features": features, "destinations": destinations, "nuclei": nuclei_count,
            "identity": "textual_homonyms" if textual else "official", "sql_queries": 0,
            "matching_and_diagnostics_equal": True, **measurements})
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
