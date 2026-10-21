"""Recebimento de telemetria: grava posições e abre/fecha viagens conforme o estado."""
from datetime import datetime

from geoalchemy2.shape import from_shape
from pydantic import AwareDatetime, BaseModel
from shapely.geometry import Point
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.estados import Estado
from app.modelos import Caminhao, EventoViagem, Posicao, Rota, Viagem


class LeituraEntrada(BaseModel):
    caminhao_id: int
    fazenda_id: int
    estado: Estado
    lon: float
    lat: float
    velocidade_kmh: float
    momento: AwareDatetime


class CaminhaoDesconhecido(Exception):
    def __init__(self, caminhao_id: int):
        super().__init__(f"Caminhão {caminhao_id} não existe")
        self.caminhao_id = caminhao_id


def _abrir_viagem(sessao: Session, caminhao: Caminhao, fazenda_id: int, momento: datetime) -> None:
    if caminhao.viagem_atual is not None:
        caminhao.viagem_atual.fim = momento
        # Só entregou quem já saiu vazio da fábrica; o resto foi cortado por um reinício.
        entregou = caminhao.estado_atual == Estado.EM_TRANSITO_VAZIO
        caminhao.viagem_atual.status = "CONCLUIDA" if entregou else "INTERROMPIDA"
    rota_id = sessao.scalar(select(Rota.id).where(Rota.fazenda_id == fazenda_id))
    viagem = Viagem(
        caminhao_id=caminhao.id,
        fazenda_id=fazenda_id,
        rota_id=rota_id,
        toneladas=caminhao.capacidade_t,
        inicio=momento,
        status="EM_ANDAMENTO",
    )
    sessao.add(viagem)
    sessao.flush()
    caminhao.viagem_atual = viagem
    caminhao.viagem_atual_id = viagem.id


def registrar_leituras(sessao: Session, leituras: list[LeituraEntrada]) -> list[int]:
    """Aplica o lote na ordem recebida. Devolve os ids dos caminhões atualizados."""
    ids = {l.caminhao_id for l in leituras}
    caminhoes = {c.id: c for c in sessao.scalars(select(Caminhao).where(Caminhao.id.in_(ids)))}
    for leitura in leituras:
        if leitura.caminhao_id not in caminhoes:
            raise CaminhaoDesconhecido(leitura.caminhao_id)

    atualizados: list[int] = []
    for leitura in leituras:
        caminhao = caminhoes[leitura.caminhao_id]
        viagem = caminhao.viagem_atual
        comecou_a_carregar = leitura.estado == Estado.CARREGANDO and (
            caminhao.estado_atual != Estado.CARREGANDO
            or (viagem is not None and viagem.fazenda_id != leitura.fazenda_id)
        )
        if comecou_a_carregar or viagem is None:
            _abrir_viagem(sessao, caminhao, leitura.fazenda_id, leitura.momento)

        if leitura.estado != caminhao.estado_atual:
            sessao.add(
                EventoViagem(
                    viagem_id=caminhao.viagem_atual_id, estado=leitura.estado, momento=leitura.momento
                )
            )
            caminhao.estado_atual = leitura.estado

        sessao.add(
            Posicao(
                caminhao_id=caminhao.id,
                viagem_id=caminhao.viagem_atual_id,
                geom=from_shape(Point(leitura.lon, leitura.lat), srid=4326),
                velocidade_kmh=leitura.velocidade_kmh,
                momento=leitura.momento,
            )
        )
        if caminhao.id not in atualizados:
            atualizados.append(caminhao.id)
    sessao.flush()
    return atualizados
