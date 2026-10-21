"""Calcula e salva a rota de cada fazenda até a fábrica (SPEC seção 5).

Uso: python -m app.scripts.gerar_rotas

Respeita a política do servidor de demonstração do OSRM: User-Agent do
projeto, uma requisição por vez e 1 s entre requisições. Se uma rota não
puder ser calculada, usa linha reta com fator de distância e avisa.
"""
import time
from collections.abc import Callable

import httpx
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import LineString
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.geo import linha_reta
from app.modelos import Fabrica, Fazenda, Rota
from app.osrm import buscar_rota

PAUSA_ENTRE_REQUISICOES_S = 1.0


def gerar_rotas(
    sessao: Session,
    settings: Settings,
    cliente: httpx.Client,
    dormir: Callable[[float], None] = time.sleep,
) -> list[str]:
    fabrica = to_shape(sessao.scalars(select(Fabrica.geom)).one())
    destino = (fabrica.x, fabrica.y)
    avisos: list[str] = []

    fazendas = sessao.scalars(select(Fazenda).order_by(Fazenda.id)).all()
    for i, fazenda in enumerate(fazendas):
        if i > 0:
            dormir(PAUSA_ENTRE_REQUISICOES_S)
        centro = to_shape(fazenda.centro)
        origem = (centro.x, centro.y)
        try:
            rota = buscar_rota(cliente, settings, origem, destino)
        except (httpx.HTTPError, ValueError, KeyError) as erro:
            rota = linha_reta(origem, destino, settings.fator_linha_reta, settings.velocidade_carregado_kmh)
            avisos.append(f"Rota de {fazenda.nome} em linha reta: {erro}")

        sessao.execute(delete(Rota).where(Rota.fazenda_id == fazenda.id))
        sessao.add(
            Rota(
                fazenda_id=fazenda.id,
                geom=from_shape(LineString(rota.coords), srid=4326),
                distancia_km=rota.distancia_km,
                duracao_prevista_min=rota.duracao_min,
            )
        )
        sessao.flush()
    return avisos


if __name__ == "__main__":
    from app.db import SessionLocal

    configuracao = get_settings()
    with SessionLocal() as s, httpx.Client(timeout=20) as http:
        for aviso in gerar_rotas(s, configuracao, http):
            print(f"Aviso: {aviso}")
        s.commit()
    print("Rotas salvas.")
