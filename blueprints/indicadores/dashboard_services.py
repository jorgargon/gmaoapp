"""
Servicios de datos para los dashboards gráficos del módulo de Indicadores.

Adaptado al modelo real del proyecto:
  - OrdenTrabajo.tipo         → tipo de intervención (no tipo_intervencion)
  - OrdenTrabajo.fechaCreacion → fecha base para filtros
  - OrdenTrabajo.tiempoParada → horas de paro de máquina
  - RegistroTiempo.tecnico    → string con nombre del técnico
  - Jerarquía polimorfa       → equipoTipo + equipoId (sin FK directa a Equipo)
  - TipoIntervencion          → catálogo configurable de tipos (con color y nombre)

Nota: usa func.strftime('%Y-%m', ...) → SQLite. Para PostgreSQL sustituir por
      func.to_char(col, 'YYYY-MM').
"""
from datetime import datetime
from collections import defaultdict

from sqlalchemy import func, case, desc, or_, and_

from models import (
    db,
    OrdenTrabajo, RegistroTiempo, TipoIntervencion,
    Maquina, Elemento, Linea, Zona, Planta, Empresa,
)
from blueprints.indicadores.services import _get_pares_bajo_nodo


# =============================================================================
# HELPERS INTERNOS
# =============================================================================

_MESES_ES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
              'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def _mes_range(fi, ff):
    """Lista de strings 'YYYY-MM' entre fi y ff inclusive."""
    meses = []
    cur = fi.replace(day=1)
    end = ff.replace(day=1)
    while cur <= end:
        meses.append(cur.strftime('%Y-%m'))
        m = cur.month + 1
        if m > 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=m)
    return meses


def _label_mes(ym):
    """'2025-01' → 'ene 25'"""
    try:
        y, m = ym.split('-')
        return f"{_MESES_ES[int(m) - 1]} {y[2:]}"
    except Exception:
        return ym


def _fi_ff_dt(fi, ff):
    """Convierte date fi/ff a datetime para filtros SQLAlchemy."""
    return (
        datetime.combine(fi, datetime.min.time()),
        datetime.combine(ff, datetime.max.time()),
    )


def _precargar_jerarquia():
    """
    Carga toda la jerarquía de activos en dicts para evitar N+1 queries.
    Devuelve dict con claves: maquinas, elementos, lineas, zonas, plantas, empresas.
    """
    return {
        'maquinas':  {m.id: m for m in Maquina.query.all()},
        'elementos': {e.id: e for e in Elemento.query.all()},
        'lineas':    {l.id: l for l in Linea.query.all()},
        'zonas':     {z.id: z for z in Zona.query.all()},
        'plantas':   {p.id: p for p in Planta.query.all()},
        'empresas':  {e.id: e for e in Empresa.query.all()},
    }


def _linea_nombre(equipo_tipo, equipo_id, jer):
    """Sube la jerarquía para obtener el nombre de Línea del activo."""
    if equipo_tipo == 'linea':
        l = jer['lineas'].get(equipo_id)
        return l.nombre if l else 'Sin línea'
    if equipo_tipo == 'maquina':
        m = jer['maquinas'].get(equipo_id)
        if m:
            l = jer['lineas'].get(m.lineaId)
            return l.nombre if l else 'Sin línea'
    if equipo_tipo == 'elemento':
        e = jer['elementos'].get(equipo_id)
        if e:
            m = jer['maquinas'].get(e.maquinaId)
            if m:
                l = jer['lineas'].get(m.lineaId)
                return l.nombre if l else 'Sin línea'
    if equipo_tipo == 'zona':
        z = jer['zonas'].get(equipo_id)
        return f"Zona {z.nombre}" if z else 'Sin zona'
    if equipo_tipo == 'planta':
        p = jer['plantas'].get(equipo_id)
        return f"Planta {p.nombre}" if p else 'Sin planta'
    return 'Sin clasificar'


def _equipo_label(equipo_tipo, equipo_id, jer):
    """Devuelve 'CODIGO: nombre' para cualquier nivel de activo."""
    key_map = {
        'maquina': 'maquinas', 'elemento': 'elementos',
        'linea': 'lineas', 'zona': 'zonas',
        'planta': 'plantas', 'empresa': 'empresas',
    }
    key = key_map.get(equipo_tipo)
    if not key:
        return f'{equipo_tipo}:{equipo_id}'
    obj = jer[key].get(equipo_id)
    if not obj:
        return f'{equipo_tipo}:{equipo_id}'
    codigo = getattr(obj, 'codigo', '')
    nombre = getattr(obj, 'nombre', '')[:25]
    return f"{codigo}: {nombre}" if codigo else nombre


