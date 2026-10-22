"""Gera o GeoJSON das 8 áreas de eucalipto a partir do recorte do MapBiomas (SPEC 3.1).

Uso: python -m app.scripts.gerar_areas_eucalipto [raster]

Lê o recorte gravado por exportar_mapbiomas, corta pelo limite de MS (malha
do IBGE em app/dados/limite_ms.geojson), confere a distância por estrada até a
fábrica no OSRM (1 s entre requisições) e grava app/dados/areas_eucalipto.geojson,
que vai para o git e é lido pelo seed.
"""
import json
import time
from pathlib import Path

import httpx
import rasterio
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from app.areas import (
    ARQUIVO_AREAS,
    ARQUIVO_LIMITE,
    AreaEucalipto,
    areas_eucalipto,
    para_geojson,
    selecionar_por_estrada,
    vetorizar,
)
from app.config import get_settings
from app.geo import distancia_km
from app.osrm import buscar_rota
from app.scripts.gerar_rotas import PAUSA_ENTRE_REQUISICOES_S
from app.scripts.exportar_mapbiomas import SAIDA_PADRAO
from app.seed import FABRICA


def carregar_limite(caminho: Path = ARQUIVO_LIMITE) -> BaseGeometry:
    return shape(json.loads(caminho.read_text(encoding="utf-8"))["features"][0]["geometry"])


if __name__ == "__main__":
    import sys

    raster = Path(sys.argv[1]) if len(sys.argv) > 1 else SAIDA_PADRAO
    configuracao = get_settings()
    _, lat, lon = FABRICA
    with rasterio.open(raster) as src:
        pedacos = vetorizar(src.read(1), src.transform, configuracao.mapbiomas_classe)
    print(f"{len(pedacos)} pedaços da classe {configuracao.mapbiomas_classe}")
    # Candidatas pela linha reta; o raio vale por estrada quando o OSRM tem rota (SPEC 3.1).
    candidatas = areas_eucalipto(
        pedacos, carregar_limite(), (lon, lat), configuracao.model_copy(update={"areas_maximo": 50})
    )

    with httpx.Client(timeout=20) as http:

        def por_estrada(area: AreaEucalipto) -> float | None:
            time.sleep(PAUSA_ENTRE_REQUISICOES_S)
            try:
                km = buscar_rota(http, configuracao, (area.centro.x, area.centro.y), (lon, lat)).distancia_km
            except (httpx.HTTPError, ValueError, KeyError) as erro:
                print(f"Sem rota para a candidata de {area.area_ha:,.0f} ha ({erro}); vale a linha reta")
                return None
            if km > configuracao.areas_raio_km:
                print(f"Candidata de {area.area_ha:,.0f} ha fica a {km:.0f} km por estrada: fora")
            return km

        areas = selecionar_por_estrada(candidatas, por_estrada, configuracao)
    ARQUIVO_AREAS.write_text(json.dumps(para_geojson(areas), ensure_ascii=False), encoding="utf-8")
    for a in areas:
        km = distancia_km((a.centro.x, a.centro.y), (lon, lat))
        print(f"{a.nome}: {a.area_ha:,.0f} ha, centro a {km:.0f} km da fábrica em linha reta")
    print(f"Gravado {ARQUIVO_AREAS}")
