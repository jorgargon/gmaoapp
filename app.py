# Archivo principal de la aplicación Flask para el GMAO
# =============================================================================

from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, and_, func, case
from models import (db, Empresa, Planta, Zona, Linea, Maquina, Elemento, 
                    Activo, Intervencion, Recambio, RecambioEquipo, MovimientoStock,
                    OrdenTrabajo, ConsumoRecambio, PlanPreventivo, TareaPreventivo,
                    GamaMantenimiento, TareaGama, RecambioGama, AsignacionGama,
                    RegistroTiempo, TipoIntervencion, Tecnico,
                    ChecklistItem, RespuestaChecklist,
                    ConfiguracionGeneral, Usuario)
from datetime import datetime, date, timedelta
from flask_jwt_extended import (
    JWTManager, create_access_token, set_access_cookies,
    unset_jwt_cookies, jwt_required, get_jwt_identity, current_user, verify_jwt_in_request
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

import json
import re
import os

# =============================================================================
# DETECCIÓN DE DISPOSITIVO MÓVIL
# =============================================================================

_MOBILE_UA_RE = re.compile(
    r'Mobile|Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini',
    re.IGNORECASE
)

def is_mobile_device():
    """Devuelve True si el User-Agent corresponde a un móvil o tablet."""
    ua = request.headers.get('User-Agent', '')
    return bool(_MOBILE_UA_RE.search(ua))

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def getEquipoNombre(tipo, id):
    """Obtiene el nombre de un equipo dado su tipo e ID"""
    if not id: return 'Sin asignar'
    
    try:
        if tipo == 'maquina':
            m = Maquina.query.get(id)
            return m.nombre if m else 'Desconocido'
        elif tipo == 'elemento':
            e = Elemento.query.get(id)
            return e.nombre if e else 'Desconocido'
        elif tipo == 'linea':
            l = Linea.query.get(id)
            return l.nombre if l else 'Desconocido'
        elif tipo == 'zona':
            z = Zona.query.get(id)
            return z.nombre if z else 'Desconocido'
        elif tipo == 'planta':
            p = Planta.query.get(id)
            return p.nombre if p else 'Desconocido'
        elif tipo == 'empresa':
            e = Empresa.query.get(id)
            return e.nombre if e else 'Desconocido'
        return 'Tipo desconocido'
    except:
        return 'Error al obtener nombre'

# =============================================================================
# CONFIGURACIÓN DE LA APLICACIÓN
# =============================================================================

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///gmao.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gmao-secret-key-2024')

db.init_app(app)

# =============================================================================
# BLUEPRINTS
# =============================================================================

from blueprints.indicadores import bp as indicadores_bp
app.register_blueprint(indicadores_bp)

from blueprints.mobile import bp as mobile_bp
app.register_blueprint(mobile_bp)

# =============================================================================
# GUARDIA MÓVIL: impide acceso a páginas de escritorio desde móvil/tablet
# =============================================================================

@app.before_request
def mobile_guard():
    """Redirige a /movil/ si el dispositivo es móvil y accede a una ruta de escritorio."""
    # Solo peticiones GET a páginas HTML
    if request.method != 'GET':
        return
    path = request.path
    # Rutas permitidas siempre: API, estáticos, login y todo lo que sea /movil/
    if path.startswith(('/api/', '/static/', '/movil/', '/login')):
        return
    if not is_mobile_device():
        return
    # Es móvil y está intentando acceder a una ruta de escritorio
    # Solo redirigimos si ya está autenticado; si no, el flujo de login lo manejará
    try:
        verify_jwt_in_request(optional=True)
        if current_user:
            return redirect(url_for('mobile.home'))
    except Exception:
        pass

# =============================================================================
# CONFIGURACIÓN JWT
# =============================================================================

app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'gmao-jwt-super-secret-key-2026')
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = False # True si usas HTTPS
app.config['JWT_COOKIE_CSRF_PROTECT'] = False # Desactivado por simplicidad, activar en prod
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=12)

jwt = JWTManager(app)

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return Usuario.query.filter_by(username=identity).first()

@jwt.unauthorized_loader
def unauthorized_callback(callback):
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'No autorizado'}), 401
    return redirect(url_for('login'))

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Sesión expirada'}), 401
    return redirect(url_for('login'))

@app.context_processor
def inject_user():
    tecnico_puede_cerrar = False
    try:
        conf = ConfiguracionGeneral.query.filter_by(clave='tecnico_puede_cerrar').first()
        if conf and conf.valor == 'true':
            tecnico_puede_cerrar = True
            
        verify_jwt_in_request(optional=True)
        return dict(current_user=current_user, tecnico_puede_cerrar=tecnico_puede_cerrar)
    except Exception:
        return dict(current_user=None, tecnico_puede_cerrar=tecnico_puede_cerrar)

def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            if not current_user or current_user.nivel not in roles:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Acceso denegado. Permisos insuficientes.'}), 403
                else:
                    flash('No tienes permisos para acceder a esta página.', 'error')
                    return redirect(url_for('home'))
            return fn(*args, **kwargs)
        return decorator
    return wrapper

@app.template_filter('formato_espanol')
def formato_espanol_filter(value, max_decimals=2):
    if value is None or value == '':
        return '-'
    try:
        val = float(value)
        if val.is_integer():
            return f"{int(val):,}".replace(",", ".")
        else:
            s_int = f"{int(val):,}".replace(",", ".")
            s_dec = ("{:." + str(max_decimals) + "f}").format(val).split(".")[1]
            return f"{s_int},{s_dec}"
    except (ValueError, TypeError):
        return value

@app.before_request
def createTables():
    if not hasattr(app, 'dbInitialized'):
        db.create_all()
        # Create default admin user if none exists
        if not Usuario.query.first():
            admin_user = Usuario(
                nombre='Admin',
                apellidos='Sistema',
                username='admin',
                password_hash=generate_password_hash('admin123', method='pbkdf2:sha256'),
                nivel='admin',
                activo=True
            )
            db.session.add(admin_user)
            try:
                db.session.commit()
                print("Default admin user created: admin / admin123")
            except Exception as e:
                db.session.rollback()
                print(f"Error creating default admin: {e}")
                
        app.dbInitialized = True

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Helper function para obtener nombre de equipo por tipo/id
def getEquipoNombre(equipoTipo, equipoId):
    """Obtiene el nombre del equipo según su tipo e ID"""
    modelos = {
        'empresa': Empresa,
        'planta': Planta,
        'zona': Zona,
        'linea': Linea,
        'maquina': Maquina,
        'elemento': Elemento
    }
    if equipoTipo in modelos and equipoId:
        entidad = modelos[equipoTipo].query.get(equipoId)
        if entidad:
            return entidad.nombre
    return ''

def getEquipoInfo(equipoTipo, equipoId):
    """Obtiene el nombre y código del equipo según su tipo e ID"""
    modelos = {
        'empresa': Empresa,
        'planta': Planta,
        'zona': Zona,
        'linea': Linea,
        'maquina': Maquina,
        'elemento': Elemento
    }
    if equipoTipo in modelos and equipoId:
        entidad = modelos[equipoTipo].query.get(equipoId)
        if entidad:
            return {
                'nombre': entidad.nombre,
                'codigo': entidad.codigo
            }
    return {'nombre': '', 'codigo': ''}

def getEquipoRutaCompleta(equipoTipo, equipoId):
    """Construye la ruta jerárquica completa del equipo (Empresa > Planta > Zona > Línea > Máquina > Elemento)"""
    if not equipoTipo or not equipoId:
        return ''
    
    ruta = []
    
    if equipoTipo == 'elemento':
        elemento = Elemento.query.get(equipoId)
        if elemento:
            ruta.append(f"{elemento.codigo}")
            maquina = Maquina.query.get(elemento.maquinaId)
            if maquina:
                ruta.insert(0, f"{maquina.codigo}")
                linea = Linea.query.get(maquina.lineaId)
                if linea:
                    ruta.insert(0, f"{linea.codigo}")
                    zona = Zona.query.get(linea.zonaId)
                    if zona:
                        ruta.insert(0, f"{zona.codigo}")
                        planta = Planta.query.get(zona.plantaId)
                        if planta:
                            ruta.insert(0, f"{planta.codigo}")
                            empresa = Empresa.query.get(planta.empresaId)
                            if empresa:
                                ruta.insert(0, f"{empresa.codigo}")
    
    elif equipoTipo == 'maquina':
        maquina = Maquina.query.get(equipoId)
        if maquina:
            ruta.append(f"{maquina.codigo}")
            linea = Linea.query.get(maquina.lineaId)
            if linea:
                ruta.insert(0, f"{linea.codigo}")
                zona = Zona.query.get(linea.zonaId)
                if zona:
                    ruta.insert(0, f"{zona.codigo}")
                    planta = Planta.query.get(zona.plantaId)
                    if planta:
                        ruta.insert(0, f"{planta.codigo}")
                        empresa = Empresa.query.get(planta.empresaId)
                        if empresa:
                            ruta.insert(0, f"{empresa.codigo}")
    
    elif equipoTipo == 'linea':
        linea = Linea.query.get(equipoId)
        if linea:
            ruta.append(f"{linea.codigo}")
            zona = Zona.query.get(linea.zonaId)
            if zona:
                ruta.insert(0, f"{zona.codigo}")
                planta = Planta.query.get(zona.plantaId)
                if planta:
                    ruta.insert(0, f"{planta.codigo}")
                    empresa = Empresa.query.get(planta.empresaId)
                    if empresa:
                        ruta.insert(0, f"{empresa.codigo}")
    
    elif equipoTipo == 'zona':
        zona = Zona.query.get(equipoId)
        if zona:
            ruta.append(f"{zona.codigo}")
            planta = Planta.query.get(zona.plantaId)
            if planta:
                ruta.insert(0, f"{planta.codigo}")
                empresa = Empresa.query.get(planta.empresaId)
                if empresa:
                    ruta.insert(0, f"{empresa.codigo}")
    
    elif equipoTipo == 'planta':
        planta = Planta.query.get(equipoId)
        if planta:
            ruta.append(f"{planta.codigo}")
            empresa = Empresa.query.get(planta.empresaId)
            if empresa:
                ruta.insert(0, f"{empresa.codigo}")
    
    elif equipoTipo == 'empresa':
        empresa = Empresa.query.get(equipoId)
        if empresa:
            ruta.append(f"{empresa.codigo}")
    
    return ' > '.join(ruta) if ruta else ''


def getEquipoRutaNombres(equipoTipo, equipoId):
    """Construye la ruta jerárquica como lista de {nombre, tipo} desde Planta hasta el equipo."""
    if not equipoTipo or not equipoId:
        return []

    ruta = []

    if equipoTipo == 'elemento':
        elem = Elemento.query.get(equipoId)
        if elem:
            ruta.append({'nombre': elem.nombre, 'tipo': 'elemento'})
            maq = Maquina.query.get(elem.maquinaId)
            if maq:
                ruta.insert(0, {'nombre': maq.nombre, 'tipo': 'maquina'})
                linea = Linea.query.get(maq.lineaId)
                if linea:
                    ruta.insert(0, {'nombre': linea.nombre, 'tipo': 'linea'})
                    zona = Zona.query.get(linea.zonaId)
                    if zona:
                        ruta.insert(0, {'nombre': zona.nombre, 'tipo': 'zona'})
                        planta = Planta.query.get(zona.plantaId)
                        if planta:
                            ruta.insert(0, {'nombre': planta.nombre, 'tipo': 'planta'})

    elif equipoTipo == 'maquina':
        maq = Maquina.query.get(equipoId)
        if maq:
            ruta.append({'nombre': maq.nombre, 'tipo': 'maquina'})
            linea = Linea.query.get(maq.lineaId)
            if linea:
                ruta.insert(0, {'nombre': linea.nombre, 'tipo': 'linea'})
                zona = Zona.query.get(linea.zonaId)
                if zona:
                    ruta.insert(0, {'nombre': zona.nombre, 'tipo': 'zona'})
                    planta = Planta.query.get(zona.plantaId)
                    if planta:
                        ruta.insert(0, {'nombre': planta.nombre, 'tipo': 'planta'})

    elif equipoTipo == 'linea':
        linea = Linea.query.get(equipoId)
        if linea:
            ruta.append({'nombre': linea.nombre, 'tipo': 'linea'})
            zona = Zona.query.get(linea.zonaId)
            if zona:
                ruta.insert(0, {'nombre': zona.nombre, 'tipo': 'zona'})
                planta = Planta.query.get(zona.plantaId)
                if planta:
                    ruta.insert(0, {'nombre': planta.nombre, 'tipo': 'planta'})

    elif equipoTipo == 'zona':
        zona = Zona.query.get(equipoId)
        if zona:
            ruta.append({'nombre': zona.nombre, 'tipo': 'zona'})
            planta = Planta.query.get(zona.plantaId)
            if planta:
                ruta.insert(0, {'nombre': planta.nombre, 'tipo': 'planta'})

    elif equipoTipo == 'planta':
        planta = Planta.query.get(equipoId)
        if planta:
            ruta.append({'nombre': planta.nombre, 'tipo': 'planta'})

    return ruta

# =============================================================================

# RUTAS DE AUTENTICACIÓN
# =============================================================================

@app.route('/login')
def login():
    try:
        verify_jwt_in_request()
        if is_mobile_device():
            return redirect(url_for('mobile.home'))
        return redirect(url_for('home'))
    except:
        return render_template('login.html')

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user = Usuario.query.filter_by(username=username).first()
    
    if not user or not user.activo:
        return jsonify({'error': 'Credenciales no válidas o usuario inactivo'}), 401
    
    if not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Contraseña incorrecta'}), 401
        
    access_token = create_access_token(identity=username)
    resp = jsonify({'success': True, 'nivel': user.nivel, 'nombre': f"{user.nombre} {user.apellidos}"})
    set_access_cookies(resp, access_token)
    return resp

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    resp = jsonify({'success': True})
    unset_jwt_cookies(resp)
    return resp

