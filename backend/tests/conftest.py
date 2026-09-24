from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Banco SQLite temporário com o schema aplicado pelas migrações do Alembic."""

    path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{path.as_posix()}")
    get_settings.cache_clear()
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    yield path
    get_settings.cache_clear()
