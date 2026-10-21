from fastapi import APIRouter, Depends
from geoalchemy2.shape import to_shape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_sessao
from app.estados import ESTADOS_CARREGADO
from app.modelos import Caminhao, Posicao

router = APIRouter()


def montar_caminhao_saida(sessao: Session, caminhao: Caminhao) -> dict:
    """Estado atual de um caminhão, no formato de GET /caminhoes e do WebSocket."""
    ultima = sessao.scalars(
        select(Posicao)
        .where(Posicao.caminhao_id == caminhao.id)
        .order_by(Posicao.momento.desc(), Posicao.id.desc())
        .limit(1)
    ).first()
    posicao = None
    if ultima is not None:
        ponto = to_shape(ultima.geom)
        posicao = {
            "lon": ponto.x,
            "lat": ponto.y,
            "velocidade_kmh": ultima.velocidade_kmh,
            "momento": ultima.momento.isoformat(),
        }
    carregado = caminhao.estado_atual in ESTADOS_CARREGADO
    return {
        "id": caminhao.id,
        "placa": caminhao.placa,
        "tipo": caminhao.tipo,
        "capacidade_t": caminhao.capacidade_t,
        "motorista": caminhao.motorista.nome,
        "estado_atual": caminhao.estado_atual,
        "viagem_atual_id": caminhao.viagem_atual_id,
        "fazenda_id": caminhao.viagem_atual.fazenda_id if caminhao.viagem_atual else None,
        "carga_t": caminhao.capacidade_t if carregado else 0,
        "posicao": posicao,
    }


@router.get("/caminhoes")
def caminhoes(sessao: Session = Depends(get_sessao)):
    return [
        montar_caminhao_saida(sessao, c)
        for c in sessao.scalars(select(Caminhao).order_by(Caminhao.id))
    ]
