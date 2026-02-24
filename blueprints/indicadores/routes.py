"""
Rutas HTTP del módulo de Indicadores y Reportes.
"""
from datetime import date, timedelta
from functools import wraps

from flask import render_template, request, jsonify, send_file
from flask_jwt_extended import jwt_required, current_user

from blueprints.indicadores import bp
from blueprints.indicadores import services
from blueprints.indicadores import dashboard_services as ds


# =============================================================================
# DECORADOR DE ACCESO
# =============================================================================

def responsable_required(f):
    """Solo responsables y admins pueden acceder a Informes."""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        if not current_user or current_user.nivel == 'tecnico':
            from flask import redirect, url_for
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated


# =============================================================================
# PÁGINAS
# =============================================================================

@bp.route('/')
@responsable_required
def index():
    return render_template('indicadores/index.html')


@bp.route('/ordenes')
@responsable_required
def informe_ordenes():
    return render_template('indicadores/informe_ordenes.html')


@bp.route('/preventivos')
@responsable_required
def informe_preventivos():
    return render_template('indicadores/informe_preventivos.html')


@bp.route('/movimientos')
@responsable_required
def informe_movimientos():
    return render_template('indicadores/informe_movimientos.html')


@bp.route('/kpi')
@responsable_required
def indicadores_kpi():
    return render_template('indicadores/indicadores_kpi.html')


# =============================================================================
# API: INFORME ÓRDENES DE TRABAJO
# =============================================================================

@bp.route('/api/ordenes')
@responsable_required
def api_ordenes():
    fi = services._parse_fecha(request.args.get('fecha_inicio'))
    ff = services._parse_fecha(request.args.get('fecha_fin'))
    tipo = request.args.get('tipo') or None
    estado = request.args.get('estado') or None
    equipo_id = request.args.get('equipo_id') or None

    rows, totales = services.get_informe_ordenes(fi, ff, tipo, estado, equipo_id)
    return jsonify({'rows': rows, 'totales': totales, 'total': len(rows)})


@bp.route('/api/ordenes/excel')
@responsable_required
def api_ordenes_excel():
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        return jsonify({'error': 'Instala openpyxl: pip install openpyxl'}), 500

    fi = services._parse_fecha(request.args.get('fecha_inicio'))
    ff = services._parse_fecha(request.args.get('fecha_fin'))
    tipo = request.args.get('tipo') or None
    estado = request.args.get('estado') or None
    equipo_id = request.args.get('equipo_id') or None

    rows, totales = services.get_informe_ordenes(fi, ff, tipo, estado, equipo_id)
    buf = services.exportar_ordenes_excel(rows, totales)

    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='informe_ordenes.xlsx',
    )


# =============================================================================
# API: INFORME PREVENTIVOS PLANIFICADOS
# =============================================================================

@bp.route('/api/preventivos')
@responsable_required
def api_preventivos():
    fd = services._parse_fecha(request.args.get('fecha_desde')) or date.today()
    fh = services._parse_fecha(request.args.get('fecha_hasta')) or (date.today() + timedelta(days=30))
    equipo_id = request.args.get('equipo_id') or None

    rows, resumen = services.get_informe_preventivos(fd, fh, equipo_id)
    return jsonify({'rows': rows, 'resumen': resumen})


@bp.route('/api/preventivos/excel')
@responsable_required
def api_preventivos_excel():
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        return jsonify({'error': 'Instala openpyxl: pip install openpyxl'}), 500

    fd = services._parse_fecha(request.args.get('fecha_desde')) or date.today()
    fh = services._parse_fecha(request.args.get('fecha_hasta')) or (date.today() + timedelta(days=30))
    equipo_id = request.args.get('equipo_id') or None

    rows, _ = services.get_informe_preventivos(fd, fh, equipo_id)
    buf = services.exportar_preventivos_excel(rows)

    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='informe_preventivos.xlsx',
    )


# =============================================================================
# API: INFORME MOVIMIENTOS DE STOCK
# =============================================================================

@bp.route('/api/movimientos')
@responsable_required
def api_movimientos():
    fi = services._parse_fecha(request.args.get('fecha_inicio'))
    ff = services._parse_fecha(request.args.get('fecha_fin'))
    tipo = request.args.get('tipo') or None
    recambio_id = request.args.get('recambio_id') or None

    rows, totales = services.get_informe_movimientos(fi, ff, tipo, recambio_id)
    return jsonify({'rows': rows, 'totales': totales, 'total': len(rows)})


