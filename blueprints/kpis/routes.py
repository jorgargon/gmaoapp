"""
Rutas del módulo KPIs de Paros de Producción.
"""
from datetime import date, timedelta
from functools import wraps

from flask import render_template, request, jsonify, send_file
from flask_jwt_extended import jwt_required, current_user

from blueprints.kpis import bp
from blueprints.kpis import paros_services as svc


# =============================================================================
# DECORADOR DE ACCESO (igual que en indicadores)
# =============================================================================

def responsable_required(f):
    """Solo responsables y admins pueden acceder a KPIs."""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        if not current_user or current_user.nivel == 'tecnico':
            from flask import redirect, url_for
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated


# =============================================================================
# PÁGINA PRINCIPAL
# =============================================================================

@bp.route('/paros')
@responsable_required
def kpis_paros():
    lineas   = svc.get_lineas()
    maquinas = svc.get_maquinas()
    return render_template('kpis/paros.html', lineas=lineas, maquinas=maquinas)


# =============================================================================
# API — DATOS JSON
# =============================================================================

@bp.route('/paros/datos')
@responsable_required
def api_paros_datos():
    hoy = date.today()

    fi = svc._parse_fecha(request.args.get('fecha_inicio')) or (hoy - timedelta(days=365))
    ff = svc._parse_fecha(request.args.get('fecha_fin'))   or hoy

    agrupacion = request.args.get('agrupacion', 'mensual')

    # Multivalue: ?linea=1&linea=2
    lineas_ids   = [int(x) for x in request.args.getlist('linea')   if x.isdigit()] or None
    maquinas_ids = [int(x) for x in request.args.getlist('maquina') if x.isdigit()] or None

    datos = svc.calcular_paros(
        fecha_ini=fi,
        fecha_fin=ff,
        agrupacion=agrupacion,
        lineas_ids=lineas_ids,
        maquinas_ids=maquinas_ids,
    )
    return jsonify(datos)


# =============================================================================
# API — LISTA DE MAQUINAS POR LÍNEA (para filtro dinámico)
# =============================================================================

@bp.route('/paros/api/maquinas')
@responsable_required
def api_maquinas():
    lineas_ids = [int(x) for x in request.args.getlist('linea') if x.isdigit()] or None
    return jsonify(svc.get_maquinas(lineas_ids))


# =============================================================================
# EXPORTAR EXCEL
# =============================================================================

@bp.route('/paros/datos/excel')
@responsable_required
def api_paros_excel():
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        return jsonify({'error': 'openpyxl no instalado'}), 500

    hoy = date.today()
    fi = svc._parse_fecha(request.args.get('fecha_inicio')) or (hoy - timedelta(days=365))
    ff = svc._parse_fecha(request.args.get('fecha_fin'))   or hoy

    agrupacion   = request.args.get('agrupacion', 'mensual')
    lineas_ids   = [int(x) for x in request.args.getlist('linea')   if x.isdigit()] or None
    maquinas_ids = [int(x) for x in request.args.getlist('maquina') if x.isdigit()] or None

    datos = svc.calcular_paros(fi, ff, agrupacion, lineas_ids, maquinas_ids)
    buf   = svc.exportar_paros_excel(datos)

    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'kpi_paros_{fi}_{ff}.xlsx',
    )
