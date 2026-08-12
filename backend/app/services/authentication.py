import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address

import bcrypt
from fastapi import HTTPException, Request, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .. import models
from ..config import AUTH_SETTINGS
from .common import set_audit_context


_DUMMY_PASSWORD_HASH = bcrypt.hashpw(
    b"software-pa-dummy-authentication-value",
    bcrypt.gensalt(),
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_user_agent(request: Request) -> str | None:
    value = request.headers.get("user-agent", "").strip()
    if not value:
        return None
    sanitized = "".join(char for char in value if char.isprintable())
    return sanitized[:512] or None


def _request_ip(request: Request) -> str | None:
    peer = request.client.host if request.client else None
    candidate = peer
    if peer in AUTH_SETTINGS.trusted_proxy_ips:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            candidate = forwarded.split(",", 1)[0].strip()
    if not candidate:
        return None
    try:
        return str(ip_address(candidate))
    except ValueError:
        return None


def _event(
    db: Session,
    *,
    event_type: str,
    reason: str,
    request: Request,
    user_id: int | None = None,
    actor_id: int | None = None,
    session_id: int | None = None,
    detail: str | None = None,
) -> models.EventoAcceso:
    event = models.EventoAcceso(
        id_usuario=user_id,
        id_usuario_actor=actor_id,
        id_sesion=session_id,
        tipo_evento=event_type,
        motivo_codigo=reason,
        detalle=detail[:200] if detail else None,
        fecha_hora=_utcnow(),
        ip_origen=_request_ip(request),
        user_agent=_safe_user_agent(request),
    )
    db.add(event)
    db.flush()
    return event


def _link_state_event(db: Session, event_id: int) -> None:
    db.execute(
        text("SELECT set_config('app.auth_event_id', :event_id, true)"),
        {"event_id": str(event_id)},
    )


def _link_system_session_event(db: Session, event_id: int) -> None:
    db.execute(
        text("SELECT set_config('app.auth_system_event_id', :event_id, true)"),
        {"event_id": str(event_id)},
    )


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales incorrectas",
    )


def _session_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesión",
    )


def create_session(
    db: Session,
    request: Request,
    username: str,
    password: str,
) -> tuple[models.Usuario, models.SesionUsuario, str, str]:
    now = _utcnow()
    normalized_username = username.strip().lower()
    user = (
        db.query(models.Usuario)
        .filter(func.lower(func.btrim(models.Usuario.correo)) == normalized_username)
        .with_for_update()
        .first()
    )

    if user is None:
        bcrypt.checkpw(password.encode("utf-8"), _DUMMY_PASSWORD_HASH)
        _event(
            db,
            event_type="login_fallido",
            reason="credenciales_invalidas",
            request=request,
        )
        db.commit()
        raise _credentials_error()

    state = (
        db.query(models.EstadoAutenticacionUsuario)
        .filter(models.EstadoAutenticacionUsuario.id_usuario == user.id_usuario)
        .with_for_update()
        .one_or_none()
    )
    if state is None:
        db.rollback()
        raise RuntimeError("El usuario no tiene estado de autenticación")

    password_valid = bcrypt.checkpw(
        password.encode("utf-8"), user.contrasena_hash.encode("utf-8")
    )
    if not user.activo:
        _event(
            db,
            event_type="login_fallido",
            reason="usuario_inactivo" if password_valid else "credenciales_invalidas",
            request=request,
            user_id=user.id_usuario,
        )
        db.commit()
        raise _credentials_error()

    if state.bloqueado_hasta is not None and state.bloqueado_hasta > now:
        _event(
            db,
            event_type="cuenta_bloqueada",
            reason="bloqueo_vigente",
            request=request,
            user_id=user.id_usuario,
        )
        db.commit()
        raise _credentials_error()

    previous_failures = state.intentos_fallidos
    if state.bloqueado_hasta is not None and state.bloqueado_hasta <= now:
        previous_failures = 0

    if not password_valid:
        failures = min(previous_failures + 1, 5)
        blocked = failures == 5
        event = _event(
            db,
            event_type="cuenta_bloqueada" if blocked else "login_fallido",
            reason="quinto_fallo" if blocked else "credenciales_invalidas",
            request=request,
            user_id=user.id_usuario,
        )
        _link_state_event(db, event.id_evento)
        state.intentos_fallidos = failures
        state.bloqueado_hasta = (
            now + timedelta(minutes=AUTH_SETTINGS.lock_minutes)
            if blocked
            else None
        )
        state.actualizado_en = now
        db.commit()
        raise _credentials_error()

    session_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    expires_at = now + timedelta(minutes=AUTH_SETTINGS.absolute_minutes)
    set_audit_context(db, user.id_usuario)
    session = models.SesionUsuario(
        id_usuario=user.id_usuario,
        token_hash=_hash_secret(session_token),
        csrf_hash=_hash_secret(csrf_token),
        fecha_creacion=now,
        ultima_actividad=now,
        expira_en=expires_at,
        ip_creacion=_request_ip(request),
        user_agent_creacion=_safe_user_agent(request),
    )
    db.add(session)
    db.flush()
    event = _event(
        db,
        event_type="login_exitoso",
        reason="inicio_sesion",
        request=request,
        user_id=user.id_usuario,
        actor_id=user.id_usuario,
        session_id=session.id_sesion,
    )
    _link_state_event(db, event.id_evento)
    state.intentos_fallidos = 0
    state.bloqueado_hasta = None
    state.ultimo_acceso_en = now
    state.actualizado_en = now
    db.commit()
    db.refresh(session)
    return user, session, session_token, csrf_token


