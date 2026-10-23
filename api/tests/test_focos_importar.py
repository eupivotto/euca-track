from datetime import UTC, date, datetime

import httpx
from sqlalchemy import func, select

from app.focos import FocoLido, arquivos_do_momento, chave_foco, importar_focos, ler_csv_focos
from app.modelos import FocoCalor
from tests.conftest import FIXTURES

AMOSTRA = (FIXTURES / "focos_diario_br_amostra.csv").read_text(encoding="utf-8")
CABECALHO = AMOSTRA.splitlines()[0]


def test_so_focos_do_recorte(settings):
    focos = ler_csv_focos(AMOSTRA, settings)
    assert len(focos) == 5
    for f in focos:
        assert -21.6 <= f.lat <= -19.8 and -52.9 <= f.lon <= -51.4


def test_hora_em_utc_e_municipio_com_acento(settings):
    primeiro = ler_csv_focos(AMOSTRA, settings)[0]
    assert primeiro.detectado_em == datetime(2026, 10, 21, 17, 32, tzinfo=UTC)
    assert primeiro.municipio == "TRÊS LAGOAS"
    assert primeiro.satelite == "NOAA-20"
    assert (primeiro.lat, primeiro.lon) == (-20.99552, -51.86399)


def test_csv_so_com_cabecalho(settings):
    assert ler_csv_focos(CABECALHO + "\n", settings) == []
    assert ler_csv_focos("", settings) == []


def test_linha_quebrada_e_ignorada(settings):
    linhas = AMOSTRA.splitlines()
    quebrada = [linhas[0], "abc, -20.9,", "x, -20.9, nao-e-numero,2026-10-21 17:32:00,NOAA-20,X,MS", *linhas[1:]]
    assert len(ler_csv_focos("\n".join(quebrada), settings)) == 5


def test_bom_no_inicio(settings):
    assert len(ler_csv_focos("﻿" + AMOSTRA, settings)) == 5


def test_chave_do_foco():
    f = FocoLido(-20.99552, -51.86399, datetime(2026, 10, 21, 17, 32, tzinfo=UTC), "NOAA-20", "X")
    assert chave_foco(f) == "-20.99552|-51.86399|2026-10-21T17:32|NOAA-20"


def test_arquivos_do_momento():
    assert arquivos_do_momento(datetime(2026, 10, 22, 1, 0, tzinfo=UTC), False) == [
        date(2026, 10, 21), date(2026, 10, 22)
    ]
    assert arquivos_do_momento(datetime(2026, 10, 22, 5, 0, tzinfo=UTC), False) == [date(2026, 10, 22)]
    assert arquivos_do_momento(datetime(2026, 10, 22, 5, 0, tzinfo=UTC), True) == [
        date(2026, 10, 21), date(2026, 10, 22)
    ]


def _cliente(pedidos, status_hoje=200):
    def handler(request):
        pedidos.append(request.url.path.rsplit("/", 1)[-1])
        if request.url.path.endswith("20261022.csv") and status_hoje != 200:
            return httpx.Response(status_hoje, text="Not Found")
        return httpx.Response(200, content=AMOSTRA.encode("utf-8"))

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_importar_duas_vezes_nao_duplica(sessao, settings):
    agora = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    pedidos = []
    novos, avisos = importar_focos(sessao, settings, _cliente(pedidos), agora)
    # Primeira vez: ontem e hoje (os dois devolvem a mesma amostra).
    assert pedidos == ["focos_diario_br_20261021.csv", "focos_diario_br_20261022.csv"]
    assert (novos, avisos) == (5, [])
    pedidos.clear()
    novos, _ = importar_focos(sessao, settings, _cliente(pedidos), agora)
    assert pedidos == ["focos_diario_br_20261022.csv"] and novos == 0
    assert sessao.scalar(select(func.count()).select_from(FocoCalor)) == 5


def test_arquivo_de_hoje_ausente_vira_aviso(sessao, settings):
    agora = datetime(2026, 10, 22, 0, 10, tzinfo=UTC)
    novos, avisos = importar_focos(sessao, settings, _cliente([], status_hoje=404), agora)
    assert novos == 5
    assert len(avisos) == 1 and "20261022" in avisos[0]