# =============================================================================
# RUTAS PRINCIPALES
# =============================================================================

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
@jwt_required()
def home():
    # Obtener estadísticas reales para el dashboard
    stats = {
        'otAbiertas': OrdenTrabajo.query.filter(OrdenTrabajo.estado.in_(['pendiente', 'en_curso', 'cerrado_parcial'])).count(),
        'otCerradasMes': OrdenTrabajo.query.filter(
            OrdenTrabajo.estado == 'cerrada',
            OrdenTrabajo.fechaFin >= date.today().replace(day=1)
        ).count(),
        'totalMaquinas': Maquina.query.count(),
        'maquinasAveriadas': Maquina.query.filter_by(estado='averiado').count(),
        'stockBajo': Recambio.query.filter(Recambio.stockActual <= Recambio.stockMinimo).count(),
        'preventivoPendiente': PlanPreventivo.query.filter(
            PlanPreventivo.activo == True,
            PlanPreventivo.proximaEjecucion <= date.today()
        ).count()
    }
    
    # Calcular % cumplimiento preventivo
    totalPreventivo = PlanPreventivo.query.filter_by(activo=True).count()
    if totalPreventivo > 0:
        stats['cumplimientoPreventivo'] = round(
            ((totalPreventivo - stats['preventivoPendiente']) / totalPreventivo) * 100
        )
    else:
        stats['cumplimientoPreventivo'] = 100
    
    return render_template('home.html', stats=stats)

# =============================================================================
# GESTIÓN DE EQUIPOS (ÁRBOL JERÁRQUICO)
# =============================================================================

@app.route('/assets')
@jwt_required()
def verActivos():
    return render_template('assets.html')

@app.route('/getActivosTree')
def getActivosTree():
    tree = []
    empresas = Empresa.query.options(
        joinedload(Empresa.plantas)
        .joinedload(Planta.zonas)
        .joinedload(Zona.lineas)
        .joinedload(Linea.maquinas)
        .joinedload(Maquina.elementos)
    ).all()
    
    for empresa in empresas:
        empresaNode = {
            'id': f'empresa-{empresa.id}',
            'text': empresa.nombre,
            'state': {'opened': False},
            'icon': 'empresa-icon',
            'a_attr': {'class': 'empresa-icon'},
            'children': []
        }
        for planta in empresa.plantas:
            plantaNode = {
                'id': f'planta-{planta.id}',
                'text': planta.nombre,
                'state': {'opened': False},
                'icon': 'planta-icon',
                'a_attr': {'class': 'planta-icon'},
                'children': []
            }
            for zona in planta.zonas:
                zonaNode = {
                    'id': f'zona-{zona.id}',
                    'text': zona.nombre,
                    'state': {'opened': False},
                    'icon': 'zona-icon',
                    'a_attr': {'class': 'zona-icon'},
                    'children': []
                }
                for linea in zona.lineas:
                    lineaNode = {
                        'id': f'linea-{linea.id}',
                        'text': linea.nombre,
                        'state': {'opened': False},
                        'icon': 'linea-icon',
                        'a_attr': {'class': 'linea-icon'},
                        'children': []
                    }
                    for maquina in linea.maquinas:
                        # Añadir indicador visual según estado
                        estadoIcon = '🟢' if maquina.estado == 'operativo' else ('🔴' if maquina.estado == 'averiado' else '🟡')
                        maquinaNode = {
                            'id': f'maquina-{maquina.id}',
                            'text': f'{estadoIcon} {maquina.nombre}',
                            'state': {'opened': False},
                            'icon': 'maquina-icon',
                            'a_attr': {'class': 'maquina-icon'},
                            'children': []
                        }
                        for elemento in maquina.elementos:
                            elementoNode = {
                                'id': f'elemento-{elemento.id}',
                                'text': elemento.nombre,
                                'state': {'opened': False},
                                'icon': 'elemento-icon',
                                'a_attr': {'class': 'elemento-icon'},
                                'children': []
                            }
                            maquinaNode['children'].append(elementoNode)
                        lineaNode['children'].append(maquinaNode)
                    zonaNode['children'].append(lineaNode)
                plantaNode['children'].append(zonaNode)
            empresaNode['children'].append(plantaNode)
        tree.append(empresaNode)
    return jsonify(tree)


# =============================================================================
# API: Lista de equipos para selectores (todos los niveles)
# =============================================================================

@app.route('/api/equipos-lista')
def getEquiposLista():
    """Devuelve lista de todos los niveles de la jerarquía para selectores"""
    equipos = []
    
    empresas = Empresa.query.all()
    for empresa in empresas:
        # Añadir empresa
        equipos.append({
            'id': empresa.id,
            'tipo': 'empresa',
            'nombre': empresa.nombre,
            'codigo': empresa.codigo,
            'ruta': empresa.nombre,
            'nivel': 0,
            'icono': '🏢'
        })
        
        for planta in empresa.plantas:
            # Añadir planta
            rutaPlanta = f"{empresa.nombre} > {planta.nombre}"
            equipos.append({
                'id': planta.id,
                'tipo': 'planta',
                'nombre': planta.nombre,
                'codigo': planta.codigo,
                'ruta': rutaPlanta,
                'nivel': 1,
                'icono': '🏭'
            })
            
            for zona in planta.zonas:
                # Añadir zona
                rutaZona = f"{empresa.nombre} > {planta.nombre} > {zona.nombre}"
                equipos.append({
                    'id': zona.id,
                    'tipo': 'zona',
                    'nombre': zona.nombre,
                    'codigo': zona.codigo,
                    'ruta': rutaZona,
                    'nivel': 2,
                    'icono': '📍'
                })
                
                for linea in zona.lineas:
                    # Añadir línea
                    rutaLinea = f"{empresa.nombre} > {planta.nombre} > {zona.nombre} > {linea.nombre}"
                    equipos.append({
                        'id': linea.id,
                        'tipo': 'linea',
                        'nombre': linea.nombre,
                        'codigo': linea.codigo,
                        'ruta': rutaLinea,
                        'nivel': 3,
                        'icono': '⚡'
                    })
                    
                    for maquina in linea.maquinas:
                        # Añadir máquina
                        rutaMaquina = f"{empresa.nombre} > {planta.nombre} > {zona.nombre} > {linea.nombre} > {maquina.nombre}"
                        estadoIcon = '🟢' if maquina.estado == 'operativo' else ('🔴' if maquina.estado == 'averiado' else '🟡')
                        equipos.append({
                            'id': maquina.id,
                            'tipo': 'maquina',
                            'nombre': maquina.nombre,
                            'codigo': maquina.codigo,
                            'ruta': rutaMaquina,
                            'nivel': 4,
                            'icono': estadoIcon,
                            'estado': maquina.estado,
                            'criticidad': maquina.criticidad
                        })
                        
                        for elemento in maquina.elementos:
                            # Añadir elemento
                            rutaElemento = f"{rutaMaquina} > {elemento.nombre}"
                            equipos.append({
                                'id': elemento.id,
                                'tipo': 'elemento',
                                'nombre': elemento.nombre,
                                'codigo': elemento.codigo,
                                'ruta': rutaElemento,
                                'nivel': 5,
                                'icono': '🔧'
                            })
    
    return jsonify(equipos)


# Mantener endpoint antiguo para compatibilidad
@app.route('/api/maquinas-lista')
def getMaquinasLista():
    """Devuelve lista plana de máquinas (legacy, usar /api/equipos-lista)"""
    equipos = getEquiposLista().get_json()
    return jsonify([e for e in equipos if e['tipo'] == 'maquina'])


@app.route('/getEntidadDetails/<tipo>/<int:id>')
def getEntidadDetails(tipo, id):
    modelo = {
        'empresa': Empresa,
        'planta': Planta,
        'zona': Zona,
        'linea': Linea,
        'maquina': Maquina,
        'elemento': Elemento
    }.get(tipo)

    if not modelo:
        return jsonify({'error': 'Tipo no válido'}), 400

    entidad = modelo.query.get_or_404(id)

    datos = {
        'id': entidad.id,
        'tipo': tipo,
        'nombre': getattr(entidad, 'nombre', ''),
        'descripcion': getattr(entidad, 'descripcion', '')
    }

    # Añadir campos específicos según el tipo
    for campo in ['modelo', 'numeroSerie', 'fabricante', 'criticidad', 'estado', 'horasOperacion', 'fechaInstalacion', 'rav']:
        if hasattr(entidad, campo):
            valor = getattr(entidad, campo)
            if isinstance(valor, date):
                valor = valor.isoformat()
            datos[campo] = valor

    # Construcción del código completo
    partes = []
    if tipo == 'empresa':
        partes.append(entidad.codigo)
    elif tipo == 'planta':
        partes.append(entidad.empresa.codigo)
        partes.append(entidad.codigo)
    elif tipo == 'zona':
        partes.append(entidad.planta.empresa.codigo)
        partes.append(entidad.planta.codigo)
        partes.append(entidad.codigo)
    elif tipo == 'linea':
        partes.append(entidad.zona.planta.empresa.codigo)
        partes.append(entidad.zona.planta.codigo)
        partes.append(entidad.zona.codigo)
        partes.append(entidad.codigo)
    elif tipo == 'maquina':
        partes.append(entidad.linea.zona.planta.empresa.codigo)
        partes.append(entidad.linea.zona.planta.codigo)
        partes.append(entidad.linea.zona.codigo)
        partes.append(entidad.linea.codigo)
        partes.append(entidad.codigo)
    elif tipo == 'elemento':
        partes.append(entidad.maquina.linea.zona.planta.empresa.codigo)
        partes.append(entidad.maquina.linea.zona.planta.codigo)
        partes.append(entidad.maquina.linea.zona.codigo)
        partes.append(entidad.maquina.linea.codigo)
        partes.append(entidad.maquina.codigo)
        partes.append(entidad.codigo)

    datos['codigo'] = '-'.join(partes)

    return jsonify(datos)

# =============================================================================
# CRUD DE ENTIDADES JERÁRQUICAS
# =============================================================================

# --- EMPRESAS ---
@app.route('/api/empresas', methods=['GET'])
def apiEmpresas():
    empresas = Empresa.query.all()
    return jsonify([{'id': e.id, 'codigo': e.codigo, 'nombre': e.nombre} for e in empresas])

@app.route('/api/empresa', methods=['POST'])
def crearEmpresa():
    data = request.get_json()
    empresa = Empresa(
        codigo=data['codigo'],
        nombre=data['nombre'],
        descripcion=data.get('descripcion', ''),
        direccion=data.get('direccion', ''),
        telefono=data.get('telefono', ''),
        email=data.get('email', '')
    )
    db.session.add(empresa)
    db.session.commit()
    return jsonify({'id': empresa.id, 'mensaje': 'Empresa creada correctamente'}), 201

@app.route('/api/empresa/<int:id>', methods=['PUT'])
def actualizarEmpresa(id):
    empresa = Empresa.query.get_or_404(id)
    data = request.get_json()
    empresa.codigo = data.get('codigo', empresa.codigo)
    empresa.nombre = data.get('nombre', empresa.nombre)
    empresa.descripcion = data.get('descripcion', empresa.descripcion)
    empresa.direccion = data.get('direccion', empresa.direccion)
    empresa.telefono = data.get('telefono', empresa.telefono)
    empresa.email = data.get('email', empresa.email)
    db.session.commit()
    return jsonify({'mensaje': 'Empresa actualizada correctamente'})

@app.route('/api/empresa/<int:id>', methods=['DELETE'])
def eliminarEmpresa(id):
    empresa = Empresa.query.get_or_404(id)
    db.session.delete(empresa)
    db.session.commit()
    return jsonify({'mensaje': 'Empresa eliminada correctamente'})

# --- PLANTAS ---
@app.route('/api/plantas')
def apiPlantas():
    empresaId = request.args.get('empresaId')
    if empresaId:
        plantas = Planta.query.filter_by(empresaId=empresaId).all()
    else:
        plantas = Planta.query.all()
    return jsonify([{'id': p.id, 'codigo': p.codigo, 'nombre': p.nombre, 'empresaId': p.empresaId} for p in plantas])

@app.route('/api/planta', methods=['POST'])
def crearPlanta():
    data = request.get_json()
    planta = Planta(
        empresaId=data['empresaId'],
        codigo=data['codigo'],
        nombre=data['nombre'],
        descripcion=data.get('descripcion', ''),
        direccion=data.get('direccion', '')
    )
    db.session.add(planta)
    db.session.commit()
    return jsonify({'id': planta.id, 'mensaje': 'Planta creada correctamente'}), 201

@app.route('/api/planta/<int:id>', methods=['PUT'])
def actualizarPlanta(id):
    planta = Planta.query.get_or_404(id)
    data = request.get_json()
    planta.codigo = data.get('codigo', planta.codigo)
    planta.nombre = data.get('nombre', planta.nombre)
    planta.descripcion = data.get('descripcion', planta.descripcion)
    planta.direccion = data.get('direccion', planta.direccion)
    db.session.commit()
    return jsonify({'mensaje': 'Planta actualizada correctamente'})

@app.route('/api/planta/<int:id>', methods=['DELETE'])
def eliminarPlanta(id):
    planta = Planta.query.get_or_404(id)
    db.session.delete(planta)
    db.session.commit()
    return jsonify({'mensaje': 'Planta eliminada correctamente'})

# --- ZONAS ---
@app.route('/api/zonas/<int:plantaId>')
def apiZonas(plantaId):
    zonas = Zona.query.filter_by(plantaId=plantaId).all()
    return jsonify([{'id': z.id, 'codigo': z.codigo, 'nombre': z.nombre} for z in zonas])

@app.route('/api/zona', methods=['POST'])
def crearZona():
    data = request.get_json()
    zona = Zona(
        plantaId=data['plantaId'],
        codigo=data['codigo'],
        nombre=data['nombre'],
        descripcion=data.get('descripcion', '')
    )
    db.session.add(zona)
    db.session.commit()
    return jsonify({'id': zona.id, 'mensaje': 'Zona creada correctamente'}), 201

@app.route('/api/zona/<int:id>', methods=['PUT'])
def actualizarZona(id):
    zona = Zona.query.get_or_404(id)
    data = request.get_json()
    zona.codigo = data.get('codigo', zona.codigo)
    zona.nombre = data.get('nombre', zona.nombre)
    zona.descripcion = data.get('descripcion', zona.descripcion)
    db.session.commit()
    return jsonify({'mensaje': 'Zona actualizada correctamente'})

