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


def test_migracao_cria_alertas_e_colunas_de_trecho(sessao):
    insp = inspect(sessao.connection())
    assert {"tipo", "caminhao_id", "fazenda_id", "foco_id", "mensagem", "aberto_em",
            "fechado_em", "status"} <= {c["name"] for c in insp.get_columns("alertas")}
    assert {"inicio_trecho", "eta_prevista", "eta_atual"} <= {
        c["name"] for c in insp.get_columns("caminhoes")
    }
    assert "ix_posicoes_momento" in {i["name"] for i in insp.get_indexes("posicoes")}


def test_um_alerta_aberto_por_tipo_e_caminhao(sessao, semeado):
    from datetime import datetime, timezone

    import pytest
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError

    from app.modelos import Alerta, Caminhao

    caminhao_id = sessao.scalars(select(Caminhao.id)).first()
    agora = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)

    def alerta(status):
        return Alerta(tipo="VELOCIDADE", caminhao_id=caminhao_id, mensagem="85 km/h",
                      aberto_em=agora, status=status)

    # Um aberto e um fechado do mesmo tipo convivem.
    sessao.add_all([alerta("FECHADO"), alerta("ABERTO")])
    sessao.flush()
    sessao.add(alerta("ABERTO"))
    with pytest.raises(IntegrityError):
        sessao.flush()
