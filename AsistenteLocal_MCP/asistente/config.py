"""Carga de configuración: agente.yaml + variables de entorno (.env)."""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Raíz del proyecto: se puede sobreescribir con ASISTENTE_PROJECT_ROOT
PROJECT_ROOT = Path(
    os.environ.get("ASISTENTE_PROJECT_ROOT")
    or Path(__file__).resolve().parents[1]
)

CONFIG_PATH = PROJECT_ROOT / "config" / "agente.yaml"
DATA_DIR = PROJECT_ROOT / "data"


def _cargar_dotenv() -> None:
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)


class Config:
    """Acceso unificado a configuración YAML + entorno."""

    def __init__(self, agente: dict | None = None) -> None:
        _cargar_dotenv()
        self.agente = agente or _cargar_yaml(CONFIG_PATH)
        self._crear_estructura_local()

    # --- propiedades de entorno ---
    @property
    def tenant_id(self) -> str:
        return os.environ.get("TENANT_ID", "").strip()

    @property
    def client_id(self) -> str:
        return os.environ.get("CLIENT_ID", "").strip()

    @property
    def graph_scopes(self) -> list[str]:
        raw = os.environ.get("GRAPH_USER_SCOPES", "Mail.Read Mail.ReadWrite")
        return raw.split()

    @property
    def dataverse_url(self) -> str:
        return os.environ.get("DATAVERSE_URL", "").strip().rstrip("/")

    @property
    def dataverse_scopes(self) -> list[str]:
        raw = os.environ.get("DATAVERSE_SCOPES", "")
        if raw.strip():
            return [s.strip() for s in raw.split(",") if s.strip()]
        if self.dataverse_url:
            return [f"{self.dataverse_url}/.default"]
        return []

    @property
    def seguimiento_dir(self) -> Path:
        override = os.environ.get("SEGUIMIENTO_DIR")
        return Path(override) if override else (DATA_DIR / "seguimiento")

    @property
    def reportes_dir(self) -> Path:
        override = os.environ.get("REPORTES_DIR")
        return Path(override) if override else (DATA_DIR / "reportes")

    @property
    def token_cache_path(self) -> Path:
        return DATA_DIR / "token_cache.bin"

    # --- helpers YAML ---
    def prioridad_alta(self) -> list[str]:
        d = self.agente.get("prioridad_alta", {})
        urgencia = d.get("urgencia", [])
        dominios = d.get("dominios", [])
        return urgencia, dominios

    def prioridad_media(self) -> list[str]:
        return self.agente.get("prioridad_media", [])

    def prioridad_baja(self) -> list[str]:
        return self.agente.get("prioridad_baja", [])

    def temas(self) -> list[dict]:
        return self.agente.get("temas", [])

    def estados_seguimiento(self) -> list[str]:
        return self.agente.get("seguimiento", {}).get("estados", [])

    def _crear_estructura_local(self) -> None:
        (self.seguimiento_dir).mkdir(parents=True, exist_ok=True)
        (self.reportes_dir).mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)


def _cargar_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


# Instancia por defecto (singleton ligero).
config = Config()