@app.route('/api/zona/<int:id>', methods=['DELETE'])
def eliminarZona(id):
    zona = Zona.query.get_or_404(id)
    db.session.delete(zona)
    db.session.commit()
    return jsonify({'mensaje': 'Zona eliminada correctamente'})

# --- LÍNEAS ---
@app.route('/api/lineas/<int:zonaId>')
def apiLineas(zonaId):
    lineas = Linea.query.filter_by(zonaId=zonaId).all()
    return jsonify([{'id': l.id, 'codigo': l.codigo, 'nombre': l.nombre} for l in lineas])

@app.route('/api/linea', methods=['POST'])
def crearLinea():
    data = request.get_json()
    linea = Linea(
        zonaId=data['zonaId'],
        codigo=data['codigo'],
        nombre=data['nombre'],
        descripcion=data.get('descripcion', '')
    )
    db.session.add(linea)
    db.session.commit()
    return jsonify({'id': linea.id, 'mensaje': 'Línea creada correctamente'}), 201

@app.route('/api/linea/<int:id>', methods=['PUT'])
def actualizarLinea(id):
    linea = Linea.query.get_or_404(id)
    data = request.get_json()
    linea.codigo = data.get('codigo', linea.codigo)
    linea.nombre = data.get('nombre', linea.nombre)
    linea.descripcion = data.get('descripcion', linea.descripcion)
    db.session.commit()
    return jsonify({'mensaje': 'Línea actualizada correctamente'})

@app.route('/api/linea/<int:id>', methods=['DELETE'])
def eliminarLinea(id):
    linea = Linea.query.get_or_404(id)
    db.session.delete(linea)
    db.session.commit()
    return jsonify({'mensaje': 'Línea eliminada correctamente'})

# --- MÁQUINAS ---
@app.route('/api/maquinas/<int:lineaId>')
def apiMaquinas(lineaId):
    maquinas = Maquina.query.filter_by(lineaId=lineaId).all()
    return jsonify([{
        'id': m.id, 
        'codigo': m.codigo, 
        'nombre': m.nombre,
        'estado': m.estado,
        'criticidad': m.criticidad
    } for m in maquinas])

@app.route('/api/maquina', methods=['POST'])
def crearMaquina():
    data = request.get_json()
    maquina = Maquina(
        lineaId=data['lineaId'],
        codigo=data['codigo'],
        nombre=data['nombre'],
        modelo=data.get('modelo', ''),
        fabricante=data.get('fabricante', ''),
        numeroSerie=data.get('numeroSerie', ''),
        descripcion=data.get('descripcion', ''),
        criticidad=data.get('criticidad', 'media'),
        estado=data.get('estado', 'operativo'),
        rav=float(data.get('rav', 0.0))
    )
    if data.get('fechaInstalacion'):
        maquina.fechaInstalacion = datetime.strptime(data['fechaInstalacion'], '%Y-%m-%d').date()
    db.session.add(maquina)
    db.session.commit()
    return jsonify({'id': maquina.id, 'mensaje': 'Máquina creada correctamente'}), 201

@app.route('/api/maquina/<int:id>', methods=['PUT'])
def actualizarMaquina(id):
    maquina = Maquina.query.get_or_404(id)
    data = request.get_json()
    maquina.codigo = data.get('codigo', maquina.codigo)
    maquina.nombre = data.get('nombre', maquina.nombre)
    maquina.modelo = data.get('modelo', maquina.modelo)
    maquina.fabricante = data.get('fabricante', maquina.fabricante)
    maquina.numeroSerie = data.get('numeroSerie', maquina.numeroSerie)
    maquina.descripcion = data.get('descripcion', maquina.descripcion)
    maquina.criticidad = data.get('criticidad', maquina.criticidad)
    maquina.estado = data.get('estado', maquina.estado)
    maquina.rav = float(data.get('rav', maquina.rav))
    if data.get('fechaInstalacion'):
        maquina.fechaInstalacion = datetime.strptime(data['fechaInstalacion'], '%Y-%m-%d').date()
    db.session.commit()
    return jsonify({'mensaje': 'Máquina actualizada correctamente'})

@app.route('/api/maquina/<int:id>', methods=['DELETE'])
def eliminarMaquina(id):
    maquina = Maquina.query.get_or_404(id)
    db.session.delete(maquina)
    db.session.commit()
    return jsonify({'mensaje': 'Máquina eliminada correctamente'})

@app.route('/api/maquina/<int:id>/estado', methods=['PUT'])
def cambiarEstadoMaquina(id):
    maquina = Maquina.query.get_or_404(id)
    data = request.get_json()
    maquina.estado = data['estado']
    db.session.commit()
    return jsonify({'mensaje': f'Estado cambiado a {maquina.estado}'})

# --- ELEMENTOS ---
@app.route('/api/elementos/<int:maquinaId>')
def apiElementos(maquinaId):
    elementos = Elemento.query.filter_by(maquinaId=maquinaId).all()
    return jsonify([{'id': e.id, 'codigo': e.codigo, 'nombre': e.nombre, 'tipo': e.tipo} for e in elementos])

@app.route('/api/elemento', methods=['POST'])
def crearElemento():
    data = request.get_json()
    elemento = Elemento(
        maquinaId=data['maquinaId'],
        codigo=data['codigo'],
        nombre=data['nombre'],
        tipo=data.get('tipo', ''),
        descripcion=data.get('descripcion', ''),
        fabricante=data.get('fabricante', ''),
        modelo=data.get('modelo', ''),
        numeroSerie=data.get('numeroSerie', ''),
        rav=float(data.get('rav', 0.0))
    )
    db.session.add(elemento)
    db.session.commit()
    return jsonify({'id': elemento.id, 'mensaje': 'Elemento creado correctamente'}), 201

@app.route('/api/elemento/<int:id>', methods=['PUT'])
def actualizarElemento(id):
    elemento = Elemento.query.get_or_404(id)
    data = request.get_json()
    elemento.codigo = data.get('codigo', elemento.codigo)
    elemento.nombre = data.get('nombre', elemento.nombre)
    elemento.tipo = data.get('tipo', elemento.tipo)
    elemento.descripcion = data.get('descripcion', elemento.descripcion)
    elemento.fabricante = data.get('fabricante', elemento.fabricante)
    elemento.modelo = data.get('modelo', elemento.modelo)
    elemento.numeroSerie = data.get('numeroSerie', elemento.numeroSerie)
    elemento.rav = float(data.get('rav', getattr(elemento, 'rav', 0.0)))
    db.session.commit()
    return jsonify({'mensaje': 'Elemento actualizado correctamente'})

@app.route('/api/elemento/<int:id>', methods=['DELETE'])
def eliminarElemento(id):
    elemento = Elemento.query.get_or_404(id)
    db.session.delete(elemento)
    db.session.commit()
    return jsonify({'mensaje': 'Elemento eliminado correctamente'})

# =============================================================================
# GESTIÓN DE RECAMBIOS
# =============================================================================

@app.route('/recambios')
@jwt_required()
def verRecambios():
    return render_template('recambios.html')

@app.route('/api/recambios')
def apiRecambios():
    busqueda = request.args.get('q', '')
    soloStockBajo = request.args.get('stockBajo', 'false') == 'true'
    
    query = Recambio.query.filter_by(activo=True)
    
    if busqueda:
        query = query.filter(or_(
            Recambio.codigo.ilike(f'%{busqueda}%'),
            Recambio.nombre.ilike(f'%{busqueda}%'),
            Recambio.descripcion.ilike(f'%{busqueda}%')
        ))
    
    if soloStockBajo:
        query = query.filter(Recambio.stockActual <= Recambio.stockMinimo)
    
    recambios = query.order_by(Recambio.nombre).all()
    return jsonify([{
        'id': r.id,
        'codigo': r.codigo,
        'nombre': r.nombre,
        'descripcion': r.descripcion,
        'categoria': r.categoria,
        'stockActual': r.stockActual,
        'stockMinimo': r.stockMinimo,
        'stockMaximo': r.stockMaximo,
        'ubicacion': r.ubicacion,
        'proveedor': r.proveedor,
        'precioUnitario': r.precioUnitario,
        'unidadMedida': r.unidadMedida,
        'stockBajo': r.stockBajo
    } for r in recambios])

@app.route('/api/recambio', methods=['POST'])
def crearRecambio():
    data = request.get_json()
    recambio = Recambio(
        codigo=data['codigo'],
        nombre=data['nombre'],
        descripcion=data.get('descripcion', ''),
        categoria=data.get('categoria', ''),
        stockActual=float(data.get('stockActual', 0)),
        stockMinimo=float(data.get('stockMinimo', 0)),
        stockMaximo=float(data.get('stockMaximo', 100)),
        ubicacion=data.get('ubicacion', ''),
        proveedor=data.get('proveedor', ''),
        codigoProveedor=data.get('codigoProveedor', ''),
        precioUnitario=data.get('precioUnitario', 0),
        unidadMedida=data.get('unidadMedida', 'unidad')
    )
    db.session.add(recambio)
    db.session.commit()
    return jsonify({'id': recambio.id, 'mensaje': 'Recambio creado correctamente'}), 201

@app.route('/api/recambio/<int:id>', methods=['GET'])
def obtenerRecambio(id):
    r = Recambio.query.get_or_404(id)
    return jsonify({
        'id': r.id,
        'codigo': r.codigo,
        'nombre': r.nombre,
        'descripcion': r.descripcion,
        'categoria': r.categoria,
        'stockActual': r.stockActual,
        'stockMinimo': r.stockMinimo,
        'stockMaximo': r.stockMaximo,
        'ubicacion': r.ubicacion,
        'proveedor': r.proveedor,
        'codigoProveedor': r.codigoProveedor,
        'precioUnitario': r.precioUnitario,
        'unidadMedida': r.unidadMedida
    })

@app.route('/api/recambio/<int:id>', methods=['PUT'])
def actualizarRecambio(id):
    recambio = Recambio.query.get_or_404(id)
    data = request.get_json()
    
    for campo in ['codigo', 'nombre', 'descripcion', 'categoria', 'stockMinimo', 
                  'stockMaximo', 'ubicacion', 'proveedor', 'codigoProveedor', 
                  'precioUnitario', 'unidadMedida']:
        if campo in data:
            setattr(recambio, campo, data[campo])
    
    db.session.commit()
    return jsonify({'mensaje': 'Recambio actualizado correctamente'})

@app.route('/api/recambio/<int:id>', methods=['DELETE'])
def eliminarRecambio(id):
    recambio = Recambio.query.get_or_404(id)
    recambio.activo = False  # Soft delete
    db.session.commit()
    return jsonify({'mensaje': 'Recambio eliminado correctamente'})

@app.route('/api/recambio/<int:id>/movimiento', methods=['POST'])
def registrarMovimiento(id):
    recambio = Recambio.query.get_or_404(id)
    data = request.get_json()
    
    stockAnterior = recambio.stockActual
    cantidad = float(data['cantidad'])
    tipo = data['tipo']
    subTipo = data.get('subTipo', '')
    
    if tipo == 'entrada':
        recambio.stockActual += cantidad
        # Si es una compra y se proporciona nuevo precio, actualizarlo
        if subTipo == 'compra' and 'nuevoPrecio' in data and data['nuevoPrecio'] is not None:
            recambio.precioUnitario = float(data['nuevoPrecio'])
    elif tipo == 'salida':
        if recambio.stockActual < cantidad:
            return jsonify({'error': 'Stock insuficiente'}), 400
        recambio.stockActual -= cantidad
    elif tipo == 'ajuste':
        recambio.stockActual = cantidad
        cantidad = cantidad - stockAnterior
    
    # Generar motivo automático basado en subTipo si no se proporciona
    motivo = data.get('motivo', '')
    if not motivo and subTipo:
        subTipoLabels = {
            'compra': 'Compra a proveedor',
            'devolucion_sin_uso': 'Devolución sin utilizar',
            'ajuste_inventario': 'Ajuste de inventario',
            'transferencia_entrada': 'Transferencia desde otra ubicación',
            'consumo_ot': 'Consumo en Orden de Trabajo',
            'devolucion_defectuoso': 'Devolución por defecto',
            'recambio_danado': 'Recambio en mal estado',
            'transferencia_salida': 'Transferencia a otra ubicación'
        }
        motivo = subTipoLabels.get(subTipo, subTipo)
    
    movimiento = MovimientoStock(
        recambioId=id,
        tipo=tipo,
        subTipo=subTipo,
        cantidad=cantidad,
        stockAnterior=stockAnterior,
        stockPosterior=recambio.stockActual,
        motivo=motivo,
        documentoRef=data.get('documentoRef', ''),
        usuario=data.get('usuario', 'Sistema')
    )
    db.session.add(movimiento)
    db.session.commit()
    
    return jsonify({
        'mensaje': 'Movimiento registrado',
        'stockActual': recambio.stockActual,
        'precioActual': recambio.precioUnitario
    })

@app.route('/api/recambio/<int:id>/movimientos')
def obtenerMovimientos(id):
    movimientos = MovimientoStock.query.filter_by(recambioId=id).order_by(MovimientoStock.fecha.desc()).limit(50).all()
    return jsonify([{
        'id': m.id,
        'tipo': m.tipo,
        'cantidad': m.cantidad,
        'stockAnterior': m.stockAnterior,
        'stockPosterior': m.stockPosterior,
        'fecha': m.fecha.isoformat(),
        'motivo': m.motivo,
        'documentoRef': m.documentoRef,
        'usuario': m.usuario
    } for m in movimientos])

# =============================================================================
# ÓRDENES DE TRABAJO
# =============================================================================

@app.route('/ordenes')
@jwt_required()
def verOrdenes():
    return render_template('ordenes.html')

