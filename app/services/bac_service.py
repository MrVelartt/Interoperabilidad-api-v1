import httpx
import unicodedata
import xmltodict
from math import ceil
from urllib.parse import urlencode, quote
from app.core.settings import settings

# === Usuarios Alma (BAC) ===
async def get_users(limit: int = 10, offset: int = 0):
    """Obtiene usuarios del sistema Alma (BAC) con paginación estándar JSON."""

    url = f"{settings.ALMA_API_URL}/users"
    params = {
        "limit": limit,
        "offset": offset,
        "order_by": "last_name,first_name,primary_id",
        "expand": "none",
        "format": "json",  # 🔹 fuerza respuesta JSON
        "apikey": settings.ALMA_API_KEY,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params, headers={"Accept": "application/json"})
        response.raise_for_status()
        data = response.json()

    # Alma devuelve los usuarios en la clave "user"
    users_data = data.get("user", [])
    total = data.get("total_record_count") or 0

    # Si Alma devuelve un solo usuario, normalizar a lista
    if isinstance(users_data, dict):
        users_data = [users_data]

    # Estructurar resultados
    usuarios = []
    for u in users_data:
        usuarios.append({
            "id": u.get("primary_id"),
            "nombre": f"{u.get('first_name', '')} {u.get('last_name', '')}".strip(),
            "estado": u.get("status", {}).get("desc") if isinstance(u.get("status"), dict) else u.get("status"),
            "link": u.get("link", {}).get("@href") if isinstance(u.get("link"), dict) else u.get("link"),
        })

    # Calcular paginación
    page = (offset // limit) + 1 if limit else 1
    total_pages = ceil(total / limit) if limit else 1

    return {
        "count": total,
        "page": page,
        "page_size": limit,
        "total_pages": total_pages,
        "results": usuarios,
    }


async def get_user_details(user_id: str):
    """
    Obtiene los detalles completos de un usuario desde el API Alma (BAC)
    y devuelve un JSON limpio con los campos relevantes.
    Compatible con todos los casos: con/sin contact_info, vacíos, múltiples.
    """
    url = f"{settings.ALMA_API_URL}/users/{user_id}"
    params = {"apikey": settings.ALMA_API_KEY}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            print(f"❌ Error {response.status_code}: {response.text}")
            response.raise_for_status()

        try:
            data = xmltodict.parse(response.text)
        except Exception as e:
            print(f"❌ Error parseando XML: {e}")
            return {"error": "Respuesta inválida de Alma"}

        u = data.get("user") or {}
        if not isinstance(u, dict):
            return {"error": f"Estructura no esperada para usuario {user_id}"}

        # --- Normalizar contact_info ---
        contact_info = u.get("contact_info")
        if not isinstance(contact_info, dict):
            contact_info = {}

        # Asegurar que cada subnodo exista como dict
        addresses_raw = contact_info.get("addresses") or {}
        emails_raw = contact_info.get("emails") or {}
        phones_raw = contact_info.get("phones") or {}

        # --- Emails ---
        emails = emails_raw.get("email", [])
        if isinstance(emails, dict):
            emails = [emails]
        email = next((e.get("email_address") for e in emails if e.get("@preferred") == "true"), None)
        email = email or (emails[0].get("email_address") if emails else None)

        # --- Teléfonos ---
        phones = phones_raw.get("phone", [])
        if isinstance(phones, dict):
            phones = [phones]
        telefono = next((p.get("phone_number") for p in phones if p.get("@preferred") == "true"), None)
        telefono = telefono or (phones[0].get("phone_number") if phones else None)

        # --- Direcciones ---
        addresses = addresses_raw.get("address", [])
        if isinstance(addresses, dict):
            addresses = [addresses]
        direccion_obj = next((a for a in addresses if a.get("@preferred") == "true"), None)
        direccion_obj = direccion_obj or (addresses[0] if addresses else None)
        direccion = None
        if direccion_obj:
            direccion = ", ".join(
                filter(None, [
                    direccion_obj.get("line1"),
                    direccion_obj.get("line2"),
                    direccion_obj.get("city"),
                ])
            )

        # --- Notas ---
        notas_raw = (u.get("user_notes") or {}).get("user_note", [])
        if isinstance(notas_raw, dict):
            notas_raw = [notas_raw]
        notas = " | ".join([n.get("note_text") for n in notas_raw if n.get("note_text")]) or None

        # --- Resultado final ---
        result = {
            "id": u.get("primary_id"),
            "nombre": f"{u.get('first_name', '').strip()} {u.get('last_name', '').strip()}".strip(),
            "nacimiento": u.get("birth_date"),
            "estado": (
                u.get("status", {}).get("#text")
                if isinstance(u.get("status"), dict)
                else u.get("status")
            ),
            "email": email,
            "telefono": telefono,
            "direccion": direccion,
            "notas": notas,
        }

        print(f"✅ Usuario procesado: {user_id}, tiene_contact_info={bool(u.get('contact_info'))}")
        return result


def normalize_str(value: str) -> str:
    """Normaliza acentos, mayúsculas y espacios para comparación segura."""
    if not value:
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', value)
        if unicodedata.category(c) != 'Mn'
    ).strip().lower()


