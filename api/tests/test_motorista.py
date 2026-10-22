import pytest

from app.motorista import Acao, Passo, erro_checkin, passo_atual

INICIO, FIM = Acao.INICIO_CARREGAMENTO, Acao.FIM_CARREGAMENTO


def test_checkin_exige_caminhao_assumido():
    assert erro_checkin("CARREGANDO", False, set(), INICIO) == "A posse do caminhão expirou enquanto o app estava sem contato. Faça de novo se ele ainda estiver na fazenda"


def test_inicio_so_na_fazenda():
    assert erro_checkin("EM_TRANSITO_VAZIO", True, set(), INICIO) == "O caminhão não está na fazenda"


def test_inicio_repetido():
    assert erro_checkin("CARREGANDO", True, {INICIO}, INICIO) == "O carregamento já foi iniciado"


def test_fim_sem_inicio():
    assert erro_checkin("CARREGANDO", True, set(), FIM) == "Inicie o carregamento antes de finalizar"


def test_fim_repetido():
    assert erro_checkin("CARREGANDO", True, {INICIO, FIM}, FIM) == "O carregamento já foi finalizado"


def test_fim_fora_da_fazenda():
    assert erro_checkin("EM_TRANSITO_CARREGADO", True, {INICIO}, FIM) == "O caminhão não está na fazenda"


def test_caminhos_validos():
    assert erro_checkin("CARREGANDO", True, set(), INICIO) is None
    assert erro_checkin("CARREGANDO", True, {INICIO}, FIM) is None


@pytest.mark.parametrize(
    ("estado", "feitas", "passo"),
    [
        (None, set(), Passo.INDO_PARA_FAZENDA),
        ("EM_TRANSITO_VAZIO", set(), Passo.INDO_PARA_FAZENDA),
        ("CARREGANDO", set(), Passo.INICIAR_CARREGAMENTO),
        ("CARREGANDO", {INICIO}, Passo.FINALIZAR_CARREGAMENTO),
        ("CARREGANDO", {INICIO, FIM}, Passo.AGUARDANDO_SAIDA),
        ("EM_TRANSITO_CARREGADO", {INICIO, FIM}, Passo.INDO_PARA_FABRICA),
        ("FILA_PATIO", set(), Passo.NA_FABRICA),
        ("PESAGEM", set(), Passo.NA_FABRICA),
        ("DESCARGA", set(), Passo.NA_FABRICA),
    ],
)
def test_passo_atual(estado, feitas, passo):
    assert passo_atual(estado, feitas) == passo
