"""Fase 2: alertas, trecho atual do caminhão e índice de posições por momento.

Revision ID: 0002_fase2
Revises: 0001_fase1
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_fase2"
down_revision = "0001_fase1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alertas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("caminhao_id", sa.Integer, sa.ForeignKey("caminhoes.id")),
        sa.Column("fazenda_id", sa.Integer, sa.ForeignKey("fazendas.id")),
        # A FK para focos_calor entra na Fase 3, junto com a tabela.
        sa.Column("foco_id", sa.Integer),
        sa.Column("mensagem", sa.String(200), nullable=False),
        sa.Column("aberto_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fechado_em", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(10), nullable=False),
    )
    # Um alerta do mesmo tipo para o mesmo caminhão não se repete enquanto estiver aberto.
    op.create_index(
        "ux_alertas_aberto", "alertas", ["tipo", "caminhao_id"], unique=True,
        postgresql_where=sa.text("status = 'ABERTO'"),
    )
    op.create_index("ix_alertas_aberto_em", "alertas", ["aberto_em"])
    for coluna in ("inicio_trecho", "eta_prevista", "eta_atual"):
        op.add_column("caminhoes", sa.Column(coluna, sa.DateTime(timezone=True)))
    op.create_index("ix_posicoes_momento", "posicoes", ["momento"])


def downgrade() -> None:
    op.drop_index("ix_posicoes_momento", table_name="posicoes")
    for coluna in ("eta_atual", "eta_prevista", "inicio_trecho"):
        op.drop_column("caminhoes", coluna)
    op.drop_index("ix_alertas_aberto_em", table_name="alertas")
    op.drop_index("ux_alertas_aberto", table_name="alertas")
    op.drop_table("alertas")
