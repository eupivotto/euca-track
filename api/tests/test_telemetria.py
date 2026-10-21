from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.modelos import Caminhao, EventoViagem, Fazenda, Posicao, Viagem
from app.telemetria import CaminhaoDesconhecido, LeituraEntrada, registrar_leituras

INICIO = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)
CABECALHO = {"X-Token": "dev-token"}


@pytest.fixture
def ids(semeado_com_rota):
    caminhoes = semeado_com_rota.scalars(select(Caminhao.id).order_by(Caminhao.id)).all()
    fazendas = semeado_com_rota.scalars(select(Fazenda.id).order_by(Fazenda.id)).all()
    return {"caminhoes": caminhoes, "fazenda": fazendas[0], "outra_fazenda": fazendas[1]}


def leitura_json(caminhao_id, fazenda_id, estado, minuto, velocidade=0.0):
    return {
        "caminhao_id": caminhao_id,
        "fazenda_id": fazenda_id,
        "estado": estado,
        "lon": -51.9,
        "lat": -20.9,
        "velocidade_kmh": velocidade,
        "momento": (INICIO + timedelta(minutes=minuto)).isoformat(),
    }


def leitura(caminhao_id, fazenda_id, estado, minuto):
    return LeituraEntrada(**leitura_json(caminhao_id, fazenda_id, estado, minuto))


def contar(sessao, modelo):
    return sessao.scalar(select(func.count()).select_from(modelo))


def test_ciclo_completo_gera_viagem_e_eventos(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    estados = ["CARREGANDO", "EM_TRANSITO_CARREGADO", "FILA_PATIO", "PESAGEM",
               "DESCARGA", "EM_TRANSITO_VAZIO", "CARREGANDO"]
    for i, e in enumerate(estados):
        registrar_leituras(sessao, [leitura(c, f, e, i * 10)])
    viagens = sessao.scalars(select(Viagem).order_by(Viagem.id)).all()
    assert [v.status for v in viagens] == ["CONCLUIDA", "EM_ANDAMENTO"]
    assert viagens[0].toneladas == 55 and viagens[0].rota_id is not None
    assert viagens[0].fim == INICIO + timedelta(minutes=60)
    assert [e.estado for e in viagens[0].eventos] == estados[:6]
    assert sessao.get(Caminhao, c).viagem_atual_id == viagens[1].id


def test_leituras_repetidas_nao_geram_eventos(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    for m in range(3):
        registrar_leituras(sessao, [leitura(c, f, "EM_TRANSITO_CARREGADO", m)])
    assert contar(sessao, EventoViagem) == 1
    assert contar(sessao, Posicao) == 3


def test_reinicio_mesmo_estado_nao_duplica_viagem(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    registrar_leituras(sessao, [leitura(c, f, "CARREGANDO", 0)])
    registrar_leituras(sessao, [leitura(c, f, "CARREGANDO", 1)])  # simulador reiniciado
    assert contar(sessao, Viagem) == 1


def test_reinicio_durante_descarga_interrompe_viagem(sessao, ids):
    # Simulador reiniciado com o caminhão na descarga: a carga não foi entregue.
    c, f = ids["caminhoes"][0], ids["fazenda"]
    for i, e in enumerate(["CARREGANDO", "EM_TRANSITO_CARREGADO", "DESCARGA", "CARREGANDO"]):
        registrar_leituras(sessao, [leitura(c, f, e, i * 10)])
    viagens = sessao.scalars(select(Viagem).order_by(Viagem.id)).all()
    assert [v.status for v in viagens] == ["INTERROMPIDA", "EM_ANDAMENTO"]


def test_reinicio_carregando_em_outra_fazenda_abre_viagem_nova(sessao, ids):
    c = ids["caminhoes"][0]
    registrar_leituras(sessao, [leitura(c, ids["fazenda"], "CARREGANDO", 0)])
    registrar_leituras(sessao, [leitura(c, ids["outra_fazenda"], "CARREGANDO", 1)])
    viagens = sessao.scalars(select(Viagem).order_by(Viagem.id)).all()
    assert [v.status for v in viagens] == ["INTERROMPIDA", "EM_ANDAMENTO"]
    assert viagens[1].fazenda_id == ids["outra_fazenda"]
    assert sessao.get(Caminhao, c).viagem_atual_id == viagens[1].id


def test_primeira_leitura_no_meio_do_ciclo_abre_viagem(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    registrar_leituras(sessao, [leitura(c, f, "FILA_PATIO", 0)])
    caminhao = sessao.get(Caminhao, c)
    assert caminhao.viagem_atual_id is not None and caminhao.estado_atual == "FILA_PATIO"


def test_posicao_fica_na_viagem_nova(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    registrar_leituras(sessao, [leitura(c, f, "CARREGANDO", 0)])
    registrar_leituras(sessao, [leitura(c, f, "EM_TRANSITO_VAZIO", 10)])
    registrar_leituras(sessao, [leitura(c, f, "CARREGANDO", 20)])
    ultima = sessao.scalars(select(Posicao).order_by(Posicao.momento.desc())).first()
    assert ultima.viagem_id == sessao.get(Caminhao, c).viagem_atual_id


def test_caminhao_desconhecido_levanta_antes_de_gravar(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    with pytest.raises(CaminhaoDesconhecido):
        registrar_leituras(sessao, [leitura(c, f, "CARREGANDO", 0), leitura(999_999, f, "CARREGANDO", 0)])
    assert contar(sessao, Posicao) == 0


def test_token_errado_401(cliente, ids):
    r = cliente.post("/telemetria", json=[], headers={"X-Token": "x"})
    assert r.status_code == 401


def test_sem_token_401(cliente, ids):
    assert cliente.post("/telemetria", json=[]).status_code == 401


def test_caminhao_desconhecido_422_sem_gravar(cliente, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    corpo = [leitura_json(c, f, "CARREGANDO", 0), leitura_json(999_999, f, "CARREGANDO", 0)]
    r = cliente.post("/telemetria", json=corpo, headers=CABECALHO)
    assert r.status_code == 422
    assert cliente.get("/caminhoes").json()[0]["posicao"] is None


def test_estado_invalido_422(cliente, ids):
    corpo = [leitura_json(ids["caminhoes"][0], ids["fazenda"], "VOANDO", 0)]
    assert cliente.post("/telemetria", json=corpo, headers=CABECALHO).status_code == 422


def test_post_responde_quantas_recebeu(cliente, ids):
    corpo = [leitura_json(c, ids["fazenda"], "CARREGANDO", 0) for c in ids["caminhoes"][:3]]
    r = cliente.post("/telemetria", json=corpo, headers=CABECALHO)
    assert r.status_code == 200 and r.json() == {"recebidas": 3}


def test_websocket_recebe_caminhao(cliente, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    with cliente.websocket_connect("/ws/frota") as ws:
        cliente.post("/telemetria", json=[leitura_json(c, f, "CARREGANDO", 0)], headers=CABECALHO)
        msg = ws.receive_json()
    assert msg["tipo"] == "caminhao"
    assert msg["caminhao"]["id"] == c and msg["caminhao"]["placa"].startswith("TLG")
    assert msg["caminhao"]["estado_atual"] == "CARREGANDO"
    assert msg["caminhao"]["posicao"]["velocidade_kmh"] == 0
