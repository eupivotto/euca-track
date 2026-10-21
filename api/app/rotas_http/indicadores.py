from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_sessao
from app.estados import Estado
from app.modelos import EventoViagem, Posicao, Viagem

router = APIRouter()


@router.get("/indicadores")
def indicadores(
    inicio: datetime | None = None,
    fim: datetime | None = None,
    sessao: Session = Depends(get_sessao),
    settings: Settings = Depends(get_settings),
):
    fuso = ZoneInfo(settings.fuso)
    # "Agora" é o relógio simulado: a leitura mais recente recebida.
    agora = sessao.scalar(select(func.max(Posicao.momento))) or datetime.now(timezone.utc)
    agora = agora.astimezone(fuso)
    if inicio is None:
        inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
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
