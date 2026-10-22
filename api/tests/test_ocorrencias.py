import pytest
from sqlalchemy import func, select

from app.config import Settings, get_settings
from app.main import app
from app.modelos import Ocorrencia
from tests.test_rotas_motorista import em
from tests.test_telemetria import ids  # noqa: F401  (ids é fixture)

# Cabeçalho mínimo de um PNG: o conteúdo não é validado, só o tipo declarado.
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture
def pasta(tmp_path):
    app.dependency_overrides[get_settings] = lambda: Settings(pasta_fotos=str(tmp_path))
    yield tmp_path
    app.dependency_overrides.pop(get_settings, None)


def enviar(cliente, c, id_local="o1", tipo="PNEU", foto=None):
    dados = {"caminhao_id": str(c), "tipo": tipo, "descricao": "Pneu furado", "id_local": id_local}
    arquivos = {"foto": foto} if foto else None
    return cliente.post("/ocorrencias", data=dados, files=arquivos)


def test_ocorrencia_com_foto(cliente, sessao, ids, pasta):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "EM_TRANSITO_CARREGADO", 0)
    r = enviar(cliente, c, foto=("pneu.png", PNG, "image/png"))
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["tipo"] == "PNEU" and corpo["descricao"] == "Pneu furado"
    assert corpo["placa"].startswith("TLG") and corpo["viagem_id"] is not None
    assert corpo["foto_url"] == f"/ocorrencias/{corpo['id']}/foto"
    assert len(list(pasta.iterdir())) == 1
    foto = cliente.get(corpo["foto_url"])
    assert foto.status_code == 200 and foto.content == PNG
    assert foto.headers["content-type"] == "image/png"


def test_ocorrencia_sem_foto(cliente, sessao, ids, pasta):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "EM_TRANSITO_CARREGADO", 0)
    corpo = enviar(cliente, c).json()
    assert corpo["foto_url"] is None
    assert cliente.get(f"/ocorrencias/{corpo['id']}/foto").status_code == 404


def test_ocorrencia_repetida_pelo_id_local_nao_duplica(cliente, sessao, ids, pasta):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "EM_TRANSITO_CARREGADO", 0)
    primeiro = enviar(cliente, c, foto=("pneu.png", PNG, "image/png"))
    segundo = enviar(cliente, c, foto=("pneu.png", PNG, "image/png"))
    assert (primeiro.status_code, segundo.status_code) == (201, 200)
    assert primeiro.json() == segundo.json()
    assert sessao.scalar(select(func.count()).select_from(Ocorrencia)) == 1
    assert len(list(pasta.iterdir())) == 1


def test_foto_de_outro_tipo_415(cliente, sessao, ids, pasta):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "EM_TRANSITO_CARREGADO", 0)
    r = enviar(cliente, c, foto=("nota.pdf", b"%PDF", "application/pdf"))
    assert r.status_code == 415 and r.json()["detail"] == "A foto precisa ser JPEG, PNG ou WebP"


def test_foto_grande_demais_413(cliente, sessao, ids, tmp_path):
    app.dependency_overrides[get_settings] = lambda: Settings(
        pasta_fotos=str(tmp_path), foto_max_mb=0.00001
    )
    try:
        c, f = ids["caminhoes"][0], ids["fazenda"]
        em(sessao, c, f, "EM_TRANSITO_CARREGADO", 0)
        r = enviar(cliente, c, foto=("pneu.png", PNG, "image/png"))
    finally:
        app.dependency_overrides.pop(get_settings, None)
    assert r.status_code == 413 and r.json()["detail"] == "A foto passa de 1e-05 MB"
    assert list(tmp_path.iterdir()) == []


def test_tipo_invalido_422(cliente, sessao, ids, pasta):
    assert enviar(cliente, ids["caminhoes"][0], tipo="CHUVA").status_code == 422


def test_caminhao_inexistente_404(cliente, ids, pasta):
    assert enviar(cliente, 999999).status_code == 404


def test_lista_filtra_por_caminhao_mais_recentes_primeiro(cliente, sessao, ids, pasta):
    c, d, f = ids["caminhoes"][0], ids["caminhoes"][1], ids["fazenda"]
    em(sessao, c, f, "EM_TRANSITO_CARREGADO", 0)
    em(sessao, d, f, "EM_TRANSITO_CARREGADO", 0)
    enviar(cliente, c, "l1")
    em(sessao, c, f, "EM_TRANSITO_CARREGADO", 5)
    enviar(cliente, c, "l2", tipo="MECANICA")
    enviar(cliente, d, "l3")
    lista = cliente.get(f"/ocorrencias?caminhao_id={c}").json()
    assert [o["tipo"] for o in lista] == ["MECANICA", "PNEU"]
    viagem = lista[0]["viagem_id"]
    assert len(cliente.get(f"/ocorrencias?viagem_id={viagem}").json()) == 2


def test_websocket_recebe_ocorrencia(cliente, sessao, ids, pasta):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    em(sessao, c, f, "EM_TRANSITO_CARREGADO", 0)
    with cliente.websocket_connect("/ws/frota") as ws:
        enviar(cliente, c)
        mensagem = ws.receive_json()
    assert mensagem["tipo"] == "ocorrencia"
    assert mensagem["ocorrencia"]["caminhao_id"] == c
