# CasaLista Voice API

Backend inicial de **CasaLista Voice**, solución para el hackathon de Colsubsidio enfocada en perfilar leads de vivienda antes del contacto comercial.

## Problema que resuelve

Colsubsidio recibe leads desde pauta digital, redes, formularios y WhatsApp sin un perfil suficiente. El equipo comercial pierde tiempo investigando afiliación, categoría, ingresos, ahorro, obligaciones, composición familiar, plazo de compra y compatibilidad con proyectos.

Esta API concentra esa información, calcula categoría A/B/C/D, determina la siguiente pregunta y genera una evaluación preliminar orientativa para el asesor.

## Alcance de esta fase (2.5)

Incluye:

- CRUD de leads en memoria
- Motor de siguiente pregunta por reglas
- Cálculo de categoría de afiliación A/B/C/D
- Evaluación preliminar de preparación/completitud
- Resumen estructurado para el asesor
- Recomendador explicable de proyectos (reglas ponderadas)
- Perfiles históricos por proyecto y matching de nombres
- Unificación canónica de proyectos duplicados
- Identificación simulada de afiliados conocidos (`mock_affiliation_service`)
- Precarga, confirmación y trazabilidad de campos
- Scripts para inspeccionar, preparar Excel, perfiles y proyectos canónicos

No incluye todavía:

- Seeds / importación Excel (fase siguiente)
- Sustitución definitiva de repositorios en memoria
- CRM, DataCrédito o sistemas reales de afiliación
- Autenticación real por OTP
- Aprobación de créditos
- Envío de correos o WhatsApp
- Modelos predictivos / redes neuronales
- Twilio (pendiente)


## Tecnologías

- Python 3.11+
- FastAPI
- Pydantic v2
- Uvicorn
- SQLAlchemy 2.x (async) + Alembic + Psycopg 3
- Pandas + OpenPyXL
- python-dotenv + pydantic-settings
- Pytest
- Ruff
- Mypy

## Requisitos

- Python 3.11 o superior
- pip
- (Opcional) rutas a los Excel del reto para los scripts de datos

## Creación del entorno virtual