async def get_publicaciones(
    region: str | None = None,
    sistema: str | None = None,
    cultivo: str | None = None,
    tipo: str | None = None,
    limit: int = 10,
    offset: int = 0
):
    """
    Consulta publicaciones del sistema BAC (Primo API)
    filtrando por región (lds05), sistema (lds08), cultivo (lds07)
    y tipo de documento (rtype). Aplica coincidencia exacta
    para 'sistema' y permite búsqueda global sin filtros.
    """
    base_url = f"{settings.PRIMO_API_URL}/search"

    # --- Construcción dinámica del query 'q' ---
    q_parts = []
    if region:
        q_parts.append(f"lds05,contains,{region}")
    if sistema:
        q_parts.append(f"lds08,contains,{sistema}")
    if cultivo:
        q_parts.append(f"lds07,contains,{cultivo}")
    if tipo:
        q_parts.append(f"rtype,contains,{tipo}")

    # ✅ Si no hay filtros, traer resultados globales (no forzar Extensionista)
    q_param = quote(";".join(q_parts) if q_parts else "any,contains,agrosavia")

    query = {
        "vid": "57BAC_INST:BAC",
        "scope": "RI_BAC",
        "apikey": settings.PRIMO_API_KEY,
        "limit": limit,
        "offset": offset,
        "sort": "date_d",
        "lang": "es"
    }

    url = f"{base_url}?{urlencode(query)}&q={q_param}"
    print(f"🔎 Consultando Primo API: {url}")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    docs = data.get("docs", [])
    publicaciones = []

    for d in docs:
        pnx = d.get("pnx", {}).get("display", {})
        delivery_links = d.get("delivery", {}).get("link", [])

        enlace = next((l["linkURL"] for l in delivery_links if l.get("displayLabel") == "Biblioteca Digital Agropecuaria"), None)
        thumb = next((l["linkURL"] for l in delivery_links if "thumbnail" in l.get("displayLabel", "").lower()), None)

        publicaciones.append({
            "id": pnx.get("mms", [None])[0],
            "titulo": pnx.get("title", [None])[0],
            "autores": pnx.get("creator", []),
            "tipo": pnx.get("type", [None])[0],
            "anio": pnx.get("creationdate", [None])[0],
            "region": pnx.get("lds05", [None])[0],
            "sistema": pnx.get("lds08", [None])[0],
            "cultivo": pnx.get("lds07", [None])[0],
            "institucion": pnx.get("lds09", [None])[0],
            "enlace": enlace,
            "thumbnail": thumb
        })

    # ✅ Filtro exacto por sistema (solo Técnico)
    if sistema:
        sistema_norm = normalize_str(sistema)
        publicaciones = [
            p for p in publicaciones
            if p.get("sistema") and normalize_str(p["sistema"]) == sistema_norm
        ]

    # ✅ Eliminar duplicados globales por ID
    vistos = set()
    publicaciones_unicas = []
    for p in publicaciones:
        pid = p.get("id")
        if pid and pid not in vistos:
            publicaciones_unicas.append(p)
            vistos.add(pid)

    total = data.get("info", {}).get("total", len(publicaciones_unicas))
    page = (offset // limit) + 1
    total_pages = ceil(total / limit) if limit else 1
    has_next_page = total > (offset + limit)

    return {
        "total": total,
        "page": page,
        "page_size": limit,
        "total_pages": total_pages,
        "has_next_page": has_next_page,
        "count": len(publicaciones_unicas),
        "results": publicaciones_unicas
    }
    

    async def get_publicacion_detalle(record_id: str):
        """
        Obtiene los metadatos de una publicación individual desde Primo.
        Admite IDs como '99913610607981' o 'alma99913610607981'.
        """
        base_url = f"{settings.PRIMO_API_URL}/search"

        # Si el ID viene como alma999..., se limpia
        if record_id.startswith("alma"):
            record_id = record_id.replace("alma", "")

        params = {
            "vid": "57BAC_INST:BAC",
            "scope": "RI_BAC",
            "apikey": settings.PRIMO_API_KEY,
            "q": f"any,contains,{record_id}",
            "limit": 1
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(base_url, params=params)
            resp.raise_for_status()
            data = resp.json()

            docs = data.get("docs", [])
            if not docs:
                return {"error": f"Publicación {record_id} no encontrada"}

            d = docs[0]
            pnx = d.get("pnx", {}).get("display", {})
            addata = d.get("pnx", {}).get("addata", {})
            delivery = d.get("delivery", {})
            links = delivery.get("link", [])

            enlace = next((l["linkURL"] for l in links if l.get("displayLabel") == "Biblioteca Digital Agropecuaria"), None)
            thumbnail = next((l["linkURL"] for l in links if "thumbnail" in l.get("displayLabel", "").lower()), None)

            return {
                "id": record_id,
                "titulo": pnx.get("title", [None])[0],
                "autores": addata.get("au", []) or addata.get("aucorp", []),
                "anio": addata.get("date", [None])[0] or pnx.get("creationdate", [None])[0],
                "tipo": pnx.get("type", [None])[0],
                "pais": pnx.get("coverage", [None])[0],
                "descripcion": pnx.get("description", [None])[0] if "description" in pnx else None,
                "enlace": enlace,
                "thumbnail": thumbnail
            }