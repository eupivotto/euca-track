"""Gera raster_teste.tif: um recorte pequeno e sintético no formato do MapBiomas.

Pixel de 0,003° (~10,4 ha perto de Três Lagoas), uint8, EPSG:4326. Blocos:
- 9 blocos da classe 9 com 8 linhas e 8 a 16 colunas (~670 a ~1330 ha);
- 1 bloco 3×3 da classe 9 (~94 ha, abaixo do mínimo);
- 2 blocos 5×5 da classe 9 separados por uma coluna de pastagem (juntos ~520 ha);
- 1 bloco 9×9 da classe 15 (pastagem).

Uso: python tests/fixtures/criar_raster_teste.py
"""
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

PIXEL = 0.003
OESTE, NORTE = -52.0, -20.5
LINHAS, COLUNAS = 34, 76

dados = np.full((LINHAS, COLUNAS), 3, dtype=np.uint8)  # formação florestal ao fundo
for i, (linha, coluna) in enumerate((r, c) for r in (2, 13, 24) for c in (2, 21, 40)):
    dados[linha : linha + 8, coluna : coluna + 8 + i] = 9
dados[2:5, 62:65] = 9
dados[13:18, 62:67] = 9
dados[13:18, 67] = 15
dados[13:18, 68:73] = 9
dados[24:33, 62:71] = 15

destino = Path(__file__).with_name("raster_teste.tif")
with rasterio.open(
    destino, "w", driver="GTiff", width=COLUNAS, height=LINHAS, count=1, dtype="uint8",
    crs="EPSG:4326", transform=from_origin(OESTE, NORTE, PIXEL, PIXEL), compress="deflate",
) as dst:
    dst.write(dados, 1)
print(f"Gravado {destino}")
