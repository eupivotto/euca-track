import json

from shapely.geometry import Point, shape

from app.config import Settings
from app.scripts.exportar_mapbiomas import ler_recorte
from app.scripts.gerar_areas_eucalipto import ARQUIVO_LIMITE, carregar_limite
from tests.conftest import FIXTURES

PIXEL = 0.003


def test_ler_recorte_devolve_so_a_janela():
    recorte = Settings(regiao_lon_min=-51.97, regiao_lon_max=-51.85, regiao_lat_min=-20.58, regiao_lat_max=-20.52)
    dados, transform, perfil = ler_recorte(str(FIXTURES / "raster_teste.tif"), recorte)
    linhas, colunas = dados.shape
    assert abs(linhas - 20) <= 1 and abs(colunas - 40) <= 1
    assert abs(transform.c - -51.97) <= PIXEL and abs(transform.f - -20.52) <= PIXEL
    assert perfil["width"] == colunas and perfil["height"] == linhas


def test_limite_ms_e_um_poligono_que_contem_tres_lagoas():
    limite = carregar_limite()
    assert limite.geom_type in {"Polygon", "MultiPolygon"}
    assert limite.contains(Point(-51.70, -20.75))
    assert not limite.contains(Point(-51.49, -20.87))  # Castilho/SP, do outro lado do rio
    assert shape(json.loads(ARQUIVO_LIMITE.read_text(encoding="utf-8"))["features"][0]["geometry"]).equals(limite)