@app.route('/api/ordenes')
def apiOrdenes():
    estado = request.args.get('estado', '')
    tipo = request.args.get('tipo', '')
    maquinaId = request.args.get('maquinaId', '')
    equipoTipo = request.args.get('equipoTipo', '')
    equipoId = request.args.get('equipoId', '')
    incluirCerradas = request.args.get('incluirCerradas', 'false') == 'true'
    
    query = OrdenTrabajo.query

    # Excluir cerradas por defecto
    if not incluirCerradas and not estado:
        query = query.filter(OrdenTrabajo.estado != 'cerrada')

    if estado:
        query = query.filter_by(estado=estado)
    if tipo:
        query = query.filter_by(tipo=tipo)
    else:
        # Las órdenes preventivas se gestionan en la página de Preventivo
        query = query.filter(OrdenTrabajo.tipo != 'preventivo')
    
    # Filtrar por equipo (nuevo formato)
    if equipoTipo and equipoId:
        query = query.filter_by(equipoTipo=equipoTipo, equipoId=int(equipoId))
    elif maquinaId:
        # Compatibilidad con formato antiguo
        query = query.filter_by(maquinaId=maquinaId)
    
    # Join con TipoIntervencion para ordenar por el campo orden configurado
    query = query.outerjoin(TipoIntervencion, OrdenTrabajo.tipo == TipoIntervencion.codigo)

    # Ordenar por TipoIntervencion.orden y luego por prioridad (urgente > alta > media > baja)
    ordenes = query.order_by(
        TipoIntervencion.orden,
        case(
            (OrdenTrabajo.prioridad == 'urgente', 1),
            (OrdenTrabajo.prioridad == 'alta', 2),
            (OrdenTrabajo.prioridad == 'media', 3),
            (OrdenTrabajo.prioridad == 'baja', 4),
            else_=5
        )
    ).all()

    
    result = []
    for o in ordenes:
        # Para compatibilidad con órdenes antiguas sin equipoTipo/equipoId
        equipoTipo = o.equipoTipo if o.equipoTipo else ('maquina' if o.maquinaId else None)
        equipoId = o.equipoId if o.equipoId else o.maquinaId
        equipoInfo = getEquipoInfo(equipoTipo, equipoId) if equipoTipo and equipoId else {'nombre': '', 'codigo': ''}
        equipoRuta = getEquipoRutaCompleta(equipoTipo, equipoId) if equipoTipo and equipoId else ''
        equipoRutaItems = getEquipoRutaNombres(equipoTipo, equipoId) if equipoTipo and equipoId else []

        result.append({
            'id': o.id,
            'numero': o.numero,
            'tipo': o.tipo,
            'prioridad': o.prioridad,
            'estado': o.estado,
            'titulo': o.titulo,
            'fechaCreacion': o.fechaCreacion.isoformat() if o.fechaCreacion else None,
            'fechaProgramada': o.fechaProgramada.isoformat() if o.fechaProgramada else None,
            'fechaInicio': o.fechaInicio.isoformat() if o.fechaInicio else None,
            'fechaFin': o.fechaFin.isoformat() if o.fechaFin else None,
            'equipoTipo': equipoTipo,
            'equipoId': equipoId,
            'equipoNombre': equipoInfo['nombre'],
            'equipoCodigo': equipoInfo['codigo'],
            'equipoRuta': equipoRuta,
            'equipoRutaItems': equipoRutaItems,
            'maquinaId': o.maquinaId,
            'maquinaNombre': o.maquina.nombre if o.maquina else equipoInfo['nombre'],
            'tecnicoAsignado': o.tecnicoAsignado,
            'tiempoEstimado': o.tiempoEstimado
        })
    
    return jsonify(result)



@app.route('/api/orden/<int:id>')
def obtenerOrden(id):
    o = OrdenTrabajo.query.get_or_404(id)
    
    # Obtener info del equipo (nombre, código y ruta completa)
    equipoTipo = o.equipoTipo if o.equipoTipo else ('maquina' if o.maquinaId else None)
    equipoId = o.equipoId if o.equipoId else o.maquinaId
    equipoInfo = getEquipoInfo(equipoTipo, equipoId) if equipoTipo and equipoId else {'nombre': '', 'codigo': ''}
    equipoRuta = getEquipoRutaCompleta(equipoTipo, equipoId) if equipoTipo and equipoId else ''
    
    return jsonify({
        'id': o.id,
        'numero': o.numero,
        'tipo': o.tipo,
        'prioridad': o.prioridad,
        'estado': o.estado,
        'titulo': o.titulo,
        'descripcionProblema': o.descripcionProblema,
        'descripcionSolucion': o.descripcionSolucion,
        'observaciones': o.observaciones,
        'fechaCreacion': o.fechaCreacion.isoformat() if o.fechaCreacion else None,
        'fechaProgramada': o.fechaProgramada.isoformat() if o.fechaProgramada else None,
        'fechaInicio': o.fechaInicio.isoformat() if o.fechaInicio else None,
        'fechaFin': o.fechaFin.isoformat() if o.fechaFin else None,
        'equipoTipo': equipoTipo,
        'equipoId': equipoId,
        'equipoNombre': equipoInfo['nombre'],
        'equipoCodigo': equipoInfo['codigo'],
        'equipoRuta': equipoRuta,
        'maquinaId': o.maquinaId,
        'maquinaNombre': o.maquina.nombre if o.maquina else equipoInfo['nombre'],
        # Mantener compatibilidad con código antiguo
        # Mantener compatibilidad con código antiguo
        'elementoId': o.elementoId,
        'tecnicoAsignado': o.tecnicoAsignado,
        'tiempoEstimado': o.tiempoEstimado,
        'tiempoReal': o.tiempoReal,
        'tiempoParada': o.tiempoParada,
        'costeTallerExterno': o.costeTallerExterno,
        'proveedorExterno': o.proveedorExterno,
        'descripcionTallerExterno': o.descripcionTallerExterno,
        'costesExternosJson': o.costesExternosJson,
        # Campos preventivo autocontenido
        'gamaId': o.gamaId,
        'gamaNombre': o.gama.nombre if o.gama else None,
        'frecuenciaTipo': o.frecuenciaTipo,
        'frecuenciaValor': o.frecuenciaValor,
        # Tareas de la gama (para mostrar en la OT)
        'gamaTareas': [{
            'id': t.id,
            'descripcion': t.descripcion,
            'orden': t.orden,
            'duracionEstimada': t.duracionEstimada,
            'herramientas': t.herramientas,
            'instrucciones': t.instrucciones
        } for t in (o.gama.tareas if o.gama else [])],
        # Items de checklist de la gama
        'checklistItems': [{
            'id': ci.id,
            'descripcion': ci.descripcion,
            'orden': ci.orden,
            'tipoRespuesta': ci.tipoRespuesta,
            'unidad': ci.unidad,
            'generaCorrectivo': ci.generaCorrectivo
        } for ci in (o.gama.checklistItems if o.gama else [])],
        # Respuestas ya guardadas para esta OT
        'respuestasChecklist': [{
            'checklistItemId': r.checklistItemId,
            'respuesta': r.respuesta,
            'observaciones': r.observaciones
        } for r in o.respuestasChecklist],
        'consumos': [{
            'id': c.id,
            'recambioId': c.recambioId,
            'recambioNombre': c.recambio.nombre,
            'cantidad': c.cantidad,
            'precioUnitario': c.precioUnitario
        } for c in o.consumos],
        'registrosTiempo': [{
            'id': r.id,
            'tecnico': r.tecnico,
            'inicio': r.inicio.isoformat() if r.inicio else None,
            'fin': r.fin.isoformat() if r.fin else None,
            'enCurso': r.enCurso,
            'duracionHoras': round(r.duracionHoras, 2)
        } for r in o.registrosTiempo]
    })

