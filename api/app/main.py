from fastapi import FastAPI

from app.rotas_http import saude

app = FastAPI(title="Rota da Madeira")
app.include_router(saude.router)
