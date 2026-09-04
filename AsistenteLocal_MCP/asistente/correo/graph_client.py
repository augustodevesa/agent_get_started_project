"""Cliente de Microsoft Graph para el correo.

- `listar_inbox`: lee la bandeja de entrada (solo lectura).
- `crear_borrador`: crea un borrador en la carpeta Drafts de Outlook.
  **Nunca envía** correos: el usuario revisa y envía desde Outlook.
"""
from __future__ import annotations

import requests

from ..auth.msal_client import get_graph_token

_GRAPH = "https://graph.microsoft.com/v1.0"


def _headers(force: bool = False) -> dict:
    token = get_graph_token(force=force)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def listar_inbox(top: int = 20, solo_no_leidos: bool = False) -> list[dict]:
    """Devuelve los últimos `top` mensajes de la bandeja de entrada."""
    filtro = ""
    if solo_no_leidos:
        filtro = "&$filter=isRead eq false"
    url = (
        f"{_GRAPH}/me/mailFolders/inbox/messages"
        f"?$top={int(top)}&$orderby=receivedDateTime desc"
        f"&$select=id,subject,from,toRecipients,receivedDateTime,isRead,bodyPreview"
        f"{filtro}"
    )
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    mensajes = resp.json().get("value", [])
    return [
        {
            "id": m.get("id"),
            "asunto": m.get("subject"),
            "remitente": _direccion(m.get("from")),
            "recibido": m.get("receivedDateTime"),
            "leido": m.get("isRead"),
            "vista_previa": (m.get("bodyPreview") or "")[:300],
        }
        for m in mensajes
    ]


def leer_mensaje(message_id: str) -> dict:
    """Lee el cuerpo completo de un mensaje por id (solo lectura)."""
    url = (
        f"{_GRAPH}/me/messages/{message_id}"
        f"?$select=id,subject,from,toRecipients,body,receivedDateTime,conversationId"
    )
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    m = resp.json()
    return {
        "id": m.get("id"),
        "asunto": m.get("subject"),
        "remitente": _direccion(m.get("from")),
        "cuerpo": (m.get("body") or {}).get("content", ""),
        "recibido": m.get("receivedDateTime"),
    }


def crear_borrador(
    asunto: str,
    cuerpo_html: str,
    destinatarios: list[str],
    mensaje_original_id: str | None = None,
) -> dict:
    """Crea un borrador en Outlook (Drafts). NO lo envía.

    Si se indica `mensaje_original_id`, se usa como base (incluye la conversación).
    """
    if not destinatarios:
        raise ValueError("Se requiere al menos un destinatario.")
    cuerpo = {"contentType": "html", "content": cuerpo_html}
    datos = {
        "subject": asunto,
        "body": cuerpo,
        "toRecipients": [
            {"emailAddress": {"address": d}} for d in destinatarios
        ],
    }
    if mensaje_original_id:
        # Crear borrador como respuesta a un mensaje
        url = f"{_GRAPH}/me/messages/{mensaje_original_id}/createReply"
        resp = requests.post(
            url, headers=_headers(), json=datos, timeout=30
        )
    else:
        url = f"{_GRAPH}/me/mailFolders/drafts/messages"
        resp = requests.post(url, headers=_headers(), json=datos, timeout=30)

    resp.raise_for_status()
    b = resp.json()
    # Abrir en el navegador/Outlook web para revisión (no enviar)
    web = b.get("webLink")
    return {
        "id": b.get("id"),
        "asunto": b.get("subject"),
        "borrador_creado": True,
        "enviado": False,  # nunca se envía automáticamente
        "para_revision": True,
        "web_link": web,
    }


def _direccion(email_object: dict | None) -> str:
    if not email_object:
        return ""
    ea = email_object.get("emailAddress") or {}
    return ea.get("address", "")
