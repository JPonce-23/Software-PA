"""Operaciones transaccionales del Subcorte 2B.

PostgreSQL mantiene las invariantes. Este servicio proporciona intención de
dominio, autorización previa, bloqueo de la raíz y errores públicos estables.
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from .access import require_afectacion_access, require_tramo_nucleo_access
from .common import set_audit_context


DOMAIN_MESSAGES = {
    "2B_CAMINAMIENTO_REQUERIDO": "Debe completar el caminamiento aplicable antes de continuar.",
    "2B_SENSIBILIZACION_REQUERIDA": "Debe completar una sensibilización antes del caminamiento.",
    "2B_FLUJO_TERMINAL": "La afectación está fuera del seguimiento ordinario.",
    "2B_ASAMBLEA_APROBADA_REQUERIDA": "El convenio colectivo requiere una asamblea aprobada del mismo ciclo.",
    "2B_RAN_INGRESO_REQUERIDO": "Debe registrar el ingreso al RAN antes de la inscripción.",
    "2B_RAN_CONVENIO_REQUERIDO": "El convenio debe estar inscrito en el RAN.",
    "2B_RAN_ASAMBLEA_REQUERIDO": "El acta colectiva debe estar inscrita en el RAN.",
    "2B_NO_CONFLICTOS_REQUERIDO": "Se requiere un informe de no conflictos completo y favorable del mismo ciclo.",
    "2B_INDEMNIZACION_COMPLETA_REQUERIDA": "La indemnización debe estar completa antes del retiro de fondos.",
    "2B_MODIFICATORIO_RAN_REQUERIDO": "El modificatorio colectivo debe estar inscrito en el RAN antes de activarse.",
    "2B_LIMITE_MENOR_QUE_PAGADO": "El nuevo límite no puede ser menor que lo ya pagado.",
    "2B_LIMITE_PAGO_EXCEDIDO": "El pago excede el saldo disponible del ciclo.",
    "2B_PAGO_INSUFICIENTE": "No se puede completar la indemnización. El monto pagado es menor al límite del convenio.",
    "2B_PAGO_INSUFICIENTE_REDUCCION": "La reducción o eliminación de este pago dejaría un ciclo completo sin fondos suficientes.",
    "2B_VERSION_FINANCIERA_INMUTABLE": "Una versión financiera vigente no se edita; registre un modificatorio.",
    "2B_REGRESION_PROHIBIDA": "No se puede revertir un hito ya concluido.",
    "2B_TERMINAL_IRREVERSIBLE": "La salida terminal no se corrige mediante edición ordinaria.",
}


def _raise_domain(exc: Exception) -> None:
    raw = str(getattr(exc, "orig", exc))
    for code, message in DOMAIN_MESSAGES.items():
        if code in raw:
            raise HTTPException(status_code=409, detail={"code": code, "message": message}) from exc
    raise HTTPException(
        status_code=409,
        detail={"code": "2B_REGLA_NEGOCIO", "message": "La operación no cumple las reglas del flujo."},
    ) from exc


def _commit(db: Session) -> None:
    try:
        db.commit()
    except (DBAPIError, IntegrityError) as exc:
        db.rollback()
        _raise_domain(exc)


def listar_ciclos(
    db: Session, user: models.Usuario, id_afectacion: int
) -> list[models.AfectacionCiclo]:
    require_afectacion_access(db, user, id_afectacion)
    return db.query(models.AfectacionCiclo).filter(
        models.AfectacionCiclo.id_afectacion == id_afectacion,
        models.AfectacionCiclo.activo.is_(True),
    ).order_by(
        models.AfectacionCiclo.tipo_ciclo,
        models.AfectacionCiclo.consecutivo,
    ).all()


def crear_ciclo(
    db: Session,
    user: models.Usuario,
    id_afectacion: int,
    data: schemas.AfectacionCicloCreate,
) -> models.AfectacionCiclo:
    afectacion = require_afectacion_access(db, user, id_afectacion)
    permitidos = {
        "colectivo": {"superficie_adicional", "obras_complementarias"},
        "individual": {"ampliacion", "ampliacion_remanente"},
    }
    if data.tipo_ciclo not in permitidos[afectacion.tipo_afectacion]:
        raise HTTPException(status_code=409, detail={
            "code": "2B_CICLO_TIPO_INCOMPATIBLE",
            "message": "El tipo de ciclo no corresponde con el derecho afectado.",
        })
    salida_terminal = db.execute(text(
        "SELECT fn_2b_salida_terminal_efectiva(:id)"
    ), {"id": afectacion.id_afectacion}).scalar_one()
    if salida_terminal:
        raise HTTPException(status_code=409, detail={
            "code": "2B_FLUJO_TERMINAL",
            "message": DOMAIN_MESSAGES["2B_FLUJO_TERMINAL"],
        })

    set_audit_context(db, user.id_usuario)
    db.query(models.Afectacion).filter(
        models.Afectacion.id_afectacion == id_afectacion
    ).with_for_update().one()
    ultimo = db.query(func.max(models.AfectacionCiclo.consecutivo)).filter(
        models.AfectacionCiclo.id_afectacion == id_afectacion,
        models.AfectacionCiclo.tipo_ciclo == data.tipo_ciclo,
        models.AfectacionCiclo.activo.is_(True),
    ).scalar() or 0
    ciclo = models.AfectacionCiclo(
        id_tramo_nucleo=afectacion.id_tramo_nucleo,
        id_afectacion=afectacion.id_afectacion,
        tipo_afectacion=afectacion.tipo_afectacion,
        tipo_ciclo=data.tipo_ciclo,
        consecutivo=ultimo + 1,
        observaciones=data.observaciones,
    )
    db.add(ciclo)
    _commit(db)
    db.refresh(ciclo)
    return ciclo


def marcar_salida_terminal(
    db: Session,
    user: models.Usuario,
    id_afectacion: int,
    data: schemas.SalidaTerminalRequest,
) -> models.Afectacion:
    afectacion = require_afectacion_access(db, user, id_afectacion)
    if afectacion.tipo_salida_terminal:
        if afectacion.tipo_salida_terminal == data.tipo_salida_terminal:
            return afectacion
        raise HTTPException(status_code=409, detail={
            "code": "2B_TERMINAL_IRREVERSIBLE",
            "message": DOMAIN_MESSAGES["2B_TERMINAL_IRREVERSIBLE"],
        })
    set_audit_context(db, user.id_usuario)
    db.query(models.Afectacion).filter(
        models.Afectacion.id_afectacion == id_afectacion
    ).with_for_update().one()
    afectacion.tipo_salida_terminal = data.tipo_salida_terminal
    afectacion.fecha_salida_terminal = datetime.now(timezone.utc)
    afectacion.motivo_salida_terminal = data.motivo
    _commit(db)
    db.refresh(afectacion)
    return afectacion


def completar_indemnizacion(
    db: Session,
    user: models.Usuario,
    id_tramite: int,
    data: schemas.ConfirmarTransicionRequest,
) -> models.TramiteFifonafe:
    tramite = db.query(models.TramiteFifonafe).filter(
        models.TramiteFifonafe.id_tramite_fifonafe == id_tramite,
        models.TramiteFifonafe.activo.is_(True),
    ).first()
    if tramite is None or tramite.tipo_tramite != "indemnizacion":
        raise HTTPException(status_code=404, detail="Trámite de indemnización no encontrado")
    require_tramo_nucleo_access(db, user, tramite.id_tramo_nucleo)
    if tramite.estatus == "completo":
        return tramite
    set_audit_context(db, user.id_usuario)
    db.query(models.AfectacionCiclo).filter(
        models.AfectacionCiclo.id_ciclo_afectacion == tramite.id_ciclo_afectacion
    ).with_for_update().one()

    total_pagado = db.execute(text("SELECT fn_2b_total_pagado_ciclo(:c)"), {"c": tramite.id_ciclo_afectacion}).scalar() or Decimal("0.00")
    limite = db.execute(text("SELECT fn_2b_limite_ciclo(:c)"), {"c": tramite.id_ciclo_afectacion}).scalar() or Decimal("0.00")
    if total_pagado < limite:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "2B_PAGO_INSUFICIENTE",
                "message": DOMAIN_MESSAGES["2B_PAGO_INSUFICIENTE"],
                "total_pagado": float(total_pagado),
                "limite": float(limite)
            }
        )

    tramite.estatus = "completo"
    if data.observaciones is not None:
        tramite.observaciones = data.observaciones
    _commit(db)
    db.refresh(tramite)
    return tramite


def completar_retiro_fondos(
    db: Session,
    user: models.Usuario,
    id_asamblea: int,
    data: schemas.ConfirmarTransicionRequest,
) -> models.Asamblea:
    asamblea = db.query(models.Asamblea).filter(
        models.Asamblea.id_asamblea == id_asamblea,
        models.Asamblea.activo.is_(True),
    ).first()
    if asamblea is None or asamblea.tipo_asamblea != "retiro_fondos":
        raise HTTPException(status_code=404, detail="Asamblea de retiro de fondos no encontrada")
    require_tramo_nucleo_access(db, user, asamblea.id_tramo_nucleo)
    if asamblea.estatus_asamblea == "completo":
        return asamblea
    set_audit_context(db, user.id_usuario)
    db.query(models.AfectacionCiclo).filter(
        models.AfectacionCiclo.id_ciclo_afectacion == asamblea.id_ciclo_afectacion
    ).with_for_update().one()
    asamblea.estatus_asamblea = "completo"
    if data.observaciones is not None:
        asamblea.observaciones = data.observaciones
    _commit(db)
    db.refresh(asamblea)
    return asamblea


def activar_modificatorio(
    db: Session,
    user: models.Usuario,
    id_convenio: int,
    data: schemas.ConfirmarTransicionRequest,
) -> models.Convenio:
    modificatorio = db.query(models.Convenio).filter(
        models.Convenio.id_convenio == id_convenio,
        models.Convenio.tipo_convenio == "modificatorio",
        models.Convenio.activo.is_(True),
    ).first()
    if modificatorio is None:
        raise HTTPException(status_code=404, detail="Convenio modificatorio no encontrado")
    require_tramo_nucleo_access(db, user, modificatorio.id_tramo_nucleo)
    if modificatorio.vigencia_financiera_desde is not None:
        return modificatorio
    if modificatorio.id_ciclo_afectacion is None:
        raise HTTPException(status_code=409, detail={
            "code": "2B_CONVENIO_CICLO_REQUERIDO",
            "message": "El modificatorio histórico requiere conciliación de ciclo.",
        })

    set_audit_context(db, user.id_usuario)
    db.query(models.AfectacionCiclo).filter(
        models.AfectacionCiclo.id_ciclo_afectacion == modificatorio.id_ciclo_afectacion
    ).with_for_update().one()
    estado = db.execute(text("""
        SELECT estado_financiero, estado_terminal
          FROM vw_afectacion_ciclo_estado
         WHERE id_ciclo_afectacion = :id
    """), {"id": modificatorio.id_ciclo_afectacion}).mappings().first()
    if estado and (estado["estado_financiero"] == "concluido" or estado["estado_terminal"]):
        raise HTTPException(status_code=409, detail={
            "code": "2B_CICLO_CONCLUIDO",
            "message": "No se puede activar un modificatorio después del cierre del ciclo.",
        })

    total = Decimal(str(db.execute(text(
        "SELECT fn_2b_total_pagado_ciclo(:id)"
    ), {"id": modificatorio.id_ciclo_afectacion}).scalar_one()))
    limite = Decimal(modificatorio.monto_100 or 0)
    if modificatorio.tipo_afectacion == "colectivo":
        limite += Decimal(modificatorio.monto_bdt or 0)
    if limite < total:
        raise HTTPException(status_code=409, detail={
            "code": "2B_LIMITE_MENOR_QUE_PAGADO",
            "message": DOMAIN_MESSAGES["2B_LIMITE_MENOR_QUE_PAGADO"],
        })

    vigente = db.query(models.Convenio).filter(
        models.Convenio.id_ciclo_afectacion == modificatorio.id_ciclo_afectacion,
        models.Convenio.activo.is_(True),
        models.Convenio.vigencia_financiera_desde.is_not(None),
        models.Convenio.vigencia_financiera_hasta.is_(None),
        models.Convenio.id_convenio != modificatorio.id_convenio,
    ).with_for_update().one_or_none()
    if vigente is None:
        raise HTTPException(status_code=409, detail={
            "code": "2B_VERSION_FINANCIERA_NO_VIGENTE",
            "message": "El ciclo no tiene una versión financiera base vigente.",
        })
    ahora = datetime.now(timezone.utc)
    vigente.vigencia_financiera_hasta = ahora
    db.flush()
    modificatorio.vigencia_financiera_desde = ahora
    if data.observaciones is not None:
        modificatorio.observaciones = data.observaciones
    _commit(db)
    db.refresh(modificatorio)
    return modificatorio


def obtener_estado_afectacion(
    db: Session, user: models.Usuario, id_afectacion: int
) -> dict:
    require_afectacion_access(db, user, id_afectacion)
    estado = db.execute(text("""
        SELECT * FROM vw_afectacion_estado WHERE id_afectacion = :id
    """), {"id": id_afectacion}).mappings().first()
    if estado is None:
        raise HTTPException(status_code=404, detail="Estado de afectación no encontrado")
    ciclos = db.execute(text("""
        SELECT id_ciclo_afectacion, id_afectacion, tipo_afectacion, tipo_ciclo,
               consecutivo, id_convenio, estado_terminal, estado_operativo,
               estado_registral, estado_financiero, no_conflictos_completo,
               indemnizacion_completa, retiro_fondos_completo, limite_pagable,
               total_pagado, saldo_disponible, superficie_ciclo_ha
          FROM vw_afectacion_ciclo_estado
         WHERE id_afectacion = :id ORDER BY tipo_ciclo, consecutivo
    """), {"id": id_afectacion}).mappings().all()
    resultado = dict(estado)
    resultado["ciclos"] = [dict(ciclo) for ciclo in ciclos]
    return resultado


def obtener_estado_tramo_nucleo(
    db: Session, user: models.Usuario, id_tramo_nucleo: int
) -> dict:
    require_tramo_nucleo_access(db, user, id_tramo_nucleo)
    estado = db.execute(text("""
        SELECT id_tramo_nucleo, id_tramo, id_nucleo, estado_legal,
               estado_geoespacial, total_afectaciones, afectaciones_liberadas,
               afectaciones_pendientes, afectaciones_en_proceso,
               afectaciones_terminales
          FROM vw_tramo_nucleo_estado WHERE id_tramo_nucleo = :id
    """), {"id": id_tramo_nucleo}).mappings().first()
    if estado is None:
        raise HTTPException(status_code=404, detail="Estado de expediente no encontrado")
    return dict(estado)
