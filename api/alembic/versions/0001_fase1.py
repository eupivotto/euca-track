"""Tabelas da fase 1: fábrica, fazendas, frota, rotas, viagens e posições.

Revision ID: 0001_fase1
Revises:
"""
import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision = "0001_fase1"
down_revision = None
branch_labels = None
depends_on = None


def _id():
    return [
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    ]


def upgrade() -> None:
    # O GeoAlchemy2 cria o índice espacial (GIST) de cada coluna Geometry.
    op.create_table(
        "fabrica", *_id(),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=False),
    )
    op.create_table(
        "fazendas", *_id(),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("area_ha", sa.Float, nullable=False),
        sa.Column("centro", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("geom", Geometry("POLYGON", srid=4326), nullable=False),
    )
    op.create_table("motoristas", *_id(), sa.Column("nome", sa.String(120), nullable=False))
    op.create_table(
        "caminhoes", *_id(),
        sa.Column("placa", sa.String(7), nullable=False, unique=True),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("capacidade_t", sa.Float, nullable=False),
        sa.Column("motorista_id", sa.Integer, sa.ForeignKey("motoristas.id"), nullable=False),
        sa.Column("estado_atual", sa.String(30)),
        sa.Column("viagem_atual_id", sa.Integer),
    )
    op.create_table(
        "rotas", *_id(),
        sa.Column("fazenda_id", sa.Integer, sa.ForeignKey("fazendas.id"), nullable=False, unique=True),
        sa.Column("geom", Geometry("LINESTRING", srid=4326), nullable=False),
        sa.Column("distancia_km", sa.Float, nullable=False),
        sa.Column("duracao_prevista_min", sa.Float, nullable=False),
    )
    op.create_table(
        "viagens", *_id(),
        sa.Column("caminhao_id", sa.Integer, sa.ForeignKey("caminhoes.id"), nullable=False),
        sa.Column("fazenda_id", sa.Integer, sa.ForeignKey("fazendas.id"), nullable=False),
        sa.Column("rota_id", sa.Integer, sa.ForeignKey("rotas.id")),
        sa.Column("toneladas", sa.Float, nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim", sa.DateTime(timezone=True)),
        sa.Column("eta_prevista", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False),
    )
    op.create_foreign_key(
        "fk_caminhoes_viagem_atual", "caminhoes", "viagens", ["viagem_atual_id"], ["id"]
    )
    op.create_table(
        "eventos_viagem", *_id(),
        sa.Column("viagem_id", sa.Integer, sa.ForeignKey("viagens.id"), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("momento", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "posicoes", *_id(),
        sa.Column("caminhao_id", sa.Integer, sa.ForeignKey("caminhoes.id"), nullable=False),
        sa.Column("viagem_id", sa.Integer, sa.ForeignKey("viagens.id")),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("velocidade_kmh", sa.Float, nullable=False),
        sa.Column("momento", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_posicoes_caminhao_momento", "posicoes", ["caminhao_id", "momento"])


def downgrade() -> None:
    op.drop_index("ix_posicoes_caminhao_momento", table_name="posicoes")
    op.drop_table("posicoes")
    op.drop_table("eventos_viagem")
    op.drop_constraint("fk_caminhoes_viagem_atual", "caminhoes", type_="foreignkey")
    op.drop_table("viagens")
    op.drop_table("rotas")
    op.drop_table("caminhoes")
    op.drop_table("motoristas")
    op.drop_table("fazendas")
    op.drop_table("fabrica")
