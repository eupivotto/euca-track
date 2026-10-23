"""Focos de calor do INPE (SPEC seção 8): regras do alerta de foco."""
import math
from datetime import datetime
from zoneinfo import ZoneInfo


def rumo_graus(de: tuple[float, float], para: tuple[float, float]) -> float:
    """Azimute inicial de `de` até `para` (lon, lat): 0 = norte, 90 = leste."""
    lon1, lat1, lon2, lat2 = map(math.radians, (*de, *para))
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return math.degrees(math.atan2(x, y)) % 360


def vento_a_favor(vento_dir: float | None, rumo_alvo_para_foco: float, angulo_max: float) -> bool | None:
    """O vento sopra do foco para o alvo?

    `vento_dir` é a direção de onde o vento vem (convenção meteorológica), então
    o vento traz o fogo quando ela aponta para o lado do foco.
    """
    if vento_dir is None:
        return None
    diferenca = abs(vento_dir - rumo_alvo_para_foco) % 360
    return min(diferenca, 360 - diferenca) < angulo_max


def texto_foco(distancia_m: float, detectado_em: datetime, a_favor: bool | None, fuso: ZoneInfo) -> str:
    km = f"{distancia_m / 1000:.1f}".replace(".", ",")
    hora = detectado_em.astimezone(fuso).strftime("%Hh%M")
    texto = f"Foco a {km} km, detectado às {hora}"
    if a_favor is None:
        return texto
    return texto + ("; vento das 13h sopra do foco para cá" if a_favor else "; vento das 13h não sopra do foco para cá")