def _get_tipos_info():
    """Dict {codigo: {nombre, color}} de TipoIntervencion activos."""
    return {
        t.codigo: {'nombre': t.nombre, 'color': t.color or '#9E9E9E'}
        for t in TipoIntervencion.query.filter_by(activo=True).all()
    }


_DEFAULT_TIPO_COLORS = {
    'correctivo': '#E53935',
    'preventivo': '#43A047',
    'mejora':     '#1E88E5',
    'predictivo': '#FB8C00',
}

_PRIORIDAD_COLORS = {
    'urgente': '#B71C1C',
    'alta':    '#E53935',
    'media':   '#FB8C00',
    'baja':    '#43A047',
}

_PRIORIDAD_ORDER = ['urgente', 'alta', 'media', 'baja']


def _tipo_color(tipo, tipos_info):
    return (tipos_info.get(tipo) or {}).get('color') or _DEFAULT_TIPO_COLORS.get(tipo, '#9E9E9E')


def _tipo_nombre(tipo, tipos_info):
    return (tipos_info.get(tipo) or {}).get('nombre') or tipo.capitalize()


def _scope_filter(nivel, nivel_id):
    """
    Devuelve condición OR para filtrar OTs por jerarquía, o None si no hay alcance.
    Usa _get_pares_bajo_nodo para obtener todos los (equipoTipo, equipoId) del nodo.
    """
    if not nivel or not nivel_id:
        return None
    pares = _get_pares_bajo_nodo(nivel, nivel_id)
    by_tipo = {}
    for t, i in pares:
        by_tipo.setdefault(t, []).append(i)
    conditions = [
        and_(OrdenTrabajo.equipoTipo == t, OrdenTrabajo.equipoId.in_(ids))
        for t, ids in by_tipo.items()
    ]
    return or_(*conditions) if conditions else None


# =============================================================================
# SERVICIO 1 – Intervenciones por Tipo / Mes  (Dashboard 3.1 + 3.2)
# =============================================================================

def get_tipos_mensuales(fi, ff, nivel=None, nivel_id=None):
    """
    Barras apiladas por mes y tipo de intervención.
    También devuelve donut de distribución total y ratio correctivo mensual.
    """
    fi_dt, ff_dt = _fi_ff_dt(fi, ff)
    tipos_info = _get_tipos_info()
    meses = _mes_range(fi, ff)

    q = db.session.query(
        func.strftime('%Y-%m', OrdenTrabajo.fechaCreacion).label('mes'),
        OrdenTrabajo.tipo,
        func.count(OrdenTrabajo.id).label('n'),
    ).filter(
        OrdenTrabajo.fechaCreacion >= fi_dt,
        OrdenTrabajo.fechaCreacion <= ff_dt,
    )
    sf = _scope_filter(nivel, nivel_id)
    if sf is not None:
        q = q.filter(sf)
    rows = q.group_by('mes', OrdenTrabajo.tipo).all()

    tipos = sorted(set(r.tipo for r in rows))
    matrix = defaultdict(lambda: defaultdict(int))
    for r in rows:
        matrix[r.mes][r.tipo] = r.n

    datasets_bar = [{
        'label': _tipo_nombre(t, tipos_info),
        'data': [matrix[m].get(t, 0) for m in meses],
        'backgroundColor': _tipo_color(t, tipos_info),
    } for t in tipos]

    # Donut: totales
    totales = defaultdict(int)
    for r in rows:
        totales[r.tipo] += r.n

    donut = {
        'labels': [_tipo_nombre(t, tipos_info) for t in tipos],
        'data':   [totales[t] for t in tipos],
        'colors': [_tipo_color(t, tipos_info) for t in tipos],
        'total':  sum(totales.values()),
    }

    # Ratio correctivo mensual
    ratio_map = {}
    for m in meses:
        total_m = sum(matrix[m].values())
        corr_m  = matrix[m].get('correctivo', 0)
        ratio_map[m] = round(corr_m / total_m * 100, 1) if total_m else 0

    return {
        'bar': {
            'labels': [_label_mes(m) for m in meses],
            'datasets': datasets_bar,
        },
        'donut': donut,
        'ratio_correctivo': {
            'labels': [_label_mes(m) for m in meses],
            'data':   [ratio_map[m] for m in meses],
        },
    }


