import pytest
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon

from app.geo import distancia_km, distancia_m, progresso_na_linha, quadrado_fazenda

para_utm_22s = Transformer.from_crs("EPSG:4326", "EPSG:31982", always_xy=True)


def test_quadrado_tem_a_area_informada():
    anel = quadrado_fazenda(-20.95, -51.95, 3200)
    area_m2 = Polygon([para_utm_22s.transform(lon, lat) for lon, lat in anel]).area
    assert area_m2 / 10_000 == pytest.approx(3200, rel=0.01)
    assert anel[0] == anel[-1] and len(anel) == 5


def test_quadrado_centrado_no_ponto():
    c = Polygon(quadrado_fazenda(-20.95, -51.95, 3200)).centroid
    assert (c.x, c.y) == pytest.approx((-51.95, -20.95), abs=1e-6)


def test_distancia_conhecida():
    # fábrica -> Fazenda Santa Luzia, em linha reta
    assert distancia_km((-51.76, -20.62), (-51.95, -20.95)) == pytest.approx(41.7, abs=0.5)


LINHA = LineString([(-51.95, -20.95), (-51.76, -20.62)])


def test_ponto_no_meio_da_linha():
    fracao, dist = progresso_na_linha(LINHA, Point(-51.855, -20.785))
    assert fracao == pytest.approx(0.5, abs=0.01) and dist < 5


def test_distancia_de_um_km_ao_norte():
    p = Point(-51.95, -20.95 + 1000 / 110_574)
    assert distancia_m(Point(-51.95, -20.95), p) == pytest.approx(1000, rel=0.01)


def test_distancia_bate_com_haversine():
    a, b = (-51.95, -20.95), (-51.90, -20.93)
    assert distancia_m(Point(a), Point(b)) == pytest.approx(distancia_km(a, b) * 1000, rel=0.01)


def test_ponto_fora_da_linha_mede_em_metros():
    # 1 km a leste do início: perpendicular aproximada à linha, longe das pontas
    fracao, dist = progresso_na_linha(LINHA, Point(-51.855 + 0.0096, -20.785))
    assert 0.4 < fracao < 0.6 and 700 < dist < 1000


def test_dentro_do_poligono_e_zero():
    fazenda = Polygon(quadrado_fazenda(-20.95, -51.95, 3200))
    assert distancia_m(fazenda, Point(-51.95, -20.95)) == 0
