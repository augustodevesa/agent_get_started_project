"""Servidor MCP del Asistente Personal (FastMCP).

Expone las herramientas que usa GitHub Copilot desde el escritorio. Se inicia con:
    python -m asistente
"""
from __future__ import annotations

import mcp.server.stdio  # noqa: F401  (asegura el handler stdio)
from mcp.server.fastmcp import FastMCP

from .catalogo import clasificador
from .seguimiento import registro
from .reportes import generador

mcp = FastMCP(
    "asistente-personal",
    instructions=(
        "Eres el 'Asistente Personal AD': un secretario ejecutivo / project manager. "
        "Clasifica correos por prioridad (Alta/Media/Baja), propone borradores de "
        "respuesta (NUNCA los envía), lleva un registro de seguimiento local de "
        "proyectos/temas y genera reportes en documentos locales. Dataverse solo se "
        "consulta (solo lectura); jamás se escriben registros en Dataverse."
    ),
)


# ---------------------------------------------------------------------------
# Correo
# ---------------------------------------------------------------------------
@mcp.tool(
    description=(
        "Lista los últimos N mensajes de la bandeja de entrada (Microsoft Graph). "
        "Solo lectura. Opcionalmente solo no leídos."
    )
)
def correo_listar_inbox(top: int = 20, solo_no_leidos: bool = False) -> dict:
    from .correo import graph_client

    try:
        mensajes = graph_client.listar_inbox(top=top, solo_no_leidos=solo_no_leidos)
        return {"ok": True, "total": len(mensajes), "mensajes": mensajes}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _msg_error(exc)}


@mcp.tool(
    description=(
        "Clasifica un correo por prioridad (Alta/Media/Baja) y tema según las reglas "
        "del agente (remitente/dominio, palabras clave de urgencia, proyecto vinculado). "
        "No requiere conexión."
    )
)
def correo_clasificar(asunto: str, cuerpo: str = "", remitente: str = "") -> dict:
    return clasificador.clasificar(asunto, cuerpo, remitente)


@mcp.tool(
    description=(
        "Lista la bandeja de entrada y clasifica cada mensaje por prioridad/tema. "
        "Ideal para '¿qué correos son urgentes?'."
    )
)
def correo_analizar_inbox(top: int = 20) -> dict:
    from .correo import graph_client

    try:
        mensajes = graph_client.listar_inbox(top=top)
        analizados = []
        for m in mensajes:
            cl = clasificador.clasificar(
                m.get("asunto", ""),
                m.get("vista_previa", ""),
                m.get("remitente", ""),
            )
            analizados.append({**m, **cl})
        analizados.sort(key=lambda x: _orden_prioridad(x.get("prioridad", "Media")))
        return {"ok": True, "total": len(analizados), "mensajes": analizados}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _msg_error(exc)}


@mcp.tool(
    description=(
        "Propone un borrador de respuesta a un correo existente (por su id) con el "
        "texto indicado. Crea el borrador en la carpeta Drafts de Outlook para que el "
        "usuario lo revise. NUNCA envía el correo."
    )
)
def correo_proponer_borrador(mensaje_id: str, texto_respuesta: str) -> dict:
    from .correo import borrador, graph_client

    try:
        original = graph_client.leer_mensaje(mensaje_id)
        remitente = original.get("remitente")
        if not remitente:
            return {"ok": False, "error": "No se pudo determinar el remitente del mensaje."}
        asunto = f"RE: {original.get('asunto', '')}"
        cuerpo_html = borrador.cuerpo_respuesta(
            texto_respuesta,
            citar_original=(original.get("cuerpo") or "")[:2000],
        )
        creado = graph_client.crear_borrador(
            asunto=asunto,
            cuerpo_html=cuerpo_html,
            destinatarios=[remitente],
            mensaje_original_id=mensaje_id,
        )
        creado["para_revision"] = True
        creado["nota"] = (
            "Borrador creado en Outlook (Drafts). Revisa y envía manualmente; "
            "el asistente nunca envía por ti."
        )
        return {"ok": True, **creado}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _msg_error(exc)}


