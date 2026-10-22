"""Dados de referência (SPEC seções 3 e 4).

Fábrica, frota e motoristas são fictícios. As fazendas são as 8 áreas reais
de eucalipto do MapBiomas (SPEC 3.1), lidas de app/dados/areas_eucalipto.geojson.

Uso: python -m app.seed
"""
import json
import random
import string
from pathlib import Path

from geoalchemy2.shape import from_shape
from shapely.geometry import Point, shape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.areas import ARQUIVO_AREAS, AreaEucalipto
from app.config import Settings, get_settings
from app.modelos import Caminhao, Fabrica, Fazenda, Motorista

FABRICA = ("Fábrica Modelo Três Lagoas", -20.6200, -51.7600)


def carregar_areas(caminho: Path = ARQUIVO_AREAS) -> list[AreaEucalipto]:
    if not caminho.exists():
        raise FileNotFoundError(
            f"{caminho} não existe. Gere com: python -m app.scripts.exportar_mapbiomas "
            "&& python -m app.scripts.gerar_areas_eucalipto"
        )
    return [
        AreaEucalipto(
            nome=f["properties"]["nome"],
            area_ha=f["properties"]["area_ha"],
            geom=shape(f["geometry"]),
            centro=Point(f["properties"]["centro"]),
        )
        for f in json.loads(caminho.read_text(encoding="utf-8"))["features"]
    ]


TOTAL_CAMINHOES = 20
TOTAL_RODOTREM = 12

PRENOMES = [
    "Antônio", "Carlos", "Edson", "Fábio", "Gilberto", "Hélio", "Ivan", "Jair",
    "Luciano", "Márcio", "Nilton", "Osmar", "Paulo", "Reinaldo", "Sérgio",
    "Valdir", "Wagner", "Adriana", "Cláudia", "Rosana",
]
SOBRENOMES = [
    "Almeida", "Barbosa", "Cardoso", "Dias", "Ferreira", "Gomes", "Lima",
    "Martins", "Nogueira", "Oliveira", "Pereira", "Ribeiro", "Santos", "Teixeira",
]


def gerar_placas(n: int, rng: random.Random) -> list[str]:
    """Placas no padrão Mercosul LLLNLNN com prefixo TLG, sem repetição."""
    placas: list[str] = []
    while len(placas) < n:
        placa = (
            f"TLG{rng.randrange(10)}{rng.choice(string.ascii_uppercase)}"
            f"{rng.randrange(100):02d}"
        )
        if placa not in placas:
            placas.append(placa)
    return placas


def gerar_nomes(n: int, rng: random.Random) -> list[str]:
    nomes: list[str] = []
    while len(nomes) < n:
        nome = f"{rng.choice(PRENOMES)} {rng.choice(SOBRENOMES)}"
        if nome not in nomes:
            nomes.append(nome)
    return nomes


def semear(sessao: Session, settings: Settings) -> None:
    """Grava fábrica, fazendas, motoristas e caminhões. Não faz nada se já houver dados."""
    if sessao.scalar(select(Fabrica.id).limit(1)) is not None:
        return

    nome, lat, lon = FABRICA
    sessao.add(Fabrica(nome=nome, geom=from_shape(Point(lon, lat), srid=4326)))

    for area in carregar_areas():
        sessao.add(
            Fazenda(
                nome=area.nome,
                area_ha=area.area_ha,
                centro=from_shape(area.centro, srid=4326),
                geom=from_shape(area.geom, srid=4326),
            )
        )

    # Placas primeiro: a ordem dos sorteios faz parte da reprodutibilidade.
    rng = random.Random(settings.seed)
    placas = gerar_placas(TOTAL_CAMINHOES, rng)
    nomes = gerar_nomes(TOTAL_CAMINHOES, rng)

    for i, (placa, nome) in enumerate(zip(placas, nomes)):
        motorista = Motorista(nome=nome)
        sessao.add(motorista)
        rodotrem = i < TOTAL_RODOTREM
        sessao.add(
            Caminhao(
                placa=placa,
                tipo="rodotrem" if rodotrem else "tritrem",
                capacidade_t=settings.capacidade_rodotrem_t if rodotrem else settings.capacidade_tritrem_t,
                motorista=motorista,
            )
        )
    sessao.flush()


if __name__ == "__main__":
    from app.db import SessionLocal

    with SessionLocal() as s:
        semear(s, get_settings())
        s.commit()
    print("Seed concluído.")