@app.route('/api/orden/<int:id>', methods=['DELETE'])
def eliminarOrden(id):
    """Elimina una orden de trabajo y sus datos relacionados"""
    try:
        orden = OrdenTrabajo.query.get_or_404(id)
        db.session.delete(orden)
        db.session.commit()
        return jsonify({'mensaje': f'OT {orden.numero} eliminada correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@app.route('/api/orden', methods=['POST'])
def crearOrden():
    data = request.get_json()
    
    # Obtener tipo y ID del equipo (nuevo formato: equipoTipo/equipoId)
    equipoTipo = data.get('equipoTipo', 'maquina')
    equipoId = data.get('equipoId') or data.get('maquinaId')  # Compatibilidad con legacy
    
    if not equipoId:
        return jsonify({'error': 'Debe especificar un equipo'}), 400
    
    # Obtener el nombre del equipo según el tipo
    equipoNombre = ''
    maquinaId = None
    modelos = {
        'empresa': Empresa,
        'planta': Planta,
        'zona': Zona,
        'linea': Linea,
        'maquina': Maquina,
        'elemento': Elemento
    }
    if equipoTipo in modelos:
        entidad = modelos[equipoTipo].query.get(equipoId)
        if entidad:
            equipoNombre = entidad.nombre
            # Si es máquina, mantener también el maquinaId para compatibilidad
            if equipoTipo == 'maquina':
                maquinaId = equipoId
    
    orden = OrdenTrabajo(
        numero=OrdenTrabajo.generarNumero(),
        tipo=data['tipo'],
        prioridad=data.get('prioridad', 'media'),
        estado='pendiente',
        titulo=data['titulo'],
        descripcionProblema=data.get('descripcionProblema', ''),
        equipoTipo=equipoTipo,
        equipoId=equipoId,
        maquinaId=maquinaId,  # Para compatibilidad
        elementoId=data.get('elementoId'),
        tecnicoAsignado=data.get('tecnicoAsignado', ''),
        tiempoEstimado=data.get('tiempoEstimado'),
        creadoPor=data.get('creadoPor', 'Sistema'),
        # Campos para OT preventiva autocontenida
        gamaId=data.get('gamaId'),
        frecuenciaTipo=data.get('frecuenciaTipo'),
        frecuenciaValor=data.get('frecuenciaValor'),
    )
    
    if 'fechaProgramada' in data:
        if data['fechaProgramada']:
            try:
                # Truncate any 'Z' or milliseconds to be safe
                val = str(data['fechaProgramada']).replace('Z', '')
                if len(val) == 10:  # YYYY-MM-DD
                    orden.fechaProgramada = datetime.fromisoformat(val)
                else:
                    orden.fechaProgramada = datetime.fromisoformat(val)
            except ValueError:
                pass
        else:
            orden.fechaProgramada = None
    
    db.session.add(orden)
    db.session.commit()
    
    # Si es correctivo y el equipo es una máquina, cambiar a averiado
    if orden.tipo == 'correctivo' and equipoTipo == 'maquina':
        maquina = Maquina.query.get(equipoId)
        if maquina and maquina.estado == 'operativo':
            maquina.estado = 'averiado'
            db.session.commit()
    
    return jsonify({'id': orden.id, 'numero': orden.numero, 'mensaje': 'Orden creada correctamente'}), 201


@app.route('/api/orden/<int:id>', methods=['PUT'])
def actualizarOrden(id):
    orden = OrdenTrabajo.query.get_or_404(id)
    data = request.get_json()
    
    for campo in ['tipo', 'prioridad', 'titulo', 'descripcionProblema',
                  'descripcionSolucion', 'observaciones', 'tecnicoAsignado',
                  'tiempoEstimado', 'tiempoReal', 'tiempoParada',
                  'gamaId', 'frecuenciaTipo', 'frecuenciaValor']:
        if campo in data:
            setattr(orden, campo, data[campo])

    if 'fechaProgramada' in data:
        if data['fechaProgramada']:
            try:
                val = str(data['fechaProgramada']).replace('Z', '')
                try:
                    orden.fechaProgramada = datetime.fromisoformat(val)
                except ValueError:
                    # Intento de fallback manual si fromisoformat falla por formato
                    if 'T' in val:
                        fech, hora = val.split('T')
                        if len(hora) == 5:
                            val = f"{fech}T{hora}:00"
                            orden.fechaProgramada = datetime.fromisoformat(val)
            except Exception as e:
                pass
        else:
            orden.fechaProgramada = None

    db.session.commit()
    return jsonify({'mensaje': 'Orden actualizada correctamente'})

@app.route('/api/orden/<int:id>/estado', methods=['PUT'])
def cambiarEstadoOrden(id):
    orden = OrdenTrabajo.query.get_or_404(id)
    data = request.get_json()
    nuevoEstado = data['estado']
    nueva_ot_numero = None
    ots_correctivas = []
    
    # Registrar fechas según el cambio de estado
    if nuevoEstado == 'en_curso':
        if not orden.fechaInicio:
            orden.fechaInicio = datetime.now()
        # Si se revierte a en_curso, limpiar la fecha de fin por si acaso
        if orden.fechaFin:
            orden.fechaFin = None
            orden.cerradoPor = None
            
    elif nuevoEstado == 'cerrado_parcial':
        # El técnico ha finalizado su trabajo — registrar fecha de primer cierre
        if not orden.fechaInicio:
            orden.fechaInicio = datetime.now()
            
        # Registrar el tiempo de fin del trabajo
        orden.fechaFin = datetime.now()

        # ── SEGURIDAD: cerrar registros de tiempo activos que el técnico no paró ──
        registros_activos = RegistroTiempo.query.filter_by(ordenId=id, enCurso=True).all()
        # Usar la fechaFin de la orden como fin del registro: el tiempo cuenta
        # desde que el técnico empezó hasta que cerró la orden, no hasta ahora.
        fin_sesion = orden.fechaFin
        for reg in registros_activos:
            reg.fin = fin_sesion
            reg.enCurso = False
        if registros_activos:
            # Recalcular tiempoReal con todos los registros ya cerrados
            tiempoTotal = db.session.query(func.sum(
                func.julianday(RegistroTiempo.fin) - func.julianday(RegistroTiempo.inicio)
            )).filter(RegistroTiempo.ordenId == id, RegistroTiempo.fin.isnot(None)).scalar()
            if tiempoTotal:
                orden.tiempoReal = round(tiempoTotal * 24, 2)
            print(f'[AVISO] OT {orden.numero}: {len(registros_activos)} registro(s) de tiempo cerrado(s) automáticamente al finalizar.')
            
        # Si era correctivo, volver la máquina a operativo
        if orden.tipo == 'correctivo':
            maquina = Maquina.query.get(orden.maquinaId)
            if maquina:
                maquina.estado = 'operativo'
        
        # Auto-generación de la siguiente OT preventiva (al cerrado_parcial)
        if orden.tipo == 'preventivo':
            nueva_ot_numero = _generarSiguienteOTPreventivo(orden)
            # Generar OTs correctivas por items de checklist NOK
            ots_correctivas = _generarCorrectivosChecklist(orden)
            
    elif nuevoEstado == 'cerrada':
        # Solo poner fechaFin si no pasó por cerrado_parcial o no tenía
        if not orden.fechaFin:
            orden.fechaFin = datetime.now()
        orden.cerradoPor = data.get('cerradoPor', 'Sistema')

        # ── SEGURIDAD: cerrar registros de tiempo activos que el técnico no paró ──
        registros_activos = RegistroTiempo.query.filter_by(ordenId=id, enCurso=True).all()
        # Usar la fechaFin de la orden como fin del registro: el tiempo cuenta
        # desde que el técnico empezó hasta que cerró la orden, no hasta ahora.
        fin_sesion = orden.fechaFin
        for reg in registros_activos:
            reg.fin = fin_sesion
            reg.enCurso = False
        if registros_activos:
            # Recalcular tiempoReal con todos los registros ya cerrados
            tiempoTotal = db.session.query(func.sum(
                func.julianday(RegistroTiempo.fin) - func.julianday(RegistroTiempo.inicio)
            )).filter(RegistroTiempo.ordenId == id, RegistroTiempo.fin.isnot(None)).scalar()
            if tiempoTotal:
                orden.tiempoReal = round(tiempoTotal * 24, 2)
            print(f'[AVISO] OT {orden.numero}: {len(registros_activos)} registro(s) de tiempo cerrado(s) automáticamente al cerrar definitivamente.')
    
    # Validar que haya técnico asignado si se pone como 'asignada'
    if nuevoEstado == 'asignada' and not (orden.tecnicoAsignado and orden.tecnicoAsignado.strip()):
        return jsonify({'error': 'No se puede marcar como asignada sin un técnico asignado'}), 400

    orden.estado = nuevoEstado
    db.session.commit()

    
    respuesta = {'mensaje': f'Estado cambiado a {nuevoEstado}'}
    if nueva_ot_numero:
        respuesta['nuevaOT'] = nueva_ot_numero
        respuesta['mensajeOT'] = f'Nueva OT preventiva generada: {nueva_ot_numero}'
    if ots_correctivas:
        respuesta['otsCorrectivas'] = ots_correctivas
        respuesta['mensajeCorrectivos'] = f'Se han generado {len(ots_correctivas)} OT(s) correctiva(s): {", ".join(ots_correctivas)}'
    return jsonify(respuesta)


def _generarSiguienteOTPreventivo(orden):
    """Genera la siguiente OT preventiva al cerrar una orden de tipo preventivo.
    Utiliza la frecuencia y gama almacenadas en la propia OT.
    Devuelve el número de la nueva OT o None si no se pudo generar."""
    try:
        if not orden.frecuenciaTipo or not orden.frecuenciaValor:
            return None  # Sin frecuencia definida, no se auto-genera

        # Evitar duplicidad: comprobar si ya se generó una OT preventiva para este equipo y gama posterior a esta
        existente = OrdenTrabajo.query.filter_by(
            tipo='preventivo',
            gamaId=orden.gamaId,
            equipoTipo=orden.equipoTipo,
            equipoId=orden.equipoId
        ).filter(OrdenTrabajo.id > orden.id).first()
        if existente:
            return None

        from datetime import timedelta
        fecha_cierre = (orden.fechaFin or datetime.now()).date()

        # Calcular fecha de la siguiente intervención
        if orden.frecuenciaTipo == 'dias':
            fecha_siguiente = fecha_cierre + timedelta(days=orden.frecuenciaValor)
        elif orden.frecuenciaTipo == 'semanas':
            fecha_siguiente = fecha_cierre + timedelta(weeks=orden.frecuenciaValor)
        elif orden.frecuenciaTipo == 'meses':
            fecha_siguiente = fecha_cierre + timedelta(days=orden.frecuenciaValor * 30)
        else:
            fecha_siguiente = fecha_cierre + timedelta(days=orden.frecuenciaValor)

        nueva = OrdenTrabajo(
            numero=OrdenTrabajo.generarNumero(),
            tipo='preventivo',
            prioridad=orden.prioridad or 'media',
            estado='pendiente',
            titulo=orden.titulo,
            descripcionProblema=orden.descripcionProblema,
            equipoTipo=orden.equipoTipo,
            equipoId=orden.equipoId,
            maquinaId=orden.maquinaId,
            gamaId=orden.gamaId,
            frecuenciaTipo=orden.frecuenciaTipo,
            frecuenciaValor=orden.frecuenciaValor,
            tiempoEstimado=orden.tiempoEstimado,
            fechaProgramada=datetime.combine(fecha_siguiente, datetime.min.time()),
            creadoPor='Sistema (auto)'
        )
        db.session.add(nueva)
        db.session.flush()
        return nueva.numero
    except Exception as e:
        print(f'Error al generar siguiente OT preventiva: {e}')
    return None


def _generarCorrectivosChecklist(orden):
    """Genera OTs correctivas para cada item de checklist respondido como NOK
    que tenga generaCorrectivo=True.
    Devuelve la lista de números de OT creadas."""
    numeros = []
    try:
        for resp in orden.respuestasChecklist:
            if resp.respuesta != 'nok':
                continue
            item = resp.item
            if not item or not item.generaCorrectivo:
                continue
            obs = resp.observaciones or ''
            problema = f'[Preventivo {orden.numero}] Checklist NOK: {item.descripcion}'
            
            # Evitar duplicidad: comprobar si ya existe una OT generada para este fallo específico
            titulo_generado = f'Correctivo: {item.descripcion}'
            existente = OrdenTrabajo.query.filter_by(
                titulo=titulo_generado,
                equipoId=orden.equipoId
            ).filter(OrdenTrabajo.descripcionProblema.like(f'[Preventivo {orden.numero}]%')).first()
            if existente:
                continue
            
            if obs:
                problema += f'. Observación: {obs}'
            correctivo = OrdenTrabajo(
                numero=OrdenTrabajo.generarNumero(),
                tipo='correctivo',
                prioridad='media',
                estado='pendiente',
                titulo=f'Correctivo: {item.descripcion}',
                descripcionProblema=problema,
                equipoTipo=orden.equipoTipo,
                equipoId=orden.equipoId,
                maquinaId=orden.maquinaId,
                creadoPor=f'Sistema (checklist OT {orden.numero})'
            )
            db.session.add(correctivo)
            db.session.flush()
            numeros.append(correctivo.numero)
    except Exception as e:
        print(f'Error al generar OTs correctivas desde checklist: {e}')
    return numeros

# =============================================================================
# CALENDARIO DE ÓRDENES (para el dashboard principal)
# =============================================================================

@app.route('/api/ordenes-calendario')
def apiOrdenesCalendario():
    """Devuelve todas las OTs con fecha programada, para mostrar en el calendario del dashboard."""
    # Filtrar OTs que tengan fechaProgramada y no estén cerradas/canceladas
    ordenes = OrdenTrabajo.query.filter(
        OrdenTrabajo.fechaProgramada.isnot(None),
        OrdenTrabajo.estado.notin_(['cerrada', 'cancelada'])
    ).order_by(OrdenTrabajo.fechaProgramada).all()
    
    resultado = []
    for o in ordenes:
        equipoNombre = getEquipoNombre(o.equipoTipo, o.equipoId) if o.equipoTipo and o.equipoId else (o.maquina.nombre if o.maquina else '')
        resultado.append({
            'id': o.id,
            'numero': o.numero,
            'tipo': o.tipo,
            'estado': o.estado,
            'titulo': o.titulo,
            'equipoNombre': equipoNombre,
            'fechaProgramada': o.fechaProgramada.date().isoformat() if o.fechaProgramada else None,
        })
    return jsonify(resultado)


@app.route('/api/ordenes-preventivo')
def apiOrdenesPreventivo():
    """Devuelve las OTs de tipo preventivo pendientes (no cerradas ni canceladas),
    ordenadas por fechaProgramada ascendente."""
    ordenes = OrdenTrabajo.query.filter(
        OrdenTrabajo.tipo == 'preventivo',
        OrdenTrabajo.estado.notin_(['cerrada', 'cancelada'])
    ).order_by(
        OrdenTrabajo.fechaProgramada.is_(None),  # Sin fecha al final
        OrdenTrabajo.fechaProgramada.asc()
    ).all()

    hoy = date.today()
    resultado = []
    for o in ordenes:
        equipoNombre = getEquipoNombre(o.equipoTipo, o.equipoId) if o.equipoTipo and o.equipoId else ''
        equipoRuta = getEquipoRutaCompleta(o.equipoTipo, o.equipoId) if o.equipoTipo and o.equipoId else ''
        fecha_prog = o.fechaProgramada.date() if o.fechaProgramada else None
        dias = (fecha_prog - hoy).days if fecha_prog else None
        vencida = dias is not None and dias < 0

        # Frecuencia legible
        frec_label = None
        if o.frecuenciaValor and o.frecuenciaTipo:
            tipos = {'dias': 'día(s)', 'semanas': 'semana(s)', 'meses': 'mes(es)'}
            frec_label = f"Cada {o.frecuenciaValor} {tipos.get(o.frecuenciaTipo, o.frecuenciaTipo)}"

        resultado.append({
            'id': o.id,
            'numero': o.numero,
            'estado': o.estado,
            'prioridad': o.prioridad,
            'titulo': o.titulo,
            'equipoNombre': equipoNombre,
            'equipoRuta': equipoRuta,
            'equipoTipo': o.equipoTipo,
            'equipoId': o.equipoId,
            'fechaProgramada': fecha_prog.isoformat() if fecha_prog else None,
            'diasRestantes': dias,
            'vencida': vencida,
            'gamaId': o.gamaId,
            'gamaNombre': o.gama.nombre if o.gama else None,
            'frecuenciaTipo': o.frecuenciaTipo,
            'frecuenciaValor': o.frecuenciaValor,
            'frecuenciaLabel': frec_label,
        })
    return jsonify(resultado)

@app.route('/api/orden/<int:id>/consumo', methods=['POST'])
def agregarConsumo(id):
    orden = OrdenTrabajo.query.get_or_404(id)
    data = request.get_json()
    
    recambio = Recambio.query.get_or_404(data['recambioId'])
    cantidad = float(data['cantidad'])
    
    # Verificar stock
    if recambio.stockActual < cantidad:
        return jsonify({'error': f'Stock insuficiente. Disponible: {recambio.stockActual}'}), 400
    
    # Crear consumo
    consumo = ConsumoRecambio(
        ordenId=id,
        recambioId=data['recambioId'],
        cantidad=cantidad,
        precioUnitario=recambio.precioUnitario
    )
    db.session.add(consumo)
    
    # Descontar stock y registrar movimiento
    stockAnterior = recambio.stockActual
    recambio.stockActual -= cantidad
    
    movimiento = MovimientoStock(
        recambioId=recambio.id,
        tipo='salida',
        cantidad=cantidad,
        stockAnterior=stockAnterior,
        stockPosterior=recambio.stockActual,
        motivo=f'Consumo OT {orden.numero}',
        documentoRef=orden.numero
    )
    db.session.add(movimiento)
    db.session.commit()
    
    return jsonify({'mensaje': 'Consumo registrado correctamente'})

# Iniciar trabajo en OT (técnico empieza a trabajar)
@app.route('/api/orden/<int:id>/iniciar', methods=['POST'])
def iniciarTrabajoOT(id):
    orden = OrdenTrabajo.query.get_or_404(id)
    data = request.get_json()
    tecnico = data.get('tecnico', 'Técnico')
    
    # Verificar si ya hay un registro en curso para este técnico
    registroActivo = RegistroTiempo.query.filter_by(
        ordenId=id, tecnico=tecnico, enCurso=True
    ).first()
    
    if registroActivo:
        return jsonify({'error': f'{tecnico} ya tiene un registro de tiempo activo'}), 400
    
    # Crear nuevo registro de tiempo
    registro = RegistroTiempo(
        ordenId=id,
        tecnico=tecnico,
        inicio=datetime.now(),
        enCurso=True
    )
    db.session.add(registro)
    
    # Si la OT estaba pendiente, pasarla a en_curso
    if orden.estado in ('pendiente', 'asignada'):
        orden.estado = 'en_curso'
        if not orden.fechaInicio:
            orden.fechaInicio = datetime.now()

    # Si no tenía técnico asignado, asignar al que inicia el trabajo
    if not orden.tecnicoAsignado:
        orden.tecnicoAsignado = tecnico

    db.session.commit()
    return jsonify({'mensaje': f'Trabajo iniciado por {tecnico}', 'registroId': registro.id})

# Pausar trabajo en OT
@app.route('/api/orden/<int:id>/pausar', methods=['POST'])
def pausarTrabajoOT(id):
    orden = OrdenTrabajo.query.get_or_404(id)
    data = request.get_json()
    tecnico = data.get('tecnico', 'Técnico')
    
    # Buscar registro activo
    registro = RegistroTiempo.query.filter_by(
        ordenId=id, tecnico=tecnico, enCurso=True
    ).first()
    
    if not registro:
        return jsonify({'error': f'No hay trabajo activo para {tecnico}'}), 400
    
    # Cerrar el registro
    registro.fin = datetime.now()
    registro.enCurso = False
    duracion = registro.duracionHoras
    
    # Actualizar tiempo real de la OT
    tiempoTotal = db.session.query(func.sum(
        func.julianday(RegistroTiempo.fin) - func.julianday(RegistroTiempo.inicio)
    )).filter(RegistroTiempo.ordenId == id, RegistroTiempo.fin.isnot(None)).scalar()
    
    if tiempoTotal:
        orden.tiempoReal = round(tiempoTotal * 24, 2)  # Convertir días a horas
    
    db.session.commit()
    return jsonify({
        'mensaje': f'Trabajo pausado por {tecnico}',
        'duracionSesion': round(duracion, 2),
        'tiempoTotalOT': orden.tiempoReal
    })

# Obtener registros de tiempo de una OT
@app.route('/api/orden/<int:id>/tiempos')
def obtenerTiemposOT(id):
    registros = RegistroTiempo.query.filter_by(ordenId=id).order_by(RegistroTiempo.inicio.desc()).all()

    return jsonify({
        'registros': [{
            'id': r.id,
            'tecnico': r.tecnico,
            'inicio': r.inicio.isoformat() if r.inicio else None,
            'fin': r.fin.isoformat() if r.fin else None,
            'enCurso': r.enCurso,
            'duracionHoras': round(r.duracionHoras, 2)
        } for r in registros]
    })

# Añadir coste de taller externo
@app.route('/api/orden/<int:id>/coste-externo', methods=['POST'])
def agregarCosteExterno(id):
    import json as _json
    orden = OrdenTrabajo.query.get_or_404(id)
    data = request.get_json()

    # Cargar lista existente
    costes = _json.loads(orden.costesExternosJson) if orden.costesExternosJson else []

    # Migración: si había un coste legacy y la lista está vacía, incorporarlo
    if not costes and orden.costeTallerExterno:
        costes.append({
            'proveedor': orden.proveedorExterno or '',
            'descripcion': orden.descripcionTallerExterno or '',
            'coste': round(float(orden.costeTallerExterno), 2)
        })

    # Añadir el nuevo coste
    costes.append({
        'proveedor': data.get('proveedor', ''),
        'descripcion': data.get('descripcion', ''),
        'coste': round(float(data.get('coste', 0)), 2)
    })

    orden.costesExternosJson = _json.dumps(costes)
    orden.costeTallerExterno = round(sum(c['coste'] for c in costes), 2)

    db.session.commit()
    return jsonify({'mensaje': 'Coste externo añadido', 'total': orden.costeTallerExterno, 'costes': costes})


@app.route('/api/orden/<int:id>/coste-externo/<int:idx>', methods=['DELETE'])
def eliminarCosteExterno(id, idx):
    import json as _json
    orden = OrdenTrabajo.query.get_or_404(id)
    costes = _json.loads(orden.costesExternosJson) if orden.costesExternosJson else []
    if idx < 0 or idx >= len(costes):
        return jsonify({'error': 'Índice no válido'}), 400
    costes.pop(idx)
    orden.costesExternosJson = _json.dumps(costes)
    orden.costeTallerExterno = round(sum(c['coste'] for c in costes), 2)
    db.session.commit()
    return jsonify({'mensaje': 'Coste eliminado', 'total': orden.costeTallerExterno, 'costes': costes})


# =============================================================================
# MANTENIMIENTO PREVENTIVO
# =============================================================================


@app.route('/preventivo')
@jwt_required()
def verPreventivo():
    return render_template('preventivo.html')

@app.route('/api/planes-preventivo')
def apiPlanesPreventivo():
    maquinaId = request.args.get('maquinaId', '')
    soloActivos = request.args.get('activos', 'true') == 'true'
    
    query = PlanPreventivo.query
    
    if maquinaId:
        query = query.filter_by(maquinaId=maquinaId)
    if soloActivos:
        query = query.filter_by(activo=True)
    
    planes = query.order_by(PlanPreventivo.proximaEjecucion).all()
    
    return jsonify([{
        'id': p.id,
        'codigo': p.codigo,
        'nombre': p.nombre,
        'descripcion': p.descripcion,
        'maquinaId': p.maquinaId,
        'maquinaNombre': p.maquina.nombre if p.maquina else '',
        'frecuenciaTipo': p.frecuenciaTipo,
        'frecuenciaValor': p.frecuenciaValor,
        'ultimaEjecucion': p.ultimaEjecucion.isoformat() if p.ultimaEjecucion else None,
        'proximaEjecucion': p.proximaEjecucion.isoformat() if p.proximaEjecucion else None,
        'activo': p.activo,
        'tiempoEstimado': p.tiempoEstimado,
        'vencido': p.proximaEjecucion and p.proximaEjecucion <= date.today()
    } for p in planes])

@app.route('/api/plan-preventivo', methods=['POST'])
def crearPlanPreventivo():
    data = request.get_json()
    
    # Obtener tipo y ID del equipo (nuevo formato: equipoTipo/equipoId)
    equipoTipo = data.get('equipoTipo', 'maquina')
    equipoId = data.get('equipoId') or data.get('maquinaId')  # Compatibilidad con legacy
    
    if not equipoId:
        return jsonify({'error': 'Debe especificar un equipo'}), 400
    
    # Si es máquina, mantener también el maquinaId para compatibilidad
    maquinaId = equipoId if equipoTipo == 'maquina' else None
    
    plan = PlanPreventivo(
        codigo=data['codigo'],
        nombre=data['nombre'],
        descripcion=data.get('descripcion', ''),
        equipoTipo=equipoTipo,
        equipoId=equipoId,
        maquinaId=maquinaId,  # Para compatibilidad
        frecuenciaTipo=data.get('frecuenciaTipo', 'dias'),
        frecuenciaValor=data.get('frecuenciaValor', 30),
        tiempoEstimado=data.get('tiempoEstimado')
    )
    
    # Calcular próxima ejecución
    plan.calcularProximaEjecucion()
    
    db.session.add(plan)
    db.session.commit()
    
    return jsonify({'id': plan.id, 'mensaje': 'Plan creado correctamente'}), 201


@app.route('/api/plan-preventivo/<int:id>', methods=['GET'])
def obtenerPlanPreventivo(id):
    p = PlanPreventivo.query.get_or_404(id)
    return jsonify({
        'id': p.id,
        'codigo': p.codigo,
        'nombre': p.nombre,
        'descripcion': p.descripcion,
        'maquinaId': p.maquinaId,
        'frecuenciaTipo': p.frecuenciaTipo,
        'frecuenciaValor': p.frecuenciaValor,
        'ultimaEjecucion': p.ultimaEjecucion.isoformat() if p.ultimaEjecucion else None,
        'proximaEjecucion': p.proximaEjecucion.isoformat() if p.proximaEjecucion else None,
        'activo': p.activo,
        'tiempoEstimado': p.tiempoEstimado,
        'tareas': [{
            'id': t.id,
            'descripcion': t.descripcion,
            'orden': t.orden,
            'duracionEstimada': t.duracionEstimada,
            'herramientas': t.herramientas,
            'instrucciones': t.instrucciones
        } for t in p.tareas]
    })

@app.route('/api/plan-preventivo/<int:id>', methods=['PUT'])
def actualizarPlanPreventivo(id):
    plan = PlanPreventivo.query.get_or_404(id)
    data = request.get_json()
    
    for campo in ['codigo', 'nombre', 'descripcion', 'frecuenciaTipo', 
                  'frecuenciaValor', 'tiempoEstimado', 'activo']:
        if campo in data:
            setattr(plan, campo, data[campo])
    
    # Recalcular próxima ejecución si cambió la frecuencia
    if 'frecuenciaTipo' in data or 'frecuenciaValor' in data:
        plan.calcularProximaEjecucion()
    
    db.session.commit()
    return jsonify({'mensaje': 'Plan actualizado correctamente'})

@app.route('/api/plan-preventivo/<int:id>/tarea', methods=['POST'])
def agregarTarea(id):
    plan = PlanPreventivo.query.get_or_404(id)
    data = request.get_json()
    
    # Obtener el siguiente número de orden
    maxOrden = db.session.query(func.max(TareaPreventivo.orden)).filter_by(planId=id).scalar() or 0
    
    tarea = TareaPreventivo(
        planId=id,
        descripcion=data['descripcion'],
        orden=maxOrden + 1,
        duracionEstimada=data.get('duracionEstimada'),
        herramientas=data.get('herramientas', ''),
        recambiosNecesarios=data.get('recambiosNecesarios', ''),
        instrucciones=data.get('instrucciones', '')
    )
    db.session.add(tarea)
    db.session.commit()
    
    return jsonify({'id': tarea.id, 'mensaje': 'Tarea agregada correctamente'})

@app.route('/api/plan-preventivo/<int:id>/generar-ot', methods=['POST'])
def generarOTPreventivo(id):
    plan = PlanPreventivo.query.get_or_404(id)
    
    # Crear OT preventiva
    orden = OrdenTrabajo(
        numero=OrdenTrabajo.generarNumero(),
        tipo='preventivo',
        prioridad='media',
        estado='pendiente',
        titulo=f'Preventivo: {plan.nombre}',
        descripcionProblema=f'Ejecución programada del plan de mantenimiento: {plan.codigo}\n\n{plan.descripcion}',
        maquinaId=plan.maquinaId,
        planPreventivoId=plan.id,
        tiempoEstimado=plan.tiempoEstimado
    )
    
    db.session.add(orden)
    
    # Actualizar fechas del plan
    plan.ultimaEjecucion = date.today()
    plan.calcularProximaEjecucion()
    
    db.session.commit()
    
    return jsonify({
        'id': orden.id,
        'numero': orden.numero,
        'mensaje': 'OT preventiva generada correctamente'
    })

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

@app.route('/configuracion')
@jwt_required()
def verConfiguracion():
    return render_template('configuracion.html')

# =============================================================================
# TIPOS DE INTERVENCIÓN
# =============================================================================

# Pool de iconos disponibles para tipos de intervención
ICONOS_DISPONIBLES = [
    {'icono': 'fa-wrench', 'nombre': 'Llave (Correctivo)'},
    {'icono': 'fa-calendar-check', 'nombre': 'Calendario (Preventivo)'},
    {'icono': 'fa-lightbulb', 'nombre': 'Bombilla (Mejora)'},
    {'icono': 'fa-hands-helping', 'nombre': 'Manos (Apoyo)'},
    {'icono': 'fa-project-diagram', 'nombre': 'Diagrama (Proyectos)'},
    {'icono': 'fa-tools', 'nombre': 'Herramientas'},
    {'icono': 'fa-cogs', 'nombre': 'Engranajes'},
    {'icono': 'fa-bolt', 'nombre': 'Rayo (Urgente)'},
    {'icono': 'fa-clipboard-list', 'nombre': 'Portapapeles (Inspección)'},
    {'icono': 'fa-sync-alt', 'nombre': 'Ciclo (Recurrente)'},
    {'icono': 'fa-hard-hat', 'nombre': 'Casco (Seguridad)'},
    {'icono': 'fa-truck', 'nombre': 'Camión (Logística)'},
    {'icono': 'fa-check-double', 'nombre': 'Verificación'},
    {'icono': 'fa-microscope', 'nombre': 'Microscopio (Análisis)'},
    {'icono': 'fa-shield-alt', 'nombre': 'Escudo (Protección)'},
]

@app.route('/api/tipos-intervencion')
def apiTiposIntervencion():
    """Listar todos los tipos de intervención activos"""
    soloActivos = request.args.get('activo', 'true') == 'true'
    query = TipoIntervencion.query
    if soloActivos:
        query = query.filter_by(activo=True)
    tipos = query.order_by(TipoIntervencion.orden, TipoIntervencion.nombre).all()
    return jsonify([{
        'id': t.id,
        'codigo': t.codigo,
        'nombre': t.nombre,
        'descripcion': t.descripcion,
        'icono': t.icono,
        'color': t.color,
        'activo': t.activo,
        'orden': t.orden
    } for t in tipos])

@app.route('/api/tipo-intervencion', methods=['POST'])
def crearTipoIntervencion():
    """Crear nuevo tipo de intervención"""
    data = request.get_json()
    
    # Generar código si no se proporciona
    codigo = data.get('codigo', '').strip().lower().replace(' ', '_')
    if not codigo:
        codigo = data['nombre'].lower().replace(' ', '_').replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ú', 'u')
    
    # Verificar código único
    if TipoIntervencion.query.filter_by(codigo=codigo).first():
        return jsonify({'error': 'Ya existe un tipo con ese código'}), 400
    
    tipo = TipoIntervencion(
        codigo=codigo,
        nombre=data['nombre'],
        descripcion=data.get('descripcion', ''),
        icono=data['icono'],
        color=data.get('color', '#1976d2'),
        activo=data.get('activo', True),
        orden=data.get('orden', 0)
    )
    db.session.add(tipo)
    db.session.commit()
    return jsonify({'id': tipo.id, 'codigo': tipo.codigo, 'mensaje': 'Tipo creado correctamente'}), 201

@app.route('/api/tipo-intervencion/<int:id>', methods=['GET'])
def obtenerTipoIntervencion(id):
    """Obtener un tipo de intervención por ID"""
    t = TipoIntervencion.query.get_or_404(id)
    return jsonify({
        'id': t.id,
        'codigo': t.codigo,
        'nombre': t.nombre,
        'descripcion': t.descripcion,
        'icono': t.icono,
        'color': t.color,
        'activo': t.activo,
        'orden': t.orden
    })

@app.route('/api/tipo-intervencion/<int:id>', methods=['PUT'])
def actualizarTipoIntervencion(id):
    """Actualizar tipo de intervención"""
    tipo = TipoIntervencion.query.get_or_404(id)
    data = request.get_json()
    
    for campo in ['nombre', 'descripcion', 'icono', 'color', 'activo', 'orden']:
        if campo in data:
            setattr(tipo, campo, data[campo])
    
    db.session.commit()
    return jsonify({'mensaje': 'Tipo actualizado correctamente'})

@app.route('/api/tipo-intervencion/<int:id>', methods=['DELETE'])
def eliminarTipoIntervencion(id):
    """Eliminar (soft delete) tipo de intervención"""
    tipo = TipoIntervencion.query.get_or_404(id)
    
    # Verificar si hay OTs usando este tipo
    otUsando = OrdenTrabajo.query.filter_by(tipo=tipo.codigo).first()
    if otUsando:
        # En lugar de eliminar, desactivar
        tipo.activo = False
        db.session.commit()
        return jsonify({'mensaje': 'Tipo desactivado (hay OTs asociadas)', 'desactivado': True})
    
    db.session.delete(tipo)
    db.session.commit()
    return jsonify({'mensaje': 'Tipo eliminado correctamente'})

@app.route('/api/iconos-disponibles')
def apiIconosDisponibles():
    """Obtener iconos que no están siendo usados por otros tipos"""
    iconosUsados = [t.icono for t in TipoIntervencion.query.filter_by(activo=True).all()]
    disponibles = [i for i in ICONOS_DISPONIBLES if i['icono'] not in iconosUsados]
    return jsonify(disponibles)

# =============================================================================
# GAMAS DE MANTENIMIENTO (Nuevo sistema)
# =============================================================================


@app.route('/api/gamas')
def apiGamas():
    activo = request.args.get('activo', '')
    buscar = request.args.get('buscar', '')
    
    query = GamaMantenimiento.query
    
    if activo == 'true':
        query = query.filter_by(activo=True)
    elif activo == 'false':
        query = query.filter_by(activo=False)
    
    if buscar:
        query = query.filter(
            or_(
                GamaMantenimiento.codigo.ilike(f'%{buscar}%'),
                GamaMantenimiento.nombre.ilike(f'%{buscar}%')
            )
        )
    
    gamas = query.order_by(GamaMantenimiento.codigo).all()
    
    return jsonify([{
        'id': g.id,
        'codigo': g.codigo,
        'nombre': g.nombre,
        'tipo': g.tipo,
        'descripcion': g.descripcion,
        'tiempoEstimado': g.tiempoEstimado,
        'activo': g.activo,
        'numTareas': len(g.tareas),
        'numRecambios': len(g.recambios),
        'numAsignaciones': len([a for a in g.asignaciones if a.activo]),
        'numChecklist': len(g.checklistItems)
    } for g in gamas])

@app.route('/api/gama', methods=['POST'])
def crearGama():
    data = request.get_json()
    
    tipo_gama = data.get('tipo', 'preventivo')
    nuevo_codigo = GamaMantenimiento.generarCodigo(tipo_gama)
    
    gama = GamaMantenimiento(
        codigo=nuevo_codigo,
        nombre=data['nombre'],
        descripcion=data.get('descripcion', ''),
        tipo=tipo_gama,
        tiempoEstimado=data.get('tiempoEstimado'),
        activo=data.get('activo', True)
    )
    
    db.session.add(gama)
    db.session.commit()
    
    return jsonify({'id': gama.id, 'mensaje': 'Gama creada correctamente'}), 201

@app.route('/api/gama/<int:id>')
def obtenerGama(id):
    g = GamaMantenimiento.query.get_or_404(id)
    
    return jsonify({
        'id': g.id,
        'codigo': g.codigo,
        'nombre': g.nombre,
        'tipo': g.tipo,
        'descripcion': g.descripcion,
        'tiempoEstimado': g.tiempoEstimado,
        'activo': g.activo,
        'fechaCreacion': g.fechaCreacion.isoformat() if g.fechaCreacion else None,
        'tareas': [{
            'id': t.id,
            'descripcion': t.descripcion,
            'orden': t.orden,
            'duracionEstimada': t.duracionEstimada,
            'herramientas': t.herramientas,
            'instrucciones': t.instrucciones
        } for t in g.tareas],
        'recambios': [{
            'id': r.id,
            'recambioId': r.recambioId,
            'recambioCodigo': r.recambio.codigo,
            'recambioNombre': r.recambio.nombre,
            'cantidad': r.cantidad,
            'observaciones': r.observaciones
        } for r in g.recambios],
        'asignaciones': [{
            'id': a.id,
            'equipoTipo': a.equipoTipo,
            'equipoId': a.equipoId,
            'equipoNombre': getEquipoNombre(a.equipoTipo, a.equipoId),
            'frecuenciaTipo': a.frecuenciaTipo,
            'frecuenciaValor': a.frecuenciaValor,
            'proximaEjecucion': a.proximaEjecucion.isoformat() if a.proximaEjecucion else None,
            'activo': a.activo
        } for a in g.asignaciones],
        'checklistItems': [{
            'id': ci.id,
            'descripcion': ci.descripcion,
            'orden': ci.orden,
            'tipoRespuesta': ci.tipoRespuesta,
            'unidad': ci.unidad,
            'generaCorrectivo': ci.generaCorrectivo
        } for ci in g.checklistItems],
        'numChecklist': len(g.checklistItems)
    })

@app.route('/api/gama/<int:id>', methods=['PUT'])
def actualizarGama(id):
    gama = GamaMantenimiento.query.get_or_404(id)
    data = request.get_json()
    
    # Verificar código único si se cambia
    if 'codigo' in data and data['codigo'] != gama.codigo:
        if GamaMantenimiento.query.filter_by(codigo=data['codigo']).first():
            return jsonify({'error': 'El código ya existe'}), 400
    
    for campo in ['codigo', 'nombre', 'descripcion', 'tipo', 'tiempoEstimado', 'activo']:
        if campo in data:
            setattr(gama, campo, data[campo])
    
    db.session.commit()
    return jsonify({'mensaje': 'Gama actualizada correctamente'})

@app.route('/api/gama/<int:id>/tarea', methods=['POST'])
def agregarTareaGama(id):
    gama = GamaMantenimiento.query.get_or_404(id)
    data = request.get_json()
    
    # Obtener el siguiente número de orden
    maxOrden = db.session.query(func.max(TareaGama.orden)).filter_by(gamaId=id).scalar() or 0
    
    tarea = TareaGama(
        gamaId=id,
        descripcion=data['descripcion'],
        orden=maxOrden + 1,
        duracionEstimada=data.get('duracionEstimada'),
        herramientas=data.get('herramientas', ''),
        instrucciones=data.get('instrucciones', '')
    )
    db.session.add(tarea)
    db.session.commit()
    
    return jsonify({'id': tarea.id, 'mensaje': 'Tarea agregada correctamente'})

@app.route('/api/gama/<int:gamaId>/tarea/<int:tareaId>', methods=['DELETE'])
def eliminarTareaGama(gamaId, tareaId):
    tarea = TareaGama.query.filter_by(id=tareaId, gamaId=gamaId).first_or_404()
    db.session.delete(tarea)
    db.session.commit()
    return jsonify({'mensaje': 'Tarea eliminada correctamente'})

@app.route('/api/gama/<int:id>/recambio', methods=['POST'])
def agregarRecambioGama(id):
    gama = GamaMantenimiento.query.get_or_404(id)
    data = request.get_json()
    
    # Verificar que el recambio existe
    recambio = Recambio.query.get_or_404(data['recambioId'])
    
    # Verificar que no esté ya añadido
    existente = RecambioGama.query.filter_by(
        gamaId=id, 
        recambioId=data['recambioId']
    ).first()
    
    if existente:
        return jsonify({'error': 'El recambio ya está en esta gama'}), 400
    
    recambioGama = RecambioGama(
        gamaId=id,
        recambioId=data['recambioId'],
        cantidad=data.get('cantidad', 1),
        observaciones=data.get('observaciones', '')
    )
    db.session.add(recambioGama)
    db.session.commit()
    
    return jsonify({'id': recambioGama.id, 'mensaje': 'Recambio agregado correctamente'})

@app.route('/api/gama/<int:gamaId>/recambio/<int:recambioGamaId>', methods=['DELETE'])
def eliminarRecambioGama(gamaId, recambioGamaId):
    recambio = RecambioGama.query.filter_by(id=recambioGamaId, gamaId=gamaId).first_or_404()
    db.session.delete(recambio)
    db.session.commit()
    return jsonify({'mensaje': 'Recambio eliminado correctamente'})

# =============================================================================
# CHECKLIST DE VERIFICACIÓN (items en gamas, respuestas en OTs)
# =============================================================================

@app.route('/api/gama/<int:gamaId>/checklist-item', methods=['POST'])
def crearChecklistItem(gamaId):
    gama = GamaMantenimiento.query.get_or_404(gamaId)
    data = request.get_json()
    if not data.get('descripcion'):
        return jsonify({'error': 'La descripción es obligatoria'}), 400
    # Calcular siguiente orden
    max_orden = db.session.query(db.func.max(ChecklistItem.orden)).filter_by(gamaId=gamaId).scalar() or 0
    item = ChecklistItem(
        gamaId=gamaId,
        descripcion=data['descripcion'],
        orden=max_orden + 1,
        tipoRespuesta=data.get('tipoRespuesta', 'ok_nok'),
        unidad=data.get('unidad'),
        generaCorrectivo=data.get('generaCorrectivo', True)
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'id': item.id, 'mensaje': 'Item de checklist creado'}), 201

@app.route('/api/gama/<int:gamaId>/checklist-item/<int:itemId>', methods=['DELETE'])
def eliminarChecklistItem(gamaId, itemId):
    item = ChecklistItem.query.filter_by(id=itemId, gamaId=gamaId).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'mensaje': 'Item eliminado correctamente'})

