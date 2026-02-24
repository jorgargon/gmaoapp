# Propuesta de Permisos por Módulo y Nivel de Usuario

Este documento recoge qué puede ver y hacer cada nivel de usuario en los módulos actuales de la aplicación GMAO. Sirve como referencia para la implementación del control de acceso.

> **Niveles definidos:** `Técnico` · `Responsable` · `Admin`

---

## Tabla de Permisos

| Módulo | Técnico | Responsable | Admin |
|--------|---------|-------------|-------|
| **Inicio / Dashboard** | Ver indicadores y calendario | Ver indicadores y calendario | Ver + acceso a Config |
| **Equipos / Activos** | Ver árbol y detalle de equipo | Ver + Editar activos | CRUD completo (crear, editar, eliminar) |
| **Recambios** | Ver stock · Registrar consumos en OT | Ver + Ajustar stock manualmente | CRUD completo + movimientos |
| **Órdenes de Trabajo** | Ver OTs · Iniciar / Pausar · **Primer cierre** (→ Cerrado Parcial) | Ver + Editar + **Cierre definitivo** | CRUD completo |
| **Preventivo** | Ver OTs preventivas · Iniciar / Pausar · **Primer cierre** (→ Cerrado Parcial) | Ver + Planificar + **Cierre definitivo** | CRUD completo |
| **Informes** | Sin acceso | Ver informes + **Exportar** | Ver informes + Exportar |
| **Configuración — Tipos / Gamas / Técnicos** | Sin acceso | Sin acceso (solo lectura en caso necesario) | CRUD completo |
| **Configuración — General** | Sin acceso | Ver (solo lectura) | Editar cualquier ajuste |
| **Configuración — Usuarios** | Sin acceso | Sin acceso | CRUD completo (solo Admin) |
| **Configuración — Permisos** | Sin acceso | Sin acceso | Editar (solo Admin) |

---

## Detalle por módulo

### Órdenes de Trabajo y Preventivo — Flujo de cierre

Ambos módulos siguen la misma lógica de doble cierre:

```
pendiente → en_curso → cerrado_parcial → cerrada
                ↑ Técnico finaliza       ↑ Responsable (o Técnico si configuración lo permite)
```

El ajuste **"Técnico puede cerrar definitivamente"** en *Configuración General* controla si un técnico puede ejecutar el Cierre Definitivo sin intervención del Responsable.

### Configuración — Permisos

La sección de permisos dentro de Configuración será accesible **solo para Admin**. Desde ahí se podrá ajustar qué operaciones concretas puede realizar cada nivel (ej: si Técnico puede ver Informes, si Responsable puede eliminar OTs, etc.).

---

## Notas de Implementación

- Los niveles **no se implementan todavía** a nivel de enforcement en esta iteración — la tabla y la gestión de usuarios se crea, pero las restricciones de UI/API se añadirán progresivamente.
- La validación de nivel se hará en el backend (Flask) una vez se implemente la sesión de usuario.
- Los botones sensibles (ej: Cierre Definitivo) se ocultarán en el frontend según el nivel del usuario en sesión.
