from app.config import Settings


def test_padroes_do_spec():
    s = Settings()
    assert (s.capacidade_rodotrem_t, s.capacidade_tritrem_t) == (55, 45)
    assert (s.velocidade_carregado_kmh, s.velocidade_vazio_kmh) == (60, 70)
    assert s.vagas_descarga == 3 and s.fator_tempo == 10 and s.meta_diaria_t == 4000
    assert s.seed == 42


def test_sobrescrita_por_ambiente(monkeypatch):
    monkeypatch.setenv("META_DIARIA_T", "5000")
    assert Settings().meta_diaria_t == 5000


def test_limites_de_alerta_do_spec():
    s = Settings()
    assert s.alerta_velocidade_max_kmh == 80 and s.alerta_parada_min == 15
    assert s.alerta_parada_velocidade_kmh == 5 and s.alerta_raio_local_m == 500
    assert s.alerta_desvio_m == 500 and s.alerta_desvio_leituras == 2
    assert s.alerta_atraso_tolerancia == 0.20
    assert s.eta_leituras == 10 and s.eta_velocidade_min_kmh == 20


def test_parametros_da_simulacao_incluem_parada(cliente):
    r = cliente.get("/simulacao/parametros").json()
    assert r["parada_min_min"] == 20 and r["parada_max_min"] == 40