```bash
cd backend
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### macOS / Linux

```bash
source venv/bin/activate
```

## Instalación de dependencias

```bash
pip install -r requirements.txt
```

## Configuración del `.env`

```bash
copy .env.example .env
```

En macOS/Linux:

```bash
cp .env.example .env
```

Variables principales:

```env
APP_NAME=CasaLista Voice API
APP_ENV=development
DEBUG=true
API_PREFIX=/api/v1
SMMLV=0
RAW_DATA_PATH=./data/raw
PROCESSED_DATA_PATH=./data/processed
CORS_ORIGINS=http://localhost:5173
PROJECTS_CATALOG_PATH=./data/processed/projects_catalog.json
PROJECT_PROFILES_PATH=./data/processed/project_profiles.json
PROJECT_ALIASES_PATH=./data/processed/project_aliases.json
PROJECTS_CANONICAL_PATH=./data/processed/projects_canonical.json
MOCK_AFFILIATES_PATH=./data/mock/mock_affiliates.json
```

Mock de compradores históricos (mismo esquema del CSV del reto, datos ficticios):

```bash
python scripts/generate_mock_buyers.py
python scripts/prepare_data.py --buyers data/mock/mock_buyers.csv --brochures "docs/Links brochures .xlsx"
```

Importante: configura `SMMLV` con el salario mínimo vigente antes de calcular categorías A/B/C. Si `SMMLV <= 0`, el cálculo salarial se bloquea con un error controlado. La categoría D (no afiliado) no requiere SMMLV.

## Ejecución de la API

Desde `backend/`:

```bash
uvicorn app.main:app --reload
```

Documentación:

- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- OpenAPI: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

## Ejecución de pruebas

```bash
pytest
```

## Calidad de código

```bash
ruff check .
mypy app
```

## Scripts de datos

Los scripts reciben rutas por argumento. No asumen rutas absolutas fijas ni modifican los Excel originales.

### Inspección

```bash
python scripts/inspect_data.py --buyers "RUTA_ARCHIVO" --brochures "RUTA_ARCHIVO"
```

### Preparación

```bash
python scripts/prepare_data.py --buyers "RUTA_ARCHIVO" --brochures "RUTA_ARCHIVO"
```

Acepta Excel (`.xlsx`) o CSV. Para el export del hackathon:

```bash
python scripts/prepare_data.py --buyers "docs/hackathon_VIVIENDAv2.xlsx - CV_SSS_VIV_PENETRACION_PERFIL_C.csv"
```

Salidas en `data/processed/`:

- `buyers_clean.csv`
- `buyers_clean.json`
- `buyers_seed.json` (listo para `ingestion.normalized_buyer_records`)
- `projects_catalog.json`
- `data_quality_report.json`
- `column_mapping.json`

Normalizaciones específicas del export:

- Afiliación inferida desde `PERIODO_AFILIADO` (vacío = no afiliado)
- `FECHA_DESISTIMIENTO` como `Si`/`No` → `desistio_normalizado`
- `VLR_VIVIENDA` escalado `/10000` por formato de exportación
- `CATEGORIA` / `SEGMENTO_POBLACIONAL` ofuscados se conservan en `normalized_data` (no se fuerzan a A/B/C/D)

Nota: la base histórica contiene principalmente compradores y desistimientos. No representa todos los leads que nunca compraron y no debe usarse como predicción directa de conversión.

## Recomendador de proyectos

El recomendador es **determinístico y explicable**. Compara el perfil del lead con perfiles históricos por proyecto y devuelve hasta 3 compatibles (máximo 10) con puntaje, razones, advertencias y confianza.

### Generar perfiles históricos

```bash
python scripts/build_project_profiles.py --buyers data/processed/buyers_clean.csv --projects data/processed/projects_catalog.json --output data/processed/project_profiles.json
```

También genera `data/processed/project_matching_report.json` con emparejamientos exactos, aproximados, ambiguos y sin coincidencia.

### Consultar recomendaciones

```bash
curl "http://localhost:8000/api/v1/leads/{LEAD_ID}/recommendations?limit=3"
```

Parámetros opcionales:

- `limit` (1-10, default 3)
- `include_unavailable` (default false)
- `min_score` (0-100)

### Cómo se calcula el puntaje

Pesos configurables en `RECOMMENDATION_WEIGHTS`:

| Criterio | Peso |
|---|---:|
| Ubicación deseada | 25 |
| Compatibilidad económica/salarial | 20 |
| Afiliación e histórico | 15 |
| Segmento comercial | 15 |
| Composición del hogar | 10 |
| Proyecto de interés | 10 |
| Preferencias adicionales | 5 |

Si un criterio no puede evaluarse, **no suma cero**: se excluye del denominador y se reduce la confianza.

### Nivel de confianza

- `low` / `medium` / `high`
- Depende de campos del lead, criterios evaluados y tamaño de muestra histórica
- Muestras pequeñas no alcanzan `high` aunque el puntaje sea alto

### Advertencias importantes

- No predice quién comprará
- No aprueba créditos ni calcula cuota hipotecaria oficial
- La compatibilidad económica es solo orientativa
- La base tiene compradores históricos y desistimientos, no todos los leads originales
- No usa género, edad ni estrato para puntuar

## Canonicalización de proyectos

Variantes del mismo proyecto (por ejemplo `Agrupación De Vivienda Monguí`, `MONGUI`, `Monguí / brochure`) se unifican bajo un `canonical_project_id`.

### Generar catálogo canónico

```bash
python scripts/build_canonical_projects.py
```

Salidas:

- `data/processed/projects_canonical.json`
- `data/processed/project_canonicalization_report.json`

Alias editables a mano:

- `data/processed/project_aliases.json`

Reglas:

- Normaliza minúsculas, tildes y espacios
- Solo fusiona cuando el alias es claro o está definido manualmente
- Coincidencias ambiguas quedan en el reporte, sin fusión automática
- El recomendador deduplica por `canonical_project_id` y muestra el nombre canónico

## Identidad simulada (afiliado conocido)

Los perfiles utilizados en esta demostración son completamente ficticios. La base histórica proporcionada por el reto está anonimizada y no permite identificar personas reales.

El backend depende de la interfaz `AffiliationLookupProvider`. La implementación actual es `MockAffiliationLookupProvider` (`mock_affiliation_service`). Para una integración real, se reemplaza el provider sin cambiar endpoints ni el flujo del lead.

### Documentos ficticios de demo

| Documento | Escenario |
|-----------|-----------|
| `1000000001` | Afiliada categoría A con datos precargados (Laura Demo) |
| `1000000002` | Afiliado categoría B sin personas a cargo |
| `1000000003` | Afiliada categoría C |
| `1000000004` | Conocido con datos incompletos |
| `1000000005` | Conocido no afiliado |
| `1000000006` | Afiliación pendiente de confirmación |
| `9999999999` | Documento inexistente → lead nuevo |

Listado rápido (solo `development`):

```bash
curl http://localhost:8000/api/v1/demo/identities
```

### Flujo afiliado conocido

1. `POST /api/v1/identity/lookup` — consulta sin crear lead
2. `POST /api/v1/leads/from-identity` con `data_consent: true` — crea lead precargado
3. `GET /api/v1/leads/{id}/next-question` — pide confirmación de datos sensibles/cambiantes
4. `POST /api/v1/leads/{id}/confirm-prefilled-data` — confirma o corrige
5. Continúa con ingreso del hogar, ahorro, obligaciones, etc.
6. Recomendaciones y resumen del asesor (con `identity_context`)

Sin consentimiento no se precarga información financiera. La identidad nunca se marca como verificada (no hay OTP).

### Flujo lead nuevo

1. Lookup de un documento inexistente → `match_status: new_lead`
2. Crear lead con `from-identity` o `POST /leads` tradicional
3. Sigue el cuestionario completo (afiliación, salario, hogar, etc.)

### Sustitución del mock por integración real

1. Implementar `AffiliationLookupProvider` contra el sistema autorizado de Colsubsidio
2. Registrar el provider real en `app/api/deps.py`
3. Mantener consentimiento, confirmación de campos y `identity_verified=false` hasta OTP/auth real
4. Retirar o deshabilitar `GET /demo/identities` fuera de desarrollo

## OpenAI Realtime (voz desde el navegador)

El backend mintá un token efímero para el navegador. La clave `OPENAI_API_KEY` permanece solo en el servidor.

### Variables

```env
OPENAI_API_KEY=
OPENAI_REALTIME_MODEL=gpt-realtime-2.1
OPENAI_REALTIME_VOICE=coral
OPENAI_REALTIME_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
OPENAI_REALTIME_ENABLED=true
OPENAI_REQUEST_TIMEOUT_SECONDS=20
```

### Endpoints de voz

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/realtime/client-secret` | Token efímero (nunca expone la API key) |
| GET | `/api/v1/voice/leads/{id}/context` | Contexto compacto para el agente |
| POST | `/api/v1/voice/leads/{id}/answer` | Respuesta validada (campo = pregunta activa) |
| POST | `/api/v1/voice/leads/{id}/complete` | Evalúa, recomienda y cierra |