@bp.route('/api/movimientos/excel')
@responsable_required
def api_movimientos_excel():
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        return jsonify({'error': 'Instala openpyxl: pip install openpyxl'}), 500

    fi = services._parse_fecha(request.args.get('fecha_inicio'))
    ff = services._parse_fecha(request.args.get('fecha_fin'))
    tipo = request.args.get('tipo') or None
    recambio_id = request.args.get('recambio_id') or None

    rows, totales = services.get_informe_movimientos(fi, ff, tipo, recambio_id)
    buf = services.exportar_movimientos_excel(rows, totales)

    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='informe_movimientos.xlsx',
    )


# =============================================================================
# API: INDICADORES KPI
# =============================================================================

@bp.route('/api/jerarquia')
@responsable_required
def api_jerarquia():
    nivel = request.args.get('nivel', 'root')
    parent_id = request.args.get('parent_id') or None
    return jsonify(services.get_hijos_jerarquia(nivel, parent_id))


@bp.route('/api/kpi')
@responsable_required
def api_kpi():
    fi = services._parse_fecha(request.args.get('fecha_inicio')) or date.today().replace(day=1)
    ff = services._parse_fecha(request.args.get('fecha_fin')) or date.today()
    nivel = request.args.get('nivel') or None
    nivel_id = request.args.get('nivel_id') or None

    resultado = services.calcular_indicadores(fi, ff, nivel, nivel_id)
    resultado['periodo'] = {
        'fecha_inicio': fi.isoformat(),
        'fecha_fin': ff.isoformat(),
    }
    return jsonify(resultado)


# =============================================================================
# PÁGINA: DASHBOARDS GRÁFICOS
# =============================================================================

@bp.route('/dashboards')
@responsable_required
def dashboards():
    return render_template('indicadores/dashboards.html')


# =============================================================================
# API: DASHBOARDS — helpers de fecha comunes
# =============================================================================

def _dash_fechas():
    """Parsea fecha_inicio/fin de la query string; defaults: año en curso."""
    hoy = date.today()
    fi = services._parse_fecha(request.args.get('fecha_inicio')) or hoy.replace(month=1, day=1)
    ff = services._parse_fecha(request.args.get('fecha_fin'))   or hoy
    return fi, ff


def _dash_nivel():
    """Parsea nivel/nivel_id de la query string para filtrado jerárquico."""
    nivel    = request.args.get('nivel') or None
    nivel_id = request.args.get('nivel_id') or None
    return nivel, nivel_id


# --- 3.1 + 3.2  Intervenciones por tipo / mes + ratio correctivo

@bp.route('/api/dashboard/tipos-mensuales')
@responsable_required
def api_dash_tipos():
    fi, ff = _dash_fechas()
    nivel, nivel_id = _dash_nivel()
    return jsonify(ds.get_tipos_mensuales(fi, ff, nivel, nivel_id))


# --- 3.3  OT por prioridad

@bp.route('/api/dashboard/prioridades')
@responsable_required
def api_dash_prioridades():
    fi, ff = _dash_fechas()
    nivel, nivel_id = _dash_nivel()
    return jsonify(ds.get_prioridades(fi, ff, nivel, nivel_id))


# --- 3.7  Pareto de averías

@bp.route('/api/dashboard/pareto-averias')
@responsable_required
def api_dash_pareto():
    fi, ff = _dash_fechas()
    nivel, nivel_id = _dash_nivel()
    limit = request.args.get('limit', 10, type=int)
    return jsonify(ds.get_pareto_averias(fi, ff, limit, nivel, nivel_id))


# --- 3.8  TOP equipos

@bp.route('/api/dashboard/top-equipos')
@responsable_required
def api_dash_top_equipos():
    fi, ff = _dash_fechas()
    nivel, nivel_id = _dash_nivel()
    limit = request.args.get('limit', 10, type=int)
    return jsonify(ds.get_top_equipos(fi, ff, limit, nivel_id=nivel_id, nivel=nivel))


# --- 3.5  Tiempos por técnico

@bp.route('/api/dashboard/tiempos-tecnicos')
@responsable_required
def api_dash_tiempos_tec():
    fi, ff = _dash_fechas()
    nivel, nivel_id = _dash_nivel()
    return jsonify(ds.get_tiempos_tecnicos(fi, ff, nivel, nivel_id))


# --- 3.6  Tiempos por línea

@bp.route('/api/dashboard/tiempos-linea')
@responsable_required
def api_dash_tiempos_linea():
    fi, ff = _dash_fechas()
    nivel, nivel_id = _dash_nivel()
    return jsonify(ds.get_tiempos_linea(fi, ff, nivel, nivel_id))


# --- 3.8.3  Heatmap equipos × meses

@bp.route('/api/dashboard/heatmap-equipos')
@responsable_required
def api_dash_heatmap():
    fi, ff = _dash_fechas()
    nivel, nivel_id = _dash_nivel()
    limit = request.args.get('limit', 15, type=int)
    return jsonify(ds.get_heatmap_equipos(fi, ff, limit, nivel, nivel_id))
