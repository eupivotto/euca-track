"""Gera o GeoJSON das 8 áreas de eucalipto a partir do recorte do MapBiomas (SPEC 3.1).

Uso: python -m app.scripts.gerar_areas_eucalipto [raster]

Lê o recorte gravado por exportar_mapbiomas, corta pelo limite de MS (malha
do IBGE em app/dados/limite_ms.geojson) e grava app/dados/areas_eucalipto.geojson,
que vai para o git e é lido pelo seed.
"""
import json
from pathlib import Path

import rasterio
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from app.areas import ARQUIVO_AREAS, ARQUIVO_LIMITE, areas_eucalipto, para_geojson, vetorizar
from app.config import get_settings
from app.geo import distancia_km
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
    areas = areas_eucalipto(pedacos, carregar_limite(), (lon, lat), configuracao)
    ARQUIVO_AREAS.write_text(json.dumps(para_geojson(areas), ensure_ascii=False), encoding="utf-8")
    for a in areas:
        km = distancia_km((a.centro.x, a.centro.y), (lon, lat))
        print(f"{a.nome}: {a.area_ha:,.0f} ha, centro a {km:.0f} km da fábrica")
    print(f"Gravado {ARQUIVO_AREAS}")
