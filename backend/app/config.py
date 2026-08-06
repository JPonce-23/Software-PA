import os
from dataclasses import dataclass
from ipaddress import ip_address


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} debe ser true o false")


def _read_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} debe ser un entero") from exc
    if value <= 0:
        raise RuntimeError(f"{name} debe ser mayor que cero")
    return value


def _read_csv(name: str, default: str = "") -> tuple[str, ...]:
    values = tuple(value.strip() for value in os.getenv(name, default).split(","))
    return tuple(value for value in values if value)


@dataclass(frozen=True)
class AuthSettings:
    environment: str
    cookie_secure: bool
    cookie_samesite: str
    inactivity_minutes: int
    absolute_minutes: int
    lock_minutes: int
    allowed_origins: tuple[str, ...]
    trusted_proxy_ips: tuple[str, ...]

    @property
    def session_cookie_name(self) -> str:
        return "__Host-pa_session" if self.cookie_secure else "pa_session_dev"

    @property
    def csrf_cookie_name(self) -> str:
        return "__Host-pa_csrf" if self.cookie_secure else "pa_csrf_dev"


def load_auth_settings() -> AuthSettings:
    environment = os.getenv("APP_ENV", "development").strip().lower()
    if environment not in {"development", "test", "production"}:
        raise RuntimeError("APP_ENV debe ser development, test o production")

    cookie_secure = _read_bool("AUTH_COOKIE_SECURE", environment == "production")
    if environment == "production" and not cookie_secure:
        raise RuntimeError("Producción requiere AUTH_COOKIE_SECURE=true")

    cookie_samesite = os.getenv("AUTH_COOKIE_SAMESITE", "lax").strip().lower()
    if cookie_samesite not in {"lax", "strict"}:
        raise RuntimeError("AUTH_COOKIE_SAMESITE debe ser lax o strict")

    allowed_origins = _read_csv("CORS_ORIGINS", "http://localhost:5173")
    if not allowed_origins or "*" in allowed_origins:
        raise RuntimeError("CORS_ORIGINS debe contener orígenes explícitos")

    trusted_proxy_ips = _read_csv("AUTH_TRUSTED_PROXY_IPS")
    for value in trusted_proxy_ips:
        try:
            ip_address(value)
        except ValueError as exc:
            raise RuntimeError(
                "AUTH_TRUSTED_PROXY_IPS sólo admite direcciones IP exactas"
            ) from exc

    inactivity_minutes = _read_positive_int("AUTH_INACTIVITY_MINUTES", 30)
    absolute_minutes = _read_positive_int("AUTH_ABSOLUTE_MINUTES", 480)
    lock_minutes = _read_positive_int("AUTH_LOCK_MINUTES", 15)
    if absolute_minutes <= inactivity_minutes:
        raise RuntimeError(
            "AUTH_ABSOLUTE_MINUTES debe ser mayor que AUTH_INACTIVITY_MINUTES"
        )

    return AuthSettings(
        environment=environment,
        cookie_secure=cookie_secure,
        cookie_samesite=cookie_samesite,
        inactivity_minutes=inactivity_minutes,
        absolute_minutes=absolute_minutes,
        lock_minutes=lock_minutes,
        allowed_origins=allowed_origins,
        trusted_proxy_ips=trusted_proxy_ips,
    )


AUTH_SETTINGS = load_auth_settings()
