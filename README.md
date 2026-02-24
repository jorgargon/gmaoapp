# GMAO — Gestión de Mantenimiento Asistido por Ordenador

Sistema web de gestión de mantenimiento desarrollado con Flask. Versión **1.0.0**.

---

## Características principales

- **Órdenes de Trabajo** — Creación, seguimiento y cierre de OTs correctivas y preventivas
- **Mantenimiento Preventivo** — Gamas de mantenimiento con programación automática por frecuencia
- **Gestión de Activos** — Árbol jerárquico: Empresa › Planta › Zona › Línea › Máquina › Elemento
- **Recambios y Stock** — Control de inventario con registro de consumos por OT
- **Indicadores y KPIs** — Dashboard con gráficos, KPIs EN 15341 e informes exportables a Excel
- **Interfaz Móvil** — Versión optimizada para tablets y móviles para técnicos en campo
- **Control de acceso** — Roles: Técnico, Responsable, Admin (autenticación JWT)

---

## Tecnologías

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.13 + Flask 3.1 |
| Base de datos | SQLite (vía SQLAlchemy 2.0) |
| Autenticación | Flask-JWT-Extended 4.7 (cookies seguras) |
| Frontend | HTML5 + CSS personalizado + jQuery + ApexCharts |
| Exportación | openpyxl + xlsxwriter |
| Iconos | Font Awesome 6.4 |

---

## Estructura del proyecto

```
gmaoAPP/
├── app.py                      # Aplicación Flask principal (~3000 líneas)
├── models.py                   # Modelos SQLAlchemy
├── requirements.txt            # Dependencias Python (versiones fijadas)
│
├── blueprints/
│   ├── indicadores/            # Módulo Informes & KPIs (EN 15341)
│   │   ├── routes.py           # Rutas /informes/*
│   │   ├── services.py         # Lógica de KPIs y exportación Excel
│   │   └── dashboard_services.py  # Datos para gráficos del dashboard
│   └── mobile/
│       ├── routes.py           # Rutas /movil/* + mini-API
│       └── __init__.py
│
├── templates/
│   ├── base.html               # Layout principal (desktop)
│   ├── login.html
│   ├── home.html               # Dashboard con gráficos y calendario
│   ├── ordenes.html            # Listado y detalle de OTs
│   ├── preventivo.html         # Mantenimiento preventivo
│   ├── assets.html             # Árbol de activos
│   ├── recambios.html          # Gestión de recambios
│   ├── configuracion.html      # Configuración general (Admin)
│   ├── indicadores/            # Dashboards, KPIs e informes
│   └── mobile/                 # Interfaz móvil para técnicos
│
├── static/
│   ├── styles.css              # CSS principal (sin Bootstrap)
│   ├── css/mobile.css          # CSS interfaz móvil
│   ├── js/ordenes-common.js    # JS compartido para OTs
│   └── images/ + icons/        # Logo e iconos de jerarquía
│
├── scripts/
│   ├── import_activos.py       # Importación masiva de activos desde CSV
│   └── initData.py             # Carga de datos de prueba (desarrollo)
│
├── docs/
│   ├── CHANGELOG.md
│   ├── MANUAL_USUARIO.md       # Manual de usuario
│   └── plantilla_importacion_activos.csv
│
└── instance/
    └── gmao.db                 # Base de datos SQLite
```

---

## Instalación y puesta en marcha

### Requisitos previos

- Python 3.11 o superior
- pip

### 1. Clonar o copiar el proyecto

```bash
cd /ruta/al/directorio
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Crear un fichero `.env` en la raíz del proyecto (o exportar variables):

```bash
export SECRET_KEY="cambia-esto-por-una-clave-segura"
export JWT_SECRET_KEY="otra-clave-secreta-para-jwt"
```

> En `app.py` existe una clave por defecto para desarrollo. **Cambiarla en producción.**

### 4. Inicializar la base de datos

La base de datos se crea automáticamente en `instance/gmao.db` al arrancar la aplicación por primera vez (`db.create_all()`).

Para cargar datos de prueba:

```bash
python scripts/initData.py
```

### 5. Arrancar el servidor

```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`.

Para acceder desde otros dispositivos en la misma red (ej. tablets):

```bash
flask run --host=0.0.0.0 --port=5000
```

---

## Acceso por roles

| Rol | Acceso |
|-----|--------|
| **Admin** | Acceso completo: configuración, usuarios, todos los módulos |
| **Responsable** | OTs, preventivo, activos, recambios, informes, KPIs |
| **Técnico** | OTs y preventivo (iniciar/pausar/cerrar parcial), recambios (consumos) |

El usuario admin por defecto es `admin` / `admin` (cambiar tras la primera configuración).

---

## Interfaz móvil

Los técnicos que accedan desde un dispositivo móvil o tablet son redirigidos automáticamente a la versión móvil en `/movil/`.

Desde un PC, se puede acceder manualmente a `/movil/` para desarrollo y pruebas.

---

## Importación masiva de activos

Para cargar la jerarquía de equipos desde un CSV:

```bash
python scripts/import_activos.py docs/plantilla_importacion_activos.csv
```

Ver `docs/plantilla_importacion_activos.csv` para el formato requerido.

---

## Modelos principales

| Modelo | Descripción |
|--------|-------------|
| `Empresa / Planta / Zona / Linea / Maquina / Elemento` | Jerarquía de activos |
| `OrdenTrabajo` | OT con tipo, estado, técnico, tiempos, costes |
| `GamaMantenimiento` | Gama de mantenimiento con tareas y checklist |
| `AsignacionGama` | Programación de gama a equipo con frecuencia |
| `RegistroTiempo` | Registros de imputación de horas por técnico y OT |
| `ConsumoRecambio` | Consumo de recambios por OT |
| `Recambio / MovimientoStock` | Inventario y trazabilidad de stock |
| `TareaRealizada` | Persistencia de tareas completadas en OTs |
| `TipoIntervencion` | Tipos de OT configurables (correctivo, preventivo, mejora…) |
| `ConfiguracionGeneral` | Parámetros globales de la aplicación (clave/valor) |
| `Usuario / Tecnico` | Usuarios con rol y perfil de técnico |

---

## Notas de desarrollo

- **Sin framework de migraciones**: los cambios de esquema se aplican directamente con `db.create_all()` o sentencias SQL manuales. Para producción, considerar Alembic.
- **Monolítico por diseño**: `app.py` contiene todas las rutas principales. Los módulos Indicadores y Móvil están en blueprints separados.
- **Sin Bootstrap**: todo el CSS es personalizado (`static/styles.css`). Las clases utilitarias principales son `.btn`, `.btnPrimary`, `.btnSecondary`, `.tableContainer`, `.dataTable`, `.indicatorCard`.
- **Autenticación JWT en cookies**: no se usan sesiones de Flask. Los tokens se almacenan en cookies HTTP-only.

---

## Changelog

Ver [docs/CHANGELOG.md](docs/CHANGELOG.md).