def _session_by_token(
    db: Session,
    token: str,
    *,
    for_update: bool = False,
) -> models.SesionUsuario | None:
    query = db.query(models.SesionUsuario).filter(
        models.SesionUsuario.token_hash == _hash_secret(token)
    )
    if for_update:
        query = query.with_for_update()
    return query.one_or_none()


def authenticate_session(
    db: Session,
    request: Request,
    token: str,
) -> tuple[models.Usuario, models.SesionUsuario]:
    now = _utcnow()
    session = _session_by_token(db, token, for_update=True)
    if session is None or session.revocada_en is not None:
        db.rollback()
        raise _session_error()

    user = db.query(models.Usuario).filter(
        models.Usuario.id_usuario == session.id_usuario
    ).one_or_none()
    inactivity_limit = now - timedelta(minutes=AUTH_SETTINGS.inactivity_minutes)
    reason = None
    if session.expira_en <= now:
        reason = "expiracion_absoluta"
    elif session.ultima_actividad <= inactivity_limit:
        reason = "expiracion_inactividad"
    elif user is None or not user.activo:
        reason = "usuario_inactivo"

    if reason is not None:
        event = _event(
            db,
            event_type=(
                "sesion_expirada"
                if reason.startswith("expiracion_")
                else "sesion_revocada"
            ),
            reason=reason,
            request=request,
            user_id=session.id_usuario,
            session_id=session.id_sesion,
        )
        _link_system_session_event(db, event.id_evento)
        session.revocada_en = now
        session.id_usuario_revoca = None
        session.motivo_revocacion = reason
        db.commit()
        raise _session_error()

    set_audit_context(db, user.id_usuario)
    session.ultima_actividad = now
    db.commit()
    return user, session


def validate_csrf(
    db: Session,
    session_token: str,
    csrf_token: str,
) -> bool:
    session = _session_by_token(db, session_token)
    if session is None:
        return False
    return hmac.compare_digest(session.csrf_hash, _hash_secret(csrf_token))


def revoke_current_session(
    db: Session,
    request: Request,
    token: str,
) -> None:
    session = _session_by_token(db, token, for_update=True)
    if session is None or session.revocada_en is not None:
        db.rollback()
        return
    now = _utcnow()
    set_audit_context(db, session.id_usuario)
    session.revocada_en = now
    session.id_usuario_revoca = session.id_usuario
    session.motivo_revocacion = "cierre_usuario"
    _event(
        db,
        event_type="logout",
        reason="cierre_usuario",
        request=request,
        user_id=session.id_usuario,
        actor_id=session.id_usuario,
        session_id=session.id_sesion,
    )
    db.commit()


def revoke_user_sessions(
    db: Session,
    request: Request,
    *,
    target_user_id: int,
    actor_user_id: int,
    reason: str,
    event_reason: str,
) -> int:
    sessions = (
        db.query(models.SesionUsuario)
        .filter(
            models.SesionUsuario.id_usuario == target_user_id,
            models.SesionUsuario.revocada_en.is_(None),
        )
        .with_for_update()
        .all()
    )
    now = _utcnow()
    set_audit_context(db, actor_user_id)
    for session in sessions:
        session.revocada_en = now
        session.id_usuario_revoca = actor_user_id
        session.motivo_revocacion = reason[:100]
        _event(
            db,
            event_type="sesion_revocada",
            reason=event_reason,
            request=request,
            user_id=target_user_id,
            actor_id=actor_user_id,
            session_id=session.id_sesion,
            detail=reason,
        )
    if not sessions:
        _event(
            db,
            event_type="sesion_revocada",
            reason=event_reason,
            request=request,
            user_id=target_user_id,
            actor_id=actor_user_id,
            detail=reason,
        )
    db.commit()
    return len(sessions)


def unlock_user(
    db: Session,
    request: Request,
    *,
    target_user_id: int,
    actor_user_id: int,
    reason: str,
) -> None:
    user = db.query(models.Usuario).filter(
        models.Usuario.id_usuario == target_user_id
    ).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    state = (
        db.query(models.EstadoAutenticacionUsuario)
        .filter(models.EstadoAutenticacionUsuario.id_usuario == target_user_id)
        .with_for_update()
        .one()
    )
    event = _event(
        db,
        event_type="desbloqueo",
        reason="desbloqueo_admin",
        request=request,
        user_id=target_user_id,
        actor_id=actor_user_id,
        detail=reason,
    )
    _link_state_event(db, event.id_evento)
    state.intentos_fallidos = 0
    state.bloqueado_hasta = None
    state.actualizado_en = _utcnow()
    db.commit()
