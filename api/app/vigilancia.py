"""Alertas no banco: monta a situação do caminhão, abre e fecha alertas."""
from datetime import datetime
from zoneinfo import ZoneInfo

from geoalchemy2.shape import to_shape
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.alertas import EM_TRANSITO, Situacao, TipoAlerta
from app.config import Settings
from app.geo import distancia_m, progresso_na_linha
from app.modelos import Alerta, Caminhao, Fabrica, Fazenda, Posicao


def locais(sessao: Session) -> list[BaseGeometry]:
    """Onde parar é normal: polígonos das fazendas e a fábrica (com o pátio)."""
    return [to_shape(g) for g in sessao.scalars(select(Fazenda.geom))] + [
        to_shape(g) for g in sessao.scalars(select(Fabrica.geom))
    ]


def _parado_desde(
    sessao: Session, caminhao_id: int, limite_kmh: float, inicio_trecho: datetime
) -> datetime | None:
    """Primeira leitura da sequência atual abaixo do limite, dentro do trecho.

    O tempo parado carregando ou no pátio, antes de o trecho começar, não conta.
    """
    ultima_andando = sessao.scalar(
        select(func.max(Posicao.momento)).where(
            Posicao.caminhao_id == caminhao_id,
            Posicao.velocidade_kmh >= limite_kmh,
            Posicao.momento >= inicio_trecho,
        )
    )
    consulta = select(func.min(Posicao.momento)).where(
        Posicao.caminhao_id == caminhao_id, Posicao.momento >= inicio_trecho
    )
    if ultima_andando is not None:
        consulta = consulta.where(Posicao.momento > ultima_andando)
    return sessao.scalar(consulta)


def montar_situacao(
    sessao: Session,
    caminhao: Caminhao,
    leitura,
    rota: LineString | None,
    locais_parada: list[BaseGeometry],
    settings: Settings,
) -> Situacao:
    """Situação na leitura atual. Chamar depois de gravar a posição e atualizar o trecho."""
    ponto = Point(leitura.lon, leitura.lat)
    parado_desde = None
    if (
        leitura.velocidade_kmh < settings.alerta_parada_velocidade_kmh
        and caminhao.inicio_trecho is not None
    ):
        parado_desde = _parado_desde(
            sessao, caminhao.id, settings.alerta_parada_velocidade_kmh, caminhao.inicio_trecho
        )

    fora_seguidas, distancia_rota = 0, None
    if rota is not None and leitura.estado in EM_TRANSITO and caminhao.inicio_trecho is not None:
        _, distancia_rota = progresso_na_linha(rota, ponto)
        recentes = sessao.scalars(
            select(Posicao.geom)
            .where(Posicao.caminhao_id == caminhao.id, Posicao.momento >= caminhao.inicio_trecho)
            .order_by(Posicao.momento.desc(), Posicao.id.desc())
            .limit(settings.alerta_desvio_leituras)
        ).all()
        for geom in recentes:
            if progresso_na_linha(rota, to_shape(geom))[1] <= settings.alerta_desvio_m:
                break
            fora_seguidas += 1

    return Situacao(
        estado=leitura.estado,
        velocidade_kmh=leitura.velocidade_kmh,
        momento=leitura.momento,
        parado_desde=parado_desde,
        distancia_local_m=min((distancia_m(l, ponto) for l in locais_parada), default=float("inf")),
        fora_da_rota_seguidas=fora_seguidas,
        inicio_trecho=caminhao.inicio_trecho,
        eta_prevista=caminhao.eta_prevista,
        eta_atual=caminhao.eta_atual,
        distancia_rota_m=distancia_rota,
    )


def _hora(momento: datetime, fuso: str) -> str:
    return momento.astimezone(ZoneInfo(fuso)).strftime("%Hh%M")


def mensagem(tipo: TipoAlerta, s: Situacao, settings: Settings) -> str:
    if tipo == TipoAlerta.VELOCIDADE:
        # Uma casa decimal: 80,3 arredondado para "80 km/h" pareceria dentro do limite.
        return f"{s.velocidade_kmh:.1f}".replace(".", ",").removesuffix(",0") + " km/h"
    if tipo == TipoAlerta.PARADA:
        minutos = round((s.momento - s.parado_desde).total_seconds() / 60)
        return f"Parado há {minutos} min fora de fazenda ou fábrica"
    if tipo == TipoAlerta.DESVIO_ROTA:
        return f"A {round(s.distancia_rota_m or 0)} m da rota"
    atraso = round((s.eta_atual - s.eta_prevista).total_seconds() / 60)
    return f"Chegada prevista às {_hora(s.eta_atual, settings.fuso)}, {atraso} min depois do previsto"


def atualizar_alertas(
    sessao: Session,
    caminhao: Caminhao,
    ativos: set[TipoAlerta],
    situacao: Situacao,
    settings: Settings,
) -> list[Alerta]:
    """Abre os ativos que não estão abertos e fecha os abertos que deixaram de valer."""
    abertos = {
        a.tipo: a
        for a in sessao.scalars(
            select(Alerta).where(Alerta.caminhao_id == caminhao.id, Alerta.status == "ABERTO")
        )
    }
    mudaram: list[Alerta] = []
    for tipo in sorted(ativos - abertos.keys()):
        alerta = Alerta(
            tipo=tipo,
            caminhao_id=caminhao.id,
            mensagem=mensagem(tipo, situacao, settings),
            aberto_em=situacao.momento,
            status="ABERTO",
        )
        sessao.add(alerta)
        mudaram.append(alerta)
    for tipo in sorted(abertos.keys() - ativos):
        alerta = abertos[tipo]
        alerta.status = "FECHADO"
        alerta.fechado_em = situacao.momento
        mudaram.append(alerta)
    sessao.flush()
    return mudaram


def alerta_saida(alerta: Alerta) -> dict:
    """Formato de GET /alertas e da mensagem "alerta" do WebSocket."""
    return {
        "id": alerta.id,
        "tipo": alerta.tipo,
        "caminhao_id": alerta.caminhao_id,
        "placa": alerta.caminhao.placa if alerta.caminhao else None,
        "fazenda_id": alerta.fazenda_id,
        "fazenda": alerta.fazenda.nome if alerta.fazenda else None,
        "mensagem": alerta.mensagem,
        "aberto_em": alerta.aberto_em.isoformat(),
        "fechado_em": alerta.fechado_em.isoformat() if alerta.fechado_em else None,
        "status": alerta.status,
    }
