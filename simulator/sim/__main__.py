"""Laço do simulador. Uso: python -m sim

A cada intervalo_telemetria_s / fator_tempo segundos reais, avança
intervalo_telemetria_s segundos simulados e envia um lote para a API.
"""
import logging
import os
import time
from collections.abc import Callable
from datetime import datetime, timezone

import httpx

from sim.cliente import ClienteApi
from sim.simulacao import Simulacao

log = logging.getLogger("sim")
ESPERA_INICIAL_S = 5


def aguardar_api(cliente: ClienteApi) -> None:
    while True:
        try:
            if cliente.http.get("/saude").status_code == 200 and cliente.fazendas():
                return
            log.warning("Sem rotas no banco: rode python -m app.scripts.gerar_rotas")
        except httpx.HTTPError as erro:
            log.warning("API ainda não respondeu: %s", erro)
        time.sleep(ESPERA_INICIAL_S)


def iniciar(
    cliente: ClienteApi,
    agora: Callable[[], datetime],
    esperar: Callable[[float], None] = time.sleep,
) -> Simulacao:
    """Monta a simulação com os dados da API, tentando de novo se ela cair no meio."""
    while True:
        try:
            return Simulacao(
                cliente.parametros(),
                cliente.fazendas(),
                cliente.caminhoes(),
                cliente.relogio_inicial(agora()),
            )
        except httpx.HTTPError as erro:
            log.warning("Falha ao ler os dados iniciais: %s", erro)
            esperar(ESPERA_INICIAL_S)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # sem uma linha por lote enviado
    http = httpx.Client(base_url=os.environ.get("API_URL", "http://api:8000"), timeout=10)
    cliente = ClienteApi(http, token=os.environ.get("TOKEN_TELEMETRIA", "dev-token"))
    aguardar_api(cliente)

    simulacao = iniciar(cliente, lambda: datetime.now(timezone.utc))
    parametros = simulacao.p
    passo_min = parametros.intervalo_telemetria_s / 60
    pausa_s = parametros.intervalo_telemetria_s / parametros.fator_tempo
    log.info("Simulando %d caminhões, um lote a cada %.1f s", len(simulacao.caminhoes), pausa_s)

    while True:
        inicio = time.monotonic()
        cliente.enviar(simulacao.passo(passo_min))
        time.sleep(max(0.0, pausa_s - (time.monotonic() - inicio)))


if __name__ == "__main__":
    main()
