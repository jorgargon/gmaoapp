# CHANGELOG — GMAO App

Registro de cambios del proyecto. Formato: `[versión / fecha] Descripción`.

---

## [1.0.0] — 2026-02-24 — Primera versión estable

### Módulos incluidos en esta versión

#### Dashboard
- Indicadores de estado en tiempo real (OTs pendientes, en curso, preventivos próximos, recambios bajo mínimos)
- Gráficos: tipos de OT mensuales (barras apiladas + donut), prioridades, TOP equipos con más averías, mapa de calor (equipo × mes), horas por técnico, tiempos por línea, Pareto de averías
- Calendario mensual con todas las OTs programadas; clic en OT abre el detalle directo

#### Órdenes de Trabajo
- Creación de OTs de cualquier tipo (correctivo, preventivo, mejora, apoyo a producción, proyectos, otro)
- Estados: pendiente › asignada › en_curso › cerrado_parcial › cerrada / cancelada
- Registro de tiempos de trabajo (inicio/pausa con cronómetro)
- Registro de consumo de recambios con descuento automático de stock
- Múltiples costes externos por OT (proveedor, concepto, importe; lista acumulativa)
- Doble cierre: técnico finaliza → `cerrado_parcial`; responsable valida → `cerrada`
- Opción de configuración para permitir cierre definitivo por técnico
- Filtros: estado, tipo, prioridad; búsqueda de OTs cerradas
- Columna de ubicación en el listado con ruta jerárquica del equipo (Planta › Zona › Línea › Máquina)

#### Mantenimiento Preventivo
- Gamas de mantenimiento con lista de tareas y checklist de verificación
- Asignación de gamas a equipos con frecuencia configurable (días, semanas, meses)
- Generación automática de la siguiente OT preventiva al cerrar la actual
- Vista de OTs preventivas con indicadores de urgencia (vencida / próxima / al día)
- Vista de gamas y programación con fechas de última y próxima ejecución

#### Activos / Equipos
- Árbol jerárquico navegable: Empresa › Planta › Zona › Línea › Máquina › Elemento
- Ficha de máquina: modelo, fabricante, número de serie, criticidad, estado, fecha instalación
- Panel lateral de historial de OTs por equipo
- Importación masiva desde CSV (`scripts/import_activos.py`)

#### Recambios
- Inventario con código, nombre, stock actual (float), stock mínimo, precio unitario
- Registro de movimientos: entrada, salida, ajuste, consumo por OT
- Alerta visual cuando el stock está por debajo del mínimo
- Exportación del historial de movimientos

#### Indicadores (KPIs EN 15341)
- 14 indicadores técnicos y económicos categorizados (E1–E14)
- Codificados por color: verde (objetivo cumplido), amarillo (atención), rojo (alerta)
- Informes filtrables por rango de fechas con exportación a Excel:
  - Informe de Órdenes de Trabajo
  - Informe de Mantenimiento Preventivo
  - Informe de Movimientos de Stock

#### Configuración (Admin)
- Configuración general (parámetros clave/valor): técnico puede cerrar, coste hora por defecto, etc.
- Gestión de usuarios y roles (técnico / responsable / admin)
- Tipos de intervención configurables con icono y color
- Gestión de gamas de mantenimiento y técnicos

#### Interfaz Móvil (`/movil/`)
- Detección automática de dispositivo móvil/tablet y redirección
- Vista de OTs correctivas con pestañas "Mis OTs" / "Activas"
- Vista de OTs preventivas con pestañas "Mis OTs" / "Activas"
- Vista de "Otras órdenes" (mejoras, proyectos, etc.)
- Detalle de OT: cronómetro, materiales, tareas, checklist, histórico del equipo, observaciones/solución
- Persistencia de tareas marcadas como realizadas en BD
- Asignación automática del técnico al iniciar trabajo si la OT no tiene técnico asignado
- Cierre respeta configuración `tecnico_puede_cerrar` (cerrado_parcial vs cerrada)
- Creación de OTs desde móvil con selector en cascada de equipo

---

## [2026-02-19] Rediseño Mantenimiento Preventivo + Mejoras Órdenes

### Mantenimiento Preventivo — Rediseño completo

**`preventivo.html`** — Reescritura total de la página:
- Nueva estructura de **dos pestañas**:
  - **Órdenes Preventivas**: lista de OTs de tipo preventivo ordenadas por fecha prevista, con indicadores de urgencia (vencida / próxima / al día) y acciones para ver o cerrar la orden.
  - **Gamas y Programación**: tabla de `AsignacionGama` con frecuencia, última ejecución, próxima ejecución, estado y botón para generar OT manualmente.
- Se eliminó el calendario de esta página (movido al dashboard).

**`app.py`** — Lógica de autogeneración de OT preventiva:
- Función `_generarSiguienteOTPreventivo(orden)`: al cerrar una OT de tipo preventivo, genera automáticamente la siguiente con la fecha calculada según la frecuencia definida en `AsignacionGama` (prioritario) o `PlanPreventivo` (legacy).
- `cambiarEstadoOrden`: modificado para llamar a `_generarSiguienteOTPreventivo` cuando el nuevo estado es `cerrada` y el tipo es `preventivo`.
- Nuevos endpoints:
  - `GET /api/ordenes-calendario` — OTs con fecha programada para el calendario del dashboard.
  - `GET /api/ordenes-preventivo` — OTs preventivas ordenadas por fecha vencimiento, con días restantes y datos de gama.

---

### Dashboard — Calendario de órdenes

**`home.html`** — Añadido calendario al final del dashboard:
- Muestra todas las OTs con `fechaProgramada` (no cerradas/canceladas).
- Órdenes representadas como chips de colores por tipo (rojo=correctivo, verde=preventivo, azul=otro).
- Navegación por meses.
- Clic en un día muestra popup con la lista de OTs; clic en una OT navega directamente al detalle en `/ordenes?ot={id}`.

---

### Órdenes — Múltiples costes externos

**`models.py`** — Campo `costesExternosJson`:
- Añadido `costesExternosJson = db.Column(db.Text)` en `OrdenTrabajo` para almacenar la lista de costes externos como JSON.
- El campo `costeTallerExterno` (Float) se mantiene como total acumulado calculado.

**`app.py`** — Endpoints de costes externos reescritos:
- `POST /api/orden/<id>/coste-externo`: acumula cada coste en la lista JSON en lugar de sobrescribir.
- `DELETE /api/orden/<id>/coste-externo/<idx>`: elimina una entrada por índice y recalcula el total.

**`ordenes-common.js`** — Visualización y gestión de la lista:
- Sección "Costes Externos" muestra todas las entradas en tabla, con fila de total y botón de eliminación por fila.
- Nueva función `eliminarCosteExternoItem(ordenId, idx)`.
