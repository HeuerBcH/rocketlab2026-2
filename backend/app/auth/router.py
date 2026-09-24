from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.auth.security import AdminUser, AuthNotConfiguredError, authenticate

auth_router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class Me(BaseModel):
    username: str


@auth_router.post(
    "/token",
    response_model=Token,
    summary="Login do administrador",
    responses={401: {"description": "Usuário ou senha inválidos"}},
)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """Recebe usuário e senha (form OAuth2) e devolve um JWT de acesso."""

    token, expires_in = await authenticate(form.username, form.password)
    return Token(access_token=token, expires_in=expires_in)


@auth_router.get(
    "/me",
    response_model=Me,
    summary="Usuário da sessão atual",
    responses={401: {"description": "Não autenticado"}},
)
async def me(username: AdminUser) -> Me:
    return Me(username=username)


def register_auth_exception_handlers(app: FastAPI) -> None:
    async def not_configured(request: Request, exc: Exception) -> JSONResponse:
        del request
        # Erro de configuração do servidor, não do usuário: 503 com instrução clara.
        return JSONResponse(
            status_code=503,
            content={"detail": f"Autenticação não configurada no servidor: {exc}"},
        )

    app.add_exception_handler(AuthNotConfiguredError, not_configured)
