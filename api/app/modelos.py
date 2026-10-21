from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ComId:
    id: Mapped[int] = mapped_column(primary_key=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Fabrica(ComId, Base):
    __tablename__ = "fabrica"
    nome: Mapped[str] = mapped_column(String(120))
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=False)


class Fazenda(ComId, Base):
    __tablename__ = "fazendas"
    nome: Mapped[str] = mapped_column(String(120))
    area_ha: Mapped[float] = mapped_column(Float)
    centro = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    geom = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)


class Motorista(ComId, Base):
    __tablename__ = "motoristas"
    nome: Mapped[str] = mapped_column(String(120))


class Caminhao(ComId, Base):
    __tablename__ = "caminhoes"
    placa: Mapped[str] = mapped_column(String(7), unique=True)
    tipo: Mapped[str] = mapped_column(String(20))
    capacidade_t: Mapped[float] = mapped_column(Float)
    motorista_id: Mapped[int] = mapped_column(ForeignKey("motoristas.id"))
    estado_atual: Mapped[str | None] = mapped_column(String(30))
    viagem_atual_id: Mapped[int | None] = mapped_column(
        ForeignKey("viagens.id", use_alter=True, name="fk_caminhoes_viagem_atual")
    )
    # Trecho em trânsito atual: quando começou, chegada prevista e ETA pelas últimas leituras.
    inicio_trecho: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    eta_prevista: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    eta_atual: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    motorista: Mapped[Motorista] = relationship()
    viagem_atual: Mapped["Viagem | None"] = relationship(foreign_keys=[viagem_atual_id])


class Rota(ComId, Base):
    __tablename__ = "rotas"
    fazenda_id: Mapped[int] = mapped_column(ForeignKey("fazendas.id"), unique=True)
    geom = mapped_column(Geometry("LINESTRING", srid=4326), nullable=False)
    distancia_km: Mapped[float] = mapped_column(Float)
    duracao_prevista_min: Mapped[float] = mapped_column(Float)


class Viagem(ComId, Base):
    __tablename__ = "viagens"
    caminhao_id: Mapped[int] = mapped_column(ForeignKey("caminhoes.id"))
    fazenda_id: Mapped[int] = mapped_column(ForeignKey("fazendas.id"))
    rota_id: Mapped[int | None] = mapped_column(ForeignKey("rotas.id"))
    toneladas: Mapped[float] = mapped_column(Float)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    eta_prevista: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20))

    fazenda: Mapped[Fazenda] = relationship()
    eventos: Mapped[list["EventoViagem"]] = relationship(order_by="EventoViagem.momento")


class EventoViagem(ComId, Base):
    __tablename__ = "eventos_viagem"
    viagem_id: Mapped[int] = mapped_column(ForeignKey("viagens.id"))
    estado: Mapped[str] = mapped_column(String(30))
    momento: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Posicao(ComId, Base):
    __tablename__ = "posicoes"
    caminhao_id: Mapped[int] = mapped_column(ForeignKey("caminhoes.id"))
    viagem_id: Mapped[int | None] = mapped_column(ForeignKey("viagens.id"))
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    velocidade_kmh: Mapped[float] = mapped_column(Float)
    momento: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_posicoes_caminhao_momento", "caminhao_id", "momento"),
        Index("ix_posicoes_momento", "momento"),
    )


class Alerta(ComId, Base):
    __tablename__ = "alertas"
    tipo: Mapped[str] = mapped_column(String(30))
    caminhao_id: Mapped[int | None] = mapped_column(ForeignKey("caminhoes.id"))
    fazenda_id: Mapped[int | None] = mapped_column(ForeignKey("fazendas.id"))
    foco_id: Mapped[int | None] = mapped_column(Integer)
    mensagem: Mapped[str] = mapped_column(String(200))
    aberto_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fechado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(10))

    caminhao: Mapped[Caminhao | None] = relationship()
    fazenda: Mapped[Fazenda | None] = relationship()

    __table_args__ = (
        Index(
            "ux_alertas_aberto", "tipo", "caminhao_id",
            unique=True, postgresql_where=text("status = 'ABERTO'"),
        ),
        Index("ix_alertas_aberto_em", "aberto_em"),
    )
