"""Cliente do OSRM. Só é usado pelo script gerar_rotas, nunca dentro de um request."""
import httpx

from app.config import Settings
from app.geo import RotaCalculada


def ler_resposta_osrm(dados: dict) -> RotaCalculada:
    if dados.get("code") != "Ok" or not dados.get("routes"):
        raise ValueError(f"OSRM sem rota (code={dados.get('code')!r})")
    rota = dados["routes"][0]
    coords = [(float(lon), float(lat)) for lon, lat in rota["geometry"]["coordinates"]]
    return RotaCalculada(coords, rota["distance"] / 1000, rota["duration"] / 60)


def buscar_rota(
    cliente: httpx.Client,
    settings: Settings,
    origem: tuple[float, float],
    destino: tuple[float, float],
) -> RotaCalculada:
    pontos = f"{origem[0]},{origem[1]};{destino[0]},{destino[1]}"
    resposta = cliente.get(
        f"{settings.osrm_url}/route/v1/driving/{pontos}",
        params={"overview": "full", "geometries": "geojson"},
        headers={"User-Agent": settings.user_agent},
    )
    resposta.raise_for_status()
    return ler_resposta_osrm(resposta.json())


def ler_resposta_nearest(dados: dict) -> tuple[tuple[float, float], float]:
    """Ponto da estrada mais próxima (lon, lat) e a distância até ele, em metros."""
    if dados.get("code") != "Ok" or not dados.get("waypoints"):
        raise ValueError(f"OSRM sem estrada próxima (code={dados.get('code')!r})")
    ponto = dados["waypoints"][0]
    lon, lat = ponto["location"]
    return (float(lon), float(lat)), float(ponto["distance"])


def buscar_mais_proximo(
    cliente: httpx.Client, settings: Settings, ponto: tuple[float, float]
) -> tuple[tuple[float, float], float]:
    resposta = cliente.get(
        f"{settings.osrm_url}/nearest/v1/driving/{ponto[0]},{ponto[1]}",
        headers={"User-Agent": settings.user_agent},
    )
    resposta.raise_for_status()
    return ler_resposta_nearest(resposta.json())
