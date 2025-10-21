from fastapi import APIRouter, Query, Path
from app.services import bac_service

router = APIRouter(prefix="/bac", tags=["BAC"])

@router.get("/usuarios", summary="Listar usuarios de Alma (BAC)")
async def listar_usuarios(
    limit: int = Query(50, ge=1, le=100, description="Número de usuarios por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento de registros para paginación")
):
    """
    Retorna usuarios del sistema Alma (BAC) con formato JSON y metadatos de paginación.
    """
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
    region: str | None = Query(None, description="Departamento o región (lds05)"),
    sistema: str | None = Query(None, description="Sistema / nivel del usuario (lds08)"),
    cultivo: str | None = Query(None, description="Cultivo o especie (lds07)"),
    tipo: str | None = Query(None, description="Tipo de documento (Libro, Video, Artículo_científico, etc.)"),
    limit: int = Query(10, ge=1, le=50, description="Número de registros por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento de registros para paginación")
):
    """
    Retorna publicaciones del sistema BAC (Primo API),
    filtradas por región, sistema, cultivo y tipo de documento.
    Ejemplo:
    /api/v1/bac/publicaciones?region=Meta&sistema=Técnico&cultivo=Mango&tipo=Libro
    """
    return await bac_service.get_publicaciones(
        region=region,
        sistema=sistema,
        cultivo=cultivo,
        tipo=tipo,
        limit=limit,
        offset=offset
    )

@router.get("/publicaciones/{record_id}")
async def detalle_publicacion(record_id: str):
    """
    Retorna los metadatos completos de una publicación individual (por ID de Primo o Alma)
    """
    return await bac_service.get_publicacion_detalle(record_id)