# ---------------------------------------------------------------------------
# Seguimiento (registro local)
# ---------------------------------------------------------------------------
@mcp.tool(
    description=(
        "Registra una entrada de seguimiento local (correo/proyecto/tema/tarea) "
        "con prioridad, estado, próximo paso y fecha límite."
    )
)
def seguimiento_registrar(
    titulo: str,
    tipo: str = "tema",
    prioridad: str = "Media",
    tema: str = "",
    asunto: str = "",
    estado: str = "Pendiente",
    proximo_paso: str = "",
    fecha_limite: str = "",
    notas: str = "",
) -> dict:
    try:
        return {
            "ok": True,
            "registro": registro.registrar(
                tipo=tipo,
                titulo=titulo,
                prioridad=prioridad,
                tema=tema,
                asunto=asunto,
                estado=estado,
                proximo_paso=proximo_paso,
                fecha_limite=fecha_limite,
                notas=notas,
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _msg_error(exc)}


@mcp.tool(description="Lista el registro de seguimiento local (opcional por estado/prioridad).")
def seguimiento_listar(estado: str = "", prioridad: str = "") -> dict:
    try:
        rows = registro.listar(estado or None, prioridad or None)
        return {"ok": True, "total": len(rows), "registros": rows}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _msg_error(exc)}


@mcp.tool(description="Actualiza el estado de una entrada de seguimiento por id.")
def seguimiento_actualizar_estado(record_id: str, estado: str, notas: str = "") -> dict:
    try:
        r = registro.actualizar_estado(record_id, estado, notas)
        if r is None:
            return {"ok": False, "error": f"No existe registro con id '{record_id}'."}
        return {"ok": True, "registro": r}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _msg_error(exc)}


@mcp.tool(description="Resumen/estadísticas del registro de seguimiento local.")
def seguimiento_resumen() -> dict:
    try:
        return {"ok": True, **registro.estadisticas()}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _msg_error(exc)}


# ---------------------------------------------------------------------------
# Dataverse (SOLO LECTURA)
# ---------------------------------------------------------------------------
@mcp.tool(
    description=(
        "Consulta (SOLO LECTURA) registros de una entidad de Dataverse Web API. "
        "Nunca crea ni modifica registros. Ej.: entidad='crc3d_workorders', "
        "select='name,statuscode', filtro='statecode eq 0'."
    )
)
def dataverse_consultar(
    entidad: str,
    select: str = "",
    filtro: str = "",
    top: int = 20,
) -> dict:
    from .dataverse import cliente

    try:
        conjunto = cliente.nombre_entidad_por_defecto(entidad)
        rows = cliente.consultar(
            conjunto,
            select=select or None,
            filtro=filtro or None,
            top=top,
        )
        return {
            "ok": True,
            "entidad": conjunto,
            "total": len(rows),
            "registros": rows,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _msg_error(exc)}


# ---------------------------------------------------------------------------
# Reportes locales
# ---------------------------------------------------------------------------
@mcp.tool(
    description=(
        "Genera un reporte/documento LOCAL (markdown y/o Word) a partir de secciones "
        "y opcionalmente del registro de seguimiento. Se guarda en data/reportes. "
        "No se envía a Dataverse."
    )
)
def reporte_generar(
    titulo: str,
    incluir_seguimiento: bool = False,
    formato: str = "markdown",
) -> dict:
    try:
        secciones = []
        if incluir_seguimiento:
            rows = registro.listar()
            cuerpo = "| ID | Fecha | Título | Prioridad | Estado | Próximo paso |\n"
            cuerpo += "|----|-------|--------|-----------|--------|--------------|\n"
            for r in rows:
                cuerpo += (
                    f"| {r.get('id')} | {r.get('fecha_registro')} | "
                    f"{r.get('titulo')} | {r.get('prioridad')} | {r.get('estado')} | "
                    f"{r.get('proximo_paso')} |\n"
                )
            secciones.append({"cabecera": "Registro de seguimiento", "cuerpo": cuerpo})
        if not secciones:
            secciones.append(
                {"cabecera": "Detalle", "cuerpo": "Sin contenido adicional especificado."}
            )
        formatos = [formato] if formato else ["markdown"]
        rutas = generador.generar(titulo, secciones, formatos=formatos)
        return {
            "ok": True,
            "titulo": titulo,
            "archivos": [str(p) for p in rutas],
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _msg_error(exc)}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _orden_prioridad(prioridad: str) -> int:
    return {"Alta": 0, "Media": 1, "Baja": 2}.get(prioridad, 1)


def _msg_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
