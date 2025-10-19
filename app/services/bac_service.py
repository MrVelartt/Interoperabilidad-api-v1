import httpx
from urllib.parse import urlencode
import xmltodict
from app.core.settings import settings

# === Usuarios Alma (BAC) ===
async def get_users(limit: int = 10, offset: int = 0):
    url = f"{settings.ALMA_API_URL}/users"
    params = {
        "offset": offset,
        "order_by": "last_name,first_name,primary_id",
        "apikey": settings.ALMA_API_KEY,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()

        data = xmltodict.parse(response.text)
        users_data = data.get("users", {})
        total = users_data.get("@total_record_count", 0)
        users = users_data.get("user", [])

        result = []
        for u in users:
            result.append({
                "id": u.get("primary_id"),
                "nombre": f"{u.get('first_name', '')} {u.get('last_name', '')}".strip(),
                "estado": u.get("status", {}).get("#text") if isinstance(u.get("status"), dict) else u.get("status"),
                "link": u.get("@link"),
            })

        return {"total": int(total), "usuarios": result}


async def get_user_details(user_id: str):
    """
    Obtiene los detalles completos de un usuario desde el API Alma (BAC)
    y devuelve un JSON limpio con los campos relevantes.
    """
    url = f"{settings.ALMA_API_URL}/users/{user_id}"
    params = {"apikey": settings.ALMA_API_KEY}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            print("❌ Error:", response.status_code, response.text)
            response.raise_for_status()

        # Parsear XML → dict
        data = xmltodict.parse(response.text)
        u = data.get("user", {})

        # === Contact info ===
        contact_info = u.get("contact_info", {})

        # Emails
        emails = contact_info.get("emails", {}).get("email", [])
        if isinstance(emails, dict):
            emails = [emails]
        email = next((e.get("email_address") for e in emails if e.get("@preferred") == "true"), None)
        email = email or (emails[0].get("email_address") if emails else None)

        # Phones
        phones = contact_info.get("phones", {}).get("phone", [])
        if isinstance(phones, dict):
            phones = [phones]
        telefono = next((p.get("phone_number") for p in phones if p.get("@preferred") == "true"), None)
        telefono = telefono or (phones[0].get("phone_number") if phones else None)

        # Addresses
        addresses = contact_info.get("addresses", {}).get("address", [])
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

        # === Notas ===
        notas_raw = u.get("user_notes", {}).get("user_note", [])
        if isinstance(notas_raw, dict):
            notas_raw = [notas_raw]
        notas = " | ".join([n.get("note_text") for n in notas_raw if n.get("note_text")]) or None

        # === Resultado limpio ===
        result = {
            "id": u.get("primary_id"),
            "nombre": f"{u.get('first_name', '')} {u.get('last_name', '')}".strip(),
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

        return result
    

async def get_publicaciones(
    extensionista: str = "Extensionista",
    tipo_documento: str | None = None,
    dpto: str | None = None,
    limit: int = 10,
    offset: int = 0
):
    """
    Consulta publicaciones en el API Primo (BAC).
    """
    base_url = f"{settings.PRIMO_API_URL}/search"

    # --- Construcción dinámica del parámetro q ---
    q_parts = [f"lds08,exact,{extensionista}"]
    if tipo_documento:
        q_parts.append(f"rtype,contains,{tipo_documento}")
    if dpto:
        q_parts.append(f"lds05,contains,{dpto}")

    q_param = ";".join(q_parts)

    # --- Armado manual de la URL ---
    query = {
        "vid": "57BAC_INST:BAC",
        "scope": "RI_BAC",
        "apikey": settings.PRIMO_API_KEY,
        "limit": limit,
        "offset": offset,
        "sort": "date_d"
    }
    url = f"{base_url}?{urlencode(query)}&q={q_param}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url)
        if response.status_code != 200:
            print("❌ Error:", response.status_code, response.text)
            response.raise_for_status()

        data = response.json()
        docs = data.get("docs", [])
        publicaciones = []

        for d in docs:
            pnx = d.get("pnx", {}).get("display", {})
            delivery = d.get("delivery", {}).get("link", [])
            enlace = next((l["linkURL"] for l in delivery if l.get("displayLabel") == "Biblioteca Digital Agropecuaria"), None)
            thumb = next((l["linkURL"] for l in delivery if "thumbnail" in l.get("displayLabel", "").lower()), None)

            publicaciones.append({
                "id": pnx.get("mms", [None])[0],
                "titulo": pnx.get("title", [None])[0],
                "autores": pnx.get("creator", []),
                "tipo": pnx.get("type", [None])[0],
                "anio": pnx.get("creationdate", [None])[0],
                "pais": pnx.get("coverage", [None])[0],
                "enlace": enlace,
                "thumbnail": thumb,
            })

        return {
            "total": data.get("info", {}).get("total", len(publicaciones)),
            "count": len(publicaciones),
            "publicaciones": publicaciones
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