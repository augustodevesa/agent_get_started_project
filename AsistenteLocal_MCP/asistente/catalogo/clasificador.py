"""Motor de clasificación de correos por prioridad y tema.

Reglas (en orden):
1. Si el tema/proyecto es conocido → toma su `prioridad_defecto` como base.
2. Si el remitente coincide con un dominio crítico → sube a Alta.
3. Si hay palabras clave de urgencia/plazo → sube a Alta.
4. Si no hay señales de urgencia y hay palabras de seguimiento normal → Media.
5. Palabras tipo boletín/notificación → Baja.
6. Por defecto → Media.
"""
from __future__ import annotations

from ..config import config


def _normalizar(texto: str) -> str:
    import unicodedata

    texto = texto or ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def detectar_tema(asunto: str, cuerpo: str) -> dict:
    """Detecta el tema/proyecto conocido según las palabras clave del YAML."""
    texto = _normalizar(f"{asunto} {cuerpo}")
    for tema in config.temas():
        for clave in tema.get("claves", []):
            if clave and _normalizar(clave) in texto:
                return {
                    "tema": tema["nombre"],
                    "prioridad_defecto": tema.get("prioridad_defecto", "Media"),
                }
    # tema genérico
    return {"tema": "Correo general", "prioridad_defecto": "Media"}


def clasificar(asunto: str, cuerpo: str = "", remitente: str = "") -> dict:
    """Devuelve prioridad (Alta/Media/Baja), tema y motivos."""
    urgencia, dominios = config.prioridad_alta()
    media = config.prioridad_media()
    baja = config.prioridad_baja()

    texto = _normalizar(f"{asunto} {cuerpo}")
    rem = _normalizar(remitente or "")
    tema_info = detectar_tema(asunto, cuerpo)
    prioridad = tema_info["prioridad_defecto"]
    motivos: list[str] = []

    # Regla: dominio crítico -> Alta
    for dom in dominios:
        if dom and dom in rem:
            prioridad = "Alta"
            motivos.append(f"Remitente de dominio crítico: {dom}")
            break

    # Regla: palabra de urgencia/plazo -> Alta
    for kw in urgencia:
        if kw and kw in texto:
            prioridad = "Alta"
            motivos.append(f"Palabra de urgencia/plazo: '{kw}'")
            break

    # Regla: si aún no es Alta, aplicar Media/Baja por palabras
    if prioridad != "Alta":
        for kw in baja:
            if kw and kw in texto:
                prioridad = "Baja"
                motivos.append(f"Contenido informativo: '{kw}'")
                break
        else:
            for kw in media:
                if kw and kw in texto:
                    prioridad = "Media"
                    motivos.append(f"Seguimiento/proyecto: '{kw}'")
                    break

    if not motivos:
        motivos.append(
            f"Tema '{tema_info['tema']}' con prioridad por defecto {prioridad}."
        )

    return {
        "prioridad": prioridad,
        "tema": tema_info["tema"],
        "motivos": motivos,
        "texto_normalizado": texto[:400],
    }


def prioridades_validas() -> list[str]:
    return config.agente.get("prioridades", ["Alta", "Media", "Baja"])