El agente no puede modificar campos arbitrarios: el backend valida el campo esperado y reutiliza los servicios existentes.

### Limitaciones

- Sin Twilio / llamadas telefónicas todavía.
- Sin persistencia de audio ni transcripciones.
- Costos variables según uso de OpenAI.
- Si `OPENAI_API_KEY` falta o Realtime está deshabilitado, el frontend puede continuar en modo mock/texto.

## Persistencia PostgreSQL (infraestructura)

Esta fase agrega la infraestructura de base de datos **sin** sustituir todavía los repositorios en memoria (`PERSISTENCE_PROVIDER=memory`).

### Arquitectura de schemas

```text
core | identity | affiliation | leads | housing
qualification | recommendations | conversations
commercial | ingestion | audit | analytics
```

Relaciones principales (texto):

```text
identity.persons
  └── leads.leads
        ├── leads.lead_profiles (1:1)
        ├── qualification.assessments
        ├── recommendations.recommendation_runs
        └── conversations.conversation_sessions

housing.projects
  └── recommendations.recommendation_items

ingestion.import_batches
  └── housing.project_historical_profiles.source_batch_id
```

### Dependencias nuevas

```text
SQLAlchemy>=2.0,<2.1
alembic>=1.18,<2
psycopg[binary]>=3.2,<4
```

### Variables de entorno

