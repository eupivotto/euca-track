import rasterio
from shapely.geometry import Polygon, box

from app.areas import areas_eucalipto, para_geojson, selecionar_por_estrada, vetorizar
from app.config import Settings
from tests.conftest import FIXTURES

# Cobre todo o raster de teste; a fábrica fica no meio dele.
LIMITE = box(-52.1, -20.7, -51.6, -20.4)
FABRICA = (-51.886, -20.551)
# Pixel do raster de teste tem ~310 m: o fechamento precisa ser maior para unir vizinhos.
AJUSTE = {"areas_fecho_m": 200}


def pedacos(classe: int = 9) -> list[Polygon]:
    with rasterio.open(FIXTURES / "raster_teste.tif") as src:
        return vetorizar(src.read(1), src.transform, classe)


def gerar(limite=LIMITE, fabrica=FABRICA, **ajustes):
    return areas_eucalipto(pedacos(), limite, fabrica, Settings(**{**AJUSTE, **ajustes}))


def dentro(area, oeste, sul, leste, norte) -> bool:
    return box(oeste, sul, leste, norte).contains(area.centro)


def test_vetorizar_so_a_classe_pedida():
    pastagem = box(-51.814, -20.599, -51.787, -20.572)  # bloco da classe 15
    assert pedacos()
    assert not any(p.intersects(pastagem.buffer(-0.001)) for p in pedacos(9))
    assert any(p.intersects(pastagem) for p in pedacos(15))


def test_area_minima_descarta_pedaco_pequeno():
    areas = gerar(areas_maximo=50)
    assert not any(dentro(a, -51.815, -20.516, -51.805, -20.505) for a in areas)


def test_vizinhos_separados_por_um_pixel_viram_uma_area():
    areas = gerar(areas_maximo=50)
    par = [a for a in areas if dentro(a, -51.815, -20.555, -51.78, -20.538)]
    assert len(par) == 1 and par[0].area_ha >= 500


def test_no_maximo_8_maiores_em_ordem():
    areas = gerar()
    assert len(areas) == 8
    tamanhos = [a.area_ha for a in areas]
    assert tamanhos == sorted(tamanhos, reverse=True)
    assert min(tamanhos) >= 500


def test_nomes_genericos():
    assert [a.nome for a in gerar()] == [f"Área de eucalipto {i:02d}" for i in range(1, 9)]


def test_corte_pelo_limite_guarda_a_maior_parte():
    # Uma faixa fora do limite corta o primeiro bloco: 3 colunas a oeste, 4 a leste.
    limite = LIMITE.difference(box(-51.985, -20.6, -51.982, -20.4))
    areas = gerar(limite=limite, areas_min_ha=100, areas_maximo=50)
    bloco = [a for a in areas if a.geom.intersects(box(-51.994, -20.53, -51.970, -20.506))]
    assert len(bloco) == 1
    assert bloco[0].geom.geom_type == "Polygon"
    assert bloco[0].geom.bounds[0] >= -51.9825
    assert all(limite.buffer(1e-6).contains(a.geom) for a in areas)


def test_raio_da_fabrica():
    assert gerar(fabrica=(-51.0, -20.0), areas_raio_km=1) == []


def test_menos_de_8_devolve_as_que_houver():
    assert len(gerar(areas_min_ha=1150)) == 3


def test_centro_dentro_da_area_em_U():
    u = box(-52.0, -20.53, -51.97, -20.5).difference(box(-51.995, -20.525, -51.975, -20.5))
    areas = areas_eucalipto([u], LIMITE, FABRICA, Settings(areas_min_ha=100))
    assert len(areas) == 1
    assert not u.contains(u.centroid)
    assert areas[0].centro.within(areas[0].geom)


def test_para_geojson():
    dados = para_geojson(gerar())
    assert dados["type"] == "FeatureCollection" and len(dados["features"]) == 8
    primeira = dados["features"][0]
    assert primeira["geometry"]["type"] == "Polygon"
    assert primeira["properties"]["nome"] == "Área de eucalipto 01"
    assert primeira["properties"]["area_ha"] >= 500
    assert len(primeira["properties"]["centro"]) == 2


def test_para_geojson_arredonda_a_5_casas():
    # ~1 m de precisão: o arquivo vai para o painel e para o celular a cada carga.
    anel = para_geojson(gerar())["features"][0]["geometry"]["coordinates"][0]
    assert all(round(v, 5) == v for ponto in anel for v in ponto)


def test_selecao_por_estrada_pula_quem_passa_do_raio():
    candidatas = gerar(areas_maximo=50)
    estrada = {candidatas[0].nome: 216.0, candidatas[2].nome: None}  # None: sem rota, vale a linha reta
    escolhidas = selecionar_por_estrada(candidatas, lambda a: estrada.get(a.nome, 80.0), Settings())
    assert len(escolhidas) == 8
    assert escolhidas[0].geom.equals(candidatas[1].geom)  # a maior ficou de fora
    assert escolhidas[1].geom.equals(candidatas[2].geom)
    assert [a.nome for a in escolhidas] == [f"Área de eucalipto {i:02d}" for i in range(1, 9)]


def test_selecao_por_estrada_para_ao_completar_o_maximo():
    consultadas = []

    def estrada(area):
        consultadas.append(area.nome)
        return 50.0

    escolhidas = selecionar_por_estrada(gerar(areas_maximo=50), estrada, Settings(areas_maximo=3))
    assert len(escolhidas) == 3 and len(consultadas) == 3  # não consulta o OSRM à toa
