from fastapi import FastAPI

from app.rotas_http import alertas, frota, indicadores, mapa, patio, saude, simulacao

app = FastAPI(title="Rota da Madeira")
app.include_router(saude.router)
app.include_router(mapa.router)
app.include_router(frota.router)
app.include_router(simulacao.router)
app.include_router(indicadores.router)
app.include_router(alertas.router)
app.include_router(patio.router)
