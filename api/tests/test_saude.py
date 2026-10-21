def test_saude_com_banco(cliente):
    r = cliente.get("/saude")
    assert r.status_code == 200
    assert r.json() == {"api": "ok", "banco": "ok"}
