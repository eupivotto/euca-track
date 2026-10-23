"""Focos de calor do INPE (SPEC seção 8): importação e regras do alerta de foco."""
import csv
import io
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points
from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.alertas import FocoPerto, TipoAlerta
from app.config import Settings
from app.modelos import Alerta, ClimaDiario, Fazenda, FocoCalor


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


def texto_foco(
    distancia_m: float, detectado_em: datetime, a_favor: bool | None, fuso: ZoneInfo, referencia: str = "",
) -> str:
    """Mensagem do alerta; `referencia` vem logo depois da distância (" da rota da …")."""
    km = f"{distancia_m / 1000:.1f}".replace(".", ",")
    hora = detectado_em.astimezone(fuso).strftime("%Hh%M")
    texto = f"Foco a {km} km{referencia}, detectado às {hora}"
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


# --- Alertas de foco perto da rota e da fazenda ---


def _vento_13h(sessao: Session, fazenda_id: int, agora_real: datetime, settings: Settings) -> float | None:
    """Direção do vento das 13h de hoje (data real local) na fazenda."""
    hoje = agora_real.astimezone(ZoneInfo(settings.fuso)).date()
    return sessao.scalar(
        select(ClimaDiario.vento_dir).where(ClimaDiario.fazenda_id == fazenda_id, ClimaDiario.data == hoje)
    )


def _foco_mais_perto(
    sessao: Session, alvo, raio_km: float, agora_real: datetime, settings: Settings,
) -> tuple[FocoCalor, float] | None:
    """Foco da janela mais perto de `alvo` (expressão de geometria 4326), a menos de `raio_km`."""
    alvo_geo = func.geography(alvo)
    foco_geo = func.geography(FocoCalor.geom)
    distancia = func.ST_Distance(alvo_geo, foco_geo)
    linha = sessao.execute(
        select(FocoCalor, distancia)
        .where(
            FocoCalor.detectado_em >= agora_real - timedelta(hours=settings.foco_janela_h),
            FocoCalor.detectado_em <= agora_real,
            func.ST_DWithin(alvo_geo, foco_geo, raio_km * 1000),
        )
        .order_by(distancia, FocoCalor.id)
        .limit(1)
    ).first()
    return (linha[0], float(linha[1])) if linha else None


def _foco_perto(
    sessao: Session, alvo_shape: BaseGeometry, alvo_sql, raio_km: float, fazenda_id: int,
    agora_real: datetime, settings: Settings,
) -> FocoPerto | None:
    achado = _foco_mais_perto(sessao, alvo_sql, raio_km, agora_real, settings)
    if achado is None:
        return None
    foco, distancia = achado
    ponto_foco = to_shape(foco.geom)
    # Rumo do ponto do alvo mais perto do foco até o foco; com o foco dentro, do centro do alvo.
    origem = nearest_points(alvo_shape, ponto_foco)[0]
    if origem.equals(ponto_foco):
        origem = alvo_shape.centroid
    a_favor = vento_a_favor(
        _vento_13h(sessao, fazenda_id, agora_real, settings),
        rumo_graus((origem.x, origem.y), (ponto_foco.x, ponto_foco.y)),
        settings.foco_vento_angulo_max,
    )
    return FocoPerto(foco.id, distancia, foco.detectado_em, a_favor)


def foco_perto_da_rota(
    sessao: Session, rota_geom: LineString, fazenda_id: int, agora_real: datetime, settings: Settings,
) -> FocoPerto | None:
    """Foco das últimas horas a menos de `foco_rota_km` da rota (vento da fazenda da viagem)."""
    alvo = func.ST_GeomFromText(rota_geom.wkt, 4326)
    return _foco_perto(sessao, rota_geom, alvo, settings.foco_rota_km, fazenda_id, agora_real, settings)


def atualizar_alertas_fazenda(
    sessao: Session, settings: Settings, agora_real: datetime, agora_sim: datetime,
) -> list[Alerta]:
    """Abre FOCO_PROXIMO_FAZENDA onde há foco recente perto do polígono e fecha onde não há mais.

    A janela dos focos usa o relógio real; abertura e fechamento, o simulado,
    para a lista de alertas seguir em ordem com os de logística.
    """
    abertos = {
        a.fazenda_id: a
        for a in sessao.scalars(
            select(Alerta).where(Alerta.tipo == TipoAlerta.FOCO_PROXIMO_FAZENDA, Alerta.status == "ABERTO")
        )
    }
    fuso = ZoneInfo(settings.fuso)
    mudaram: list[Alerta] = []
    for fazenda in sessao.scalars(select(Fazenda).order_by(Fazenda.id)).all():
        poligono = select(Fazenda.geom).where(Fazenda.id == fazenda.id).scalar_subquery()
        perto = _foco_perto(
            sessao, to_shape(fazenda.geom), poligono, settings.foco_fazenda_km, fazenda.id, agora_real, settings,
        )
        aberto = abertos.get(fazenda.id)
        if perto is not None and aberto is None:
            alerta = Alerta(
                tipo=TipoAlerta.FOCO_PROXIMO_FAZENDA, fazenda_id=fazenda.id, foco_id=perto.foco_id,
                mensagem=texto_foco(perto.distancia_m, perto.detectado_em, perto.a_favor, fuso),
                aberto_em=agora_sim, status="ABERTO",
            )
            sessao.add(alerta)
            mudaram.append(alerta)
        elif perto is None and aberto is not None:
            aberto.status = "FECHADO"
            aberto.fechado_em = agora_sim
            mudaram.append(aberto)
    sessao.flush()
    return mudaram
