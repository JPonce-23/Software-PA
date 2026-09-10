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
from ..passwords import is_within_bcrypt_limit
from .common import commit_or_conflict, set_audit_context


_DUMMY_PASSWORD_HASH = bcrypt.hashpw(
    b"software-pa-dummy-authentication-value",
    bcrypt.gensalt(),
).decode("utf-8")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def password_matches(password: str, password_hash: str) -> bool:
    """Compare a password only when it is safe to pass to bcrypt."""
    password_bytes = password.encode("utf-8")
    if not is_within_bcrypt_limit(password):
        return False
    return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))


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
        password_matches(password, _DUMMY_PASSWORD_HASH)
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

    password_valid = password_matches(password, user.contrasena_hash)
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


def _revoke_user_sessions_in_transaction(
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
        session.motivo_revocacion = reason
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
    return len(sessions)


def revoke_user_sessions(
    db: Session,
    request: Request,
    *,
    target_user_id: int,
    actor_user_id: int,
    reason: str,
    event_reason: str,
) -> int:
    target = (
        db.query(models.Usuario)
        .filter(models.Usuario.id_usuario == target_user_id)
        .with_for_update()
        .one_or_none()
    )
    if target is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    revoked = _revoke_user_sessions_in_transaction(
        db,
        request,
        target_user_id=target_user_id,
        actor_user_id=actor_user_id,
        reason=reason,
        event_reason=event_reason,
    )
    db.commit()
    return revoked


def change_user_email(
    db: Session,
    request: Request,
    *,
    target_user_id: int,
    actor_user_id: int,
    email: str,
    reason: str,
) -> int:
    target = db.query(models.Usuario).filter(
        models.Usuario.id_usuario == target_user_id
    ).with_for_update().one_or_none()
    if target is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if target.correo.strip().lower() == email:
        db.rollback()
        raise HTTPException(status_code=409, detail="El correo no presenta cambios")
    duplicate = db.query(models.Usuario.id_usuario).filter(
        func.lower(func.btrim(models.Usuario.correo)) == email,
        models.Usuario.id_usuario != target_user_id,
    ).first()
    if duplicate is not None:
        db.rollback()
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    set_audit_context(db, actor_user_id)
    target.correo = email
    _event(
        db,
        event_type="cambio_correo",
        reason="cambio_correo_admin",
        request=request,
        user_id=target_user_id,
        actor_id=actor_user_id,
        detail=reason,
    )
    revoked = _revoke_user_sessions_in_transaction(
        db, request, target_user_id=target_user_id, actor_user_id=actor_user_id,
        reason=reason, event_reason="cambio_correo_admin",
    )
    commit_or_conflict(db, "No fue posible cambiar el correo")
    return revoked


def change_own_password(
    db: Session,
    request: Request,
    *,
    user_id: int,
    current_password: str,
    new_password: str,
) -> int:
    target = db.query(models.Usuario).filter(
        models.Usuario.id_usuario == user_id
    ).with_for_update().one_or_none()
    if target is None:
        db.rollback()
        raise HTTPException(status_code=401, detail="No se pudo validar la sesión")
    if not password_matches(current_password, target.contrasena_hash):
        db.rollback()
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")
    if password_matches(new_password, target.contrasena_hash):
        db.rollback()
        raise HTTPException(status_code=409, detail="La contraseña nueva no puede coincidir con la actual")
    set_audit_context(db, user_id)
    target.contrasena_hash = hash_password(new_password)
    _event(
        db, event_type="cambio_contrasena", reason="cambio_contrasena_usuario",
        request=request, user_id=user_id, actor_id=user_id,
        detail="Cambio de contraseña solicitado por el usuario",
    )
    revoked = _revoke_user_sessions_in_transaction(
        db, request, target_user_id=user_id, actor_user_id=user_id,
        reason="Cambio de contraseña solicitado por el usuario",
        event_reason="cambio_contrasena_usuario",
    )
    commit_or_conflict(db, "No fue posible cambiar la contraseña")
    return revoked


def reset_user_password(
    db: Session,
    request: Request,
    *,
    target_user_id: int,
    actor_user_id: int,
    new_password: str,
    reason: str,
) -> int:
    if target_user_id == actor_user_id:
        raise HTTPException(status_code=409, detail="Use el cambio de contraseña propio")
    target = db.query(models.Usuario).filter(
        models.Usuario.id_usuario == target_user_id
    ).with_for_update().one_or_none()
    if target is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if password_matches(new_password, target.contrasena_hash):
        db.rollback()
        raise HTTPException(status_code=409, detail="La contraseña nueva no puede coincidir con la actual")
    set_audit_context(db, actor_user_id)
    target.contrasena_hash = hash_password(new_password)
    _event(
        db, event_type="restablecimiento_contrasena", reason="restablecimiento_contrasena_admin",
        request=request, user_id=target_user_id, actor_id=actor_user_id, detail=reason,
    )
    revoked = _revoke_user_sessions_in_transaction(
        db, request, target_user_id=target_user_id, actor_user_id=actor_user_id,
        reason=reason, event_reason="restablecimiento_contrasena_admin",
    )
    commit_or_conflict(db, "No fue posible restablecer la contraseña")
    return revoked


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
    ).with_for_update().one_or_none()
    if user is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    state = (
        db.query(models.EstadoAutenticacionUsuario)
        .filter(models.EstadoAutenticacionUsuario.id_usuario == target_user_id)
        .with_for_update()
        .one()
    )
    now = _utcnow()
    if state.bloqueado_hasta is None or state.bloqueado_hasta <= now:
        db.rollback()
        raise HTTPException(status_code=409, detail="La cuenta no está bloqueada")
    set_audit_context(db, actor_user_id)
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
    state.actualizado_en = now
    db.commit()
