"""Fase 2B: app do motorista — check-ins, ocorrências e posse do caminhão pelo app.

Revision ID: 0003_motorista
Revises: 0002_fase2
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_motorista"
down_revision = "0002_fase2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "checkins",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("viagem_id", sa.Integer, sa.ForeignKey("viagens.id"), nullable=False),
        sa.Column("caminhao_id", sa.Integer, sa.ForeignKey("caminhoes.id"), nullable=False),
        sa.Column("acao", sa.String(30), nullable=False),
        sa.Column("momento", sa.DateTime(timezone=True), nullable=False),
        # Gerado no celular: o mesmo envio repetido pela fila offline não duplica.
        sa.Column("id_local", sa.String(36), nullable=False, unique=True),
    )
    op.create_table(
        "ocorrencias",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("viagem_id", sa.Integer, sa.ForeignKey("viagens.id")),
        sa.Column("motorista_id", sa.Integer, sa.ForeignKey("motoristas.id"), nullable=False),
        sa.Column("caminhao_id", sa.Integer, sa.ForeignKey("caminhoes.id"), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("descricao", sa.String(500), nullable=False),
        sa.Column("foto_url", sa.String(200)),
        sa.Column("momento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id_local", sa.String(36), nullable=False, unique=True),
    )
    op.add_column("caminhoes", sa.Column("assumido_ate", sa.DateTime(timezone=True)))
    op.add_column(
        "caminhoes",
        sa.Column("fazenda_destino_id", sa.Integer, sa.ForeignKey("fazendas.id")),
    )


def downgrade() -> None:
    op.drop_column("caminhoes", "fazenda_destino_id")
    op.drop_column("caminhoes", "assumido_ate")
    op.drop_table("ocorrencias")
    op.drop_table("checkins")