# =============================================================================
# SERVICIO 2 – OT por Prioridad  (Dashboard 3.3)
# =============================================================================

def get_prioridades(fi, ff, nivel=None, nivel_id=None):
    """Donut + barras mensuales por prioridad."""
    fi_dt, ff_dt = _fi_ff_dt(fi, ff)
    meses = _mes_range(fi, ff)
    sf = _scope_filter(nivel, nivel_id)

    q_tot = db.session.query(
        OrdenTrabajo.prioridad,
        func.count(OrdenTrabajo.id).label('n'),
    ).filter(
        OrdenTrabajo.fechaCreacion >= fi_dt,
        OrdenTrabajo.fechaCreacion <= ff_dt,
    )
    if sf is not None:
        q_tot = q_tot.filter(sf)
    rows_tot = q_tot.group_by(OrdenTrabajo.prioridad).all()

    # Ordenar según prioridad (mayor a menor)
    presentes = set(r.prioridad for r in rows_tot)
    prioridades = [p for p in _PRIORIDAD_ORDER if p in presentes]
    prioridades += sorted(presentes - set(_PRIORIDAD_ORDER))  # tipos no estándar al final

    totales = {r.prioridad: r.n for r in rows_tot}
    donut = {
        'labels': [p.capitalize() for p in prioridades],
        'data':   [totales.get(p, 0) for p in prioridades],
        'colors': [_PRIORIDAD_COLORS.get(p, '#9E9E9E') for p in prioridades],
        'total':  sum(totales.values()),
    }

    q_mes = db.session.query(
        func.strftime('%Y-%m', OrdenTrabajo.fechaCreacion).label('mes'),
        OrdenTrabajo.prioridad,
        func.count(OrdenTrabajo.id).label('n'),
    ).filter(
        OrdenTrabajo.fechaCreacion >= fi_dt,
        OrdenTrabajo.fechaCreacion <= ff_dt,
    )
    if sf is not None:
        q_mes = q_mes.filter(sf)
    rows_mes = q_mes.group_by('mes', OrdenTrabajo.prioridad).all()

    matrix = defaultdict(lambda: defaultdict(int))
    for r in rows_mes:
        matrix[r.mes][r.prioridad] = r.n

    datasets = [{
        'label': p.capitalize(),
        'data':  [matrix[m].get(p, 0) for m in meses],
        'backgroundColor': _PRIORIDAD_COLORS.get(p, '#9E9E9E'),
    } for p in prioridades]

    return {
        'donut': donut,
        'bar': {
            'labels': [_label_mes(m) for m in meses],
            'datasets': datasets,
        },
    }


# =============================================================================
# SERVICIO 3 – TOP Equipos  (Dashboard 3.8)
# =============================================================================

def get_top_equipos(fi, ff, limit=10, solo_correctivas=False, nivel=None, nivel_id=None):
    """
    TOP equipos por nº de intervenciones y horas de paro.
    Devuelve datos para Chart.js barras horizontales + tabla.
    """
    fi_dt, ff_dt = _fi_ff_dt(fi, ff)
    jer = _precargar_jerarquia()

    q = db.session.query(
        OrdenTrabajo.equipoTipo,
        OrdenTrabajo.equipoId,
        func.count(OrdenTrabajo.id).label('num_ot'),
        func.sum(OrdenTrabajo.tiempoParada).label('horas_paro'),
    ).filter(
        OrdenTrabajo.fechaCreacion >= fi_dt,
        OrdenTrabajo.fechaCreacion <= ff_dt,
    )
    if solo_correctivas:
        q = q.filter(OrdenTrabajo.tipo == 'correctivo')
    sf = _scope_filter(nivel, nivel_id)
    if sf is not None:
        q = q.filter(sf)

    rows = q.group_by(
        OrdenTrabajo.equipoTipo, OrdenTrabajo.equipoId
    ).order_by(func.count(OrdenTrabajo.id).desc()).limit(limit).all()

    tabla = [{
        'label':      _equipo_label(r.equipoTipo, r.equipoId, jer),
        'linea':      _linea_nombre(r.equipoTipo, r.equipoId, jer),
        'num_ot':     r.num_ot,
        'horas_paro': round(r.horas_paro or 0, 1),
    } for r in rows]

    return {
        'tabla': tabla,
        'chart_ot': {
            'labels': [r['label'] for r in tabla],
            'data':   [r['num_ot'] for r in tabla],
        },
        'chart_paro': {
            'labels': [r['label'] for r in tabla],
            'data':   [r['horas_paro'] for r in tabla],
        },
    }


