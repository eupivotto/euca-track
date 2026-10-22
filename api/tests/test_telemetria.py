from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, func, select

from app.modelos import Caminhao, EventoViagem, Fazenda, Posicao, Rota, Viagem
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


# Rota da fixture semeado_com_rota: de INICIO_ROTA (fazenda) a FIM_ROTA (fábrica), 54,2 km.
INICIO_ROTA = (-51.95, -20.95)
FIM_ROTA = (-51.76, -20.62)
MEIO_ROTA = (-51.855, -20.785)


def leitura_json_em(caminhao_id, fazenda_id, estado, minuto, ponto=MEIO_ROTA, vel=60.0):
    lon, lat = ponto
    return {**leitura_json(caminhao_id, fazenda_id, estado, minuto, vel), "lon": lon, "lat": lat}


def leitura_em(caminhao_id, fazenda_id, estado, minuto, ponto=MEIO_ROTA, vel=60.0):
    return LeituraEntrada(**leitura_json_em(caminhao_id, fazenda_id, estado, minuto, ponto, vel))


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
    assert r.status_code == 200 and r.json()["recebidas"] == 3


def test_websocket_recebe_caminhao(cliente, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    with cliente.websocket_connect("/ws/frota") as ws:
        cliente.post("/telemetria", json=[leitura_json(c, f, "CARREGANDO", 0)], headers=CABECALHO)
        msg = ws.receive_json()
    assert msg["tipo"] == "caminhao"
    assert msg["caminhao"]["id"] == c and msg["caminhao"]["placa"].startswith("TLG")
    assert msg["caminhao"]["estado_atual"] == "CARREGANDO"
    assert msg["caminhao"]["posicao"]["velocidade_kmh"] == 0


def test_entrar_em_transito_define_trecho_e_previsto(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    registrar_leituras(sessao, [leitura(c, f, "CARREGANDO", 0)])
    registrar_leituras(sessao, [leitura_em(c, f, "EM_TRANSITO_CARREGADO", 10, INICIO_ROTA)])
    cam = sessao.get(Caminhao, c)
    assert cam.inicio_trecho == INICIO + timedelta(minutes=10)
    # 54,2 km a 60 km/h (velocidade configurada do carregado)
    assert cam.eta_prevista == cam.inicio_trecho + timedelta(minutes=54.2)
    assert cam.viagem_atual.eta_prevista == cam.eta_prevista


def test_previsto_nao_muda_dentro_do_trecho(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    registrar_leituras(sessao, [leitura_em(c, f, "EM_TRANSITO_CARREGADO", 0, INICIO_ROTA)])
    previsto = sessao.get(Caminhao, c).eta_prevista
    registrar_leituras(sessao, [leitura_em(c, f, "EM_TRANSITO_CARREGADO", 5, vel=30)])
    cam = sessao.get(Caminhao, c)
    assert cam.eta_prevista == previsto and cam.inicio_trecho == INICIO


def test_eta_atual_pela_distancia_restante(sessao, ids):
    # Na metade da rota a 54,2 km/h: faltam 27,1 km, 30 min.
    c, f = ids["caminhoes"][0], ids["fazenda"]
    registrar_leituras(sessao, [leitura_em(c, f, "EM_TRANSITO_CARREGADO", 0, MEIO_ROTA, vel=54.2)])
    cam = sessao.get(Caminhao, c)
    assert abs((cam.eta_atual - (INICIO + timedelta(minutes=30))).total_seconds()) < 60


def test_eta_ignora_leituras_de_antes_do_trecho(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    for m in range(5):
        registrar_leituras(sessao, [leitura_em(c, f, "CARREGANDO", m, INICIO_ROTA, vel=0)])
    registrar_leituras(sessao, [leitura_em(c, f, "EM_TRANSITO_CARREGADO", 5, MEIO_ROTA, vel=54.2)])
    cam = sessao.get(Caminhao, c)
    # Com as leituras paradas na média, a velocidade cairia ao mínimo (20 km/h) e o ETA para +81 min.
    assert abs((cam.eta_atual - (INICIO + timedelta(minutes=35))).total_seconds()) < 60


def test_eta_usa_so_as_ultimas_leituras(sessao, ids, settings):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    registrar_leituras(sessao, [leitura_em(c, f, "EM_TRANSITO_CARREGADO", 0, INICIO_ROTA, vel=10)])
    for m in range(1, settings.eta_leituras + 1):
        registrar_leituras(sessao, [leitura_em(c, f, "EM_TRANSITO_CARREGADO", m, MEIO_ROTA, vel=54.2)])
    cam = sessao.get(Caminhao, c)
    momento = INICIO + timedelta(minutes=settings.eta_leituras)
    assert abs((cam.eta_atual - (momento + timedelta(minutes=30))).total_seconds()) < 60


def test_sair_do_transito_limpa_o_trecho(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    registrar_leituras(sessao, [leitura_em(c, f, "EM_TRANSITO_CARREGADO", 0)])
    registrar_leituras(sessao, [leitura_em(c, f, "FILA_PATIO", 10, FIM_ROTA, vel=0)])
    cam = sessao.get(Caminhao, c)
    assert (cam.inicio_trecho, cam.eta_prevista, cam.eta_atual) == (None, None, None)


def test_trecho_sem_rota_fica_sem_eta(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    sessao.execute(delete(Rota).where(Rota.fazenda_id == f))
    registrar_leituras(sessao, [leitura_em(c, f, "EM_TRANSITO_CARREGADO", 0)])
    cam = sessao.get(Caminhao, c)
    assert cam.inicio_trecho == INICIO and cam.eta_prevista is None and cam.eta_atual is None


def test_vazio_usa_a_rota_ao_contrario(sessao, ids):
    # Vazio saindo da fábrica (fim da linha): falta a rota inteira, a 70 km/h previstos.
    c, f = ids["caminhoes"][0], ids["fazenda"]
    registrar_leituras(sessao, [leitura_em(c, f, "EM_TRANSITO_VAZIO", 0, FIM_ROTA, vel=54.2)])
    cam = sessao.get(Caminhao, c)
    assert abs((cam.eta_atual - (INICIO + timedelta(minutes=60))).total_seconds()) < 60
    assert cam.eta_prevista == INICIO + timedelta(minutes=54.2 / 70 * 60)


def test_caminhao_saida_tem_eta_e_fazenda(cliente, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    corpo = [leitura_json(c, f, "CARREGANDO", 0), leitura_json_em(c, f, "EM_TRANSITO_CARREGADO", 1)]
    cliente.post("/telemetria", json=corpo, headers=CABECALHO)
    saida = next(x for x in cliente.get("/caminhoes").json() if x["id"] == c)
    assert saida["eta"] is not None and saida["fazenda"].startswith("Área de eucalipto")


def test_leitura_grava_fazenda_de_destino(sessao, ids):
    c = ids["caminhoes"][0]
    registrar_leituras(sessao, [leitura(c, ids["fazenda"], "CARREGANDO", 0)])
    registrar_leituras(sessao, [leitura(c, ids["outra_fazenda"], "EM_TRANSITO_VAZIO", 10)])
    caminhao = sessao.get(Caminhao, c)
    assert caminhao.fazenda_destino_id == ids["outra_fazenda"]
    assert caminhao.viagem_atual.fazenda_id == ids["fazenda"]
