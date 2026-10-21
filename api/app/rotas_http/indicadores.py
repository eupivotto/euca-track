from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_sessao
from app.estados import Estado
from app.modelos import Caminhao, EventoViagem, Viagem
from app.operacao import agora_simulado, espera_media_fila_min, inicio_do_dia

router = APIRouter()

HORA, DIA = timedelta(hours=1), timedelta(days=1)


def _ciclo_medio_min(sessao: Session, inicio: datetime, fim: datetime) -> float | None:
    """Duração média das viagens concluídas no período. Interrompidas não contam."""
    segundos = sessao.scalar(
        select(func.avg(func.extract("epoch", Viagem.fim - Viagem.inicio))).where(
            Viagem.status == "CONCLUIDA", Viagem.fim >= inicio, Viagem.fim < fim
        )
    )
    return None if segundos is None else float(segundos) / 60


def _serie(entregas: list[tuple[datetime, float]], inicio: datetime, fim: datetime) -> list[dict]:
    """Toneladas por hora (período de até 1 dia) ou por dia, cobrindo o período inteiro."""
    passo = HORA if fim - inicio <= DIA else DIA
    baldes = [0.0] * -(-(fim - inicio) // passo)  # arredonda para cima
    for momento, toneladas in entregas:
        baldes[int((momento - inicio) // passo)] += toneladas
    return [
        {"inicio": (inicio + i * passo).isoformat(), "toneladas": t} for i, t in enumerate(baldes)
    ]


@router.get("/indicadores")
def indicadores(
    inicio: AwareDatetime | None = None,
    fim: AwareDatetime | None = None,
    dias: int = Query(1, ge=1, le=30),
    sessao: Session = Depends(get_sessao),
    settings: Settings = Depends(get_settings),
):
    fuso = ZoneInfo(settings.fuso)
    agora = agora_simulado(sessao, fuso)
    if inicio is None:
        # Sem período: os últimos `dias` dias, terminando no fim de hoje (no fuso da operação).
        inicio = inicio_do_dia(agora) - (dias - 1) * DIA
        fim = fim or inicio_do_dia(agora) + DIA
    if fim is None:
        fim = inicio + DIA
    if fim <= inicio:
        raise HTTPException(status_code=422, detail="O fim do período precisa ser depois do início")

    # Entregue = viagem que saiu vazia da fábrica dentro do período.
    entregas = sessao.execute(
        select(EventoViagem.momento, Viagem.toneladas)
        .join(Viagem, EventoViagem.viagem_id == Viagem.id)
        .where(
            EventoViagem.estado == Estado.EM_TRANSITO_VAZIO,
            EventoViagem.momento >= inicio,
            EventoViagem.momento < fim,
        )
    ).all()

    estados = [e for e in sessao.scalars(select(Caminhao.estado_atual)) if e is not None]
    por_estado = {e.value: estados.count(e) for e in Estado}
    # Esperar na fila não é uso da frota.
    em_uso = len(estados) - por_estado[Estado.FILA_PATIO]

    periodo_dias = (fim - inicio) / DIA
    return {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "agora": agora.isoformat(),
        "dias": periodo_dias,
        "toneladas": float(sum(t for _, t in entregas)),
        "viagens": len(entregas),
        "meta_t": settings.meta_diaria_t * periodo_dias,
        "ciclo_medio_min": _ciclo_medio_min(sessao, inicio, fim),
        "fila_media_min": espera_media_fila_min(sessao, inicio, fim),
        "uso_frota": em_uso / len(estados) if estados else 0,
        "frota_por_estado": por_estado,
        "serie": _serie([(m.astimezone(fuso), t) for m, t in entregas], inicio, fim),
    }
