"""Gera o hash da senha do administrador para o .env.

Uso (a partir de ``backend/``)::

    python -m app.auth.hash_password
"""

from getpass import getpass

from app.auth.security import password_hasher


def main() -> None:
    password = getpass("Nova senha do administrador: ")
    if len(password) < 8:
        raise SystemExit("A senha deve ter pelo menos 8 caracteres.")
    if password != getpass("Repita a senha: "):
        raise SystemExit("As senhas não conferem.")
    print("\nCole no backend/.env (com as aspas simples):")
    print(f"ADMIN_PASSWORD_HASH='{password_hasher().hash(password)}'")


if __name__ == "__main__":
    main()
