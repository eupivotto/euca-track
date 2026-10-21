from sim.estados import Estado, proximo_estado


def test_ciclo_na_ordem_do_spec():
    e, vistos = Estado.CARREGANDO, []
    for _ in range(6):
        vistos.append(e)
        e = proximo_estado(e)
    assert vistos == ["CARREGANDO", "EM_TRANSITO_CARREGADO", "FILA_PATIO", "PESAGEM",
                      "DESCARGA", "EM_TRANSITO_VAZIO"]
    assert e == Estado.CARREGANDO
