"""Clima diário do Open-Meteo por fazenda e recálculo da FMA (SPEC seção 7).

Só roda nas rotinas agendadas, nunca dentro de um request.
"""
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

import httpx
from geoalchemy2.shape import to_shape
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.fma import DiaClima, serie_fma
from app.modelos import ClimaDiario, Fazenda, RiscoDiario

VARIAVEIS = "relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m"
PAUSA_S = 1.0


@dataclass
class ClimaDia:
    data: date
    ur_13h: float | None
    chuva_mm: float | None
    vento_kmh: float | None
    vento_dir: float | None


def ler_open_meteo(dados: dict) -> list[ClimaDia]:
    """Um dia por data: UR e vento da hora 13:00 local, chuva somada no dia."""
    horas = dados["hourly"]
    dias: dict[str, dict] = {}
    for i, momento in enumerate(horas["time"]):
        dia = dias.setdefault(momento[:10], {"chuvas": [], "13h": None})
        dia["chuvas"].append(horas["precipitation"][i])
        if momento.endswith("T13:00"):
            dia["13h"] = i
    saida = []
    for texto, dia in sorted(dias.items()):
        chuvas = [c for c in dia["chuvas"] if c is not None]
        i = dia["13h"]

        def as_13h(variavel: str) -> float | None:
            return None if i is None else horas[variavel][i]

        saida.append(ClimaDia(
            data=date.fromisoformat(texto),
            ur_13h=as_13h("relative_humidity_2m"),
            chuva_mm=sum(chuvas) if chuvas else None,
            vento_kmh=as_13h("wind_speed_10m"),
            vento_dir=as_13h("wind_direction_10m"),
        ))
    return saida


def buscar_clima(
    cliente: httpx.Client, settings: Settings, lon: float, lat: float,
    inicio: date, fim: date, historico: bool,
) -> list[ClimaDia]:
    """Histórico de `inicio` a `fim`, ou a previsão com os dias que faltam até hoje."""
    params: dict = {
        "latitude": round(lat, 4), "longitude": round(lon, 4),
        "hourly": VARIAVEIS, "timezone": settings.fuso,
    }
    if historico:
        url = settings.open_meteo_historico_url
        params |= {"start_date": inicio.isoformat(), "end_date": fim.isoformat()}
    else:
        url = settings.open_meteo_url
        params |= {"past_days": (fim - inicio).days, "forecast_days": 1}
    resposta = cliente.get(url, params=params, headers={"User-Agent": settings.user_agent}, timeout=30)
    resposta.raise_for_status()
    return ler_open_meteo(resposta.json())


def _gravar_clima(sessao: Session, fazenda_id: int, dias: list[ClimaDia]) -> None:
    for d in dias:
        valores = {"ur_13h": d.ur_13h, "chuva_mm": d.chuva_mm, "vento_kmh": d.vento_kmh, "vento_dir": d.vento_dir}
        sessao.execute(
            insert(ClimaDiario)
            .values(fazenda_id=fazenda_id, data=d.data, **valores)
            .on_conflict_do_update(constraint="uq_clima_diario_fazenda_data", set_=valores)
        )


def recalcular_risco(sessao: Session, settings: Settings, fazenda_id: int) -> None:
    """Refaz a série inteira: um dia corrigido pela previsão muda os seguintes."""
    clima = sessao.scalars(select(ClimaDiario).where(ClimaDiario.fazenda_id == fazenda_id)).all()
    serie = serie_fma([DiaClima(c.data, c.ur_13h, c.chuva_mm) for c in clima], settings)
    sessao.execute(delete(RiscoDiario).where(RiscoDiario.fazenda_id == fazenda_id))
    sessao.add_all(
        RiscoDiario(fazenda_id=fazenda_id, data=d, fma=fma, classe=str(classe)) for d, fma, classe in serie
    )
    sessao.flush()


def importar_clima(
    sessao: Session, settings: Settings, cliente: httpx.Client, hoje: date,
    dormir: Callable[[float], None] = time.sleep,
) -> list[str]:
    """Busca o clima de cada fazenda e recalcula o risco. Devolve avisos.

    Sem nenhuma linha ainda, faz o backfill pelo histórico (e preenche pelo
    histórico a lacuna de quando o painel ficou desligado); sempre pede a
    previsão com os últimos 3 dias, que substitui o que o histórico trouxe.
    """
    avisos: list[str] = []
    requisicoes = 0

    def pausar() -> None:
        nonlocal requisicoes
        if requisicoes:
            dormir(PAUSA_S)
        requisicoes += 1

    for fazenda in sessao.scalars(select(Fazenda).order_by(Fazenda.id)).all():
        centro = to_shape(fazenda.centro)
        ultima = sessao.scalar(
            select(func.max(ClimaDiario.data)).where(ClimaDiario.fazenda_id == fazenda.id)
        )
        # Sem nada, os últimos 60 dias; depois de dias parado, só a lacuna que a previsão não cobre.
        inicio_historico = (
            hoje - timedelta(days=settings.clima_backfill_dias) if ultima is None else ultima + timedelta(days=1)
        )
        try:
            dias: list[ClimaDia] = []
            if inicio_historico < hoje - timedelta(days=3):
                pausar()
                dias += buscar_clima(
                    cliente, settings, centro.x, centro.y, inicio_historico, hoje - timedelta(days=1),
                    historico=True,
                )
            pausar()
            dias += buscar_clima(cliente, settings, centro.x, centro.y, hoje - timedelta(days=3), hoje,
                                 historico=False)
        except (httpx.HTTPError, ValueError, KeyError) as erro:
            avisos.append(f"{fazenda.nome}: clima não atualizado ({erro})")
            continue
        _gravar_clima(sessao, fazenda.id, dias)
        recalcular_risco(sessao, settings, fazenda.id)
    return avisos