```env
DATABASE_ENABLED=true
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/home_30x
DATABASE_ADMIN_URL=
DATABASE_NAME=home_30x
DATABASE_ECHO=false
PERSISTENCE_PROVIDER=memory
TEST_DATABASE_URL=
```

Reglas:

- `DATABASE_URL` la usan SQLAlchemy y Alembic.
- `DATABASE_ADMIN_URL` solo para crear la base (opcional).
- `PERSISTENCE_PROVIDER=memory` mantiene la API actual en memoria.
- Las pruebas destructivas usan únicamente `TEST_DATABASE_URL`.

### Permisos requeridos en `home_30x`

El usuario de migraciones necesita `CREATE` en la base (hoy `home_30x` es owned by `postgres`).

Como rol `postgres` / owner:

```sql
GRANT CONNECT, CREATE ON DATABASE home_30x TO vanvar_plane_dev_user;
-- preferible en hackathon:
-- ALTER DATABASE home_30x OWNER TO vanvar_plane_dev_user;
```

Ver también [`ops/postgres/grant_migrator_on_home_30x.sql.example`](ops/postgres/grant_migrator_on_home_30x.sql.example).

### Crear la base (opcional)

PowerShell:

```powershell
cd backend
python scripts/bootstrap_database.py --check-only
```

Linux/macOS:

```bash
cd backend
python scripts/bootstrap_database.py --check-only
```

### Migraciones

```powershell
cd backend
python -m alembic upgrade head
python -m alembic current --check-heads
python -m alembic check
python scripts/verify_migrations.py
```

Downgrade:

```powershell
python -m alembic downgrade -1
python -m alembic downgrade base
```

Futuras migraciones:

```powershell
python -m alembic revision --autogenerate -m "description"
python -m alembic upgrade head
```

### Health checks

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Salud del servicio (no depende de PostgreSQL) |
| GET | `/health/database` | Conexión, Alembic head, schemas y extensiones |

### Convenciones

- Tablas/columnas en `snake_case`, schemas explícitos (nunca `public` para negocio).
- UUID nativo + `gen_random_uuid()`.
- Dinero en `NUMERIC(14,2)` (nunca `FLOAT`).
- JSONB solo para metadata flexible.
- Identificadores sensibles: hash + ciphertext (sin texto plano).
- Constraints e índices con nombre.

### Roles (ejemplo)

Ver [`ops/postgres/roles_and_grants.sql.example`](ops/postgres/roles_and_grants.sql.example). No se ejecuta automáticamente.

### Limitaciones de esta fase

- Los leads de la API siguen en memoria.
- No hay seeds ni importación Excel.
- No hay cifrado real de PII (solo columnas preparadas).
- En Windows, Alembic/psycopg async usa `SelectorEventLoop`.

### Seeds / carga histórica

Tras `prepare_data` y `build_project_profiles`:

```bash
python scripts/seed_historical_data.py --dry-run
python scripts/seed_historical_data.py
```

Reemplazar un seed previo:

```bash
python scripts/seed_historical_data.py --force
```

Carga en PostgreSQL:

- `housing.projects` (+ etapas, precios, assets)
- `ingestion.import_batches` + `normalized_buyer_records`
- `housing.project_historical_profiles` + `project_profile_distributions`
- `ingestion.seed_executions` (idempotencia por checksum)

Defaults de rutas: `data/processed/buyers_seed.json`, `projects_catalog.json`, `project_profiles.json`.

### Brochures / 360

```bash
python scripts/prepare_data.py --buyers "docs/....csv" --brochures "docs/Links brochures .xlsx"
python scripts/seed_brochure_assets.py --dry-run
python scripts/seed_brochure_assets.py
```

Actualiza `project_assets` (brochure + tour_360), `project_locations` y `project_aliases` emparejando por nombre (no requiere `--force` del seed histórico).

### Recuperación de errores comunes

| Error | Acción |
|-------|--------|
| `permission denied for database` | Otorgar `CREATE` o ownership sobre `home_30x` |
| extensión no crea | Crear `pgcrypto/citext/unaccent/pg_trgm` como superuser |
| `TEST_DATABASE_URL` vacío | Las pruebas de migración se omiten a propósito |
| ProactorEventLoop (Windows) | Usar el `env.py` del repo (ya ajustado) |

## Endpoints principales


| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Salud del servicio |
| GET | `/health/database` | Salud de PostgreSQL (degraded si no hay permisos/migraciones) |
| POST | `/api/v1/leads` | Crear lead |
| POST | `/api/v1/leads/from-identity` | Crear lead desde identidad simulada |
| POST | `/api/v1/leads/{id}/confirm-prefilled-data` | Confirmar/corregir precarga |
| GET | `/api/v1/leads` | Listar leads |
| GET | `/api/v1/leads/{id}` | Obtener lead |
| PATCH | `/api/v1/leads/{id}` | Actualizar parcialmente |
| DELETE | `/api/v1/leads/{id}` | Eliminar (solo desarrollo) |
| GET | `/api/v1/leads/{id}/next-question` | Siguiente pregunta |
| POST | `/api/v1/leads/{id}/evaluate` | Evaluación preliminar |
| GET | `/api/v1/leads/{id}/summary` | Resumen para asesor |
| GET | `/api/v1/leads/{id}/recommendations` | Recomendaciones de proyectos |
| POST | `/api/v1/identity/lookup` | Consulta de afiliación simulada |
| GET | `/api/v1/demo/identities` | Identidades ficticias (solo development) |
| GET | `/api/v1/projects` | Listar catálogo de proyectos |
| GET | `/api/v1/projects/{id}` | Obtener proyecto |
| POST | `/api/v1/evaluation/affiliation-category` | Calcular categoría A/B/C/D |

## Ejemplos con curl

```bash
curl http://localhost:8000/health
```

```bash
curl -X POST http://localhost:8000/api/v1/leads ^
  -H "Content-Type: application/json" ^
  -d "{\"nombre\":\"Ana Pérez\",\"consentimiento\":true,\"afiliado\":true,\"canal_origen\":\"whatsapp\"}"
```

```bash
curl -X POST http://localhost:8000/api/v1/evaluation/affiliation-category ^
  -H "Content-Type: application/json" ^
  -d "{\"afiliado\":true,\"salario_mensual\":2500000,\"afiliacion_confirmada\":false}"
```

```bash
curl "http://localhost:8000/api/v1/leads/{LEAD_ID}/recommendations?limit=3"
```

```bash
curl "http://localhost:8000/api/v1/projects?disponible=true&nombre=mongui"
```

### Identidad simulada

```bash
curl -X POST http://localhost:8000/api/v1/identity/lookup ^
  -H "Content-Type: application/json" ^
  -d "{\"document_type\":\"CC\",\"document_number\":\"1000000001\"}"
```

```bash
curl -X POST http://localhost:8000/api/v1/leads/from-identity ^
  -H "Content-Type: application/json" ^
  -d "{\"document_type\":\"CC\",\"document_number\":\"1000000001\",\"data_consent\":true}"
```

```bash
curl -X POST http://localhost:8000/api/v1/leads/{LEAD_ID}/confirm-prefilled-data ^
  -H "Content-Type: application/json" ^
  -d "{\"confirmations\":{\"salario_mensual\":{\"confirmed\":true},\"personas_a_cargo\":{\"confirmed\":false,\"new_value\":2}}}"
```

## Limitaciones actuales

- Persistencia operativa de leads todavía en memoria (`PERSISTENCE_PROVIDER=memory`); la estructura PostgreSQL ya existe
- La afiliación conocida es **simulada**; no consulta sistemas reales de Colsubsidio
- Sin OTP ni verificación real de identidad
- Sin integración real de buró de crédito
- El puntaje de readiness mide preparación/completitud del perfil, no capacidad hipotecaria oficial
- El catálogo actual no trae municipio/departamento/ubicación confiables
- Los precios históricos (`VLR_VIVIENDA`) tienen escala no confiable y no se usan para excluir proyectos
- La restricción comercial 90/10 está modelada como contexto regulatorio, sin contador real de ventas
- Sin seeds ni carga Excel todavía

## Próximos pasos

1. Otorgar permisos de migrador sobre `home_30x` y aplicar `alembic upgrade head`
2. Seeds + normalización histórica
3. Repositorios PostgreSQL detrás de `PERSISTENCE_PROVIDER`
4. Sustituir el mock de afiliación por integración autorizada
5. Integración Twilio
6. Autenticación/OTP para verificación de identidad
