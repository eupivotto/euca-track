"""Posição ao longo de uma linha. Coordenadas sempre em (lon, lat)."""
import math

RAIO_TERRA_KM = 6371.0088

Ponto = tuple[float, float]


def _distancia_km(a: Ponto, b: Ponto) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * RAIO_TERRA_KM * math.asin(math.sqrt(h))


def comprimento_km(coords: list[Ponto]) -> float:
    return sum(_distancia_km(a, b) for a, b in zip(coords, coords[1:]))


def ponto_na_linha(coords: list[Ponto], km: float) -> Ponto:
    """Ponto a `km` do início da linha, limitado às pontas."""
    if km <= 0:
        return coords[0]
    restante = km
    for a, b in zip(coords, coords[1:]):
        segmento = _distancia_km(a, b)
        if segmento > 0 and restante <= segmento:
            t = restante / segmento
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        restante -= segmento
    return coords[-1]
