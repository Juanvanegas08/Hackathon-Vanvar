# CasaLista Voice API

Backend inicial de **CasaLista Voice**, solución para el hackathon de Colsubsidio enfocada en perfilar leads de vivienda antes del contacto comercial.

## Problema que resuelve

Colsubsidio recibe leads desde pauta digital, redes, formularios y WhatsApp sin un perfil suficiente. El equipo comercial pierde tiempo investigando afiliación, categoría, ingresos, ahorro, obligaciones, composición familiar, plazo de compra y compatibilidad con proyectos.

Esta API concentra esa información, calcula categoría A/B/C/D, determina la siguiente pregunta y genera una evaluación preliminar orientativa para el asesor.

## Alcance de esta fase

Incluye:

- CRUD de leads en memoria
- Motor de siguiente pregunta por reglas
- Cálculo de categoría de afiliación A/B/C/D
- Evaluación preliminar de preparación/completitud
- Resumen estructurado para el asesor
- Modelos listos para un recomendador de proyectos
- Scripts para inspeccionar y preparar Excel históricos

No incluye todavía:

- OpenAI / agente de voz
- Twilio
- Frontend
- CRM, DataCrédito o sistemas reales de afiliación
- Aprobación de créditos
- Envío de correos o WhatsApp
- Algoritmo de recomendación de proyectos
- PostgreSQL / Supabase

## Tecnologías

- Python 3.11+
- FastAPI
- Pydantic v2
- Uvicorn
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

Salidas en `data/processed/`:

- `buyers_clean.csv`
- `buyers_clean.json`
- `projects_catalog.json`
- `data_quality_report.json`
- `column_mapping.json`

Nota: la base histórica contiene principalmente compradores y desistimientos. No representa todos los leads que nunca compraron y no debe usarse como predicción directa de conversión.

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Salud del servicio |
| POST | `/api/v1/leads` | Crear lead |
| GET | `/api/v1/leads` | Listar leads |
| GET | `/api/v1/leads/{id}` | Obtener lead |
| PATCH | `/api/v1/leads/{id}` | Actualizar parcialmente |
| DELETE | `/api/v1/leads/{id}` | Eliminar (solo desarrollo) |
| GET | `/api/v1/leads/{id}/next-question` | Siguiente pregunta |
| POST | `/api/v1/leads/{id}/evaluate` | Evaluación preliminar |
| GET | `/api/v1/leads/{id}/summary` | Resumen para asesor |
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

## Limitaciones actuales

- Persistencia solo en memoria (se pierde al reiniciar)
- Sin integración real de afiliación ni buró de crédito
- El puntaje mide preparación/completitud del perfil, no capacidad hipotecaria oficial
- No hay recomendador de proyectos ni agente de voz
- La restricción comercial 90/10 está modelada como configuración futura, sin contador de ventas

## Próximos pasos

1. Recomendador de proyectos a partir del catálogo histórico
2. Persistencia en PostgreSQL / Supabase
3. Agente de voz conversacional
4. Integración Twilio
5. Confirmación oficial de afiliación y enriquecimiento controlado de datos
