"""Cliente de autenticación MSAL (device-code) para Graph y Dataverse.

Usa flujo de *device code*: el usuario autentica una sola vez y el token se
guarda en `data/token_cache.bin`. Los tokens se renuevan automáticamente.
"""
from __future__ import annotations

from pathlib import Path

import msal

from ..config import config

# Un scopes = un "recurso" con su propio token (Graph vs Dataverse).
_AUTHORITY = "https://login.microsoftonline.com/"


class NoConfiguradoError(RuntimeError):
    """Faltan credenciales (TENANT_ID / CLIENT_ID) en el .env."""


class _AppMSAL:
    """Wrapper perezoso sobre PublicClientApplication con caché de tokens."""

    def __init__(self, scope_key: str, scopes: list[str], cache_path: Path):
        self.scope_key = scope_key
        self.scopes = scopes
        self.cache_path = cache_path
        self._app: msal.PublicClientApplication | None = None

    def _verificar_env(self) -> None:
        if not config.tenant_id or not config.client_id:
            raise NoConfiguradoError(
                "Faltan TENANT_ID y/o CLIENT_ID en el .env. "
                "Consulta README.md, paso 3 y 4."
            )

    def _app_msal(self) -> msal.PublicClientApplication:
        if self._app is None:
            self._verificar_env()
            authority = f"{_AUTHORITY}{config.tenant_id}"
            self._app = msal.PublicClientApplication(
                client_id=config.client_id,
                authority=authority,
                token_cache=self._cargar_cache(),
            )
        return self._app

    def _cargar_cache(self) -> msal.SerializableTokenCache:
        cache = msal.SerializableTokenCache()
        if self.cache_path.exists():
            try:
                cache.deserialize(self.cache_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return cache

    def _guardar_cache(self) -> None:
        app = self._app
        if app is None:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            app.token_cache.serialize(), encoding="utf-8"
        )

    def get_token(self, force: bool = False) -> str:
        app = self._app_msal()
        # Buscar token válido en caché
        cuentas = app.get_accounts()
        if cuentas and not force:
            resultado = app.acquire_token_silent(self.scopes, account=cuentas[0])
            if resultado and "access_token" in resultado:
                return resultado["access_token"]
        # Device code
        flujo = app.initiate_device_flow(scopes=self.scopes)
        if "user_code" not in flujo:
            raise RuntimeError(f"Error iniciando device flow: {flujo}")
        print(
            "\n=== Autenticación requerida ===\n"
            f"1) Abre: {flujo['verification_uri']}\n"
            f"2) Introduce el código: {flujo['user_code']}\n"
            "(Puede tardar; espera a que se confirme...)\n"
        )
        resultado = app.acquire_token_by_device_flow(flujo)
        if "access_token" not in resultado:
            raise RuntimeError(f"Autenticación fallida: {resultado.get('error_description')}")
        self._guardar_cache()
        return resultado["access_token"]

    def limpiar(self) -> None:
        if self.cache_path.exists():
            self.cache_path.unlink()
        self._app = None


# Instancias por recurso
_graph = _AppMSAL("graph", config.graph_scopes, config.token_cache_path)


def get_graph_token(force: bool = False) -> str:
    return _graph.get_token(force=force)


def _dataverse_app() -> _AppMSAL | None:
    if not config.dataverse_url or not config.dataverse_scopes:
        return None
    # caché separada para dataverse
    return _AppMSAL(
        "dataverse",
        config.dataverse_scopes,
        config.token_cache_path.with_name("token_cache_dataverse.bin"),
    )


def get_dataverse_token(force: bool = False) -> str:
    app = _dataverse_app()
    if app is None:
        raise NoConfiguradoError(
            "Dataverse no configurado. Revisa DATAVERSE_URL en el .env."
        )
    return app.get_token(force=force)
