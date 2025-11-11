from fastapi import APIRouter, Query, Response
from app.services import bac_service

router = APIRouter(prefix="/bac", tags=["BAC"])


@router.get("/usuarios")
async def listar_usuarios(
    response: Response,
    limit: int = Query(50, ge=1, le=200, description="Cantidad de registros a retornar"),
    offset: int = Query(0, ge=0, description="Número de registros a saltar")
):
    data, total = await bac_service.get_users(limit=limit, offset=offset)

    end = offset + len(data) - 1 if data else offset

    response.headers["Content-Range"] = f"items {offset}-{end}/{total}"
    response.headers["X-Total-Count"] = str(total)
    response.headers["Accept-Ranges"] = "items"

    return data


@router.get("/usuarios/{user_id}")
async def detalle_usuario(user_id: str):
    return await bac_service.get_user_details(user_id)


@router.get("/publicaciones")
async def listar_publicaciones(
    response: Response,
    limit: int = Query(30, ge=1, le=200, description="Cantidad de registros a retornar"),
    offset: int = Query(0, ge=0, description="Número de registros a saltar"),
    region: str | None = None,
    sistema: str | None = None,
    cultivo: str | None = None,
    tipo: str | None = None,
):
    data, total = await bac_service.get_publicaciones(
        region=region,
        sistema=sistema,
        cultivo=cultivo,
        tipo=tipo,
        limit=limit,
        offset=offset,
    )

    end = offset + len(data) - 1 if data else offset

    response.headers["Content-Range"] = f"items {offset}-{end}/{total}"
    response.headers["X-Total-Count"] = str(total)
    response.headers["Accept-Ranges"] = "items"

    return data


@router.get("/publicaciones/{record_id}")
async def detalle_publicacion(record_id: str):
    return await bac_service.get_publicacion_detalle(record_id)
