# Manual de Usuario — GMAO v1.0.0

**Sistema de Gestión de Mantenimiento Asistido por Ordenador**

---

## Índice

1. [Acceso a la aplicación](#1-acceso-a-la-aplicación)
2. [Roles de usuario](#2-roles-de-usuario)
3. [Pantalla principal](#3-pantalla-principal)
4. [Órdenes de Trabajo](#4-órdenes-de-trabajo)
5. [Mantenimiento Preventivo](#5-mantenimiento-preventivo)
6. [Equipos / Activos](#6-equipos--activos)
7. [Recambios y Stock](#7-recambios-y-stock)
8. [Informes e Indicadores](#8-informes-e-indicadores)
9. [Configuración](#9-configuración)
10. [Interfaz Móvil para Técnicos](#10-interfaz-móvil-para-técnicos)
11. [Flujos de trabajo habituales](#11-flujos-de-trabajo-habituales)

---

## 1. Acceso a la aplicación

### Versión escritorio (PC / portátil)

Abrir un navegador web e introducir la dirección que facilite el administrador del sistema. Se mostrará la pantalla de inicio de sesión. Introducir el nombre de usuario y la contraseña, y pulsar **Entrar**.

### Versión móvil (tablet / smartphone)

Al acceder desde un dispositivo móvil o tablet, la aplicación detecta automáticamente el dispositivo y redirige a la **interfaz móvil** optimizada para pantalla táctil. Si la redirección no se produce automáticamente, añadir `/movil/` al final de la dirección web.

### Cierre de sesión

- **Escritorio**: botón de usuario o cierre de sesión en la barra de navegación superior.
- **Móvil**: icono de salida en la esquina superior derecha de cualquier pantalla.

---

## 2. Roles de usuario

| Rol | Acceso |
|-----|--------|
| **Técnico** | Órdenes de trabajo y preventivo (iniciar, pausar, finalizar trabajo), registro de tiempos y consumos de recambios. No accede a Informes ni a Configuración General/Usuarios. |
| **Responsable** | Todo lo del técnico, más: cierre definitivo de OTs, acceso a Informes e Indicadores, edición de activos y recambios, gestión de técnicos en Configuración. |
| **Admin** | Acceso completo a todos los módulos, incluida la Configuración General y la gestión de usuarios. |

---

## 3. Pantalla principal

Tras el inicio de sesión, la pantalla principal muestra dos elementos:

### Accesos rápidos

Botones que llevan directamente a cada módulo de la aplicación:

- **Equipos** — árbol de activos de la empresa
- **Recambios** — inventario y stock de repuestos
- **Órdenes** — listado de órdenes de trabajo correctivas
- **Preventivo** — órdenes de mantenimiento preventivo
- **Informes** — solo visible para Responsable y Admin

### Calendario de órdenes programadas

Muestra el mes en curso con todas las órdenes de trabajo que tienen una **fecha programada** asignada. Cada OT aparece como una pequeña etiqueta de color:

- **Rojo** — OT correctiva
- **Verde** — OT preventiva
- **Azul** — Otros tipos

**Navegar entre meses** con las flechas izquierda y derecha.

**Ver las órdenes de un día**: hacer clic en cualquier día que tenga OTs muestra una ventana emergente con el detalle de esas órdenes. Al hacer clic en una OT de la lista, la aplicación navega directamente a su detalle.

---

## 4. Órdenes de Trabajo

### Acceso

Pantalla principal → **Órdenes**, o menú lateral.

### Vista de lista

La pantalla muestra una tabla con las órdenes activas (por defecto, sin incluir las cerradas). Las columnas son:

| Columna | Descripción |
|---------|-------------|
| Número | Código único (ej. OT-00042) |
| Tipo | Icono con color según el tipo de intervención configurado |
| Prioridad | Etiqueta de color: urgente / alta / media / baja |
| Fecha Apertura | Fecha y hora de creación de la OT |
| Equipo | Nombre del equipo o máquina directamente asignado |
| Ubicación | Ruta jerárquica completa: Planta › Zona › Línea › Máquina |
| Avería | Título/descripción breve del trabajo |
| Estado | Estado actual de la orden |

En la barra superior se muestran dos contadores en tiempo real: **Pendientes** (órdenes pendientes + asignadas) y **En Curso**.

Para ver también las **órdenes cerradas**, activar la casilla **Mostrar cerradas**.

**Filtros disponibles**: estado, tipo de intervención, prioridad. Los filtros de estado y tipo consultan directamente al servidor; el filtro de prioridad actúa sobre los datos ya cargados.

Los botones de la barra lateral derecha permiten: crear una nueva OT, recargar la lista, o filtrar rápidamente por estado en curso o pendiente.

### Abrir el detalle de una OT

Hacer clic en cualquier fila de la tabla abre el **panel de detalle** a la derecha de la pantalla.

### Crear una nueva OT

Botón **+ Nueva OT** en la barra lateral derecha. Se abre un formulario con los campos:

- **Tipo de intervención** (configurable: correctivo, preventivo, mejora, apoyo a producción, proyectos, etc.)
- **Prioridad**: baja / media / alta / urgente
- **Equipo**: selector jerárquico (planta → zona → línea → máquina → elemento)
- **Título / Avería**: descripción breve
- **Descripción del problema**: texto libre, campo opcional
- **Técnico asignado**
- **Fecha programada**: opcional; aparecerá en el calendario de la pantalla principal
- **Tiempo estimado** en horas

### Estados de una OT

```
pendiente → asignada → en_curso → cerrado_parcial → cerrada
                                                   → cancelada
```

| Estado | Descripción |
|--------|-------------|
| **Pendiente** | OT creada, sin técnico o sin iniciar |
| **Asignada** | Tiene técnico asignado pero no se ha iniciado trabajo |
| **En Curso** | Hay trabajo activo en este momento |
| **Cerrado Parcial** | El técnico ha finalizado; pendiente de validación por el responsable |
| **Cerrada** | OT completamente cerrada y validada |
| **Cancelada** | OT anulada |

### Acciones en el panel de detalle

**Registro de tiempos**: iniciar y pausar trabajo activa un cronómetro que registra las horas imputadas. Si se inicia trabajo sin técnico asignado, el sistema asigna automáticamente al usuario que inicia la sesión.

**Registro de materiales**: buscar el recambio por nombre o código, introducir la cantidad y confirmar. El stock se descuenta automáticamente del inventario.

**Costes externos**: añadir líneas con proveedor, concepto e importe para trabajos realizados por talleres o servicios externos. Se pueden añadir múltiples líneas y eliminar individualmente. El total se acumula en la OT.

**Historial del equipo**: muestra las últimas órdenes cerradas del mismo equipo, con fecha, descripción del problema y solución aplicada.

**Solución y observaciones**: campo de texto para documentar qué se ha hecho.

**Cambio de estado**:
- Si la configuración permite que el técnico cierre definitivamente: botón **Cerrar orden**.
- Si no: botón **Finalizar trabajo** (pasa a `cerrado_parcial`); el responsable cierra definitivamente desde su panel.

---

## 5. Mantenimiento Preventivo

### Acceso

Pantalla principal → **Preventivo**, o menú lateral.

### Vista

La pantalla muestra una única tabla con todas las órdenes preventivas activas. En la parte superior, tres contadores:

- **Vencidas**: OTs cuya fecha prevista ya ha pasado
- **Esta semana**: OTs que vencen en los próximos 7 días
- **Total**: total de OTs preventivas activas

Las columnas de la tabla son:

| Columna | Descripción |
|---------|-------------|
| Número | Código de la OT |
| Prioridad | Etiqueta de prioridad |
| Fecha prevista | Fecha programada para la intervención |
| Equipo | Nombre del equipo |
| Gama / Título | Gama de mantenimiento vinculada, o título de la OT |
| Frecuencia | Periodicidad configurada (ej. cada 30 días, cada 3 meses) |
| Estado | Estado actual de la OT |
| Días | Días restantes o días vencida. Aparece en rojo si vencida, naranja si es esta semana |

Hacer clic en una fila abre el panel de detalle completo de la OT, con las mismas funciones que en órdenes correctivas, más las secciones de tareas y checklist si la gama las tiene definidas.

### Crear una nueva OT Preventiva

Botón **+ Nueva OT** en la barra lateral. Se abre un formulario específico para preventivo con los campos:

- **Título / Descripción**
- **Equipo** (selector con toda la jerarquía)
- **Gama de mantenimiento**: opcional; vincula la OT a una gama existente
- **Frecuencia**: valor numérico y tipo (días, semanas o meses)
- **Prioridad**
- **Fecha de primera intervención**
- **Descripción / Trabajos a realizar**

### Cierre y autogeneración

Al cerrar una OT preventiva, el sistema genera automáticamente la **siguiente OT preventiva** con la fecha calculada según la frecuencia configurada. De este modo el plan de mantenimiento se mantiene sin necesidad de intervención manual.

> Las gamas de mantenimiento (definición de tareas, checklist, asignación a equipos) se gestionan en **Configuración → Gamas de Mantenimiento**.

---

## 6. Equipos / Activos

### Acceso

Pantalla principal → **Equipos**, o menú lateral.

### Árbol de activos

El panel izquierdo muestra el árbol completo de activos con búsqueda integrada:

```
Empresa
└── Planta
    └── Zona
        └── Línea
            └── Máquina
                └── Elemento
```

Hacer clic en cualquier nodo muestra su información en el panel de detalle derecho.

### Panel de detalle

Al seleccionar una máquina o elemento se muestra:

- **Datos generales**: código, nombre, descripción, fabricante, modelo, número de serie, criticidad, estado, fecha de instalación
- **Historial de OTs**: últimas órdenes de trabajo del equipo, con acceso directo al detalle de cada una

### Añadir, editar y eliminar activos

Al seleccionar un nodo en el árbol, aparecen en la barra lateral los botones **Editar** y **Eliminar** para ese elemento. El botón **Nuevo** (en la barra lateral o en la cabecera de la página) permite añadir un nuevo elemento como hijo del nodo seleccionado o de forma independiente.

> La creación y edición de activos solo está disponible para **Responsable** y **Admin**.

### Nueva OT desde el árbol de equipos

Al seleccionar un equipo en el árbol, aparece el botón **Nueva OT** en la barra lateral. Esto abre el formulario de nueva OT con el equipo ya preseleccionado.

---

## 7. Recambios y Stock

### Acceso

Pantalla principal → **Recambios**, o menú lateral.

### Vista de inventario

Tres indicadores en la parte superior:

- **Total Recambios**: número total de referencias
- **Stock Bajo**: referencias con stock por debajo del mínimo configurado (en rojo)
- **Valor Stock**: valor total del inventario actual

**Filtros**: búsqueda por código o nombre, casilla "Solo stock bajo", filtro por categoría.

**Botón Stock Bajo** en la barra lateral: filtra la lista mostrando solo los artículos con stock insuficiente.

### Tabla de recambios

Cada fila muestra: código, nombre, stock actual, stock mínimo, unidad de medida, precio unitario y estado (alerta si stock bajo mínimo).

Hacer clic en una fila abre el panel de detalle con el historial de movimientos del recambio.

### Registrar movimientos de stock

Desde la barra lateral (solo Responsable y Admin):

- **Entrada**: recepción de material (compra, devolución)
- **Salida**: consumo o uso no vinculado a una OT

El consumo vinculado a una OT se registra desde el **panel de detalle de la OT** (sección Materiales), no desde aquí.

### Exportar inventario

Botón **Exportar** en la barra lateral: descarga el inventario completo en formato Excel.

---

## 8. Informes e Indicadores

### Acceso

Pantalla principal → **Informes** (solo Responsable y Admin), o menú lateral.

La sección de Informes tiene una pantalla de inicio con cinco accesos:

---

### Órdenes de Trabajo

Listado completo de OTs con costes y horas registradas.

- **Filtros**: rango de fechas, tipo, estado, equipo
- **Columnas principales**: número, tipo, estado, equipo, técnico, tiempo real, costes
- **Exportar a Excel**: descarga el informe con todos los datos filtrados

### Preventivos Planificados

Plan preventivo futuro y estado de cumplimiento.

- **Filtros**: rango de fechas, equipo
- **Exportar a Excel**

### Movimientos de Stock

Trazabilidad de todas las entradas, salidas y consumos de recambios.

- **Filtros**: rango de fechas, tipo de movimiento, recambio
- **Exportar a Excel**

---

### Dashboards Gráficos

Análisis visual interactivo del mantenimiento con los siguientes gráficos (filtro por rango de fechas):

- **Tipos de OT por mes**: barras apiladas con el volumen mensual de correctivas, preventivas y otras + donut de distribución + ratio de correctivo
- **Prioridades**: distribución por nivel de prioridad (donut + barras mensuales)
- **TOP equipos / Pareto de averías**: ranking de máquinas con más órdenes correctivas, con análisis de Pareto
- **Mapa de calor**: actividad de mantenimiento por equipo y mes
- **Horas por técnico**: imputación total de horas por técnico en el período
- **Tiempos por línea**: tiempo de reacción, reparación y paro de producción agrupado por línea productiva

### Indicadores KPI (EN 15341)

Cuadro de mandos con **14 indicadores** basados en la norma europea de mantenimiento EN 15341, organizados en tres categorías: económicos, técnicos y organizativos.

Cada indicador muestra su valor calculado con código de colores:
- **Verde**: el indicador cumple el objetivo definido
- **Amarillo**: atención, próximo al límite
- **Rojo**: el indicador no cumple el objetivo

Se puede seleccionar el rango de fechas para calcular los KPIs sobre el período deseado.

---

## 9. Configuración

> La visibilidad de las pestañas depende del rol del usuario.

### Acceso

Menú lateral → **Configuración**

### Tipos de Intervención *(Responsable y Admin)*

Catálogo de los tipos de OT disponibles en el sistema. Para cada tipo se define:

- **Código y nombre**
- **Icono** (Font Awesome) y **color** de representación
- **Orden** de aparición en los listados
- **Estado**: activo / inactivo

> Solo el **Admin** puede crear o eliminar tipos. Los cambios afectan inmediatamente a todos los formularios de la aplicación.

### Gamas de Mantenimiento *(Responsable y Admin)*

Las gamas definen el contenido técnico de cada intervención preventiva. Para cada gama:

- **Código, tipo y nombre**
- **Descripción** y tiempo estimado de ejecución
- **Tareas a realizar**: lista de pasos con descripción, instrucciones, herramientas y duración estimada. Cada tarea tiene un número de orden.
- **Recambios asociados**: materiales que se utilizan habitualmente en esta gama
- **Asignaciones**: equipos a los que está asignada la gama, con su frecuencia de intervención
- **Checklist de verificación**: puntos de control con tipo de respuesta (OK/NOK, valor numérico o texto libre)

> Solo el **Admin** puede crear o eliminar gamas.

### General *(solo Admin)*

Parámetros globales del sistema:

| Parámetro | Descripción |
|-----------|-------------|
| **Técnico puede cerrar definitivamente** | Si está activo, los técnicos pueden cerrar OTs sin necesitar validación del responsable |
| **Coste hora por defecto** | Coste horario empleado en el cálculo de KPIs cuando el técnico no tiene coste propio configurado |

Los cambios se aplican de forma inmediata.

### Usuarios *(solo Admin)*

Alta, modificación y baja de usuarios. Para cada usuario:

- **Nombre de usuario** (para el login) y **contraseña**
- **Nombre y apellidos** visibles en la aplicación
- **Nivel**: técnico / responsable / admin
- **Técnico vinculado**: relaciona el usuario con un perfil del catálogo de técnicos
- **Estado**: activo / inactivo

### Técnicos *(Responsable y Admin)*

Catálogo de técnicos de mantenimiento con sus datos de perfil:

- Nombre y apellidos, especialidad
- Teléfono y email de contacto
- **Coste por hora**: empleado en el cálculo de costes de mano de obra en KPIs e informes
- Estado activo/inactivo

---

## 10. Interfaz Móvil para Técnicos

La interfaz móvil está pensada para que los técnicos trabajen desde tablets o smartphones en campo, sin necesidad de acceder a la versión de escritorio.

### Navegación

Una barra fija en la parte inferior contiene cuatro secciones:

| Icono | Sección |
|-------|---------|
| Llave inglesa | **Correctivo** — OTs de mantenimiento correctivo |
| Escudo | **Preventivo** — OTs de mantenimiento preventivo |
| Carpeta | **Otras** — OTs de mejora, proyectos, apoyo a producción, etc. |
| Más | **Nueva OT** — Crear una nueva orden de trabajo |

En la cabecera superior aparece el nombre del técnico, un acceso rápido a crear nueva OT y el botón de cierre de sesión.

### Listas de órdenes

Cada una de las tres pantallas (Correctivo, Preventivo, Otras) tiene dos pestañas:

- **Mis OTs**: órdenes asignadas al técnico en sesión, ordenadas por estado y fecha
- **Activas**: todas las órdenes activas del sistema (pendientes + en curso), ordenadas por urgencia

Cada tarjeta muestra: número, título, tipo, estado, prioridad, técnico asignado, fecha de creación y fecha programada (si existe). La ruta del equipo se muestra en forma de migas: **Planta › Zona › Línea › Máquina**.

### Detalle de una OT

Al tocar una tarjeta se abre la vista de detalle. La cabecera muestra el título, tipo, prioridad y ubicación del equipo. El resto se organiza en **secciones colapsables** (tocar la cabecera de cada sección para expandir o contraer):

#### Información
Técnico asignado, fecha programada, tiempo estimado y descripción del problema.

#### Control de tiempo
Muestra el tiempo total registrado y el estado de la sesión actual.

- **Iniciar trabajo**: activa el cronómetro. Si la OT no tiene técnico asignado, se asigna automáticamente al usuario en sesión.
- **Pausar trabajo**: detiene el cronómetro y guarda el tiempo imputado. Se puede reanudar en cualquier momento.

Debajo del botón se muestra el historial de sesiones anteriores (técnico, hora de inicio y duración).

#### Materiales usados
Lista de recambios ya registrados en la OT. El botón **Registrar material** abre un buscador de recambios (por nombre o código). Al seleccionar uno e introducir la cantidad, el consumo queda registrado y el stock se descuenta automáticamente.

#### Tareas a realizar *(solo preventivo con gama)*
Lista de pasos de la gama de mantenimiento con checkbox para marcar cada uno como realizado. Los checks **se guardan en la base de datos** al marcarlos; si se sale y se vuelve a entrar, las tareas siguen marcadas. Una barra de progreso indica cuántas tareas se han completado.

Cada tarea puede mostrar instrucciones adicionales, herramientas necesarias y duración estimada.

#### Checklist preventivo *(solo preventivo con checklist)*
Puntos de control de la gama. Según el tipo de punto, la respuesta puede ser:
- **OK / NOK** con campo de observaciones
- **Valor numérico** (ej. una medición)
- **Texto libre**

Botón **Guardar checklist** para persistir las respuestas.

#### Histórico del equipo
Muestra las últimas órdenes cerradas del mismo equipo, con fecha, descripción del problema y solución aplicada. Si no hay intervenciones previas, aparece un aviso. Esta sección está disponible para cualquier OT que tenga equipo asignado.

#### Solución / Observaciones
Dos campos de texto: **descripción de la solución** aplicada y **observaciones** generales. Botón **Guardar** para registrar los cambios.

#### Acciones
Según el estado de la OT y la configuración del sistema:

- **Asignarme esta OT** — si la OT está pendiente y sin técnico asignado
- **Finalizar trabajo** — pasa la OT a `cerrado_parcial`; el responsable realiza el cierre definitivo
- **Cerrar orden** — cierre definitivo directo (solo disponible si la configuración **Técnico puede cerrar definitivamente** está activada)

> La sección de Solución y Acciones no aparece si la OT ya está cerrada o cancelada.

### Crear una nueva OT desde móvil

La pantalla **Nueva OT** tiene un formulario con:

- **Tipo**: agrupado en "Mantenimiento" (correctivo, preventivo) y "Otras órdenes" (mejora, proyecto, otro)
- **Prioridad**: baja (por defecto media), alta, urgente
- **Título**
- **Descripción del problema**
- **Equipo**: selector en cascada (Planta → Zona → Línea → Máquina → Elemento)
- **Técnico asignado**
- **Fecha programada**

---

## 11. Flujos de trabajo habituales

### Técnico: atender una OT correctiva

1. Abrir la app móvil → pestaña **Correctivo**
2. Consultar **Mis OTs** o **Activas** para encontrar la orden
3. Tocar la tarjeta para abrir el detalle
4. Consultar el **Histórico del equipo** para ver si el problema es recurrente
5. Pulsar **Iniciar trabajo** (el cronómetro comienza)
6. Realizar la intervención
7. Registrar en **Materiales usados** los recambios empleados
8. Anotar la **Solución aplicada** en el campo correspondiente
9. Pulsar **Pausar** si hay que interrumpir, o **Finalizar trabajo** al terminar
10. El responsable revisa y realiza el cierre definitivo desde la versión escritorio

### Técnico: ejecutar un preventivo

1. Abrir la app móvil → pestaña **Preventivo**
2. Abrir la OT del equipo correspondiente
3. Pulsar **Iniciar trabajo**
4. Ir completando las **Tareas** marcando cada paso (se guardan automáticamente)
5. Cumplimentar el **Checklist de verificación** y pulsar **Guardar checklist**
6. Registrar consumos de materiales (lubricantes, filtros, etc.)
7. Anotar observaciones relevantes
8. Pulsar **Finalizar trabajo**
9. El sistema genera automáticamente la siguiente OT preventiva para ese equipo

### Responsable: cierre y validación de OTs

1. En **Órdenes de Trabajo** (escritorio), filtrar por estado **Cerrado Parcial**
2. Abrir cada OT y revisar: tiempos registrados, materiales consumidos, solución anotada
3. Si la intervención es correcta, cambiar el estado a **Cerrada**
4. Si hay aspectos pendientes, cambiar el estado a **En Curso** para que el técnico continúe

### Responsable: seguimiento del plan preventivo

1. Acceder a **Preventivo** (escritorio)
2. Revisar las OTs marcadas como **vencidas** (rojo) o **esta semana** (naranja)
3. Para OTs urgentes, asignar técnico o cambiar la fecha programada si es necesario
4. Usar **Nueva OT** si se necesita generar manualmente una intervención preventiva

### Admin: dar de alta un usuario nuevo

1. Ir a **Configuración → Usuarios**
2. Pulsar **Nuevo Usuario**
3. Rellenar: nombre de usuario, contraseña, nombre completo, nivel de acceso
4. Vincular con un técnico del catálogo si aplica
5. Guardar

### Admin: crear una nueva gama de mantenimiento

1. Ir a **Configuración → Gamas de Mantenimiento**
2. Pulsar **Nueva Gama**
3. Rellenar código, tipo, nombre, descripción y tiempo estimado
4. Añadir las **tareas** en orden (con instrucciones, herramientas y duración si se conocen)
5. Añadir el **checklist** con los puntos de verificación y su tipo de respuesta
6. Guardar la gama
7. Para programar la gama en un equipo: al crear o editar una OT preventiva, seleccionar la gama en el formulario

---

## Preguntas frecuentes

**¿Qué ocurre si cierro la app con el cronómetro en marcha?**
El registro de tiempo queda abierto. Al volver a la OT, el cronómetro seguirá activo. Para detenerlo, pulsar **Pausar**.

**¿Por qué no veo el módulo Informes?**
El módulo de Informes solo es visible para usuarios con nivel **Responsable** o **Admin**. Si eres técnico, no aparece en el menú.

**¿Cómo consulto el historial de intervenciones de un equipo?**
Desde la versión escritorio: acceder a **Equipos**, seleccionar la máquina en el árbol y consultar la pestaña de historial en el panel de detalle. Desde la versión móvil: abrir cualquier OT del equipo y desplegar la sección **Histórico del equipo**.

**¿Puedo crear una OT preventiva directamente?**
Sí. En **Preventivo** (escritorio), pulsar **+ Nueva OT**. Desde la app móvil, usar el botón **Nueva OT** de la barra inferior y seleccionar tipo "Preventivo".

**¿Qué significa "cerrado parcial"?**
El técnico ha terminado su parte, pero la OT espera validación del responsable antes de cerrarse definitivamente. Esto permite que el responsable verifique que la incidencia quedó correctamente resuelta. Si la configuración **Técnico puede cerrar definitivamente** está activa, los técnicos pueden cerrar directamente sin pasar por este estado intermedio.

**¿Se pueden exportar los informes?**
Sí. Todos los informes del módulo **Informes** (Órdenes, Preventivos y Movimientos de Stock) tienen un botón **Exportar** que genera un archivo `.xlsx` descargable.

**¿Qué pasa cuando se cierra una OT preventiva?**
El sistema calcula automáticamente la fecha de la siguiente intervención según la frecuencia configurada y genera una nueva OT preventiva para ese equipo, manteniendo la programación sin intervención manual.

---

*GMAO v1.0.0 — Documentación generada el 2026-02-24*
