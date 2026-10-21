"""Funções geométricas simples. Coordenadas sempre em (lon, lat)."""
import math
from dataclasses import dataclass

RAIO_TERRA_KM = 6371.0088
METROS_POR_GRAU_LAT = 111_320


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
