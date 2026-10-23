"""Fase 3B: clima diário, risco (FMA) e focos de calor.

Revision ID: 0004_risco
Revises: 0003_motorista
"""
import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision = "0004_risco"
down_revision = "0003_motorista"
branch_labels = None
depends_on = None


def _base() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "clima_diario",
        *_base(),
        sa.Column("fazenda_id", sa.Integer, sa.ForeignKey("fazendas.id"), nullable=False),
        sa.Column("data", sa.Date, nullable=False),
        sa.Column("ur_13h", sa.Float),
        sa.Column("chuva_mm", sa.Float),
        sa.Column("vento_kmh", sa.Float),
        sa.Column("vento_dir", sa.Float),
        sa.UniqueConstraint("fazenda_id", "data", name="uq_clima_diario_fazenda_data"),
    )
    op.create_table(
        "risco_diario",
        *_base(),
        sa.Column("fazenda_id", sa.Integer, sa.ForeignKey("fazendas.id"), nullable=False),
        sa.Column("data", sa.Date, nullable=False),
        sa.Column("fma", sa.Float, nullable=False),
        sa.Column("classe", sa.String(12), nullable=False),
        sa.UniqueConstraint("fazenda_id", "data", name="uq_risco_diario_fazenda_data"),
    )
    op.create_table(
        "focos_calor",
        *_base(),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("satelite", sa.String(40), nullable=False),
        sa.Column("detectado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("municipio", sa.String(120)),
        # lat|lon|data e hora|satélite: igualdade de geometria no índice não é confiável.
        sa.Column("chave", sa.String(120), nullable=False),
        sa.UniqueConstraint("chave", name="uq_focos_calor_chave"),
    )
    op.create_index("ix_focos_calor_detectado_em", "focos_calor", ["detectado_em"])


def downgrade() -> None:
    op.drop_table("focos_calor")
    op.drop_table("risco_diario")
    op.drop_table("clima_diario")
