from datetime import timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_sessao
from app.estados import Estado
from app.modelos import Caminhao, EventoViagem
from app.operacao import agora_simulado, espera_media_fila_min, inicio_do_dia

router = APIRouter()

JANELA_CHEGADAS = timedelta(hours=2)


def _minutos(delta: timedelta) -> float:
    return round(delta.total_seconds() / 60, 1)


@router.get("/patio/fila")
def fila(sessao: Session = Depends(get_sessao), settings: Settings = Depends(get_settings)):
    agora = agora_simulado(sessao, ZoneInfo(settings.fuso))
    caminhoes = sessao.scalars(select(Caminhao).order_by(Caminhao.id)).all()

    na_fila = []
    for c in caminhoes:
        if c.estado_atual != Estado.FILA_PATIO:
            continue
        chegou = sessao.scalar(
            select(func.max(EventoViagem.momento)).where(
                EventoViagem.viagem_id == c.viagem_atual_id,
                EventoViagem.estado == Estado.FILA_PATIO,
            )
        ) or agora
        na_fila.append((chegou, c))
    na_fila.sort(key=lambda par: (par[0], par[1].id))

    chegadas = sorted(
        (
            c
            for c in caminhoes
            if c.estado_atual == Estado.EM_TRANSITO_CARREGADO
            and c.eta_atual is not None
            and agora <= c.eta_atual <= agora + JANELA_CHEGADAS
        ),
        key=lambda c: c.eta_atual,
    )

    return {
        "agora": agora.isoformat(),
        "vagas_total": settings.vagas_descarga,
        "vagas_ocupadas": sum(c.estado_atual in (Estado.PESAGEM, Estado.DESCARGA) for c in caminhoes),
        "fila": [
            {
                "caminhao_id": c.id,
                "placa": c.placa,
                "posicao": i,
                "chegou_em": chegou.isoformat(),
                "esperando_min": _minutos(agora - chegou),
            }
            for i, (chegou, c) in enumerate(na_fila, start=1)
        ],
        "espera_media_min": espera_media_fila_min(sessao, inicio_do_dia(agora), agora + timedelta(seconds=1)),
        "chegadas": [
            {
                "caminhao_id": c.id,
                "placa": c.placa,
                "fazenda": c.viagem_atual.fazenda.nome if c.viagem_atual else None,
                "eta": c.eta_atual.isoformat(),
            }
            for c in chegadas
        ],
    }
