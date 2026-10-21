from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.config import Settings
from app.modelos import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_online() -> None:
    # Settings() novo (sem cache) para respeitar o DATABASE_URL dos testes.
    engine = create_engine(Settings().database_url)
    with engine.connect() as conexao:
        context.configure(connection=conexao, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
