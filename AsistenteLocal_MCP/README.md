# Asistente Personal MCP (PM / Jefe de Operaciones)

Asistente local que opera desde tu escritorio como un **secretario / project manager**. Se registra como
**MCP server** en VS Code y se usa desde **GitHub Copilot**.

## Capacidades (MVP)

| Área | Qué hace | Integración |
|------|----------|-------------|
| Correo | Lista la bandeja de entrada, **clasifica** correos por prioridad (Alta/Media/Baja) y tema, y **propone borradores** de respuesta (los crea en Outlook **Drafts**, nunca los envía) | Microsoft Graph (solo lectura + crear borradores) |
| Seguimiento | Registro de seguimiento de proyectos/temas/correos en **archivo local** (CSV + Markdown) | Local `data/seguimiento/` |
| Dataverse | **Solo lectura/consulta** de tablas para enriquecer respuestas/reportes | Dataverse Web API (GET) |
| Reportes | Genera **documentos locales** (Markdown/Word) a partir del registro y consultas | Local `data/reportes/` |

**Principios de seguridad:**
- Nunca envía correos automáticamente: solo crea borradores que tú apruebas en Outlook.
- Dataverse solo se **consulta** (no se crean ni modifican tablas/registros).
- El registro de seguimiento vive localmente en este proyecto.

## Estructura

```
AsistenteLocal_MCP/
├── config/agente.yaml        # Persona + categorías + reglas de prioridad
├── asistente/
│   ├── server.py             # Servidor MCP (FastMCP) con las herramientas
│   ├── config.py             # Carga de configuración y entorno
│   ├── auth/msal_client.py   # Autenticación delegada (device-code) MSAL
│   ├── catalogo/clasificador.py  # Motor de prioridad Alta/Media/Baja
│   ├── correo/graph_client.py    # Graph: leer inbox + crear borrador
│   ├── dataverse/cliente.py      # Dataverse Web API (solo lectura)
│   ├── seguimiento/registro.py   # Registro local CSV + Markdown
│   └── reportes/generador.py     # Documentos locales (md/docx)
├── data/
│   ├── seguimiento/          # registro.csv + REGISTRO.md
│   └── reportes/             # documentos generados
├── .env                      # credenciales (NO versionar)
└── .vscode/mcp.json          # registro del MCP server
```

## Configuración (5 pasos)

### 1. Instalar dependencias
```powershell
cd "AsistenteLocal_MCP"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Crear el `.env`
```powershell
Copy-Item .env.example .env
```
Completa los valores (ver abajo).

### 3. Registrar una app en Azure (para Graph y Dataverse)
En [aka.ms/aadappregistrations](https://aka.ms/aadappregistrations):
1. **Nuevo registro** → nombre `AsistentePersonalLocal`, cuentas de este directorio.
2. En **Permisos de API** agrega (delegados):
   - `Microsoft Graph` → `Mail.Read`, `Mail.ReadWrite` (para leer y crear borradores).
   - `Dynamics CRM` (Dataverse) → `user_impersonation` *(si vas a consultar Dataverse)*.
3. **Conceder consentimiento de administrador** (si tu tenant lo exige).
4. Copia el `Application (client) ID` y el `Directory (tenant) ID` al `.env`.

> Para tu buzón personal con **device-code** no se necesita `client_secret`.

### 4. Variables del `.env`
| Variable | Descripción |
|----------|-------------|
| `TENANT_ID` | Directorio (tenant) ID |
| `CLIENT_ID` | Application (client) ID de la app |
| `GRAPH_USER_SCOPES` | `Mail.Read Mail.ReadWrite` |
| `DATAVERSE_URL` | URL del entorno (p. ej. `https://org123.crm.dynamics.com`) — opcional |
| `DATAVERSE_SCOPES` | `https://<org>.crm.dynamics.com/.default` — opcional |

### 5. Registrar el MCP server y usarlo desde Copilot
El archivo `.vscode/mcp.json` ya define el servidor. Actívalo desde la paleta:
**"MCP: List MCP servers"** → habilitar `asistente-personal`.

En el primer uso de una herramienta que requiera Graph/Dataverse, el server iniciará el
flujo **device-code** (te mostrará un código para autenticar en `microsoft.com/devicelogin`).
El token se guarda en `data/token_cache.bin`.

## Uso desde Copilot (ejemplos)
- *"Clasifica los últimos 20 correos de mi bandeja por prioridad y dime cuáles son urgentes."*
- *"Crea un borrador en Outlook respondiendo a [remitente] confirmando la reunión."*
- *"Registra seguimiento del tema X con prioridad Alta y fecha límite 10/09."*
- *"Genera un reporte semanal de seguimiento en la carpeta data/reportes."*
- *"Consulta el estado de las work orders en Dataverse (tabla crc3d_workorder)."*

## Probar sin credenciales
El clasificador, el registro local y el generador de reportes funcionan **sin conexión**.
Para probar el MCP sin autenticarte puedes usar las herramientas de seguimiento y reportes.
