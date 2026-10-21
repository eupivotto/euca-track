from fastapi import APIRouter, Depends
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_sessao
from app.modelos import Fabrica, Fazenda, Rota

router = APIRouter()


def _feature(geom, propriedades: dict) -> dict:
    return {"type": "Feature", "geometry": mapping(to_shape(geom)), "properties": propriedades}


@router.get("/fazendas")
def fazendas(sessao: Session = Depends(get_sessao)):
    features = [
        _feature(f.geom, {"id": f.id, "tipo": "fazenda", "nome": f.nome, "area_ha": f.area_ha})
        for f in sessao.scalars(select(Fazenda).order_by(Fazenda.id))
    ]
    features += [
        _feature(f.geom, {"id": f.id, "tipo": "fabrica", "nome": f.nome})
        for f in sessao.scalars(select(Fabrica).order_by(Fabrica.id))
    ]
    return {"type": "FeatureCollection", "features": features}


@router.get("/rotas")
def rotas(sessao: Session = Depends(get_sessao)):
    features = [
        _feature(
            r.geom,
            {
                "id": r.id,
                "fazenda_id": r.fazenda_id,
                "distancia_km": r.distancia_km,
                "duracao_prevista_min": r.duracao_prevista_min,
            },
        )
        for r in sessao.scalars(select(Rota).order_by(Rota.fazenda_id))
    ]
    return {"type": "FeatureCollection", "features": features}
