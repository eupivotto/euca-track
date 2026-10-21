from datetime import timedelta

from sqlalchemy import select

from app.modelos import Alerta
from app.telemetria import registrar_leituras
from tests.test_telemetria import (  # noqa: F401  (ids é fixture)
    CABECALHO,
    FIM_ROTA,
    INICIO,
    INICIO_ROTA,
    MEIO_ROTA,
    ids,
    leitura_em,
    leitura_json_em,
)

# ~2 km antes da fábrica, sobre a rota: longe de fazenda e fábrica (> 500 m).
PERTO_DO_FIM = (-51.769, -20.636)
# ~900 m a leste do meio da rota.
FORA_DA_ROTA = (MEIO_ROTA[0] + 0.0096, MEIO_ROTA[1])


def alertas(sessao, tipo=None):
    consulta = select(Alerta).order_by(Alerta.id)
    if tipo:
        consulta = consulta.where(Alerta.tipo == tipo)
    return sessao.scalars(consulta).all()


def enviar(sessao, c, f, estado, minuto, ponto=MEIO_ROTA, vel=60.0):
    return registrar_leituras(sessao, [leitura_em(c, f, estado, minuto, ponto, vel)])


def test_alerta_abre_uma_vez_enquanto_aberto(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    for m in range(3):
        enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", m, vel=85)
    assert [a.status for a in alertas(sessao, "VELOCIDADE")] == ["ABERTO"]


def test_alerta_fecha_quando_a_condicao_passa(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 0, vel=85)
    enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 1, vel=70)
    [alerta] = alertas(sessao, "VELOCIDADE")
    assert alerta.status == "FECHADO" and alerta.fechado_em == INICIO + timedelta(minutes=1)


def test_alerta_reabre_depois_de_fechado(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    for m, vel in enumerate([85, 70, 85]):
        enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", m, vel=vel)
    assert [a.status for a in alertas(sessao, "VELOCIDADE")] == ["FECHADO", "ABERTO"]


def test_alerta_fecha_ao_sair_do_transito(sessao, ids):
    # A 10 km/h a média cai ao mínimo de 20 km/h: 54,2 km levariam 163 min, previstos 54.
    c, f = ids["caminhoes"][0], ids["fazenda"]
    enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 0, INICIO_ROTA, vel=10)
    assert [a.status for a in alertas(sessao, "ATRASO")] == ["ABERTO"]
    enviar(sessao, c, f, "FILA_PATIO", 60, FIM_ROTA, vel=0)
    assert [a.status for a in alertas(sessao, "ATRASO")] == ["FECHADO"]
    # Na viagem seguinte, o trecho novo não herda o atraso.
    enviar(sessao, c, f, "EM_TRANSITO_VAZIO", 100, FIM_ROTA, vel=70)
    assert [a.status for a in alertas(sessao, "ATRASO")] == ["FECHADO"]


def test_parada_pela_sequencia_de_leituras(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 0, PERTO_DO_FIM, vel=60)
    # Parado a partir de 0,5 min, uma leitura a cada 30 s.
    for i in range(1, 34):
        enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", i / 2, PERTO_DO_FIM, vel=0)
    [alerta] = alertas(sessao, "PARADA")
    # Parado desde 0,5 min: passa de 15 min na leitura de 16 min.
    assert alerta.aberto_em == INICIO + timedelta(minutes=16)
    assert alerta.mensagem == "Parado há 16 min fora de fazenda ou fábrica"


def test_parada_volta_a_andar_fecha(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    for i in range(0, 40):
        enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", i / 2, PERTO_DO_FIM, vel=0)
    enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 20, PERTO_DO_FIM, vel=50)
    assert [a.status for a in alertas(sessao, "PARADA")] == ["FECHADO"]


def test_desvio_com_duas_leituras_fora_da_rota(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 0, MEIO_ROTA)
    enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 1, FORA_DA_ROTA)
    assert alertas(sessao, "DESVIO_ROTA") == []
    enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 2, FORA_DA_ROTA)
    [alerta] = alertas(sessao, "DESVIO_ROTA")
    assert alerta.status == "ABERTO" and alerta.mensagem.startswith("A ")
    assert alerta.mensagem.endswith(" m da rota")


def test_lote_devolve_alertas_que_mudaram(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    lote = enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 0, vel=85)
    assert lote.caminhoes == [c]
    assert lote.alertas == [alertas(sessao, "VELOCIDADE")[0].id]
    assert enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 1, vel=85).alertas == []


def test_websocket_recebe_alerta(cliente, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    with cliente.websocket_connect("/ws/frota") as ws:
        corpo = [leitura_json_em(c, f, "EM_TRANSITO_CARREGADO", 0, vel=85)]
        cliente.post("/telemetria", json=corpo, headers=CABECALHO)
        mensagens = [ws.receive_json(), ws.receive_json()]
    assert [m["tipo"] for m in mensagens] == ["caminhao", "alerta"]
    assert mensagens[0]["caminhao"]["alertas_abertos"] == ["VELOCIDADE"]
    alerta = mensagens[1]["alerta"]
    assert alerta["mensagem"] == "85 km/h" and alerta["status"] == "ABERTO"
    assert alerta["caminhao_id"] == c and alerta["placa"].startswith("TLG")


def test_get_alertas_filtra_por_status_e_tipo(cliente, sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    d = ids["caminhoes"][1]
    enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 0, vel=85)
    enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 1, vel=70)  # fecha
    enviar(sessao, d, f, "EM_TRANSITO_CARREGADO", 2, vel=90)
    abertos = cliente.get("/alertas?status=ABERTO").json()
    assert [(a["caminhao_id"], a["tipo"]) for a in abertos] == [(d, "VELOCIDADE")]
    assert len(cliente.get("/alertas?tipo=VELOCIDADE").json()) == 2
    assert cliente.get("/alertas?tipo=PARADA").json() == []
    # Mais recentes primeiro.
    assert [a["caminhao_id"] for a in cliente.get("/alertas").json()] == [d, c]
