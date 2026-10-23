"""Rotinas agendadas: clima do Open-Meteo e focos do INPE (SPEC seções 7 e 8).

Uso: python -m app.rotinas  (serviço `rotinas` do compose)

É o único processo que fala com essas fontes; a API só lê o que fica no banco.
Uma fonte fora do ar vira aviso no log e a rotina tenta de novo na próxima vez.
"""
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from app.clima import importar_clima
from app.config import Settings
from app.focos import atualizar_alertas_fazenda, importar_focos
from app.operacao import agora_simulado

FabricaSessao = Callable[[], AbstractContextManager[Session]]


def _avisar(avisos: list[str]) -> None:
    for aviso in avisos:
        print(f"Aviso: {aviso}", flush=True)


def rodar_clima(fabrica_sessao: FabricaSessao, settings: Settings, cliente: httpx.Client, hoje: date) -> None:
    try:
        with fabrica_sessao() as sessao:
            avisos = importar_clima(sessao, settings, cliente, hoje)
            sessao.commit()
        _avisar(avisos)
        print(f"Clima atualizado ({hoje:%d/%m}).", flush=True)
    except Exception as erro:  # noqa: BLE001 — o agendador não pode morrer
        print(f"Erro na rotina de clima: {erro!r}", flush=True)


def rodar_focos(
    fabrica_sessao: FabricaSessao, settings: Settings, cliente: httpx.Client, agora_utc: datetime,
) -> None:
    try:
        with fabrica_sessao() as sessao:
            novos, avisos = importar_focos(sessao, settings, cliente, agora_utc)
            alertas = atualizar_alertas_fazenda(
                sessao, settings, agora_utc, agora_simulado(sessao, ZoneInfo(settings.fuso))
            )
            sessao.commit()
        _avisar(avisos)
        print(f"Focos: {novos} novos, {len(alertas)} alertas de fazenda abertos ou fechados.", flush=True)
    except Exception as erro:  # noqa: BLE001
        print(f"Erro na rotina de focos: {erro!r}", flush=True)


def main() -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler

    from app.config import get_settings
    from app.db import SessionLocal

    settings = get_settings()
    cliente = httpx.Client()
    fuso = ZoneInfo(settings.fuso)

    def clima() -> None:
        rodar_clima(SessionLocal, settings, cliente, datetime.now(fuso).date())

    def focos() -> None:
        rodar_focos(SessionLocal, settings, cliente, datetime.now(UTC))

    clima()
    focos()
    agendador = BlockingScheduler(timezone=fuso, job_defaults={"max_instances": 1, "coalesce": True})
    agendador.add_job(clima, "interval", hours=settings.rotina_clima_h)
    agendador.add_job(focos, "interval", minutes=settings.rotina_focos_min)
    print("Rotinas agendadas.", flush=True)
    agendador.start()


if __name__ == "__main__":
    main()
