"""Cliente de Dataverse Web API — **solo operaciones de lectura (GET)**.

Este módulo NO crea ni modifica registros ni tablas. Únicamente consulta para
enriquecer respuestas y generar reportes locales.
"""
from __future__ import annotations

import urllib.parse

import requests

from ..auth.msal_client import get_dataverse_token
from ..config import config

_VERSION = "api/data/v9.2"


def _url() -> str:
    if not config.dataverse_url:
        raise RuntimeError("DATAVERSE_URL no configurada en el .env.")
    return f"{config.dataverse_url}/{_VERSION}"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_dataverse_token()}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }


def consultar(
    entidad: str,
    select: str | None = None,
    filtro: str | None = None,
    top: int = 20,
    orderby: str | None = None,
) -> list[dict]:
    """Consulta (GET) registros de una entidad de Dataverse.

    - `entidad`: nombre lógico del conjunto de entidades, p. ej. `crc3d_workorders`.
    - `select`: columnas separadas por coma.
    - `filtro`: OData `$filter` (p. ej. `statecode eq 0`).
    """
    query: list[str] = []
    if select:
        query.append(f"$select={select}")
    if filtro:
        query.append(f"$filter={filtro}")
    if orderby:
        query.append(f"$orderby={orderby}")
    query.append(f"$top={int(top)}")

    entidad_enc = urllib.parse.quote(entidad)
    url = f"{_url()}/{entidad_enc}"
    if query:
        url += "?" + "&".join(query)

    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json().get("value", [])


def consultar_por_id(entidad: str, record_id: str, select: str | None = None) -> dict:
    """Consulta (GET) un registro concreto por GUID."""
    entidad_enc = urllib.parse.quote(entidad)
    url = f"{_url()}/{entidad_enc}({record_id})"
    if select:
        url += f"?$select={select}"
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def nombre_entidad_por_defecto(tabla: str) -> str:
    """Convierte un nombre de tabla amigable al conjunto lógico si hace falta.

    P. ej. 'crc3d_workorder' -> 'crc3d_workorders' (regla típica plural).
    Si ya termina en 's' o el usuario dio el conjunto exacto, se devuelve igual.
    """
    t = (tabla or "").strip().lower()
    if not t:
        return t
    if t.endswith("s"):
        return t
    # para entidades personalizadas se agrega 's' de forma conservadora
    return t + "s"
