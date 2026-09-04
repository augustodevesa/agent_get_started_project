"""Registro de seguimiento persistido en archivos locales (CSV + Markdown).

El registro vive en `data/seguimiento/` y contiene las entradas de
proyectos/temas/correos que el asistente da seguimiento.
"""
from __future__ import annotations

import csv
import datetime as dt
import uuid
from pathlib import Path

from ..config import config

COLUMNAS = [
    "id",
    "fecha_registro",
    "tipo",        # correo | proyecto | tema | tarea
    "titulo",
    "asunto",      # opcional: id de mensaje o referencia
    "prioridad",   # Alta | Media | Baja
    "tema",        # proyecto/tema vinculado
    "estado",      # Pendiente | En curso | En espera | Completado | Cancelado
    "proximo_paso",
    "fecha_limite",
    "notas",
]


def _csv_path() -> Path:
    nombre = config.agente.get("seguimiento", {}).get("archivo_csv", "registro_seguimiento.csv")
    return config.seguimiento_dir / nombre


def _md_path() -> Path:
    nombre = config.agente.get("seguimiento", {}).get("archivo_markdown", "REGISTRO.md")
    return config.seguimiento_dir / nombre


def _leer() -> list[dict]:
    path = _csv_path()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _escribir(rows: list[dict]) -> None:
    path = _csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNAS)
        writer.writeheader()
        writer.writerows(rows)
    _escribir_markdown(rows)


def _validar_estado(estado: str) -> str:
    validos = config.estados_seguimiento() or ["Pendiente"]
    estado = (estado or "").strip()
    if not estado:
        return "Pendiente"
    # búsqueda case-insensitive
    for v in validos:
        if v.lower() == estado.lower():
            return v
    return "Pendiente"


def registrar(
    tipo: str,
    titulo: str,
    prioridad: str = "Media",
    tema: str = "",
    asunto: str = "",
    estado: str = "Pendiente",
    proximo_paso: str = "",
    fecha_limite: str = "",
    notas: str = "",
) -> dict:
    """Crea una entrada de seguimiento y devuelve el registro creado."""
    row = {
        "id": str(uuid.uuid4())[:8],
        "fecha_registro": dt.date.today().isoformat(),
        "tipo": (tipo or "tema").strip(),
        "titulo": (titulo or "").strip(),
        "asunto": asunto,
        "prioridad": (prioridad or "Media").capitalize(),
        "tema": tema,
        "estado": _validar_estado(estado),
        "proximo_paso": proximo_paso,
        "fecha_limite": fecha_limite,
        "notas": notas,
    }
    if not row["titulo"]:
        raise ValueError("Se requiere un título.")
    rows = _leer()
    rows.append(row)
    _escribir(rows)
    return row


def listar(estado: str | None = None, prioridad: str | None = None) -> list[dict]:
    rows = _leer()
    if estado:
        rows = [r for r in rows if r.get("estado", "").lower() == estado.lower()]
    if prioridad:
        rows = [r for r in rows if r.get("prioridad", "").lower() == prioridad.lower()]
    return rows


def actualizar_estado(record_id: str, estado: str, notas: str = "") -> dict | None:
    rows = _leer()
    for r in rows:
        if r.get("id") == record_id:
            r["estado"] = _validar_estado(estado)
            if notas:
                r["notas"] = (r.get("notas", "") + " | " + notas).strip(" |")
            _escribir(rows)
            return r
    return None


def _escribir_markdown(rows: list[dict]) -> None:
    path = _md_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        "# Registro de seguimiento",
        "",
        f"_Actualizado: {dt.datetime.now().isoformat(timespec='minutes')}_",
        "",
        "| ID | Fecha | Tipo | Título | Prioridad | Tema | Estado | Próximo paso | Fecha límite |",
        "|----|-------|------|--------|-----------|------|--------|--------------|--------------|",
    ]
    for r in rows:
        titulo = (r.get("titulo") or "").replace("|", "\\|")
        lineas.append(
            f"| {r.get('id')} | {r.get('fecha_registro')} | {r.get('tipo')} "
            f"| {titulo} | {r.get('prioridad')} | {r.get('tema')} | {r.get('estado')} "
            f"| {r.get('proximo_paso')} | {r.get('fecha_limite')} |"
        )
    path.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def estadisticas() -> dict:
    rows = _leer()
    resumen: dict = {}
    for r in rows:
        est = r.get("estado", "Pendiente")
        resumen[est] = resumen.get(est, 0) + 1
    return {
        "total": len(rows),
        "por_estado": resumen,
        "csv": str(_csv_path()),
        "markdown": str(_md_path()),
    }