# =============================================================================
# SERVICIO 4 – Pareto de Averías  (Dashboard 3.7)
# =============================================================================

def get_pareto_averias(fi, ff, limit=10, nivel=None, nivel_id=None):
    """
    Pareto: equipos con más OTs correctivas.
    Devuelve barras + línea acumulada % para Chart.js mixed.
    """
    data = get_top_equipos(fi, ff, limit=limit, solo_correctivas=True, nivel=nivel, nivel_id=nivel_id)
    tabla = data['tabla']

    if not tabla:
        return {'labels': [], 'counts': [], 'cumulative_pct': [], 'tabla': []}

    total = sum(r['num_ot'] for r in tabla)
    acum = 0
    for r in tabla:
        acum += r['num_ot']
        r['pct']      = round(r['num_ot'] / total * 100, 1) if total else 0
        r['pct_acum'] = round(acum / total * 100, 1) if total else 0

    return {
        'labels':         [r['label'] for r in tabla],
        'counts':         [r['num_ot'] for r in tabla],
        'cumulative_pct': [r['pct_acum'] for r in tabla],
        'tabla':          tabla,
    }


# =============================================================================
# SERVICIO 5 – Tiempos por Técnico  (Dashboard 3.5)
# =============================================================================

def get_tiempos_tecnicos(fi, ff, nivel=None, nivel_id=None):
    """
    Horas imputadas por técnico, desglosadas por tipo de OT.
    Fuente: RegistroTiempo (solo entradas cerradas, fin IS NOT NULL).
    """
    fi_dt, ff_dt = _fi_ff_dt(fi, ff)
    tipos_info = _get_tipos_info()
    sf = _scope_filter(nivel, nivel_id)

    q_rt = db.session.query(
        RegistroTiempo.tecnico,
        RegistroTiempo.inicio,
        RegistroTiempo.fin,
        OrdenTrabajo.tipo,
        OrdenTrabajo.id.label('ot_id'),
    ).join(
        OrdenTrabajo, RegistroTiempo.ordenId == OrdenTrabajo.id
    ).filter(
        RegistroTiempo.fin.isnot(None),
        OrdenTrabajo.fechaCreacion >= fi_dt,
        OrdenTrabajo.fechaCreacion <= ff_dt,
    )
    if sf is not None:
        q_rt = q_rt.filter(sf)
    rts = q_rt.all()

    horas_tipo = defaultdict(lambda: defaultdict(float))
    ot_set = defaultdict(set)

    for rt in rts:
        h = (rt.fin - rt.inicio).total_seconds() / 3600
        tecnico = (rt.tecnico or 'Sin técnico').strip()
        horas_tipo[tecnico][rt.tipo] += h
        ot_set[tecnico].add(rt.ot_id)

    tecnicos = sorted(horas_tipo.keys(),
                      key=lambda t: sum(horas_tipo[t].values()), reverse=True)
    todos_tipos = sorted({t for v in horas_tipo.values() for t in v})

    datasets = [{
        'label': _tipo_nombre(tipo, tipos_info),
        'data':  [round(horas_tipo[t].get(tipo, 0), 2) for t in tecnicos],
        'backgroundColor': _tipo_color(tipo, tipos_info),
    } for tipo in todos_tipos]

    tabla = [{
        'tecnico': t,
        **{tipo: round(horas_tipo[t].get(tipo, 0), 1) for tipo in todos_tipos},
        'total':   round(sum(horas_tipo[t].values()), 1),
        'num_ot':  len(ot_set[t]),
    } for t in tecnicos]

    return {
        'chart': {
            'labels':   tecnicos,
            'datasets': datasets,
        },
        'tabla':  tabla,
        'tipos':  todos_tipos,
    }


# =============================================================================
# SERVICIO 6 – Tiempos de Mantenimiento por Línea  (Dashboard 3.6)
# =============================================================================

