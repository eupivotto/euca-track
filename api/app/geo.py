"""Funções geométricas simples. Coordenadas sempre em (lon, lat)."""
import math
from dataclasses import dataclass

import shapely
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry

RAIO_TERRA_KM = 6371.0088
METROS_POR_GRAU_LAT = 111_320
# Projeção local para medir em metros: equiretangular em torno de uma latitude.
METROS_POR_GRAU_LAT_LOCAL = 110_574


def quadrado_fazenda(lat: float, lon: float, area_ha: float) -> list[tuple[float, float]]:
    """Anel fechado de um quadrado com a área informada, centrado no ponto."""
    lado_m = math.sqrt(area_ha * 10_000)
    dlat = lado_m / 2 / METROS_POR_GRAU_LAT
    dlon = lado_m / 2 / (METROS_POR_GRAU_LAT * math.cos(math.radians(lat)))
    return [
        (lon - dlon, lat - dlat),
        (lon + dlon, lat - dlat),
        (lon + dlon, lat + dlat),
        (lon - dlon, lat + dlat),
        (lon - dlon, lat - dlat),
    ]


def distancia_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distância de haversine entre dois pontos (lon, lat)."""
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * RAIO_TERRA_KM * math.asin(math.sqrt(h))


@dataclass
class RotaCalculada:
    coords: list[tuple[float, float]]
    distancia_km: float
    duracao_min: float


def linha_reta(
    origem: tuple[float, float], destino: tuple[float, float], fator: float, velocidade_kmh: float
) -> RotaCalculada:
    """Rota de reserva quando o OSRM não responde: linha reta com fator de distância."""
    distancia = distancia_km(origem, destino) * fator
    return RotaCalculada([origem, destino], distancia, distancia / velocidade_kmh * 60)


def em_metros(geom: BaseGeometry, lat_ref: float) -> BaseGeometry:
    """Geometria em metros, por projeção equiretangular em torno de lat_ref.

    O erro fica abaixo de 1% nas distâncias de poucos km que os alertas medem.
    """
    escala_x = METROS_POR_GRAU_LAT * math.cos(math.radians(lat_ref))
    return shapely.transform(geom, lambda xy: xy * (escala_x, METROS_POR_GRAU_LAT_LOCAL))


def progresso_na_linha(linha: LineString, ponto: Point) -> tuple[float, float]:
    """(fração de 0 a 1 ao longo da linha, distância em metros do ponto à linha)."""
    linha_m, ponto_m = em_metros(linha, ponto.y), em_metros(ponto, ponto.y)
    if linha_m.length == 0:
        return 0.0, linha_m.distance(ponto_m)
    return linha_m.project(ponto_m, normalized=True), linha_m.distance(ponto_m)


def distancia_m(geom: BaseGeometry, ponto: Point) -> float:
    """Distância em metros do ponto à geometria; 0 dentro de um polígono."""
    return em_metros(geom, ponto.y).distance(em_metros(ponto, ponto.y))
