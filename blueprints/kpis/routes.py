"""
Rutas del módulo KPIs de Paros de Producción.
"""
import logging
from datetime import date, timedelta
from functools import wraps

log = logging.getLogger(__name__)

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
    plantas  = svc.get_plantas()
    return render_template('kpis/paros.html', plantas=plantas)


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

    plantas_ids  = [int(x) for x in request.args.getlist('planta')  if x.isdigit()] or None
    zonas_ids    = [int(x) for x in request.args.getlist('zona')    if x.isdigit()] or None
    lineas_ids   = [int(x) for x in request.args.getlist('linea')   if x.isdigit()] or None
    maquinas_ids = [int(x) for x in request.args.getlist('maquina') if x.isdigit()] or None

    datos = svc.calcular_paros(
        fecha_ini=fi,
        fecha_fin=ff,
        agrupacion=agrupacion,
        plantas_ids=plantas_ids,
        zonas_ids=zonas_ids,
        lineas_ids=lineas_ids,
        maquinas_ids=maquinas_ids,
    )
    return jsonify(datos)


# =============================================================================
# API — LISTAS PARA FILTROS EN CASCADA
# =============================================================================

@bp.route('/paros/api/zonas')
@responsable_required
def api_zonas():
    plantas_ids = [int(x) for x in request.args.getlist('planta') if x.isdigit()] or None
    return jsonify(svc.get_zonas(plantas_ids))


@bp.route('/paros/api/lineas')
@responsable_required
def api_lineas():
    zonas_ids = [int(x) for x in request.args.getlist('zona') if x.isdigit()] or None
    return jsonify(svc.get_lineas(zonas_ids))


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
    plantas_ids  = [int(x) for x in request.args.getlist('planta')  if x.isdigit()] or None
    zonas_ids    = [int(x) for x in request.args.getlist('zona')    if x.isdigit()] or None
    lineas_ids   = [int(x) for x in request.args.getlist('linea')   if x.isdigit()] or None
    maquinas_ids = [int(x) for x in request.args.getlist('maquina') if x.isdigit()] or None

    datos = svc.calcular_paros(fi, ff, agrupacion, lineas_ids, maquinas_ids,
                               plantas_ids=plantas_ids, zonas_ids=zonas_ids)
    buf   = svc.exportar_paros_excel(datos)

    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'kpi_paros_{fi}_{ff}.xlsx',
    )


# =============================================================================
# EXPORTAR PDF
# =============================================================================

@bp.route('/paros/datos/pdf', methods=['GET', 'POST'])
@responsable_required
def api_paros_pdf():
    hoy = date.today()
    fi = svc._parse_fecha(request.args.get('fecha_inicio')) or (hoy - timedelta(days=365))
    ff = svc._parse_fecha(request.args.get('fecha_fin'))   or hoy

    agrupacion   = request.args.get('agrupacion', 'mensual')
    plantas_ids  = [int(x) for x in request.args.getlist('planta')  if x.isdigit()] or None
    zonas_ids    = [int(x) for x in request.args.getlist('zona')    if x.isdigit()] or None
    lineas_ids   = [int(x) for x in request.args.getlist('linea')   if x.isdigit()] or None
    maquinas_ids = [int(x) for x in request.args.getlist('maquina') if x.isdigit()] or None

    datos = svc.calcular_paros(fi, ff, agrupacion, lineas_ids, maquinas_ids,
                               plantas_ids=plantas_ids, zonas_ids=zonas_ids)

    # Imágenes de gráficas enviadas desde el cliente (solo en POST)
    chart_images = {}
    if request.method == 'POST':
        body = request.get_json(silent=True, force=True) or {}
        chart_images = body.get('charts', {})
        log.info("PDF route: %d gráficas en el cuerpo POST", len(chart_images))

    buf = svc.exportar_paros_pdf(datos, chart_images=chart_images)

    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'kpi_paros_{fi}_{ff}.pdf',
    )
