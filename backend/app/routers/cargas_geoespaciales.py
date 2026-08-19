from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import auth, models
from ..database import get_db
from ..schemas_cargas_geoespaciales import (
    CandidatoTramoNucleoResponse,
    CargaFeatureResponse,
    CargaGeoespacialResponse,
    ConfirmarCargaRequest,
    ConfirmarCandidatoRequest,
    RechazarCandidatoRequest,
    TipoCargaGeoespacial,
)
from ..services import cargas_geoespaciales as service
from ..services.access import require_tramo_access


router = APIRouter(prefix="/cargas-geoespaciales", tags=["Cargas geoespaciales"])
allowed = auth.RoleChecker(["admin", "geografo"])


def _feature_response(feature: models.CargaGeoespacialFeature) -> dict:
    data = {
        "id_carga_feature": feature.id_carga_feature,
        "indice_feature": feature.indice_feature,
        "capa_origen": feature.capa_origen,
        "tipo_geometria": feature.tipo_geometria,
        "estado": feature.estado,
        "errores": feature.errores or [],
        "advertencias": feature.advertencias or [],
        "transformaciones": feature.transformaciones or [],
        "area_original_m2": feature.area_original_m2,
        "area_normalizada_m2": feature.area_normalizada_m2,
        "diferencia_area_relativa": feature.diferencia_area_relativa,
        "seleccionado": feature.seleccionado,
        "geometria_geojson": None,
    }
    return data


def _record_response(db: Session, record: models.CargaGeoespacial) -> dict:
    payload = {column.name: getattr(record, column.name) for column in models.CargaGeoespacial.__table__.columns}
    features = db.query(models.CargaGeoespacialFeature).filter_by(id_carga=record.id_carga).order_by(
        models.CargaGeoespacialFeature.indice_feature
    ).all()
    serialized = []
    for feature in features:
        item = _feature_response(feature)
        if feature.geometria_normalizada is not None:
            item["geometria_geojson"] = db.query(func.ST_AsGeoJSON(models.CargaGeoespacialFeature.geometria_normalizada)).filter(
                models.CargaGeoespacialFeature.id_carga_feature == feature.id_carga_feature
            ).scalar()
            if item["geometria_geojson"]:
                import json
                item["geometria_geojson"] = json.loads(item["geometria_geojson"])
        serialized.append(item)
    payload["features"] = serialized
    return payload


@router.post("", response_model=CargaGeoespacialResponse, status_code=201)
async def upload(
    tipo_objetivo: TipoCargaGeoespacial = Form(...),
    file: UploadFile = File(...),
    fuente: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    record = await service.stage_upload(db, file, tipo_objetivo, current_user.id_usuario, fuente)
    return _record_response(db, record)


@router.post("/tramos/{id_tramo}/candidatos/detectar")
def detect_candidates(
    id_tramo: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    require_tramo_access(db, current_user, id_tramo)
    created = service.detect_candidates(db, id_tramo, current_user.id_usuario)
    return {"candidatos_nuevos": created}


@router.get("/tramos/{id_tramo}/candidatos", response_model=list[CandidatoTramoNucleoResponse])
def list_candidates(
    id_tramo: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    require_tramo_access(db, current_user, id_tramo)
    rows = db.query(
        models.CandidatoTramoNucleo,
        models.NucleoAgrario.nombre_nucleo.label("nombre_nucleo"),
    ).join(models.NucleoAgrario).filter(
        models.CandidatoTramoNucleo.id_tramo == id_tramo
    ).order_by(models.CandidatoTramoNucleo.fecha_deteccion.desc()).all()
    return [
        {
            **{
                column.name: getattr(candidate, column.name)
                for column in models.CandidatoTramoNucleo.__table__.columns
            },
            "nombre_nucleo": nombre_nucleo,
        }
        for candidate, nombre_nucleo in rows
    ]


@router.post("/candidatos/{id_candidato}/confirmar")
def confirm_candidate(
    id_candidato: int,
    payload: ConfirmarCandidatoRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    relation = service.confirm_candidate(db, id_candidato, user_id=current_user.id_usuario, **payload.model_dump())
    return {"id_tramo_nucleo": relation.id_tramo_nucleo}


@router.post("/candidatos/{id_candidato}/rechazar")
def reject_candidate(
    id_candidato: int,
    payload: RechazarCandidatoRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    service.reject_candidate(db, id_candidato, payload.motivo, current_user.id_usuario)
    return {"detail": "Candidato rechazado."}


@router.get("/{id_carga}", response_model=CargaGeoespacialResponse)
def get_upload(
    id_carga: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    return _record_response(db, service.get_carga_or_404(db, id_carga, current_user))


@router.post("/{id_carga}/confirmar", response_model=CargaFeatureResponse)
def confirm_upload(
    id_carga: int,
    payload: ConfirmarCargaRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    record = service.get_carga_or_404(db, id_carga, current_user)
    feature = service.confirm_feature(db, record, payload.id_carga_feature, current_user.id_usuario)
    return _feature_response(feature)
