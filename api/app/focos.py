"""Focos de calor do INPE (SPEC seção 8): importação e regras do alerta de foco."""
import csv
import io
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.modelos import FocoCalor


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


# --- Importação do arquivo diário ---


@dataclass
class FocoLido:
    lat: float
    lon: float
    detectado_em: datetime  # UTC
    satelite: str
    municipio: str | None


def ler_csv_focos(texto: str, settings: Settings) -> list[FocoLido]:
    """Focos do recorte da região; linhas quebradas são ignoradas."""
    focos = []
    for linha in csv.DictReader(io.StringIO(texto.lstrip("﻿"))):
        try:
            # A latitude vem com espaços à esquerda e às vezes sem o zero (" -.358070").
            lat, lon = float(linha["lat"]), float(linha["lon"])
            detectado = datetime.strptime(linha["data_hora_gmt"].strip(), "%Y-%m-%d %H:%M:%S")
            satelite = linha["satelite"].strip()
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if not satelite:
            continue
        if not (settings.regiao_lat_min <= lat <= settings.regiao_lat_max
                and settings.regiao_lon_min <= lon <= settings.regiao_lon_max):
            continue
        municipio = (linha.get("municipio") or "").strip() or None
        focos.append(FocoLido(lat, lon, detectado.replace(tzinfo=UTC), satelite, municipio))
    return focos


def chave_foco(f: FocoLido) -> str:
    return f"{f.lat:.5f}|{f.lon:.5f}|{f.detectado_em:%Y-%m-%dT%H:%M}|{f.satelite}"


def arquivos_do_momento(agora_utc: datetime, primeira_vez: bool) -> list[date]:
    """O arquivo de hoje (UTC); o de ontem também logo após a virada, para fechar o dia."""
    hoje = agora_utc.astimezone(UTC).date()
    if primeira_vez or agora_utc.astimezone(UTC).hour < 2:
        return [hoje - timedelta(days=1), hoje]
    return [hoje]


def importar_focos(
    sessao: Session, settings: Settings, cliente: httpx.Client, agora_utc: datetime,
) -> tuple[int, list[str]]:
    """Baixa os arquivos do momento e grava os focos novos. Devolve (novos, avisos)."""
    primeira_vez = not sessao.scalar(select(exists().where(FocoCalor.id.is_not(None))))
    novos = 0
    avisos: list[str] = []
    for dia in arquivos_do_momento(agora_utc, primeira_vez):
        url = settings.inpe_focos_url.format(data=f"{dia:%Y%m%d}")
        try:
            resposta = cliente.get(url, headers={"User-Agent": settings.user_agent}, timeout=60)
            resposta.raise_for_status()
        except httpx.HTTPError as erro:
            # O arquivo do dia só aparece depois da primeira passagem de satélite.
            avisos.append(f"Focos de {dia:%Y%m%d} não baixados ({erro})")
            continue
        for foco in ler_csv_focos(resposta.content.decode("utf-8", errors="replace"), settings):
            novo_id = sessao.scalar(
                insert(FocoCalor)
                .values(
                    geom=from_shape(Point(foco.lon, foco.lat), srid=4326),
                    satelite=foco.satelite, detectado_em=foco.detectado_em,
                    municipio=foco.municipio, chave=chave_foco(foco),
                )
                .on_conflict_do_nothing(constraint="uq_focos_calor_chave")
                .returning(FocoCalor.id)
            )
            novos += novo_id is not None
    sessao.flush()
    return novos, avisos
