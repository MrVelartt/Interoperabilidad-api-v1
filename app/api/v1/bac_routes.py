from fastapi import APIRouter, Query, Path
from app.services import bac_service

router = APIRouter(prefix="/bac", tags=["BAC"])

# === EXISTENTE ===
@router.get("/usuarios")
async def listar_usuarios(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    """Retorna usuarios del sistema Alma (BAC)."""
    return await bac_service.get_users(limit=limit, offset=offset)

# === NUEVO ===
@router.get("/usuarios/{user_id}")
async def detalle_usuario(user_id: str = Path(..., description="ID del usuario en Alma")):
    """
    Retorna los detalles completos de un usuario específico desde Alma (BAC).
    """
    return await bac_service.get_user_details(user_id)

@router.get("/publicaciones")
async def listar_publicaciones(
    extensionista: str = "Extensionista",
    tipo_documento: str | None = None,
    dpto: str | None = None,
    limit: int = 10,
    offset: int = 0
):
    """
    Retorna publicaciones del sistema BAC (Primo API).
    Ejemplo de búsqueda:
    /publicaciones?extensionista=Extensionista&tipo_documento=Libro&dpto=Antioquia
    """
    return await bac_service.get_publicaciones(
        extensionista=extensionista,
        tipo_documento=tipo_documento,
        dpto=dpto,
        limit=limit,
        offset=offset
    )


@router.get("/publicaciones/{record_id}")
async def detalle_publicacion(record_id: str):
    """
    Retorna los metadatos completos de una publicación individual (por ID de Primo o Alma)
    """
    return await bac_service.get_publicacion_detalle(record_id)