def get_tiempos_linea(fi, ff, nivel=None, nivel_id=None):
    """
    Tiempos promedio (reacción, reparación) y total de paro por línea.
    Solo OTs con fechaInicio y fechaFin no nulos.
    """
    fi_dt, ff_dt = _fi_ff_dt(fi, ff)
    jer = _precargar_jerarquia()
    sf = _scope_filter(nivel, nivel_id)

    q_ord = OrdenTrabajo.query.filter(
        OrdenTrabajo.fechaCreacion >= fi_dt,
        OrdenTrabajo.fechaCreacion <= ff_dt,
        OrdenTrabajo.fechaInicio.isnot(None),
        OrdenTrabajo.fechaFin.isnot(None),
    )
    if sf is not None:
        q_ord = q_ord.filter(sf)
    ordenes = q_ord.all()

    data = defaultdict(lambda: {
        't_reaccion': [], 't_reparacion': [], 't_paro': 0.0, 'count': 0
    })

    for o in ordenes:
        linea = _linea_nombre(o.equipoTipo, o.equipoId, jer)
        t_reac = (o.fechaInicio - o.fechaCreacion).total_seconds() / 3600
        t_rep  = (o.fechaFin   - o.fechaInicio).total_seconds() / 3600

        if 0 <= t_reac <= 720:
            data[linea]['t_reaccion'].append(t_reac)
        if 0 < t_rep <= 720:
            data[linea]['t_reparacion'].append(t_rep)

        data[linea]['t_paro'] += o.tiempoParada or 0.0
        data[linea]['count'] += 1

    def avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0

    lineas = sorted(data.keys())
    tabla = [{
        'linea':          l,
        'count':          data[l]['count'],
        'avg_reaccion':   avg(data[l]['t_reaccion']),
        'avg_reparacion': avg(data[l]['t_reparacion']),
        'total_paro':     round(data[l]['t_paro'], 1),
    } for l in lineas]

    return {
        'chart': {
            'labels': lineas,
            'datasets': [
                {
                    'label': 'T. Reacción prom. (h)',
                    'data':  [avg(data[l]['t_reaccion']) for l in lineas],
                    'backgroundColor': '#1E88E5',
                },
                {
                    'label': 'T. Reparación prom. (h)',
                    'data':  [avg(data[l]['t_reparacion']) for l in lineas],
                    'backgroundColor': '#FB8C00',
                },
                {
                    'label': 'T. Paro total (h)',
                    'data':  [round(data[l]['t_paro'], 1) for l in lineas],
                    'backgroundColor': '#E53935',
                },
            ],
        },
        'tabla': tabla,
    }


# =============================================================================
# SERVICIO 7 – Heatmap Equipos × Meses  (Dashboard 3.8.3)
# =============================================================================

def get_heatmap_equipos(fi, ff, limit=15, nivel=None, nivel_id=None):
    """
    Series para ApexCharts heatmap: TOP {limit} equipos × meses.
    Cada serie es un equipo; cada punto es {x: 'mes', y: nº OTs}.
    """
    fi_dt, ff_dt = _fi_ff_dt(fi, ff)
    jer = _precargar_jerarquia()
    meses = _mes_range(fi, ff)
    sf = _scope_filter(nivel, nivel_id)

    q_top = db.session.query(
        OrdenTrabajo.equipoTipo,
        OrdenTrabajo.equipoId,
        func.count(OrdenTrabajo.id).label('total'),
    ).filter(
        OrdenTrabajo.fechaCreacion >= fi_dt,
        OrdenTrabajo.fechaCreacion <= ff_dt,
    )
    if sf is not None:
        q_top = q_top.filter(sf)
    top_rows = q_top.group_by(
        OrdenTrabajo.equipoTipo, OrdenTrabajo.equipoId
    ).order_by(desc('total')).limit(limit).all()

    if not top_rows:
        return []

    series = []
    for r in top_rows:
        label = _equipo_label(r.equipoTipo, r.equipoId, jer)

        monthly = db.session.query(
            func.strftime('%Y-%m', OrdenTrabajo.fechaCreacion).label('mes'),
            func.count(OrdenTrabajo.id).label('cnt'),
        ).filter(
            OrdenTrabajo.equipoTipo == r.equipoTipo,
            OrdenTrabajo.equipoId   == r.equipoId,
            OrdenTrabajo.fechaCreacion >= fi_dt,
            OrdenTrabajo.fechaCreacion <= ff_dt,
        ).group_by('mes').all()

        month_map = {m.mes: m.cnt for m in monthly}
        series.append({
            'name': label,
            'data': [{'x': _label_mes(m), 'y': month_map.get(m, 0)} for m in meses],
        })

    return series
