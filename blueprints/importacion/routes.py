"""
Rutas HTTP del módulo de Importación Masiva.
Solo accesible para usuarios con nivel 'admin'.
"""
import os
import time
import logging
from functools import wraps

from flask import render_template, request, redirect, url_for
from flask_jwt_extended import jwt_required, current_user

from blueprints.importacion import bp
from blueprints.importacion import parser as p
from blueprints.importacion import validator as v
from blueprints.importacion import importer as imp
from blueprints.importacion import verifier
from models import db

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

MAX_UPLOAD_MB = int(os.environ.get('MAX_UPLOAD_MB', 10))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Configurar logger con FileHandler
_log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(_log_dir, exist_ok=True)

log = logging.getLogger('importacion')
if not log.handlers:
    log.setLevel(logging.INFO)
    _fh = logging.FileHandler(os.path.join(_log_dir, 'importacion.log'), encoding='utf-8')
    _fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    log.addHandler(_fh)

# =============================================================================
# DECORADOR ADMIN
# =============================================================================

def admin_required(f):
    """Solo administradores pueden acceder al módulo de importación."""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        if not current_user or current_user.nivel != 'admin':
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated


# =============================================================================
# MAPAS DE TIPO → FUNCIONES
# =============================================================================

TIPOS_CONFIG = {
    'activos': {
        'titulo': 'Importación de Activos',
        'parse': p.parse_activos,
        'validate': v.validate_activos,
        'import': imp.import_activos,
        'sheets': ['PLANTAS', 'ZONAS', 'LINEAS', 'MAQUINAS', 'ELEMENTOS'],
    },
    'gamas': {
        'titulo': 'Importación de Gamas de Mantenimiento',
        'parse': p.parse_gamas,
        'validate': v.validate_gamas,
        'import': imp.import_gamas,
        'sheets': ['GAMAS', 'TAREAS', 'CHECKLIST', 'RECAMBIOS'],
    },
    'historico': {
        'titulo': 'Importación de Histórico de OTs',
        'parse': p.parse_historico,
        'validate': v.validate_historico,
        'import': imp.import_historico,
        'sheets': ['ORDENES'],
    },
    'recambios': {
        'titulo': 'Importación de Recambios y Stock',
        'parse': p.parse_recambios,
        'validate': v.validate_recambios,
        'import': imp.import_recambios,
        'sheets': ['RECAMBIOS'],
    },
    'tecnicos': {
        'titulo': 'Importación de Técnicos',
        'parse': p.parse_tecnicos,
        'validate': v.validate_tecnicos,
        'import': imp.import_tecnicos,
        'sheets': ['TECNICOS'],
    },
    'usuarios': {
        'titulo': 'Importación de Usuarios',
        'parse': p.parse_usuarios,
        'validate': v.validate_usuarios,
        'import': imp.import_usuarios,
        'sheets': ['USUARIOS'],
    },
}


# =============================================================================
# RUTAS
# =============================================================================

@bp.route('/')
@admin_required
def index():
    return render_template('importacion/index.html')


@bp.route('/upload/<tipo>', methods=['POST'])
@admin_required
def upload(tipo):
    """Procesa la subida de un fichero Excel e importa los datos."""
    t_inicio = time.time()

    if tipo not in TIPOS_CONFIG:
        return render_template('importacion/resultado.html', result={
            'tipo': tipo,
            'titulo': 'Error',
            'sheets': [],
            'tiempo_s': 0,
            'exito': False,
            'mensaje_error': f"Tipo de importación desconocido: '{tipo}'",
        })

    config = TIPOS_CONFIG[tipo]

    # Comprobar que se ha subido un fichero
    if 'fichero' not in request.files:
        return render_template('importacion/resultado.html', result={
            'tipo': tipo,
            'titulo': config['titulo'],
            'sheets': [],
            'tiempo_s': round(time.time() - t_inicio, 2),
            'exito': False,
            'mensaje_error': 'No se ha seleccionado ningún fichero.',
        })

    fichero = request.files['fichero']

    if not fichero.filename:
        return render_template('importacion/resultado.html', result={
            'tipo': tipo,
            'titulo': config['titulo'],
            'sheets': [],
            'tiempo_s': round(time.time() - t_inicio, 2),
            'exito': False,
            'mensaje_error': 'Nombre de fichero vacío.',
        })

    if not fichero.filename.lower().endswith('.xlsx'):
        return render_template('importacion/resultado.html', result={
            'tipo': tipo,
            'titulo': config['titulo'],
            'sheets': [],
            'tiempo_s': round(time.time() - t_inicio, 2),
            'exito': False,
            'mensaje_error': 'Solo se aceptan ficheros .xlsx',
        })

    # Leer bytes y comprobar tamaño
    file_bytes = fichero.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        return render_template('importacion/resultado.html', result={
            'tipo': tipo,
            'titulo': config['titulo'],
            'sheets': [],
            'tiempo_s': round(time.time() - t_inicio, 2),
            'exito': False,
            'mensaje_error': f'El fichero supera el límite de {MAX_UPLOAD_MB} MB.',
        })

    try:
        log.info(f"Inicio importación '{tipo}' por usuario '{current_user.username}' — {len(file_bytes)} bytes")

        # 1. PARSEAR
        parsed = config['parse'](file_bytes)

        # 2. VALIDAR
        validated = config['validate'](parsed)

        # 3. IMPORTAR
        import_results = config['import'](validated)

        # 4. Construir resultado para la plantilla
        sheets_result = []
        total_errores_global = 0

        for sheet_name in config['sheets']:
            parsed_rows = parsed.get(sheet_name, [])
            val_data = validated.get(sheet_name, {'valid': [], 'errors': [], 'warnings': []})
            imp_data = import_results.get(sheet_name, {'insertadas': 0, 'actualizadas': 0, 'errores': 0})

            total_excel = len(parsed_rows)
            n_valid = len(val_data.get('valid', []))
            n_errors_val = len(val_data.get('errors', []))
            n_imp_errors = imp_data.get('errores', 0)
            errores_total = n_errors_val + n_imp_errors

            omitidas = total_excel - n_valid - n_errors_val

            total_errores_global += errores_total

            sheets_result.append({
                'nombre': sheet_name,
                'total_excel': total_excel,
                'insertadas': imp_data.get('insertadas', 0),
                'actualizadas': imp_data.get('actualizadas', 0),
                'errores': errores_total,
                'omitidas': max(omitidas, 0),
                'filas_error': val_data.get('errors', []),
                'advertencias': val_data.get('warnings', []),
            })

        tiempo_s = round(time.time() - t_inicio, 2)
        exito = total_errores_global == 0

        log.info(
            f"Fin importación '{tipo}' — {tiempo_s}s — "
            f"errores_totales={total_errores_global}"
        )

        return render_template('importacion/resultado.html', result={
            'tipo': tipo,
            'titulo': config['titulo'],
            'sheets': sheets_result,
            'tiempo_s': tiempo_s,
            'exito': exito,
            'mensaje_error': None,
        })

    except Exception as e:
        db.session.rollback()
        log.error(f"Excepción no controlada en importación '{tipo}': {e}", exc_info=True)
        return render_template('importacion/resultado.html', result={
            'tipo': tipo,
            'titulo': config['titulo'],
            'sheets': [],
            'tiempo_s': round(time.time() - t_inicio, 2),
            'exito': False,
            'mensaje_error': f'Error inesperado durante la importación: {str(e)}',
        })


@bp.route('/verificar')
@admin_required
def verificar():
    """Muestra el estado actual de la BD."""
    summary = verifier.get_db_summary()
    return render_template('importacion/verificar.html', summary=summary)