@app.route('/api/orden/<int:id>/checklist', methods=['GET'])
def obtenerChecklistOrden(id):
    orden = OrdenTrabajo.query.get_or_404(id)
    items = orden.gama.checklistItems if orden.gama else []
    respuestas_map = {r.checklistItemId: r for r in orden.respuestasChecklist}
    return jsonify([{
        'id': ci.id,
        'descripcion': ci.descripcion,
        'orden': ci.orden,
        'tipoRespuesta': ci.tipoRespuesta,
        'unidad': ci.unidad,
        'generaCorrectivo': ci.generaCorrectivo,
        'respuesta': respuestas_map[ci.id].respuesta if ci.id in respuestas_map else None,
        'observaciones': respuestas_map[ci.id].observaciones if ci.id in respuestas_map else None
    } for ci in items])

@app.route('/api/orden/<int:id>/checklist', methods=['POST'])
def guardarChecklistOrden(id):
    """Guarda (o actualiza) las respuestas del checklist de una OT.
    Body: [{checklistItemId, respuesta, observaciones}]
    """
    orden = OrdenTrabajo.query.get_or_404(id)
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({'error': 'Se esperaba una lista de respuestas'}), 400

    # Eliminar respuestas previas y reemplazar
    RespuestaChecklist.query.filter_by(ordenId=id).delete()

    for r in data:
        item_id = r.get('checklistItemId')
        if not item_id:
            continue
        resp = RespuestaChecklist(
            ordenId=id,
            checklistItemId=item_id,
            respuesta=r.get('respuesta', ''),
            observaciones=r.get('observaciones', '')
        )
        db.session.add(resp)

    db.session.commit()
    return jsonify({'mensaje': 'Checklist guardado correctamente'})

