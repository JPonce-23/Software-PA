from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..config import AUTH_SETTINGS
from ..database import get_db
from ..services import authentication as service


router = APIRouter(tags=["Autenticación"])


def _set_auth_cookies(
    response: Response,
    *,
    session_token: str,
    csrf_token: str,
) -> None:
    max_age = AUTH_SETTINGS.absolute_minutes * 60
    common = {
        "secure": AUTH_SETTINGS.cookie_secure,
        "samesite": AUTH_SETTINGS.cookie_samesite,
        "path": "/",
        "max_age": max_age,
    }
    response.set_cookie(
        AUTH_SETTINGS.session_cookie_name,
        session_token,
        httponly=True,
        **common,
    )
    response.set_cookie(
        AUTH_SETTINGS.csrf_cookie_name,
        csrf_token,
        httponly=False,
        **common,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        AUTH_SETTINGS.session_cookie_name,
        path="/",
        secure=AUTH_SETTINGS.cookie_secure,
        samesite=AUTH_SETTINGS.cookie_samesite,
    )
    response.delete_cookie(
        AUTH_SETTINGS.csrf_cookie_name,
        path="/",
        secure=AUTH_SETTINGS.cookie_secure,
        samesite=AUTH_SETTINGS.cookie_samesite,
    )


@router.post(
    "/auth/sesiones",
    response_model=schemas.AuthSessionResponse,
    summary="Iniciar sesión con cookie segura",
)
def create_auth_session(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user, session, session_token, csrf_token = service.create_session(
        db,
        request,
        form_data.username,
        form_data.password,
    )
    _set_auth_cookies(
        response,
        session_token=session_token,
        csrf_token=csrf_token,
    )
    return {"user": user, "expira_en": session.expira_en}


@router.get(
    "/auth/sesion",
    response_model=schemas.AuthSessionResponse,
    summary="Consultar la sesión actual",
)
def get_auth_session(
    context: tuple[models.Usuario, models.SesionUsuario] = Depends(
        auth.get_session_context
    ),
):
    user, session = context
    return {"user": user, "expira_en": session.expira_en}


@router.post(
    "/auth/logout",
    response_model=schemas.AuthOperationResponse,
    summary="Cerrar la sesión actual",
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(AUTH_SETTINGS.session_cookie_name)
    if token:
        service.revoke_current_session(db, request, token)
    _clear_auth_cookies(response)
    return {"detail": "Sesión cerrada"}


@router.post(
    "/auth/logout-todas",
    response_model=schemas.AuthOperationResponse,
    summary="Cerrar todas las sesiones propias",
)
def logout_all(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user),
):
    service.revoke_user_sessions(
        db,
        request,
        target_user_id=current_user.id_usuario,
        actor_user_id=current_user.id_usuario,
        reason="Cierre de todas las sesiones por el usuario",
        event_reason="cierre_total",
    )
    _clear_auth_cookies(response)
    return {"detail": "Todas las sesiones fueron cerradas"}


@router.post(
    "/usuarios/{id_usuario}/desbloquear",
    response_model=schemas.AuthOperationResponse,
    summary="Desbloquear una cuenta",
)
def unlock_user(
    id_usuario: int,
    data: schemas.AuthActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    service.unlock_user(
        db,
        request,
        target_user_id=id_usuario,
        actor_user_id=current_user.id_usuario,
        reason=data.motivo,
    )
    return {"detail": "Cuenta desbloqueada"}


@router.post(
    "/usuarios/{id_usuario}/revocar-sesiones",
    response_model=schemas.AuthOperationResponse,
    summary="Revocar las sesiones de un usuario",
)
def revoke_sessions(
    id_usuario: int,
    data: schemas.AuthActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    service.revoke_user_sessions(
        db,
        request,
        target_user_id=id_usuario,
        actor_user_id=current_user.id_usuario,
        reason=data.motivo,
        event_reason="revocacion_admin",
    )
    return {"detail": "Sesiones revocadas"}
