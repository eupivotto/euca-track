"""Baixa só o recorte da região do raster do MapBiomas (SPEC seção 3.1).

Uso: python -m app.scripts.exportar_mapbiomas [saida]

O GeoTIFF público da coleção 10 tem 800 MB, mas é dividido em blocos e o
servidor aceita leitura por trechos: o GDAL busca só os blocos do recorte
(~3 MB). Dispensa conta no Earth Engine. A saída fica fora do git; o que vai
para o repositório é o GeoJSON gerado por gerar_areas_eucalipto.
"""
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.windows import from_bounds

from app.config import Settings, get_settings

SAIDA_PADRAO = Path(__file__).resolve().parents[2] / "dados" / "mapbiomas_2024_recorte.tif"


def ler_recorte(origem: str, settings: Settings) -> tuple[np.ndarray, Affine, dict]:
    """Lê a janela do recorte da config; origem é um caminho local ou /vsicurl/<url>."""
    with rasterio.open(origem) as src:
        janela = from_bounds(
            settings.regiao_lon_min, settings.regiao_lat_min,
            settings.regiao_lon_max, settings.regiao_lat_max,
            src.transform,
        ).round_offsets().round_lengths()
        dados = src.read(1, window=janela)
        transform = src.window_transform(janela)
        perfil = {**src.profile, "width": dados.shape[1], "height": dados.shape[0], "transform": transform}
    return dados, transform, perfil


if __name__ == "__main__":
    import sys

    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else SAIDA_PADRAO
    configuracao = get_settings()
    dados, _, perfil = ler_recorte(f"/vsicurl/{configuracao.mapbiomas_url}", configuracao)
    destino.parent.mkdir(parents=True, exist_ok=True)
    perfil.update(compress="deflate", tiled=True, blockxsize=256, blockysize=256)
    with rasterio.open(destino, "w", **perfil) as dst:
        dst.write(dados, 1)
    print(f"Recorte {dados.shape[1]}x{dados.shape[0]} gravado em {destino}")
