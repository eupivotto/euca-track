from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_sessao
from app.modelos import Caminhao, Posicao, Rota, Viagem

router = APIRouter()


def _resumo(sessao: Session, viagem: Viagem) -> dict:
    return {
        "id": viagem.id,
        "caminhao_id": viagem.caminhao_id,
        "placa": sessao.get(Caminhao, viagem.caminhao_id).placa,
        "fazenda": viagem.fazenda.nome,
        "toneladas": viagem.toneladas,
        "inicio": viagem.inicio.isoformat(),
        "fim": viagem.fim.isoformat() if viagem.fim else None,
        "status": viagem.status,
    }


@router.get("/viagens")
def viagens(
    caminhao_id: int | None = None,
    limite: int = Query(20, ge=1, le=100),
    sessao: Session = Depends(get_sessao),
):
    consulta = select(Viagem).order_by(Viagem.inicio.desc(), Viagem.id.desc()).limit(limite)
    if caminhao_id is not None:
        consulta = consulta.where(Viagem.caminhao_id == caminhao_id)
    return [_resumo(sessao, v) for v in sessao.scalars(consulta)]


@router.get("/viagens/{viagem_id}")
def viagem(viagem_id: int, sessao: Session = Depends(get_sessao)):
    """Trajeto, rota prevista e eventos de uma viagem, para o replay."""
    v = sessao.get(Viagem, viagem_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Viagem não encontrada")
    rota = sessao.get(Rota, v.rota_id) if v.rota_id else None
    pontos = sessao.scalars(
        select(Posicao)
        .where(Posicao.viagem_id == v.id)
        .order_by(Posicao.momento, Posicao.id)
    )
    return {
        **_resumo(sessao, v),
        "rota": mapping(to_shape(rota.geom)) if rota else None,
        "pontos": [
            {
                "lon": (ponto := to_shape(p.geom)).x,
                "lat": ponto.y,
                "velocidade_kmh": p.velocidade_kmh,
                "momento": p.momento.isoformat(),
            }
            for p in pontos
        ],
        "eventos": [{"estado": e.estado, "momento": e.momento.isoformat()} for e in v.eventos],
    }
