"""Áreas reais de eucalipto a partir do raster do MapBiomas (SPEC seção 3.1).

Funções puras: o raster chega já lido; quem baixa e grava são os scripts
exportar_mapbiomas e gerar_areas_eucalipto.
"""
from dataclasses import dataclass

import numpy as np
import shapely
from affine import Affine
from pyproj import Transformer
from rasterio.features import shapes
from shapely.geometry import Point, Polygon, mapping, shape
from shapely.ops import unary_union

from app.config import Settings

# SIRGAS 2000 / UTM 22S: medidas em metros na região de Três Lagoas.
SRID_METROS = 31982
_PARA_METROS = Transformer.from_crs(4326, SRID_METROS, always_xy=True)
_PARA_GRAUS = Transformer.from_crs(SRID_METROS, 4326, always_xy=True)


@dataclass
class AreaEucalipto:
    nome: str
    area_ha: float
    geom: Polygon  # EPSG:4326
    centro: Point  # EPSG:4326, sempre dentro da área


def _projetar(geom, transformador: Transformer):
    return shapely.transform(geom, lambda xy: np.column_stack(transformador.transform(xy[:, 0], xy[:, 1])))


def vetorizar(dados: np.ndarray, transform: Affine, classe: int) -> list[Polygon]:
    """Polígonos (EPSG:4326) dos pixels da classe pedida."""
    mascara = dados == classe
    return [
        shape(g)
        for g, valor in shapes(mascara.astype(np.uint8), mask=mascara, transform=transform)
        if valor == 1
    ]


def _partes(geom) -> list[Polygon]:
    if geom.is_empty:
        return []
    return list(geom.geoms) if hasattr(geom, "geoms") else [geom]


def areas_eucalipto(
    pedacos: list[Polygon],
    limite: Polygon,
    fabrica: tuple[float, float],
    settings: Settings,
) -> list[AreaEucalipto]:
    """Une vizinhos, corta pelo limite, filtra por área e distância e nomeia as maiores."""
    if not pedacos:
        return []
    fecho = settings.areas_fecho_m
    metros = [_projetar(p, _PARA_METROS) for p in pedacos]
    unidas = unary_union([p.buffer(fecho) for p in metros]).buffer(-fecho)
    limite_m = _projetar(limite, _PARA_METROS)
    fabrica_m = Point(_PARA_METROS.transform(*fabrica))

    candidatas: list[Polygon] = []
    for area in _partes(unidas):
        partes = [p for p in _partes(area.intersection(limite_m)) if p.geom_type == "Polygon"]
        if not partes:
            continue
        # A coluna é POLYGON: de uma área cortada pelo limite fica só a maior parte.
        maior = max(partes, key=lambda p: p.area).simplify(settings.areas_simplificar_m)
        if maior.area / 10_000 >= settings.areas_min_ha and maior.distance(fabrica_m) <= settings.areas_raio_km * 1000:
            candidatas.append(maior)

    candidatas.sort(key=lambda p: p.area, reverse=True)
    return [
        AreaEucalipto(
            nome=f"Área de eucalipto {i:02d}",
            area_ha=round(p.area / 10_000, 1),
            geom=_projetar(p, _PARA_GRAUS),
            # representative_point, não centroide: em área com buraco ou em U o centroide cai fora.
            centro=_projetar(p.representative_point(), _PARA_GRAUS),
        )
        for i, p in enumerate(candidatas[: settings.areas_maximo], start=1)
    ]


def para_geojson(areas: list[AreaEucalipto]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": mapping(a.geom),
                "properties": {"nome": a.nome, "area_ha": a.area_ha, "centro": [a.centro.x, a.centro.y]},
            }
            for a in areas
        ],
    }
