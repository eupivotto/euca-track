from app.tempo_real import Difusor


class WsFalso:
    def __init__(self, falha: bool = False):
        self.falha = falha
        self.recebidas: list[dict] = []

    async def accept(self):
        pass

    async def send_json(self, mensagem: dict):
        if self.falha:
            raise RuntimeError("conexão fechada")
        self.recebidas.append(mensagem)


async def test_broadcast_entrega_para_todos():
    a, b = WsFalso(), WsFalso()
    d = Difusor()
    await d.conectar(a)
    await d.conectar(b)
    await d.difundir({"tipo": "caminhao"})
    assert a.recebidas == b.recebidas == [{"tipo": "caminhao"}]


async def test_broadcast_descarta_conexao_morta():
    viva, morta = WsFalso(), WsFalso(falha=True)
    d = Difusor()
    await d.conectar(viva)
    await d.conectar(morta)
    await d.difundir({"tipo": "caminhao"})
    assert viva.recebidas == [{"tipo": "caminhao"}]
    assert morta not in d.conexoes


async def test_desconectar_remove():
    ws = WsFalso()
    d = Difusor()
    await d.conectar(ws)
    d.desconectar(ws)
    d.desconectar(ws)  # duas vezes não quebra
    assert d.conexoes == set()
