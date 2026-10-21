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
