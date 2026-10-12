# agent_get_started_project — asistente personal integrado (MCP + Graph + Dataverse)

Proyecto propio de automatización de trabajo: un asistente local en Python expuesto como
**MCP server** y consumido desde GitHub Copilot, más los agentes exportados de Power Platform
Copilot Studio. Todo el código de integración es mío.

## Qué hace

El asistente actúa como secretario ejecutivo / PM y se apoya en tres integraciones reales:

| Área | Herramientas MCP | Integración |
| --- | --- | --- |
| Correo | `correo_listar_inbox`, `correo_analizar_inbox`, `correo_clasificar`, `correo_proponer_borrador` | **Microsoft Graph**: lee la bandeja, clasifica por prioridad y crea el borrador de respuesta en Outlook (**nunca envía**) |
| Seguimiento | `seguimiento_registrar`, `seguimiento_listar`, `seguimiento_actualizar_estado`, `seguimiento_resumen` | Registro local en CSV + Markdown |
| Dataverse | `dataverse_consultar` | **Dataverse Web API** (`GET`, solo lectura/consulta) |
| Reportes | `reporte_generar` | Documentos locales (Markdown / Word) desde el registro |

Autenticación: **MSAL device-code** contra una app registrada en Azure AD — sin `client_secret`.

**Principios de seguridad del diseño:** nunca envía correo automáticamente (solo borradores),
Dataverse es de solo lectura y el registro de seguimiento vive local.

## Estructura

```
AsistenteLocal_MCP/            servidor MCP en Python (FastMCP)
  asistente/server.py            definición de las herramientas MCP
  asistente/auth/msal_client.py  autenticación delegada (device-code)
  asistente/correo/graph_client.py  Graph: leer inbox + crear borrador
  asistente/dataverse/cliente.py    Dataverse Web API (GET)
  asistente/catalogo/clasificador.py  motor de prioridad Alta/Media/Baja
  asistente/seguimiento/registro.py   registro local (CSV + Markdown)
  asistente/reportes/generador.py     reportes locales (md/docx)
  config/agente.yaml             persona, categorías y reglas de prioridad
Dev_agentes/                   export de los agentes de Copilot Studio (.mcs.yml)
clon_agente_AD/                copia de trabajo de esos mismos agentes
dashboard_metricas_email.html  tablero de métricas del correo
```

Los `.mcs.yml` son el export de Copilot Studio: agente, acciones que consumen MCP servers
(Office 365, GitHub, Teams), base de conocimiento y referencias de conexión.

## Puesta en marcha

1. `cd AsistenteLocal_MCP` → entorno virtual → `pip install -r requirements.txt`
2. `Copy-Item .env.example .env` y completar los valores (no se versiona el `.env`):
   `TENANT_ID`, `CLIENT_ID`, `GRAPH_USER_SCOPES`, y opcionalmente `DATAVERSE_URL` /
   `DATAVERSE_SCOPES`.
3. Registrar una app en Azure AD (**solo permisos delegados**): `Mail.Read`, `Mail.ReadWrite` y,
   para Dataverse, `user_impersonation` de Dynamics CRM. Con device-code no hace falta secreto.
4. Habilitar el servidor desde VS Code (`MCP: List MCP servers` → `asistente-personal`; ya está
   declarado en `.vscode/mcp.json`).

El detalle de cada paso está en [`AsistenteLocal_MCP/README.md`](AsistenteLocal_MCP/README.md).
