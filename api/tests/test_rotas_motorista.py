from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.modelos import Checkin
from app.telemetria import registrar_leituras
from tests.test_telemetria import INICIO, ids, leitura  # noqa: F401  (ids é fixture)


def em(sessao, c, f, estado, minuto):
    registrar_leituras(sessao, [leitura(c, f, estado, minuto)])
    sessao.flush()


def checkin(cliente, c, acao, id_local):
    return cliente.post(
        "/motorista/checkin", json={"caminhao_id": c, "acao": acao, "id_local": id_local}
    )


def caminhao_no_painel(cliente, c):
    return next(x for x in cliente.get("/caminhoes").json() if x["id"] == c)


def test_painel_de_caminhao_inexistente_404(cliente, ids):
    r = cliente.get("/motorista/caminhoes/999999")
    assert r.status_code == 404 and r.json()["detail"] == "Caminhão não encontrado"


def test_assumir_define_posse_pelo_relogio_simulado(cliente, sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "EM_TRANSITO_VAZIO", 0)
    painel = cliente.post("/motorista/assumir", json={"caminhao_id": c}).json()
    assert painel["assumido"] is True
    assert datetime.fromisoformat(painel["assumido_ate"]) == INICIO + timedelta(minutes=60)
    assert caminhao_no_painel(cliente, c)["assumido"] is True


def test_posse_expira(cliente, sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "EM_TRANSITO_VAZIO", 0)
    cliente.post("/motorista/assumir", json={"caminhao_id": c})
    em(sessao, c, f, "EM_TRANSITO_VAZIO", 61)
    assert caminhao_no_painel(cliente, c)["assumido"] is False
    assert cliente.get(f"/motorista/caminhoes/{c}").json()["assumido"] is False


def test_soltar_devolve_ao_simulador(cliente, sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "EM_TRANSITO_VAZIO", 0)
    cliente.post("/motorista/assumir", json={"caminhao_id": c})
    painel = cliente.post("/motorista/soltar", json={"caminhao_id": c}).json()
    assert painel["assumido"] is False and painel["assumido_ate"] is None


def test_checkin_inicio_e_fim_na_fazenda(cliente, sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "CARREGANDO", 0)
    cliente.post("/motorista/assumir", json={"caminhao_id": c})
    r = checkin(cliente, c, "INICIO_CARREGAMENTO", "a1")
    assert r.status_code == 201 and r.json()["acao"] == "INICIO_CARREGAMENTO"
    assert datetime.fromisoformat(r.json()["momento"]) == INICIO
    assert checkin(cliente, c, "FIM_CARREGAMENTO", "a2").status_code == 201
    painel = cliente.get(f"/motorista/caminhoes/{c}").json()
    assert painel["passo"] == "AGUARDANDO_SAIDA"
    assert [x["acao"] for x in painel["checkins"]] == ["INICIO_CARREGAMENTO", "FIM_CARREGAMENTO"]
    assert painel["viagem_id"] == r.json()["viagem_id"]


def test_checkin_repetido_pelo_id_local_nao_duplica(cliente, sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "CARREGANDO", 0)
    cliente.post("/motorista/assumir", json={"caminhao_id": c})
    primeiro = checkin(cliente, c, "INICIO_CARREGAMENTO", "repetido")
    segundo = checkin(cliente, c, "INICIO_CARREGAMENTO", "repetido")
    assert (primeiro.status_code, segundo.status_code) == (201, 200)
    assert primeiro.json() == segundo.json()
    assert sessao.scalar(select(func.count()).select_from(Checkin)) == 1


def test_checkin_sem_posse_409(cliente, sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "CARREGANDO", 0)
    r = checkin(cliente, c, "INICIO_CARREGAMENTO", "b1")
    assert r.status_code == 409 and r.json()["detail"] == "A posse do caminhão expirou enquanto o app estava sem contato. Faça de novo se ele ainda estiver na fazenda"


def test_checkin_de_caminhao_inexistente_404(cliente, ids):
    assert checkin(cliente, 999999, "INICIO_CARREGAMENTO", "c1").status_code == 404


def test_destino_e_a_fazenda_da_ultima_leitura(cliente, sessao, ids):
    c = ids["caminhoes"][0]
    em(sessao, c, ids["fazenda"], "CARREGANDO", 0)
    em(sessao, c, ids["outra_fazenda"], "EM_TRANSITO_VAZIO", 10)
    painel = cliente.get(f"/motorista/caminhoes/{c}").json()
    assert painel["destino"]["fazenda_id"] == ids["outra_fazenda"]
    assert painel["destino"]["nome"] and painel["destino"]["distancia_km"] > 0
    assert painel["passo"] == "INDO_PARA_FAZENDA"
    assert painel["caminhao"]["placa"].startswith("TLG")


def test_checkin_difunde_o_caminhao(cliente, sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "CARREGANDO", 0)
    with cliente.websocket_connect("/ws/frota") as ws:
        cliente.post("/motorista/assumir", json={"caminhao_id": c})
        mensagem = ws.receive_json()
        checkin(cliente, c, "INICIO_CARREGAMENTO", "d1")
        depois = ws.receive_json()
    assert mensagem["tipo"] == "caminhao" and mensagem["caminhao"]["assumido"] is True
    assert depois["tipo"] == "caminhao" and depois["caminhao"]["id"] == c


def telemetria(cliente, c, f, estado, minuto):
    from tests.test_telemetria import CABECALHO, leitura_json

    r = cliente.post("/telemetria", json=[leitura_json(c, f, estado, minuto)], headers=CABECALHO)
    assert r.status_code == 200
    return r.json()


def test_telemetria_devolve_assumidos(cliente, sessao, ids):
    c, d, f = ids["caminhoes"][0], ids["caminhoes"][1], ids["fazenda"]
    em(sessao, c, f, "EM_TRANSITO_VAZIO", 0)
    cliente.post("/motorista/assumir", json={"caminhao_id": c})
    r = telemetria(cliente, d, f, "EM_TRANSITO_VAZIO", 1)
    assert r == {"recebidas": 1, "assumidos": [c], "liberados": []}
    # Passada a posse (60 min simulados), o caminhão volta ao simulador.
    assert telemetria(cliente, d, f, "EM_TRANSITO_VAZIO", 61)["assumidos"] == []


def test_telemetria_libera_quem_finalizou_o_carregamento(cliente, sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "CARREGANDO", 0)
    cliente.post("/motorista/assumir", json={"caminhao_id": c})
    checkin(cliente, c, "INICIO_CARREGAMENTO", "e1")
    assert telemetria(cliente, c, f, "CARREGANDO", 1)["liberados"] == []
    checkin(cliente, c, "FIM_CARREGAMENTO", "e2")
    # Liberado mesmo depois que a posse expira.
    assert telemetria(cliente, c, f, "CARREGANDO", 90)["liberados"] == [c]


def test_viagem_seguinte_nao_herda_a_liberacao(cliente, sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "CARREGANDO", 0)
    cliente.post("/motorista/assumir", json={"caminhao_id": c})
    checkin(cliente, c, "INICIO_CARREGAMENTO", "g1")
    checkin(cliente, c, "FIM_CARREGAMENTO", "g2")
    for i, estado in enumerate(["EM_TRANSITO_CARREGADO", "FILA_PATIO", "PESAGEM", "DESCARGA",
                                "EM_TRANSITO_VAZIO"], start=1):
        assert telemetria(cliente, c, f, estado, i * 10)["liberados"] == []
    assert telemetria(cliente, c, f, "CARREGANDO", 60)["liberados"] == []
