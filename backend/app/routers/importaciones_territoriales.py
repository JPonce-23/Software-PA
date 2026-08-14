from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services import importaciones_territoriales as service


router = APIRouter(prefix="/importaciones-territoriales", tags=["Importaciones territoriales"])


@router.post(
    "/{tipo}/previsualizar",
    response_model=schemas.ImportacionTerritorialPreviewResponse,
)
async def previsualizar_importacion(
    tipo: str,
    file: UploadFile = File(...),
    id_proyecto: Optional[int] = Form(None),
    id_tramo: Optional[int] = Form(None),
    id_nucleo: Optional[int] = Form(None),
    id_tramo_nucleo: Optional[int] = Form(None),
    id_municipio_fallback: Optional[int] = Form(None),
    id_entidad_fallback: Optional[int] = Form(None),
    tipo_nucleo_fallback: Optional[str] = Form(None),
    ids_tramo_contexto: Optional[List[int]] = Form(None),
    fuente: Optional[str] = Form(None),
    fecha_vigencia_inicio: Optional[str] = Form(None),
    ancho_izquierdo_m: Optional[Decimal] = Form(None),
    ancho_derecho_m: Optional[Decimal] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(["admin", "geografo"])),
):
    if tipo == "nucleos":
        raise HTTPException(
            status_code=410,
            detail="La importacion de nucleos requiere el flujo geoespacial con staging.",
        )
    if tipo == "cruces_operativos" and current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administrador puede importar cruces operativos.")
    if not file.filename or not file.filename.lower().endswith((".geojson", ".json")):
        raise HTTPException(status_code=400, detail="El archivo debe tener extension .geojson o .json")
    max_bytes = 10 * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="Archivo excede el limite de 10MB")
    data = service.parse_geojson(content)
    contexto = {
        "id_proyecto": id_proyecto,
        "id_tramo": id_tramo,
        "id_nucleo": id_nucleo,
        "id_tramo_nucleo": id_tramo_nucleo,
        "id_municipio_fallback": id_municipio_fallback,
        "id_entidad_fallback": id_entidad_fallback,
        "tipo_nucleo_fallback": tipo_nucleo_fallback,
        "ids_tramo_contexto": ids_tramo_contexto or [],
        "fuente": fuente,
        "fecha_vigencia_inicio": fecha_vigencia_inicio,
        "ancho_izquierdo_m": str(ancho_izquierdo_m) if ancho_izquierdo_m is not None else None,
        "ancho_derecho_m": str(ancho_derecho_m) if ancho_derecho_m is not None else None,
    }
    return service.preview(
        db,
        tipo,
        data,
        service.file_hash(content),
        current_user,
        contexto,
    )


@router.post(
    "/{tipo}/confirmar",
    response_model=schemas.ImportacionTerritorialConfirmResponse,
)
def confirmar_importacion(
    tipo: str,
    data: schemas.ImportacionTerritorialConfirmRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(["admin", "geografo"])),
):
    if tipo == "nucleos":
        raise HTTPException(
            status_code=410,
            detail="La importacion de nucleos requiere confirmacion desde staging.",
        )
    if tipo == "cruces_operativos" and current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administrador puede importar cruces operativos.")
    return service.confirm(db, tipo, data, current_user)
