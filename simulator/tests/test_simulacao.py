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
    "parada_min_min": 20,
    "parada_max_min": 40,
}
FABRICA = (-51.76, -20.62)
INICIO = datetime(2026, 10, 20, 6, 0, tzinfo=timezone.utc)


def fazendas_padrao():
    return [
        FazendaSim(id=1, area_ha=3200, coords_rota=[(-51.80, -20.62), FABRICA]),
        FazendaSim(id=2, area_ha=2800, coords_rota=[(-51.80, -20.66), FABRICA]),
    ]


def nova_sim(caminhoes=None, fazendas=None, **parametros):
    return Simulacao(
        Parametros.de_json({**PARAMETROS_PADRAO, **parametros}),
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


EM_TRANSITO = {"EM_TRANSITO_CARREGADO", "EM_TRANSITO_VAZIO"}
# Rota longa (~33 km) para os trechos terem muitas leituras.
FAZENDA_LONGE = [FazendaSim(id=1, area_ha=3200, coords_rota=[(-52.07, -20.62), FABRICA])]


def trechos(leituras):
    """Agrupa as leituras de um caminhão em trechos: [(estado, [leituras]), ...]."""
    grupos = []
    for leitura in leituras:
        if grupos and grupos[-1][0] == leitura["estado"]:
            grupos[-1][1].append(leitura)
        else:
            grupos.append((leitura["estado"], [leitura]))
    return grupos


def leituras_de(s, passos, caminhao=0):
    return [s.passo(0.5)[caminhao] for _ in range(passos)]


def test_velocidade_constante_dentro_do_trecho():
    s = nova_sim(caminhoes=[(1, 55)], fazendas=FAZENDA_LONGE, prob_evento_viagem=0)
    em_transito = [g for e, g in trechos(leituras_de(s, 1000)) if e in EM_TRANSITO]
    assert len(em_transito) >= 2
    for grupo in em_transito:
        assert len({l["velocidade_kmh"] for l in grupo}) == 1


def test_velocidade_por_trecho_dentro_da_variacao():
    s = nova_sim(fazendas=FAZENDA_LONGE, prob_evento_viagem=0)
    limites = {"EM_TRANSITO_CARREGADO": 60, "EM_TRANSITO_VAZIO": 70}
    velocidades = set()
    for _ in range(3000):
        for l in s.passo(0.5):
            if l["estado"] in EM_TRANSITO:
                base = limites[l["estado"]]
                assert base * 0.85 - 0.05 <= l["velocidade_kmh"] <= base * 1.15 + 0.05
                velocidades.add(l["velocidade_kmh"])
    assert len(velocidades) > 20  # cada trecho sorteia a sua


def test_parada_nao_prevista_segura_o_caminhao():
    s = nova_sim(caminhoes=[(1, 55)], fazendas=FAZENDA_LONGE,
                 prob_evento_viagem=1, parada_min_min=20, parada_max_min=20)
    carregado = next(g for e, g in trechos(leituras_de(s, 600)) if e == "EM_TRANSITO_CARREGADO")
    paradas = [l for l in carregado if l["velocidade_kmh"] == 0]
    # 20 min parado = 40 leituras de 30 s, seguidas e no mesmo lugar.
    assert len(paradas) == 40
    inicio = carregado.index(paradas[0])
    assert carregado[inicio:inicio + 40] == paradas
    assert len({(l["lon"], l["lat"]) for l in paradas}) == 1
    assert carregado[inicio + 40]["velocidade_kmh"] > 0


def test_sem_evento_nao_para_no_transito():
    s = nova_sim(fazendas=FAZENDA_LONGE, prob_evento_viagem=0)
    for _ in range(1000):
        for l in s.passo(0.5):
            if l["estado"] in EM_TRANSITO:
                assert l["velocidade_kmh"] > 0


def test_assumido_nao_termina_o_carregamento_sozinho():
    s = nova_sim(caminhoes=[(1, 55)])
    s.controlar({1}, set())
    for _ in range(400):  # 200 min, bem mais que o carregamento máximo (60)
        assert s.passo(0.5)[0]["estado"] == "CARREGANDO"


def test_liberado_sai_no_passo_seguinte_uma_vez():
    s = nova_sim(caminhoes=[(1, 55)], prob_evento_viagem=0)
    s.controlar({1}, set())
    s.passo(0.5)
    s.controlar({1}, {1})
    assert s.passo(0.5)[0]["estado"] == "EM_TRANSITO_CARREGADO"
    s.controlar({1}, set())
    # Percorre o ciclo até carregar de novo: a viagem nova não sai sem novo check-in.
    estados = [s.passo(0.5)[0]["estado"] for _ in range(2000)]
    volta = estados.index("CARREGANDO")
    assert set(estados[volta:]) == {"CARREGANDO"}


def test_solto_volta_a_contar_o_tempo():
    s = nova_sim(caminhoes=[(1, 55)])
    s.controlar({1}, set())
    for _ in range(200):
        s.passo(0.5)
    s.controlar(set(), set())
    estados = [s.passo(0.5)[0]["estado"] for _ in range(130)]  # 65 min
    assert "EM_TRANSITO_CARREGADO" in estados
