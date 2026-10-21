"""Regras dos alertas de logística (SPEC seção 6). Funções puras, sem banco."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.config import Settings
from app.estados import Estado

EM_TRANSITO = {Estado.EM_TRANSITO_CARREGADO, Estado.EM_TRANSITO_VAZIO}


class TipoAlerta(StrEnum):
    ATRASO = "ATRASO"
    PARADA = "PARADA"
    DESVIO_ROTA = "DESVIO_ROTA"
    VELOCIDADE = "VELOCIDADE"


@dataclass
class Situacao:
    """O que se sabe do caminhão na leitura mais recente."""

    estado: Estado
    velocidade_kmh: float
    momento: datetime
    # Primeira leitura da sequência atual abaixo do limite de parada (None se está andando).
    parado_desde: datetime | None
    # Até a fazenda ou a fábrica mais próxima.
    distancia_local_m: float
    # Leituras seguidas do trecho, terminando na atual, longe da rota (0 sem rota).
    fora_da_rota_seguidas: int
    inicio_trecho: datetime | None
    eta_prevista: datetime | None
    eta_atual: datetime | None


def alertas_ativos(s: Situacao, settings: Settings) -> set[TipoAlerta]:
    ativos: set[TipoAlerta] = set()
    if s.velocidade_kmh > settings.alerta_velocidade_max_kmh:
        ativos.add(TipoAlerta.VELOCIDADE)
    # Parar para carregar, na fila ou descarregando é o normal: só vale em trânsito.
    if s.estado not in EM_TRANSITO:
        return ativos

    if (
        s.parado_desde is not None
        and s.momento - s.parado_desde > timedelta(minutes=settings.alerta_parada_min)
        and s.distancia_local_m > settings.alerta_raio_local_m
    ):
        ativos.add(TipoAlerta.PARADA)
    if s.fora_da_rota_seguidas >= settings.alerta_desvio_leituras:
        ativos.add(TipoAlerta.DESVIO_ROTA)
    if s.inicio_trecho and s.eta_prevista and s.eta_atual:
        previsto = s.eta_prevista - s.inicio_trecho
        if s.eta_atual - s.inicio_trecho > previsto * (1 + settings.alerta_atraso_tolerancia):
            ativos.add(TipoAlerta.ATRASO)
    return ativos
