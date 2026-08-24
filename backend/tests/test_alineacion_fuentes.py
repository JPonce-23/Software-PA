"""Contratos incorporados por la alineación con las fuentes funcionales."""

import pytest
from pydantic import ValidationError

from app.schemas import ActividadCampoCreate, TramiteFifonafeCreate


def _informe(**changes):
    data = {
        "id_tramo_nucleo": 1,
        "id_convenio": 1,
        "id_afectacion": 1,
        "id_ciclo_afectacion": 1,
        "tipo_afectacion": "individual",
        "tipo_tramite": "informe_no_conflictos",
        "estatus": "programado",
    }
    data.update(changes)
    return data


def test_informe_fifonafe_admite_captura_progresiva():
    informe = TramiteFifonafeCreate.model_validate(_informe())
    assert informe.hay_conflictos is None
    assert informe.no_oficio_fifonafe_a_dgaopr is None


def test_informe_fifonafe_completo_exige_resultado_y_oficios():
    with pytest.raises(ValidationError, match="cuatro oficios"):
        TramiteFifonafeCreate.model_validate(_informe(estatus="completo"))


def test_actividad_captura_programacion_realizacion_y_resultado():
    actividad = ActividadCampoCreate.model_validate({
        "id_tramo_nucleo": 1,
        "tipo_actividad": "sensibilizacion",
        "fecha_programada": "2026-08-01",
        "fecha_realizada": "2026-08-02",
        "resultado": "Participación registrada en minuta.",
    })
    assert actividad.resultado == "Participación registrada en minuta."


def test_actividad_rechaza_realizacion_anterior_a_programacion():
    with pytest.raises(ValidationError, match="fecha_realizada"):
        ActividadCampoCreate.model_validate({
            "id_tramo_nucleo": 1,
            "tipo_actividad": "caminamiento",
            "fecha_programada": "2026-08-02",
            "fecha_realizada": "2026-08-01",
        })
