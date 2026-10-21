import pytest
from pyproj import Transformer
from shapely.geometry import Polygon

from app.geo import distancia_km, quadrado_fazenda

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
