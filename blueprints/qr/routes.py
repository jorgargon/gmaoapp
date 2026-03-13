"""
Rutas del módulo QR: página de configuración de etiquetas y API de filtros.
"""
from flask import render_template, request, jsonify, send_file
from flask_jwt_extended import jwt_required

from blueprints.qr import bp
from blueprints.qr.qr_services import (
    generar_qr_bytes, get_activos_filtrados,
    generar_pdf_etiquetas, get_plantas, get_zonas, get_lineas, get_maquinas,
)
from blueprints.configuracion.routes import config_required


# ─── Página de etiquetas (configuración) ─────────────────────────────────────

@bp.route('/etiquetas')
@config_required
def etiquetas():
    plantas = get_plantas()
    return render_template('configuracion/qr_labels.html', plantas=plantas)


# ─── API filtros en cascada ──────────────────────────────────────────────────

@bp.route('/api/zonas')
@jwt_required()
def api_zonas():
    planta_id = request.args.get('planta', type=int)
    return jsonify(get_zonas(planta_id))


@bp.route('/api/lineas')
@jwt_required()
def api_lineas():
    zona_id = request.args.get('zona', type=int)
    return jsonify(get_lineas(zona_id))


@bp.route('/api/maquinas')
@jwt_required()
def api_maquinas():
    linea_id = request.args.get('linea', type=int)
    return jsonify(get_maquinas(linea_id))


# ─── Conteo de etiquetas ────────────────────────────────────────────────────

@bp.route('/api/conteo')
@jwt_required()
def api_conteo():
    activos = _get_activos_from_params()
    return jsonify({'total': len(activos)})


# ─── Preview QR individual ──────────────────────────────────────────────────

@bp.route('/api/preview')
@jwt_required()
def api_preview():
    equipo_tipo = request.args.get('equipoTipo', '')
    equipo_id = request.args.get('equipoId', type=int)
    if not equipo_tipo or not equipo_id:
        return jsonify({'error': 'Parámetros requeridos'}), 400
    base_url = request.host_url
    buf = generar_qr_bytes(equipo_tipo, equipo_id, base_url)
    return send_file(buf, mimetype='image/png', download_name='qr_preview.png')


# ─── Descarga PDF de etiquetas ───────────────────────────────────────────────

@bp.route('/descargar-pdf')
@config_required
def descargar_pdf():
    activos = _get_activos_from_params()
    if not activos:
        return jsonify({'error': 'No se encontraron activos para los filtros seleccionados'}), 404
    base_url = request.host_url
    buf = generar_pdf_etiquetas(activos, base_url)
    return send_file(buf, mimetype='application/pdf',
                     download_name='etiquetas_qr.pdf', as_attachment=True)


# ─── Helper ──────────────────────────────────────────────────────────────────

def _get_activos_from_params():
    planta_id = request.args.get('planta', type=int)
    zona_id = request.args.get('zona', type=int)
    linea_id = request.args.get('linea', type=int)
    maquina_id = request.args.get('maquina', type=int)
    return get_activos_filtrados(planta_id, zona_id, linea_id, maquina_id)
