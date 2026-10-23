"""Focos de calor e risco de incêndio, lidos do banco (as rotinas é que buscam nas fontes).

Clima e focos são reais: "hoje" e as janelas usam o relógio de verdade, não o simulado.
"""
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_sessao
from app.modelos import ClimaDiario, Fazenda, FocoCalor, RiscoDiario

router = APIRouter()


def hoje_real(settings: Settings) -> date:
    return datetime.now(ZoneInfo(settings.fuso)).date()


@router.get("/focos")
def focos(horas: int = Query(24, ge=1, le=72), sessao: Session = Depends(get_sessao)):
    desde = datetime.now(UTC) - timedelta(hours=horas)
    consulta = select(FocoCalor).where(FocoCalor.detectado_em >= desde).order_by(FocoCalor.detectado_em)
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": mapping(to_shape(f.geom)),
                "properties": {
                    "id": f.id,
                    "detectado_em": f.detectado_em.isoformat(),
                    "satelite": f.satelite,
                    "municipio": f.municipio,
                },
            }
            for f in sessao.scalars(consulta)
        ],
    }


@router.get("/risco/fazendas")
def risco_fazendas(
    data: date | None = None,
    sessao: Session = Depends(get_sessao),
    settings: Settings = Depends(get_settings),
):
    dia = data or hoje_real(settings)
    riscos = {
        r.fazenda_id: r for r in sessao.scalars(select(RiscoDiario).where(RiscoDiario.data == dia))
    }
    saida = []
    for fazenda in sessao.scalars(select(Fazenda).order_by(Fazenda.id)):
        r = riscos.get(fazenda.id)
        saida.append({
            "fazenda_id": fazenda.id, "nome": fazenda.nome, "data": dia.isoformat(),
            "fma": r.fma if r else None, "classe": r.classe if r else None,
        })
    return saida


@router.get("/risco/historico")
def risco_historico(
    dias: int = Query(30, ge=1, le=90),
    sessao: Session = Depends(get_sessao),
    settings: Settings = Depends(get_settings),
):
    hoje = hoje_real(settings)
    datas = [hoje - timedelta(days=d) for d in range(dias - 1, -1, -1)]
    riscos = {
        (r.fazenda_id, r.data): r
        for r in sessao.scalars(select(RiscoDiario).where(RiscoDiario.data.between(datas[0], hoje)))
    }
    climas = {
        (c.fazenda_id, c.data): c
        for c in sessao.scalars(select(ClimaDiario).where(ClimaDiario.data.between(datas[0], hoje)))
    }

    def celula(fazenda_id: int, dia: date) -> dict | None:
        r = riscos.get((fazenda_id, dia))
        if r is None:
            return None
        c = climas.get((fazenda_id, dia))
        return {
            "data": dia.isoformat(), "fma": r.fma, "classe": r.classe,
            "chuva_mm": c.chuva_mm if c else None, "ur_13h": c.ur_13h if c else None,
        }

    return {
        "datas": [d.isoformat() for d in datas],
        "fazendas": [
            {"fazenda_id": f.id, "nome": f.nome, "dias": [celula(f.id, d) for d in datas]}
            for f in sessao.scalars(select(Fazenda).order_by(Fazenda.id))
        ],
    }


def risco_atual(sessao: Session, settings: Settings) -> dict[int, RiscoDiario]:
    """Risco de hoje de cada fazenda, ou do último dia calculado até hoje."""
    ultimo = (
        select(RiscoDiario.fazenda_id, func.max(RiscoDiario.data).label("data"))
        .where(RiscoDiario.data <= hoje_real(settings))
        .group_by(RiscoDiario.fazenda_id)
        .subquery()
    )
    consulta = select(RiscoDiario).join(
        ultimo, (RiscoDiario.fazenda_id == ultimo.c.fazenda_id) & (RiscoDiario.data == ultimo.c.data)
    )
    return {r.fazenda_id: r for r in sessao.scalars(consulta)}
