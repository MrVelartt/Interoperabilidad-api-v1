from fastapi import FastAPI
from app.api.v1.routes import router as api_router
from app.core.settings import settings

app = FastAPI(
    title="Interoperabilidad API",
    version="1.0.0",
    description="API para integración e interoperabilidad (ETLs, automatizaciones y microservicios)."
)

# Incluir las rutas
app.include_router(api_router, prefix="/api/v1")


    