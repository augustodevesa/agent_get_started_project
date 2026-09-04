"""Ayudantes para armar borradores de respuesta (no se envían)."""
from __future__ import annotations

import html


def cuerpo_respuesta(
    respuesta_texto: str,
    citar_original: str | None = None,
    firma: str = "Atentamente,\n[Tu nombre]",
) -> str:
    """Convierte texto plano en HTML ligero para el borrador de Outlook."""
    parrafos = "".join(
        f"<p>{html.escape(p)}</p>" for p in (respuesta_texto or "").split("\n") if p.strip()
    )
    citado = ""
    if citar_original:
        esc = html.escape(citar_original)
        citado = (
            "<hr/>"
            "<div style='color:#555;font-size:12px'>"
            f"<blockquote>{esc}</blockquote></div>"
        )
    firma_html = "<p>--</p><p>" + html.escape(firma).replace("\n", "<br/>") + "</p>"
    return f"{parrafos}{firma_html}{citado}"