# =============================================================================
# ASIGNACIONES DE GAMAS A EQUIPOS
# =============================================================================

@app.route('/api/asignaciones')
def apiAsignaciones():
    equipoTipo = request.args.get('equipoTipo', '')
    equipoId = request.args.get('equipoId', '')
    gamaId = request.args.get('gamaId', '')
    activo = request.args.get('activo', 'true')
    
    query = AsignacionGama.query
    
    if equipoTipo and equipoId:
        query = query.filter_by(equipoTipo=equipoTipo, equipoId=int(equipoId))
    if gamaId:
        query = query.filter_by(gamaId=int(gamaId))
    if activo == 'true':
        query = query.filter_by(activo=True)
    
    asignaciones = query.order_by(AsignacionGama.proximaEjecucion).all()
    
    return jsonify([{
        'id': a.id,
        'gamaId': a.gamaId,
        'gamaCodigo': a.gama.codigo,
        'gamaNombre': a.gama.nombre,
        'equipoTipo': a.equipoTipo,
        'equipoId': a.equipoId,
        'equipoNombre': getEquipoNombre(a.equipoTipo, a.equipoId),
        'frecuenciaTipo': a.frecuenciaTipo,
        'frecuenciaValor': a.frecuenciaValor,
        'ultimaEjecucion': a.ultimaEjecucion.isoformat() if a.ultimaEjecucion else None,
        'proximaEjecucion': a.proximaEjecucion.isoformat() if a.proximaEjecucion else None,
        'activo': a.activo,
        'vencido': a.proximaEjecucion and a.proximaEjecucion <= date.today() if a.activo else False
    } for a in asignaciones])

@app.route('/api/asignacion', methods=['POST'])
def crearAsignacion():
    data = request.get_json()
    
    # Verificar que la gama existe
    gama = GamaMantenimiento.query.get_or_404(data['gamaId'])
    
    # Verificar que el equipo existe
    equipoTipo = data['equipoTipo']
    equipoId = data['equipoId']
    equipoNombre = getEquipoNombre(equipoTipo, equipoId)
    if not equipoNombre:
        return jsonify({'error': 'El equipo no existe'}), 400
    
    asignacion = AsignacionGama(
        gamaId=data['gamaId'],
        equipoTipo=equipoTipo,
        equipoId=equipoId,
        frecuenciaTipo=data.get('frecuenciaTipo', 'dias'),
        frecuenciaValor=data.get('frecuenciaValor', 30),
        activo=data.get('activo', True)
    )
    
    # Calcular próxima ejecución
    asignacion.calcularProximaEjecucion()
    
    db.session.add(asignacion)
    db.session.commit()
    
    return jsonify({'id': asignacion.id, 'mensaje': 'Asignación creada correctamente'}), 201

@app.route('/api/asignacion/<int:id>')
def obtenerAsignacion(id):
    a = AsignacionGama.query.get_or_404(id)
    
    return jsonify({
        'id': a.id,
        'gamaId': a.gamaId,
        'gamaCodigo': a.gama.codigo,
        'gamaNombre': a.gama.nombre,
        'equipoTipo': a.equipoTipo,
        'equipoId': a.equipoId,
        'equipoNombre': getEquipoNombre(a.equipoTipo, a.equipoId),
        'frecuenciaTipo': a.frecuenciaTipo,
        'frecuenciaValor': a.frecuenciaValor,
        'ultimaEjecucion': a.ultimaEjecucion.isoformat() if a.ultimaEjecucion else None,
        'proximaEjecucion': a.proximaEjecucion.isoformat() if a.proximaEjecucion else None,
        'activo': a.activo,
        'fechaAsignacion': a.fechaAsignacion.isoformat() if a.fechaAsignacion else None
    })

@app.route('/api/asignacion/<int:id>', methods=['PUT'])
def actualizarAsignacion(id):
    asignacion = AsignacionGama.query.get_or_404(id)
    data = request.get_json()
    
    for campo in ['frecuenciaTipo', 'frecuenciaValor', 'activo']:
        if campo in data:
            setattr(asignacion, campo, data[campo])
    
    # Recalcular próxima ejecución si cambió la frecuencia
    if 'frecuenciaTipo' in data or 'frecuenciaValor' in data:
        asignacion.calcularProximaEjecucion()
    
    db.session.commit()
    return jsonify({'mensaje': 'Asignación actualizada correctamente'})

@app.route('/api/asignacion/<int:id>/desactivar', methods=['PUT'])
def desactivarAsignacion(id):
    asignacion = AsignacionGama.query.get_or_404(id)
    asignacion.activo = False
    db.session.commit()
    return jsonify({'mensaje': 'Asignación desactivada correctamente'})

