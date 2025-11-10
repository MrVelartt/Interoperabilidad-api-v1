from fastapi import APIRouter, Query, Path, Response
from app.services import bac_service

router = APIRouter(prefix="/bac", tags=["BAC"])


def parse_range_param(range_param: str | None):
    if not range_param:
        return 0, 50  # Rango por defecto
    start, end = range_param.replace("items=", "").split("-")
    start = int(start)
    end = int(end)
    limit = (end - start) + 1
    return start, limit


@router.get("/usuarios")
async def listar_usuarios(
    response: Response,
    range: str | None = Query(None, description="Formato: start-end, ej: 0-49")
):
    offset, limit = parse_range_param(range)

    data, total = await bac_service.get_users(limit=limit, offset=offset)

    end = offset + len(data) - 1 if data else offset
    response.headers["Content-Range"] = f"{offset}-{end}/{total}"
    response.headers["Accept-Ranges"] = "items"

    return data


@router.get("/usuarios/{user_id}")
async def detalle_usuario(user_id: str):
    return await bac_service.get_user_details(user_id)


@router.get("/publicaciones")
async def listar_publicaciones(
    response: Response,
    range: str | None = Query(None, description="Formato: start-end, ej: 0-49"),
    region: str | None = None,
    sistema: str | None = None,
    cultivo: str | None = None,
    tipo: str | None = None,
):
    offset, limit = parse_range_param(range)

    data, total = await bac_service.get_publicaciones(
        region=region,
        sistema=sistema,
        cultivo=cultivo,
        tipo=tipo,
        limit=limit,
        offset=offset
    )

    end = offset + len(data) - 1 if data else offset
    response.headers["Content-Range"] = f"{offset}-{end}/{total}"
    response.headers["Accept-Ranges"] = "items"

    return data


@router.get("/publicaciones/{record_id}")
async def detalle_publicacion(record_id: str):
    return await bac_service.get_publicacion_detalle(record_id)
