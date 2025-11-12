import httpx
import unicodedata
import xmltodict
from urllib.parse import urlencode, quote
from app.core.settings import settings


async def get_users(limit: int, offset: int):
    url = f"{settings.ALMA_API_URL}/users"
    params = {
        "limit": limit,
        "offset": offset,
        "order_by": "last_name,first_name,primary_id",
        "expand": "none",
        "format": "json",
        "apikey": settings.ALMA_API_KEY,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=params, headers={"Accept": "application/json"})
        r.raise_for_status()
        data = r.json()

    raw = data.get("user", [])
    total = data.get("total_record_count", 0)

    if isinstance(raw, dict):
        raw = [raw]

    users = []
    for u in raw:
        users.append({
            "id": u.get("primary_id"),
            "nombre": f"{u.get('first_name','')} {u.get('last_name','')}".strip(),
            "estado": u.get("status", {}).get("desc") if isinstance(u.get("status"), dict) else u.get("status"),
            "link": u.get("link", {}).get("@href") if isinstance(u.get("link"), dict) else u.get("link"),
        })

    return users, total


async def get_user_details(user_id: str):
    url = f"{settings.ALMA_API_URL}/users/{user_id}"
    params = {"apikey": settings.ALMA_API_KEY}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = xmltodict.parse(r.text)

    u = data.get("user", {}) or {}

    contact = u.get("contact_info") or {}
    emails = (contact.get("emails") or {}).get("email", [])
    phones = (contact.get("phones") or {}).get("phone", [])
    addresses = (contact.get("addresses") or {}).get("address", [])

    if isinstance(emails, dict): emails = [emails]
    if isinstance(phones, dict): phones = [phones]
    if isinstance(addresses, dict): addresses = [addresses]

    email = next((e.get("email_address") for e in emails if e.get("@preferred") == "true"), None)
    telefono = next((p.get("phone_number") for p in phones if p.get("@preferred") == "true"), None)
    addr = next((a for a in addresses if a.get("@preferred") == "true"), None)

    direccion = None
    if addr:
        direccion = ", ".join(filter(None, [addr.get("line1"), addr.get("line2"), addr.get("city")]))

    notas = (u.get("user_notes") or {}).get("user_note", [])
    if isinstance(notas, dict): notas = [notas]
    notas = " | ".join([n.get("note_text") for n in notas if n.get("note_text")]) or None

    return {
        "id": u.get("primary_id"),
        "nombre": f"{u.get('first_name','').strip()} {u.get('last_name','').strip()}".strip(),
        "nacimiento": u.get("birth_date"),
        "estado": u.get("status", {}).get("#text") if isinstance(u.get("status"), dict) else u.get("status"),
        "email": email,
        "telefono": telefono,
        "direccion": direccion,
        "notas": notas,
    }
def normalize_str(value: str) -> str:
    if not value:
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', value)
        if unicodedata.category(c) != 'Mn'
    ).lower()


# --- Diccionario de equivalencias BAC ---
TIPO_EQUIVALENCIAS = {
    "boletin": ["boletin_tecnico", "boletin_divulgativo"],
    "manual": ["manual", "cartilla", "plegable"],
    "libro": ["libro", "libro_de_analisis", "libro_resultado_de_investigacion", "capitulo"],
    "revista": ["articulo_cientifico", "memorias_eventos_academicos"],
    "informe": ["informe", "estudio_de_vigilancia", "plan", "modelo_productivo"],
    "audiovisual": ["video", "multimedia", "infografia"],
    "tesis": ["trabajo_de_grado"],
    "otros": ["other"]
}


async def get_publicaciones(region=None, sistema=None, cultivo=None, tipo=None, limit=10, offset=0):
    base = f"{settings.PRIMO_API_URL}/search"

    q = []
    if region:
        q.append(f"lds05,contains,{region}")
    if sistema:
        q.append(f"lds08,contains,{sistema}")
    if cultivo:
        q.append(f"lds07,contains,{cultivo}")


    q = quote(";".join(q) if q else "any,contains,agrosavia")

    params = {
        "vid": "57BAC_INST:BAC",
        "scope": "RI_BAC",
        "apikey": settings.PRIMO_API_KEY,
        "limit": limit,
        "offset": offset,
        "sort": "date_d",
        "lang": "es",
    }

    url = f"{base}?{urlencode(params)}&q={q}"

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()

    docs = data.get("docs", [])
    out = []

    for d in docs:
        p = d.get("pnx", {}).get("display", {})
        links = d.get("delivery", {}).get("link", [])

        enlace = next(
            (l.get("linkURL") for l in links if l.get("displayLabel") == "Biblioteca Digital Agropecuaria"),
            None
        )
        thumb = next(
            (l.get("linkURL") for l in links if "thumbnail" in l.get("displayLabel", "").lower()),
            None
        )

        out.append({
            "id": p.get("mms", [None])[0],
            "titulo": p.get("title", [None])[0],
            "autores": p.get("creator", []),
            "tipo": p.get("type", [None])[0],
            "anio": p.get("creationdate", [None])[0],
            "region": p.get("lds05", [None])[0],
            "sistema": p.get("lds08", [None])[0],
            "cultivo": p.get("lds07", [None])[0],
            "institucion": p.get("lds09", [None])[0],
            "enlace": enlace,
            "thumbnail": thumb
        })

    # --- Filtro sistema (exacto, insensible a mayúsculas/acentos) ---
    if sistema:
        sys_cmp = normalize_str(sistema)
        out = [p for p in out if p.get("sistema") and normalize_str(p["sistema"]) == sys_cmp]

    # --- Filtro tipo con equivalencias ---
    if tipo:
        tipo_cmp = normalize_str(tipo)
        posibles = TIPO_EQUIVALENCIAS.get(tipo_cmp, [tipo_cmp])
        out = [
            p for p in out
            if p.get("tipo") and normalize_str(p["tipo"]) in posibles
        ]

    # --- Unicidad y conteo total ---
    uniq = {p["id"]: p for p in out if p.get("id")}.values()
    total = data.get("info", {}).get("total", len(uniq))

    return list(uniq), total


async def get_publicacion_detalle(record_id: str):
    base = f"{settings.PRIMO_API_URL}/search"

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
        r = await client.get(base, params=params)
        r.raise_for_status()
        data = r.json()

    docs = data.get("docs", [])
    if not docs:
        return {"error": "No encontrado"}

    d = docs[0]
    p = d.get("pnx", {}).get("display", {})
    ad = d.get("pnx", {}).get("addata", {})
    links = d.get("delivery", {}).get("link", [])

    enlace = next((l.get("linkURL") for l in links if l.get("displayLabel") == "Biblioteca Digital Agropecuaria"), None)
    thumb = next((l.get("linkURL") for l in links if "thumbnail" in l.get("displayLabel", "").lower()), None)

    return {
        "id": record_id,
        "titulo": p.get("title", [None])[0],
        "autores": ad.get("au", []) or ad.get("aucorp", []),
        "anio": ad.get("date", [None])[0] or p.get("creationdate", [None])[0],
        "tipo": p.get("type", [None])[0],
        "pais": p.get("coverage", [None])[0],
        "descripcion": p.get("description", [None])[0] if "description" in p else None,
        "enlace": enlace,
        "thumbnail": thumb
    }
