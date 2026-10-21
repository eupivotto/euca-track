"""Difusão de mensagens da frota para os clientes de WebSocket."""
import logging

from fastapi import WebSocket

log = logging.getLogger(__name__)


class Difusor:
    def __init__(self) -> None:
        self.conexoes: set[WebSocket] = set()

    async def conectar(self, ws: WebSocket) -> None:
        await ws.accept()
        self.conexoes.add(ws)

    def desconectar(self, ws: WebSocket) -> None:
        self.conexoes.discard(ws)

    async def difundir(self, mensagem: dict) -> None:
        # Uma conexão que caiu não pode atrapalhar as outras nem a telemetria.
        for ws in list(self.conexoes):
            try:
                await ws.send_json(mensagem)
            except Exception:  # noqa: BLE001
                log.info("Conexão de WebSocket descartada")
                self.desconectar(ws)


difusor = Difusor()
