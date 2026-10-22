"""Conversa com a API: lê parâmetros, fazendas, rotas e frota; envia telemetria."""
import logging
from datetime import datetime

import httpx

from sim.simulacao import FazendaSim, Parametros

log = logging.getLogger(__name__)


class ClienteApi:
    def __init__(self, http: httpx.Client, token: str) -> None:
        self.http = http
        self.token = token

    def _get(self, caminho: str):
        resposta = self.http.get(caminho)
        resposta.raise_for_status()
        return resposta.json()

    def parametros(self) -> Parametros:
        return Parametros.de_json(self._get("/simulacao/parametros"))

    def fazendas(self) -> list[FazendaSim]:
        """Fazendas com rota até a fábrica. Fazenda sem rota fica de fora."""
        rotas = {
            f["properties"]["fazenda_id"]: [tuple(p) for p in f["geometry"]["coordinates"]]
            for f in self._get("/rotas")["features"]
        }
        return [
            FazendaSim(id=p["id"], area_ha=p["area_ha"], coords_rota=rotas[p["id"]])
            for p in (f["properties"] for f in self._get("/fazendas")["features"])
            if p["tipo"] == "fazenda" and p["id"] in rotas
        ]

    def caminhoes(self) -> list[tuple[int, float]]:
        return [(c["id"], c["capacidade_t"]) for c in self._get("/caminhoes")]

    def relogio_inicial(self, agora_real: datetime) -> datetime:
        """Onde o relógio simulado começa: nunca antes da última leitura gravada.

        Sem isso, um simulador reiniciado grava posições "no passado" e o
        painel continua mostrando as da execução anterior.
        """
        ultimo = datetime.fromisoformat(self._get("/indicadores")["agora"])
        return max(agora_real, ultimo)

    def enviar(self, leituras: list[dict]) -> dict | None:
        """Envia um lote e devolve a resposta. Nunca levanta: a simulação segue mesmo com a API fora."""
        try:
            resposta = self.http.post("/telemetria", json=leituras, headers={"X-Token": self.token})
        except httpx.HTTPError as erro:
            log.warning("Falha ao enviar telemetria: %s", erro)
            return None
        if resposta.status_code != 200:
            log.warning("API recusou a telemetria: %s %s", resposta.status_code, resposta.text[:200])
            return None
        return resposta.json()
