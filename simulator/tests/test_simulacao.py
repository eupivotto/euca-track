from collections import Counter
from datetime import datetime, timedelta, timezone

import pytest

from sim.estados import Estado
from sim.simulacao import FazendaSim, Parametros, Simulacao

PARAMETROS_PADRAO = {
    "seed": 42,
    "capacidade_rodotrem_t": 55,
    "capacidade_tritrem_t": 45,
    "velocidade_carregado_kmh": 60,
    "velocidade_vazio_kmh": 70,
    "variacao_velocidade": 0.15,
    "carregamento_min_min": 40,
    "carregamento_max_min": 60,
    "pesagem_min": 5,
    "descarga_min_min": 25,
    "descarga_max_min": 35,
    "vagas_descarga": 3,
    "intervalo_telemetria_s": 30,
    "fator_tempo": 10,
    "prob_evento_viagem": 0.05,
}
FABRICA = (-51.76, -20.62)
INICIO = datetime(2026, 10, 20, 6, 0, tzinfo=timezone.utc)


def fazendas_padrao():
    return [
        FazendaSim(id=1, area_ha=3200, coords_rota=[(-51.80, -20.62), FABRICA]),
        FazendaSim(id=2, area_ha=2800, coords_rota=[(-51.80, -20.66), FABRICA]),
    ]


def nova_sim(caminhoes=None, fazendas=None):
    return Simulacao(
        Parametros.de_json(PARAMETROS_PADRAO),
        fazendas or fazendas_padrao(),
        caminhoes or [(i, 55 if i <= 12 else 45) for i in range(1, 21)],
        INICIO,
    )


def test_parametros_ignoram_chaves_extras():
    p = Parametros.de_json({**PARAMETROS_PADRAO, "outra_coisa": 1})
    assert p.vagas_descarga == 3


def test_mesma_semente_mesma_simulacao():
    a, b = nova_sim(), nova_sim()
    for _ in range(200):
        assert a.passo(0.5) == b.passo(0.5)


def test_todos_comecam_carregando_em_fazenda_sorteada():
    s = nova_sim()
    assert {c.estado for c in s.caminhoes} == {Estado.CARREGANDO}
    assert [c.fazenda_id for c in s.caminhoes] == [c.fazenda_id for c in nova_sim().caminhoes]
    assert len({c.fazenda_id for c in s.caminhoes}) == 2  # sorteio usou as duas fazendas


def test_leitura_no_formato_da_api():
    leitura = nova_sim(caminhoes=[(7, 55)]).passo(0.5)[0]
    assert set(leitura) == {"caminhao_id", "fazenda_id", "estado", "lon", "lat", "velocidade_kmh", "momento"}
    assert leitura["caminhao_id"] == 7 and leitura["estado"] == "CARREGANDO"
    assert leitura["velocidade_kmh"] == 0
    assert datetime.fromisoformat(leitura["momento"]) == INICIO + timedelta(seconds=30)


def test_carregando_fica_no_inicio_da_rota():
    s = nova_sim(caminhoes=[(1, 55)])
    leitura = s.passo(0.5)[0]
    rota = {f.id: f.coords_rota for f in fazendas_padrao()}[leitura["fazenda_id"]]
    assert (leitura["lon"], leitura["lat"]) == rota[0]


def test_caminhao_percorre_o_ciclo_completo():
    s = nova_sim(caminhoes=[(1, 55)])
    vistos = []
    for _ in range(2000):
        e = s.passo(0.5)[0]["estado"]
        if not vistos or vistos[-1] != e:
            vistos.append(e)
    assert vistos[:7] == ["CARREGANDO", "EM_TRANSITO_CARREGADO", "FILA_PATIO", "PESAGEM",
                          "DESCARGA", "EM_TRANSITO_VAZIO", "CARREGANDO"]


def test_quem_chega_aparece_na_fila():
    s = nova_sim(caminhoes=[(1, 55)])
    s.caminhoes[0].estado, s.caminhoes[0].km = Estado.EM_TRANSITO_CARREGADO, 10_000
    assert s.passo(0.5)[0]["estado"] == "FILA_PATIO"
    assert s.passo(0.5)[0]["estado"] == "PESAGEM"


def test_quarto_caminhao_espera_na_fila():
    s = nova_sim(caminhoes=[(i, 55) for i in range(1, 5)])
    for c in s.caminhoes:  # todos chegam juntos, em ordem de id
        c.estado, c.km = Estado.EM_TRANSITO_CARREGADO, 10_000
    s.passo(0.5)
    assert s.fila == [1, 2, 3, 4]
    s.passo(0.5)
    estados = {c.id: c.estado for c in s.caminhoes}
    assert [estados[i] for i in (1, 2, 3)] == [Estado.PESAGEM] * 3
    assert estados[4] == Estado.FILA_PATIO and s.fila == [4]


def test_fila_anda_quando_abre_vaga():
    s = nova_sim(caminhoes=[(i, 55) for i in range(1, 5)])
    for c in s.caminhoes:
        c.estado, c.km = Estado.EM_TRANSITO_CARREGADO, 10_000
    s.passo(0.5)
    s.passo(0.5)
    s.caminhoes[0].estado, s.caminhoes[0].minutos_restantes = Estado.DESCARGA, 0.1
    s.passo(0.5)
    assert s.caminhoes[0].estado == Estado.EM_TRANSITO_VAZIO
    assert s.caminhoes[3].estado == Estado.PESAGEM and s.fila == []


def test_patio_fica_na_fabrica_parado():
    s = nova_sim(caminhoes=[(1, 55)])
    s.caminhoes[0].estado, s.caminhoes[0].km = Estado.EM_TRANSITO_CARREGADO, 10_000
    leitura = s.passo(0.5)[0]
    assert (leitura["lon"], leitura["lat"]) == FABRICA and leitura["velocidade_kmh"] == 0


def test_velocidade_dentro_da_variacao():
    s = nova_sim(caminhoes=[(1, 55)])
    s.caminhoes[0].estado = Estado.EM_TRANSITO_CARREGADO
    v = s.passo(0.5)[0]["velocidade_kmh"]
    assert 60 * 0.85 <= v <= 60 * 1.15


def test_vazio_anda_no_sentido_da_fazenda():
    s = nova_sim(caminhoes=[(1, 55)])
    c = s.caminhoes[0]
    c.estado, c.km, c.fazenda_id = Estado.EM_TRANSITO_VAZIO, 0.5, 1
    leitura = s.passo(0.5)[0]
    # saiu da fábrica (-51.76) rumo à fazenda 1 (-51.80)
    assert -51.80 < leitura["lon"] < -51.76


def test_vazio_escolhe_fazenda_pela_area():
    s = nova_sim(fazendas=[
        FazendaSim(id=1, area_ha=1, coords_rota=[(-51.80, -20.62), FABRICA]),
        FazendaSim(id=2, area_ha=9, coords_rota=[(-51.80, -20.66), FABRICA]),
    ])
    sorteios = Counter(s.sortear_fazenda() for _ in range(1000))
    assert 0.85 < sorteios[2] / 1000 < 0.95


def test_relogio_avanca():
    s = nova_sim()
    t0 = s.agora
    s.passo(0.5)
    assert s.agora - t0 == timedelta(seconds=30)


def test_sem_fazendas_nao_comeca():
    with pytest.raises(ValueError):
        Simulacao(Parametros.de_json(PARAMETROS_PADRAO), [], [(1, 55)], INICIO)
