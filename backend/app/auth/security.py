"""Autenticação do administrador com JWT (OAuth2 password flow).

Há um único usuário (o administrador), configurado por variáveis de ambiente:
não existe tabela de usuários. A senha nunca é guardada em texto, só o hash
(Argon2, via pwdlib).
"""

import logging
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from hmac import compare_digest
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
AUDIENCE = "rocketlab-admin"

# tokenUrl habilita o botão "Authorize" do Swagger (/docs) com usuário e senha.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


@lru_cache
def password_hasher() -> PasswordHash:
    return PasswordHash.recommended()


class AuthNotConfiguredError(RuntimeError):
    """ADMIN_PASSWORD_HASH ou AUTH_SECRET_KEY ausentes no .env."""


def credentials_error(detail: str = "Não autenticado") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def secret_key() -> str:
    key = get_settings().auth_secret_key.get_secret_value()
    if len(key) < 32:
        raise AuthNotConfiguredError("AUTH_SECRET_KEY ausente ou curta (mínimo 32 caracteres)")
    return key


def verify_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    password_hash = settings.admin_password_hash.get_secret_value()
    if not password_hash:
        raise AuthNotConfiguredError("ADMIN_PASSWORD_HASH ausente")
    # Verifica a senha mesmo com usuário errado: o tempo de resposta não revela
    # se o usuário existe.
    try:
        password_ok = password_hasher().verify(password, password_hash)
    except Exception as exc:  # hash malformado no .env
        raise AuthNotConfiguredError("ADMIN_PASSWORD_HASH inválido") from exc
    username_ok = compare_digest(username.encode(), settings.admin_username.encode())
    return password_ok and username_ok


async def authenticate(username: str, password: str) -> tuple[str, int]:
    """Valida as credenciais e devolve (token, segundos até expirar)."""

    # Argon2 é propositalmente lento: roda fora do event loop.
    if not await run_in_threadpool(verify_credentials, username, password):
        logger.warning("Tentativa de login inválida para o usuário %r", username)
        raise credentials_error("Usuário ou senha inválidos")

    settings = get_settings()
    now = datetime.now(UTC)
    expires_in = settings.access_token_minutes * 60
    token = jwt.encode(
        {
            "sub": settings.admin_username,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
        },
        secret_key(),
        algorithm=ALGORITHM,
    )
    return token, expires_in


async def current_admin(token: Annotated[str | None, Depends(oauth2_scheme)]) -> str:
    """Dependência das rotas protegidas: exige um token válido do administrador."""

    if not token:
        raise credentials_error()
    try:
        payload = jwt.decode(
            token,
            secret_key(),
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
            options={"require": ["sub", "exp", "iat", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise credentials_error("Sessão expirada; entre novamente") from exc
    except jwt.InvalidTokenError as exc:
        raise credentials_error("Token inválido") from exc
    if payload["sub"] != get_settings().admin_username:
        raise credentials_error("Token inválido")
    return payload["sub"]


AdminUser = Annotated[str, Depends(current_admin)]
