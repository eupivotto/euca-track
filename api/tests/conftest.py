import os
from pathlib import Path

# Os testes usam sempre o banco rota_teste, nunca o de desenvolvimento.
os.environ["DATABASE_URL"] = os.environ.get(
    "DATABASE_URL_TESTE", "postgresql+psycopg://rota:rota@db:5432/rota_teste"
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import engine, get_sessao  # noqa: E402
from app.main import app  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def banco_migrado():
    ini = RAIZ / "alembic.ini"
    if ini.exists():
        from alembic import command
        from alembic.config import Config

        cfg = Config(str(ini))
        cfg.set_main_option("script_location", str(RAIZ / "alembic"))
        command.upgrade(cfg, "head")
    yield


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def sessao():
    conexao = engine.connect()
    transacao = conexao.begin()
    s = Session(bind=conexao, join_transaction_mode="create_savepoint")
    try:
        yield s
    finally:
        s.close()
        transacao.rollback()
        conexao.close()


@pytest.fixture
def cliente(sessao):
    app.dependency_overrides[get_sessao] = lambda: sessao
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