@app.route('/api/asignacion/<int:id>/generar-ot', methods=['POST'])
def generarOTDesdeAsignacion(id):
    asignacion = AsignacionGama.query.get_or_404(id)
    gama = asignacion.gama
    
    # Crear OT preventiva
    orden = OrdenTrabajo(
        numero=OrdenTrabajo.generarNumero(),
        tipo='preventivo',
        prioridad='media',
        estado='pendiente',
        titulo=f'Preventivo: {gama.nombre}',
        descripcionProblema=f'Ejecución programada de la gama: {gama.codigo}\n\n{gama.descripcion}',
        equipoTipo=asignacion.equipoTipo,
        equipoId=asignacion.equipoId,
        asignacionGamaId=asignacion.id,
        gamaId=asignacion.gamaId,
        frecuenciaTipo=asignacion.frecuenciaTipo,
        frecuenciaValor=asignacion.frecuenciaValor,
        tiempoEstimado=gama.tiempoEstimado / 60 if gama.tiempoEstimado else None,  # Convertir minutos a horas
        fechaProgramada=datetime.combine(asignacion.proximaEjecucion, datetime.min.time()) if asignacion.proximaEjecucion else None
    )
    
    # Si es máquina, añadir maquinaId para compatibilidad
    if asignacion.equipoTipo == 'maquina':
        orden.maquinaId = asignacion.equipoId
    
    db.session.add(orden)
    
    # Actualizar fechas de la asignación
    asignacion.ultimaEjecucion = date.today()
    asignacion.calcularProximaEjecucion()
    
    db.session.commit()
    
    return jsonify({
        'id': orden.id,
        'numero': orden.numero,
        'mensaje': 'OT preventiva generada correctamente'
    })

# =============================================================================
# DASHBOARD Y ESTADÍSTICAS
# =============================================================================

@app.route('/api/dashboard/stats')
def dashboardStats():
    hoy = date.today()
    inicioMes = hoy.replace(day=1)
    
    stats = {
        # OTs
        'otPendientes': OrdenTrabajo.query.filter_by(estado='pendiente').count(),
        'otEnCurso': OrdenTrabajo.query.filter_by(estado='en_curso').count(),
        'otCerradasMes': OrdenTrabajo.query.filter(
            OrdenTrabajo.estado == 'cerrada',
            OrdenTrabajo.fechaFin >= inicioMes
        ).count(),
        
        # Equipos
        'totalMaquinas': Maquina.query.count(),
        'maquinasOperativas': Maquina.query.filter_by(estado='operativo').count(),
        'maquinasAveriadas': Maquina.query.filter_by(estado='averiado').count(),
        
        # Stock
        'stockBajo': Recambio.query.filter(
            Recambio.activo == True,
            Recambio.stockActual <= Recambio.stockMinimo
        ).count(),
        
        # Preventivo
        'preventivoPendiente': PlanPreventivo.query.filter(
            PlanPreventivo.activo == True,
            PlanPreventivo.proximaEjecucion <= hoy
        ).count(),
        'preventivoProximaSemana': PlanPreventivo.query.filter(
            PlanPreventivo.activo == True,
            PlanPreventivo.proximaEjecucion > hoy,
            PlanPreventivo.proximaEjecucion <= hoy + timedelta(days=7)
        ).count()
    }
    
    # Calcular % disponibilidad
    if stats['totalMaquinas'] > 0:
        stats['disponibilidad'] = round(
            (stats['maquinasOperativas'] / stats['totalMaquinas']) * 100
        )
    else:
        stats['disponibilidad'] = 100
    
    return jsonify(stats)

@app.route('/api/dashboard/ot-por-tipo')
def otPorTipo():
    """Devuelve conteo de OTs agrupadas por tipo para gráficos"""
    resultado = db.session.query(
        OrdenTrabajo.tipo,
        func.count(OrdenTrabajo.id)
    ).group_by(OrdenTrabajo.tipo).all()
    
    return jsonify([{'tipo': r[0], 'cantidad': r[1]} for r in resultado])

@app.route('/api/dashboard/ot-por-estado')
def otPorEstado():
    """Devuelve conteo de OTs agrupadas por estado para gráficos"""
    resultado = db.session.query(
        OrdenTrabajo.estado,
        func.count(OrdenTrabajo.id)
    ).group_by(OrdenTrabajo.estado).all()
    
    return jsonify([{'estado': r[0], 'cantidad': r[1]} for r in resultado])

# =============================================================================
# RUTAS LEGACY (mantener compatibilidad)
# =============================================================================

@app.route('/edit_activo/<int:id>', methods=['GET', 'POST'])
def editActivo(id):
    activo = Activo.query.get_or_404(id)
    if request.method == 'POST':
        activo.nombre = request.form['nombre']
        activo.descripcion = request.form['descripcion']
        activo.numeroSerie = request.form.get('numeroSerie', '')
        activo.estado = request.form.get('estado', 'Operativo')
        db.session.commit()
        return redirect(url_for('verActivos'))
    return render_template('edit_activo.html', activo=activo)

@app.route('/delete_activo/<int:id>')
def deleteActivo(id):
    activo = Activo.query.get_or_404(id)
    db.session.delete(activo)
    db.session.commit()
    return redirect(url_for('verActivos'))

@app.route('/getActivoDetails/<int:id>')
def getActivoDetails(id):
    activo = Activo.query.get_or_404(id)
    return jsonify({
        'id': activo.id,
        'nombre': activo.nombre,
        'descripcion': activo.descripcion,
        'estado': activo.estado,
        'codigoCompleto': activo.codigoCompleto,
        'fechaAlta': activo.fechaAlta.isoformat() if activo.fechaAlta else None,
        'fechaBaja': activo.fechaBaja.isoformat() if activo.fechaBaja else None,
    })

@app.route('/getIntervenciones/<int:activoId>')
def getIntervenciones(activoId):
    intervenciones = Intervencion.query.filter_by(activoId=activoId).order_by(Intervencion.fecha.desc()).all()
    return jsonify([
        {
            'id': i.id,
            'tipo': i.tipo,
            'fecha': i.fecha.isoformat(),
            'descripcion': i.descripcion,
            'duracion': i.duracion,
            'tecnico': i.tecnico
        } for i in intervenciones
    ])

@app.route('/nuevo_formulario')
def nuevoFormulario():
    return render_template('altaActivo.html')

@app.route('/guardar_activo', methods=['POST'])
def guardarActivo():
    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')
    modelo = request.form.get('modelo')
    numeroSerie = request.form.get('numeroSerie')
    fabricante = request.form.get('fabricante')
    plantaId = request.form.get('planta')
    zonaId = request.form.get('zona')
    lineaId = request.form.get('linea')
    maquinaId = request.form.get('maquina')
    elementoId = request.form.get('elemento')

    activo = Activo(
        nombre=nombre,
        descripcion=descripcion,
        modelo=modelo,
        numeroSerie=numeroSerie,
        fabricante=fabricante,
        plantaId=plantaId or None,
        zonaId=zonaId or None,
        lineaId=lineaId or None,
        maquinaId=maquinaId or None,
        elementoId=elementoId or None,
        estado='Operativo'
    )
    db.session.add(activo)
    db.session.commit()
    return redirect(url_for('verActivos'))

@app.route('/alta_activo')
def testAlta():
    return render_template('altaActivo.html')




# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================


# =============================================================================
# GESTIÓN DE TÉCNICOS (MAESTRO)
# =============================================================================

@app.route('/api/tecnicos')
def apiTecnicos():
    # Mostrar todos o filtrar por activos
    soloActivos = request.args.get('activo') == 'true'
    
    query = Tecnico.query
    if soloActivos:
        query = query.filter_by(activo=True)
        
    tecnicos = query.order_by(Tecnico.nombre).all()
    
    return jsonify([{
        'id': t.id,
        'nombre': t.nombre,
        'apellidos': t.apellidos,
        'especialidad': t.especialidad,
        'telefono': t.telefono,
        'tipo_tecnico': t.tipo_tecnico,
        'activo': t.activo,
        'costeHora': t.costeHora
    } for t in tecnicos])

@app.route('/api/tecnico/<int:id>')
def getTecnico(id):
    t = Tecnico.query.get_or_404(id)
    return jsonify({
        'id': t.id,
        'nombre': t.nombre,
        'apellidos': t.apellidos,
        'especialidad': t.especialidad,
        'telefono': t.telefono,
        'tipo_tecnico': t.tipo_tecnico,
        'activo': t.activo,
        'costeHora': t.costeHora
    })

@app.route('/api/tecnico', methods=['POST'])
def crearTecnico():
    data = request.get_json()
    
    # Validaciones básicas
    if not data.get('nombre'):
        return jsonify({'error': 'El nombre es obligatorio'}), 400
        
    tecnico = Tecnico(
        nombre=data['nombre'],
        apellidos=data.get('apellidos', ''),
        especialidad=data.get('especialidad', ''),
        telefono=data.get('telefono', ''),
        tipo_tecnico=data.get('tipo_tecnico', 'interno'),
        activo=data.get('activo', True),
        costeHora=data.get('costeHora', 0)
    )
    
    try:
        db.session.add(tecnico)
        db.session.commit()
        return jsonify({'id': tecnico.id, 'mensaje': 'Técnico creado correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/tecnico/<int:id>', methods=['PUT'])
def actualizarTecnico(id):
    t = Tecnico.query.get_or_404(id)
    data = request.get_json()
    
    t.nombre = data.get('nombre', t.nombre)
    t.apellidos = data.get('apellidos', t.apellidos)
    t.especialidad = data.get('especialidad', t.especialidad)
    t.telefono = data.get('telefono', t.telefono)
    t.tipo_tecnico = data.get('tipo_tecnico', t.tipo_tecnico)
    t.activo = data.get('activo', t.activo)
    t.costeHora = data.get('costeHora', t.costeHora)
    
    try:
        db.session.commit()
        return jsonify({'mensaje': 'Técnico actualizado correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/tecnico/<int:id>', methods=['DELETE'])
def eliminarTecnico(id):
    t = Tecnico.query.get_or_404(id)
    
    try:
        db.session.delete(t)
        db.session.commit()
        return jsonify({'mensaje': 'Técnico eliminado correctamente', 'eliminado': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =============================================================================
# CONFIGURACIÓN GENERAL
# =============================================================================

_CONFIG_DEFAULTS = [
    ('tecnico_puede_cerrar', 'false', 'El técnico puede hacer el cierre definitivo sin necesidad de un responsable', 'booleano'),
]

def _seed_config():
    changed = False
    for clave, valor, descripcion, tipo in _CONFIG_DEFAULTS:
        if not ConfiguracionGeneral.query.filter_by(clave=clave).first():
            db.session.add(ConfiguracionGeneral(clave=clave, valor=valor, descripcion=descripcion, tipo=tipo))
            changed = True
    if changed:
        db.session.commit()


@app.route('/api/config-general', methods=['GET'])
def getConfigGeneral():
    _seed_config()
    registros = ConfiguracionGeneral.query.order_by(ConfiguracionGeneral.clave).all()
    return jsonify([{
        'id': r.id,
        'clave': r.clave,
        'valor': r.valor,
        'descripcion': r.descripcion,
        'tipo': r.tipo,
    } for r in registros])


@app.route('/api/config-general', methods=['PUT'])
def putConfigGeneral():
    data = request.get_json()
    if not isinstance(data, list):
        data = [data]
    for item in data:
        clave = item.get('clave')
        valor = item.get('valor')
        if not clave:
            continue
        reg = ConfiguracionGeneral.query.filter_by(clave=clave).first()
        if reg:
            reg.valor = str(valor)
        else:
            db.session.add(ConfiguracionGeneral(clave=clave, valor=str(valor)))
    db.session.commit()
    return jsonify({'mensaje': 'Configuración guardada correctamente'})


# =============================================================================
# GESTIÓN DE USUARIOS
# =============================================================================

@app.route('/api/usuarios', methods=['GET'])
def getUsuarios():
    soloActivos = request.args.get('activo', 'false') == 'true'
    q = Usuario.query
    if soloActivos:
        q = q.filter_by(activo=True)
    usuarios = q.order_by(Usuario.nombre).all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'nombre': u.nombre,
        'apellidos': u.apellidos or '',
        'nivel': u.nivel,
        'tecnicoId': u.tecnicoId,
        'tecnicoNombre': f"{u.tecnico.nombre} {u.tecnico.apellidos or ''}".strip() if u.tecnico else None,
        'activo': u.activo,
        'fechaAlta': u.fechaAlta.isoformat() if u.fechaAlta else None,
        'ultimoAcceso': u.ultimoAcceso.isoformat() if u.ultimoAcceso else None,
    } for u in usuarios])


@app.route('/api/usuario', methods=['POST'])
def crearUsuario():
    data = request.get_json()
    if not data.get('username') or not data.get('nombre') or not data.get('nivel'):
        return jsonify({'error': 'Nombre, usuario y nivel son obligatorios'}), 400
    if Usuario.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Ya existe un usuario con ese login'}), 409
    u = Usuario(
        username=data['username'],
        nombre=data['nombre'],
        apellidos=data.get('apellidos', ''),
        nivel=data['nivel'],
        tecnicoId=data.get('tecnicoId') or None,
        activo=True,
    )
    if data.get('password'):
        u.set_password(data['password'])
    db.session.add(u)
    db.session.commit()
    return jsonify({'id': u.id, 'mensaje': 'Usuario creado correctamente'}), 201



@app.route('/api/usuario/<int:id>', methods=['PUT'])
def actualizarUsuario(id):
    u = Usuario.query.get_or_404(id)
    data = request.get_json()
    for campo in ['username', 'nombre', 'apellidos', 'nivel', 'activo']:
        if campo in data:
            setattr(u, campo, data[campo])
    if 'tecnicoId' in data:
        u.tecnicoId = data['tecnicoId'] or None
    if data.get('password'):
        u.set_password(data['password'])
    try:
        db.session.commit()
        return jsonify({'mensaje': 'Usuario actualizado correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/usuario/<int:id>', methods=['DELETE'])
def eliminarUsuario(id):
    u = Usuario.query.get_or_404(id)
    try:
        db.session.delete(u)
        db.session.commit()
        return jsonify({'mensaje': 'Usuario eliminado correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)