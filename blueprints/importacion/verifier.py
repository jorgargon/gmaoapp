"""
Verificador del estado de la BD: cuenta registros y muestra los últimos 5 de cada entidad.
"""
from models import (
    db, Planta, Zona, Linea, Maquina, Elemento,
    Recambio, Tecnico, Usuario,
    GamaMantenimiento, TareaGama, ChecklistItem,
    OrdenTrabajo,
)


def _fmt_date(val):
    """Formatea una fecha/datetime a string legible, o None."""
    if val is None:
        return None
    try:
        return val.strftime('%d/%m/%Y')
    except Exception:
        return str(val)


def get_db_summary():
    """
    Devuelve un dict con counts y últimos 5 registros de cada entidad principal.
    """
    summary = {}

    # --- PLANTAS ---
    total_plantas = Planta.query.count()
    ultimas_plantas = Planta.query.order_by(Planta.id.desc()).limit(5).all()
    summary['plantas'] = {
        'total': total_plantas,
        'ultimos': [
            {'codigo': p.codigo, 'nombre': p.nombre, 'ts': None}
            for p in ultimas_plantas
        ],
    }

    # --- ZONAS ---
    total_zonas = Zona.query.count()
    ultimas_zonas = Zona.query.order_by(Zona.id.desc()).limit(5).all()
    summary['zonas'] = {
        'total': total_zonas,
        'ultimos': [
            {'codigo': z.codigo, 'nombre': z.nombre, 'ts': None}
            for z in ultimas_zonas
        ],
    }

    # --- LINEAS ---
    total_lineas = Linea.query.count()
    ultimas_lineas = Linea.query.order_by(Linea.id.desc()).limit(5).all()
    summary['lineas'] = {
        'total': total_lineas,
        'ultimos': [
            {'codigo': l.codigo, 'nombre': l.nombre, 'ts': None}
            for l in ultimas_lineas
        ],
    }

    # --- MAQUINAS ---
    total_maquinas = Maquina.query.count()
    ultimas_maquinas = Maquina.query.order_by(Maquina.id.desc()).limit(5).all()
    summary['maquinas'] = {
        'total': total_maquinas,
        'ultimos': [
            {'codigo': m.codigo, 'nombre': m.nombre, 'ts': None}
            for m in ultimas_maquinas
        ],
    }

    # --- ELEMENTOS ---
    total_elementos = Elemento.query.count()
    ultimos_elementos = Elemento.query.order_by(Elemento.id.desc()).limit(5).all()
    summary['elementos'] = {
        'total': total_elementos,
        'ultimos': [
            {'codigo': e.codigo, 'nombre': e.nombre, 'ts': None}
            for e in ultimos_elementos
        ],
    }

    # --- RECAMBIOS ---
    total_recambios = Recambio.query.count()
    ultimos_recambios = Recambio.query.order_by(Recambio.id.desc()).limit(5).all()
    summary['recambios'] = {
        'total': total_recambios,
        'ultimos': [
            {'codigo': r.codigo, 'nombre': r.nombre, 'ts': _fmt_date(r.fechaAlta)}
            for r in ultimos_recambios
        ],
    }

    # --- TECNICOS ---
    total_tecnicos = Tecnico.query.count()
    ultimos_tecnicos = Tecnico.query.order_by(Tecnico.id.desc()).limit(5).all()
    summary['tecnicos'] = {
        'total': total_tecnicos,
        'ultimos': [
            {
                'codigo': str(t.id),
                'nombre': f"{t.nombre} {t.apellidos or ''}".strip(),
                'ts': None,
            }
            for t in ultimos_tecnicos
        ],
    }

    # --- USUARIOS ---
    total_usuarios = Usuario.query.count()
    ultimos_usuarios = Usuario.query.order_by(Usuario.id.desc()).limit(5).all()
    summary['usuarios'] = {
        'total': total_usuarios,
        'ultimos': [
            {
                'codigo': u.username,
                'nombre': f"{u.nombre} {u.apellidos or ''}".strip(),
                'ts': _fmt_date(u.fechaAlta),
            }
            for u in ultimos_usuarios
        ],
    }

    # --- GAMAS ---
    total_gamas = GamaMantenimiento.query.count()
    total_tareas = TareaGama.query.count()
    total_checklist = ChecklistItem.query.count()
    ultimas_gamas = GamaMantenimiento.query.order_by(GamaMantenimiento.id.desc()).limit(5).all()
    summary['gamas'] = {
        'total': total_gamas,
        'tareas': total_tareas,
        'checklist': total_checklist,
        'ultimos': [
            {
                'codigo': g.codigo,
                'nombre': g.nombre,
                'ts': _fmt_date(g.fechaCreacion),
            }
            for g in ultimas_gamas
        ],
    }

    # --- ORDENES ---
    total_ordenes = OrdenTrabajo.query.count()
    ultimas_ordenes = OrdenTrabajo.query.order_by(OrdenTrabajo.id.desc()).limit(5).all()
    summary['ordenes'] = {
        'total': total_ordenes,
        'ultimos': [
            {
                'codigo': ot.numero,
                'nombre': ot.titulo,
                'ts': _fmt_date(ot.fechaCreacion),
            }
            for ot in ultimas_ordenes
        ],
    }

    return summary
