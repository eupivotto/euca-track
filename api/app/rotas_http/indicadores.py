from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_sessao
from app.estados import Estado
from app.modelos import EventoViagem, Viagem
from app.operacao import agora_simulado, inicio_do_dia

router = APIRouter()


@router.get("/indicadores")
def indicadores(
    inicio: datetime | None = None,
    fim: datetime | None = None,
    sessao: Session = Depends(get_sessao),
    settings: Settings = Depends(get_settings),
):
    agora = agora_simulado(sessao, ZoneInfo(settings.fuso))
    if inicio is None:
        inicio = inicio_do_dia(agora)
    if fim is None:
        fim = inicio + timedelta(days=1)

    # Entregue = viagem que saiu vazia da fábrica dentro do período.
    toneladas, viagens = sessao.execute(
        select(func.coalesce(func.sum(Viagem.toneladas), 0), func.count(Viagem.id))
        .join(EventoViagem, EventoViagem.viagem_id == Viagem.id)
        .where(
            EventoViagem.estado == Estado.EM_TRANSITO_VAZIO,
            EventoViagem.momento >= inicio,
            EventoViagem.momento < fim,
        )
    ).one()

    dias = (fim - inicio) / timedelta(days=1)
    return {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "agora": agora.isoformat(),
        "toneladas": float(toneladas),
        "viagens": viagens,
        "meta_t": settings.meta_diaria_t * dias,
    }
