"""Cálculos da operação lidos do banco: relógio simulado, espera no pátio e ciclo."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.estados import Estado
from app.modelos import EventoViagem, Posicao


def agora_simulado(sessao: Session, fuso: ZoneInfo) -> datetime:
    """"Agora" é o relógio simulado: a leitura mais recente recebida."""
    agora = sessao.scalar(select(func.max(Posicao.momento))) or datetime.now(timezone.utc)
    return agora.astimezone(fuso)


def inicio_do_dia(momento: datetime) -> datetime:
    return momento.replace(hour=0, minute=0, second=0, microsecond=0)


def espera_media_fila_min(sessao: Session, inicio: datetime, fim: datetime) -> float | None:
    """Média de (entrada na pesagem − entrada na fila), para pesagens em [inicio, fim)."""
    fila, pesagem = aliased(EventoViagem), aliased(EventoViagem)
    segundos = sessao.scalar(
        select(func.avg(func.extract("epoch", pesagem.momento - fila.momento)))
        .join(fila, fila.viagem_id == pesagem.viagem_id)
        .where(
            fila.estado == Estado.FILA_PATIO,
            pesagem.estado == Estado.PESAGEM,
            pesagem.momento >= inicio,
            pesagem.momento < fim,
        )
    )
    return None if segundos is None else float(segundos) / 60
