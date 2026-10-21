"""Recebimento de telemetria: grava posições, abre/fecha viagens e acompanha o trecho."""
from datetime import datetime, timedelta

from geoalchemy2.shape import from_shape, to_shape
from pydantic import AwareDatetime, BaseModel
from shapely.geometry import LineString, Point
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.estados import Estado
from app.eta import calcular_eta
from app.geo import progresso_na_linha
from app.modelos import Caminhao, EventoViagem, Posicao, Rota, Viagem

EM_TRANSITO = {Estado.EM_TRANSITO_CARREGADO, Estado.EM_TRANSITO_VAZIO}


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


def _rotas(sessao: Session) -> dict[int, tuple[LineString, float]]:
    """Rota de cada fazenda (sentido fazenda → fábrica) e sua distância em km."""
    return {
        r.fazenda_id: (to_shape(r.geom), r.distancia_km) for r in sessao.scalars(select(Rota))
    }


def _atualizar_trecho(
    sessao: Session,
    caminhao: Caminhao,
    leitura: LeituraEntrada,
    entrou: bool,
    rota: tuple[LineString, float] | None,
    settings: Settings,
) -> None:
    """Início, chegada prevista e ETA do trecho em trânsito. A posição já foi gravada."""
    if leitura.estado not in EM_TRANSITO:
        caminhao.inicio_trecho = caminhao.eta_prevista = caminhao.eta_atual = None
        return
    carregado = leitura.estado == Estado.EM_TRANSITO_CARREGADO
    if entrou or caminhao.inicio_trecho is None:
        caminhao.inicio_trecho = leitura.momento
        caminhao.eta_prevista = None
        if rota is not None:
            # Previsto pela velocidade média configurada, não pela duração do OSRM (de carro).
            velocidade = settings.velocidade_carregado_kmh if carregado else settings.velocidade_vazio_kmh
            caminhao.eta_prevista = leitura.momento + timedelta(hours=rota[1] / velocidade)
            if carregado and caminhao.viagem_atual is not None:
                caminhao.viagem_atual.eta_prevista = caminhao.eta_prevista
    if rota is None:
        caminhao.eta_atual = None
        return
    linha, distancia_km = rota
    fracao, _ = progresso_na_linha(linha, Point(leitura.lon, leitura.lat))
    # A rota vai da fazenda à fábrica; o vazio a percorre ao contrário.
    restante_km = (1 - fracao) * distancia_km if carregado else fracao * distancia_km
    velocidades = sessao.scalars(
        select(Posicao.velocidade_kmh)
        .where(Posicao.caminhao_id == caminhao.id, Posicao.momento >= caminhao.inicio_trecho)
        .order_by(Posicao.momento.desc(), Posicao.id.desc())
        .limit(settings.eta_leituras)
    ).all()
    caminhao.eta_atual = calcular_eta(
        leitura.momento, restante_km, list(velocidades), settings.eta_velocidade_min_kmh
    )


def registrar_leituras(
    sessao: Session, leituras: list[LeituraEntrada], settings: Settings | None = None
) -> list[int]:
    """Aplica o lote na ordem recebida. Devolve os ids dos caminhões atualizados."""
    settings = settings or get_settings()
    ids = {l.caminhao_id for l in leituras}
    caminhoes = {c.id: c for c in sessao.scalars(select(Caminhao).where(Caminhao.id.in_(ids)))}
    for leitura in leituras:
        if leitura.caminhao_id not in caminhoes:
            raise CaminhaoDesconhecido(leitura.caminhao_id)

    rotas = _rotas(sessao)
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

        entrou = leitura.estado != caminhao.estado_atual
        if entrou:
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
        _atualizar_trecho(
            sessao, caminhao, leitura, entrou, rotas.get(leitura.fazenda_id), settings
        )
        if caminhao.id not in atualizados:
            atualizados.append(caminhao.id)
    sessao.flush()
    return atualizados
