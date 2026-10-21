from sqlalchemy import inspect, text


def test_tabelas_da_fase_1_existem(sessao):
    nomes = set(inspect(sessao.connection()).get_table_names())
    assert {"fabrica", "fazendas", "motoristas", "caminhoes", "rotas",
            "viagens", "eventos_viagem", "posicoes"} <= nomes


def test_geometrias_em_4326(sessao):
    srid = sessao.execute(text("SELECT Find_SRID('public', 'fazendas', 'geom')")).scalar()
    assert srid == 4326


def test_indice_de_posicoes(sessao):
    idx = {i["name"] for i in inspect(sessao.connection()).get_indexes("posicoes")}
    assert "ix_posicoes_caminhao_momento" in idx
