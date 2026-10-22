"""Calcula e salva a rota de cada fazenda até a fábrica (SPEC seção 5).

Uso: python -m app.scripts.gerar_rotas [--faltantes]

Com --faltantes, só calcula as fazendas que ainda não têm rota (é o que a
subida do compose roda).

A rota sai do ponto da área mais próximo de uma estrada (SPEC 3.1): o
/nearest do OSRM é consultado para pontos espalhados na borda da área.

Respeita a política do servidor de demonstração do OSRM: User-Agent do
projeto, uma requisição por vez e 1 s entre requisições. Se uma rota não
puder ser calculada, usa linha reta com fator de distância e avisa.
"""
import time
from collections.abc import Callable

import httpx
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import LineString, Polygon
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.geo import linha_reta
from app.modelos import Fabrica, Fazenda, Rota
from app.osrm import buscar_mais_proximo, buscar_rota

PAUSA_ENTRE_REQUISICOES_S = 1.0
PONTOS_BORDA = 12
ERROS_OSRM = (httpx.HTTPError, ValueError, KeyError)


def pontos_borda(geom: Polygon, quantidade: int = PONTOS_BORDA) -> list[tuple[float, float]]:
    """Pontos igualmente espaçados no contorno externo da área."""
    anel = geom.exterior
    return [(p.x, p.y) for p in (anel.interpolate(i / quantidade, normalized=True) for i in range(quantidade))]


def ponto_carregamento(
    cliente: httpx.Client,
    settings: Settings,
    geom: Polygon,
    centro: tuple[float, float],
    dormir: Callable[[float], None],
    nome: str,
) -> tuple[tuple[float, float], str | None]:
    """Estrada mais perto da borda da área; sem resposta do OSRM, o centro e um aviso."""
    melhor: tuple[tuple[float, float], float] | None = None
    for ponto in pontos_borda(geom):
        dormir(PAUSA_ENTRE_REQUISICOES_S)
        try:
            estrada, distancia = buscar_mais_proximo(cliente, settings, ponto)
        except ERROS_OSRM:
            continue
        if melhor is None or distancia < melhor[1]:
            melhor = (estrada, distancia)
    if melhor is None:
        return centro, f"Ponto de carregamento de {nome} no centro da área: OSRM sem estrada próxima"
    return melhor[0], None


def gerar_rotas(
    sessao: Session,
    settings: Settings,
    cliente: httpx.Client,
    dormir: Callable[[float], None] = time.sleep,
    somente_faltantes: bool = False,
) -> list[str]:
    fabrica = to_shape(sessao.scalars(select(Fabrica.geom)).one())
    destino = (fabrica.x, fabrica.y)
    avisos: list[str] = []

    consulta = select(Fazenda).order_by(Fazenda.id)
    if somente_faltantes:
        consulta = consulta.where(~Fazenda.id.in_(select(Rota.fazenda_id)))
    fazendas = sessao.scalars(consulta).all()
    # Uma pausa antes de cada requisição, menos a primeira do script.
    requisicoes = 0

    def pausar(segundos: float) -> None:
        nonlocal requisicoes
        if requisicoes:
            dormir(segundos)
        requisicoes += 1

    for fazenda in fazendas:
        centro = to_shape(fazenda.centro)
        origem, aviso = ponto_carregamento(
            cliente, settings, to_shape(fazenda.geom), (centro.x, centro.y), pausar, fazenda.nome
        )
        if aviso:
            avisos.append(aviso)
        pausar(PAUSA_ENTRE_REQUISICOES_S)
        try:
            rota = buscar_rota(cliente, settings, origem, destino)
        except ERROS_OSRM as erro:
            rota = linha_reta(origem, destino, settings.fator_linha_reta, settings.velocidade_carregado_kmh)
            avisos.append(f"Rota de {fazenda.nome} em linha reta: {erro}")

        sessao.execute(delete(Rota).where(Rota.fazenda_id == fazenda.id))
        sessao.add(
            Rota(
                fazenda_id=fazenda.id,
                geom=from_shape(LineString(rota.coords), srid=4326),
                distancia_km=rota.distancia_km,
                duracao_prevista_min=rota.duracao_min,
            )
        )
        sessao.flush()
    return avisos


if __name__ == "__main__":
    import sys

    from app.db import SessionLocal

    configuracao = get_settings()
    with SessionLocal() as s, httpx.Client(timeout=20) as http:
        faltantes = "--faltantes" in sys.argv
        for aviso in gerar_rotas(s, configuracao, http, somente_faltantes=faltantes):
            print(f"Aviso: {aviso}")
        s.commit()
    print("Rotas salvas.")
