"""
Rutas del módulo móvil/tablet para técnicos.
Interfaz reducida centrada en Órdenes de Trabajo.
"""
from functools import wraps
from flask import render_template, redirect, url_for, request, jsonify
from flask_jwt_extended import jwt_required, current_user, verify_jwt_in_request
from sqlalchemy import case as sa_case, or_, and_

from blueprints.mobile import bp
from models import (
    OrdenTrabajo, RegistroTiempo, ConsumoRecambio, Recambio,
    Maquina, Elemento, Linea, Zona, Planta, Empresa, Tecnico,
    GamaMantenimiento, ChecklistItem, RespuestaChecklist,
    TareaRealizada, db
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _nombre_tecnico(user):
    """Devuelve el nombre completo del técnico para comparar con tecnicoAsignado."""
    if user is None:
        return ''
    if user.tecnico:
        t = user.tecnico
        return f"{t.nombre} {t.apellidos}".strip() if t.apellidos else t.nombre
    nombre = user.nombre or ''
    apellidos = user.apellidos or ''
    return f"{nombre} {apellidos}".strip()


def _get_ruta_nombres(equipoTipo, equipoId):
    """
    Retorna lista de dicts {nombre, tipo} desde Planta hasta el equipo,
    excluyendo niveles Empresa (muy genérico para espacio en pantalla).
    """
    if not equipoTipo or not equipoId:
        return []

    ruta = []

    if equipoTipo == 'elemento':
        elem = Elemento.query.get(equipoId)
        if elem:
            ruta.append({'nombre': elem.nombre, 'codigo': elem.codigo, 'tipo': 'elemento'})
            maq = Maquina.query.get(elem.maquinaId)
            if maq:
                ruta.insert(0, {'nombre': maq.nombre, 'codigo': maq.codigo, 'tipo': 'maquina'})
                _add_superior_maquina(maq, ruta)

    elif equipoTipo == 'maquina':
        maq = Maquina.query.get(equipoId)
        if maq:
            ruta.append({'nombre': maq.nombre, 'codigo': maq.codigo, 'tipo': 'maquina'})
            _add_superior_maquina(maq, ruta)

    elif equipoTipo == 'linea':
        linea = Linea.query.get(equipoId)
        if linea:
            ruta.append({'nombre': linea.nombre, 'codigo': linea.codigo, 'tipo': 'linea'})
            _add_superior_linea(linea, ruta)

    elif equipoTipo == 'zona':
        zona = Zona.query.get(equipoId)
        if zona:
            ruta.append({'nombre': zona.nombre, 'codigo': zona.codigo, 'tipo': 'zona'})
            planta = Planta.query.get(zona.plantaId)
            if planta:
                ruta.insert(0, {'nombre': planta.nombre, 'codigo': planta.codigo, 'tipo': 'planta'})

    elif equipoTipo == 'planta':
        planta = Planta.query.get(equipoId)
        if planta:
            ruta.append({'nombre': planta.nombre, 'codigo': planta.codigo, 'tipo': 'planta'})

    return ruta


def _add_superior_maquina(maq, ruta):
    linea = Linea.query.get(maq.lineaId)
    if linea:
        ruta.insert(0, {'nombre': linea.nombre, 'codigo': linea.codigo, 'tipo': 'linea'})
        _add_superior_linea(linea, ruta)


def _add_superior_linea(linea, ruta):
    zona = Zona.query.get(linea.zonaId)
    if zona:
        ruta.insert(0, {'nombre': zona.nombre, 'codigo': zona.codigo, 'tipo': 'zona'})
        planta = Planta.query.get(zona.plantaId)
        if planta:
            ruta.insert(0, {'nombre': planta.nombre, 'codigo': planta.codigo, 'tipo': 'planta'})


def _enrich_ot(ot):
    """Añade equipoRutaNombres y nombre corto del equipo a un OT."""
    equipoTipo = ot.equipoTipo or ('maquina' if ot.maquinaId else None)
    equipoId = ot.equipoId or ot.maquinaId
    ruta = _get_ruta_nombres(equipoTipo, equipoId)
    ot._ruta = ruta
    ot._equipoTipoEfectivo = equipoTipo
    ot._equipoIdEfectivo = equipoId
    return ot


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def movil_required(f):
    """Requiere autenticación JWT (cualquier nivel)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Rutas de vistas HTML
# ---------------------------------------------------------------------------

_TIPOS_PRINCIPALES = ('correctivo', 'preventivo')

def _tipo_filter(tipo):
    """Devuelve el filtro SQLAlchemy para el tipo de OT.
    tipo puede ser un string ('correctivo', 'preventivo') o
    '__otras__' para todo lo que no sea correctivo/preventivo."""
    if tipo == '__otras__':
        return OrdenTrabajo.tipo.notin_(_TIPOS_PRINCIPALES)
    return OrdenTrabajo.tipo == tipo


def _queries_ot(nombre_tecnico, tipo):
    """Devuelve (mis_ots, ots_pendientes) enriquecidas para un tipo/categoría de OT."""
    estado_order = sa_case(
        (OrdenTrabajo.estado == 'en_curso', 1),
        (OrdenTrabajo.estado == 'asignada', 2),
        (OrdenTrabajo.estado == 'pendiente', 3),
        else_=4
    )
    prio_order = sa_case(
        (OrdenTrabajo.prioridad == 'urgente', 1),
        (OrdenTrabajo.prioridad == 'alta',    2),
        (OrdenTrabajo.prioridad == 'media',   3),
        else_=4
    )

    mis = OrdenTrabajo.query.filter(
        _tipo_filter(tipo),
        OrdenTrabajo.tecnicoAsignado == nombre_tecnico,
        OrdenTrabajo.estado.notin_(['cerrada', 'cancelada'])
    ).order_by(estado_order, OrdenTrabajo.fechaCreacion.desc()).all()

    pendientes = OrdenTrabajo.query.filter(
        _tipo_filter(tipo),
        OrdenTrabajo.estado.in_(['pendiente', 'asignada', 'en_curso'])
    ).order_by(estado_order, prio_order, OrdenTrabajo.fechaCreacion.desc()).all()

    return [_enrich_ot(o) for o in mis], [_enrich_ot(o) for o in pendientes]


@bp.route('/')
@movil_required
def home():
    nombre_tecnico = _nombre_tecnico(current_user)
    mis_ots, ots_pendientes = _queries_ot(nombre_tecnico, 'correctivo')
    return render_template(
        'mobile/home.html',
        mis_ots=mis_ots,
        ots_pendientes=ots_pendientes,
        nombre_tecnico=nombre_tecnico,
    )


@bp.route('/preventivo')
@movil_required
def preventivo():
    nombre_tecnico = _nombre_tecnico(current_user)
    mis_ots, ots_pendientes = _queries_ot(nombre_tecnico, 'preventivo')
    return render_template(
        'mobile/preventivo.html',
        mis_ots=mis_ots,
        ots_pendientes=ots_pendientes,
        nombre_tecnico=nombre_tecnico,
    )


@bp.route('/otras')
@movil_required
def otras():
    nombre_tecnico = _nombre_tecnico(current_user)
    mis_ots, ots_pendientes = _queries_ot(nombre_tecnico, '__otras__')
    return render_template(
        'mobile/otras.html',
        mis_ots=mis_ots,
        ots_pendientes=ots_pendientes,
        nombre_tecnico=nombre_tecnico,
    )


@bp.route('/ot/<int:id>')
@movil_required
def ver_ot(id):
    ot = OrdenTrabajo.query.get_or_404(id)
    _enrich_ot(ot)

    nombre_tecnico = _nombre_tecnico(current_user)

    # ¿Hay trabajo en curso para este técnico en esta OT?
    trabajo_activo = RegistroTiempo.query.filter_by(
        ordenId=id, tecnico=nombre_tecnico, enCurso=True
    ).first()

    # Registros de tiempo
    registros_tiempo = RegistroTiempo.query.filter_by(ordenId=id).order_by(
        RegistroTiempo.inicio.desc()
    ).all()

    # Consumos
    consumos = ConsumoRecambio.query.filter_by(ordenId=id).all()

    # Tareas y checklist de la gama (solo preventivos con gama)
    tareas_gama = []
    tareas_realizadas_ids = set()
    checklist_items = []
    respuestas_map = {}
    if ot.tipo == 'preventivo' and ot.gama:
        tareas_gama = sorted(ot.gama.tareas, key=lambda t: t.orden)
        tareas_realizadas_ids = {
            tr.tareaId for tr in TareaRealizada.query.filter_by(ordenId=id).all()
        }
        checklist_items = sorted(ot.gama.checklistItems, key=lambda c: c.orden)
        for resp in ot.respuestasChecklist:
            respuestas_map[resp.checklistItemId] = resp

    # Histórico del equipo: todas las OTs cerradas del mismo equipo
    # Se busca por cualquiera de las dos formas en que puede estar guardado el equipo
    historico_equipo = []
    et = ot.equipoTipo or ('maquina' if ot.maquinaId else None)
    ei = ot.equipoId or ot.maquinaId
    if et and ei:
        condiciones = [
            and_(OrdenTrabajo.equipoTipo == et, OrdenTrabajo.equipoId == ei)
        ]
        # También incluir OTs legacy que usen maquinaId directamente
        maq_id = ot.maquinaId or (ei if et == 'maquina' else None)
        if maq_id:
            condiciones.append(OrdenTrabajo.maquinaId == maq_id)

        historico_equipo = OrdenTrabajo.query.filter(
            OrdenTrabajo.id != ot.id,
            OrdenTrabajo.estado == 'cerrada',
            or_(*condiciones),
        ).order_by(OrdenTrabajo.fechaFin.desc()).limit(15).all()

    return render_template(
        'mobile/ot_detail.html',
        ot=ot,
        nombre_tecnico=nombre_tecnico,
        trabajo_activo=trabajo_activo,
        registros_tiempo=registros_tiempo,
        consumos=consumos,
        tareas_gama=tareas_gama,
        tareas_realizadas_ids=tareas_realizadas_ids,
        checklist_items=checklist_items,
        respuestas_map=respuestas_map,
        historico_equipo=historico_equipo,
    )


@bp.route('/nueva')
@movil_required
def nueva_ot():
    # Plantas como dicts (JSON serializable para el template)
    plantas = [{'id': p.id, 'nombre': p.nombre, 'codigo': p.codigo}
               for p in Planta.query.order_by(Planta.nombre).all()]
    tecnicos = Tecnico.query.filter_by(activo=True).order_by(Tecnico.nombre).all()

    nombre_tecnico = _nombre_tecnico(current_user)

    # Pre-fill desde QR scan (query params opcionales)
    prefill_tipo = request.args.get('equipoTipo', '')
    prefill_id = request.args.get('equipoId', type=int, default=0)

    return render_template(
        'mobile/nueva_ot.html',
        plantas=plantas,
        tecnicos=tecnicos,
        nombre_tecnico=nombre_tecnico,
        prefill_tipo=prefill_tipo,
        prefill_id=prefill_id,
    )


# ---------------------------------------------------------------------------
# QR Scanner
# ---------------------------------------------------------------------------

@bp.route('/qr-scan')
@movil_required
def qr_scan():
    return render_template('mobile/qr_scan.html')


@bp.route('/qr/<equipo_tipo>/<int:equipo_id>')
@movil_required
def qr_result(equipo_tipo, equipo_id):
    """Resultado del escaneo QR: muestra OTs pendientes del activo y sus hijos."""
    TIPOS_VALIDOS = ('planta', 'zona', 'linea', 'maquina', 'elemento')
    if equipo_tipo not in TIPOS_VALIDOS:
        return render_template('mobile/qr_result.html',
                               activo_nombre='Tipo no válido', equipo_tipo=equipo_tipo,
                               equipo_id=equipo_id, ruta=[], ots=[], error=True), 404

    # Verificar que el activo existe
    MODEL_MAP = {'planta': Planta, 'zona': Zona, 'linea': Linea,
                 'maquina': Maquina, 'elemento': Elemento}
    activo = MODEL_MAP[equipo_tipo].query.get(equipo_id)
    if not activo:
        return render_template('mobile/qr_result.html',
                               activo_nombre='Activo no encontrado', equipo_tipo=equipo_tipo,
                               equipo_id=equipo_id, ruta=[], ots=[], error=True), 404

    ruta = _get_ruta_nombres(equipo_tipo, equipo_id)

    # Recoger todos los pares (tipo, id) del activo y sus hijos
    targets = _get_descendant_targets(equipo_tipo, equipo_id)

    # Construir condiciones de filtro
    condiciones = []
    for t_tipo, t_id in targets:
        condiciones.append(
            and_(OrdenTrabajo.equipoTipo == t_tipo, OrdenTrabajo.equipoId == t_id)
        )
        # Campo legacy maquinaId
        if t_tipo == 'maquina':
            condiciones.append(OrdenTrabajo.maquinaId == t_id)

    ots = []
    if condiciones:
        ots = OrdenTrabajo.query.filter(
            OrdenTrabajo.estado.in_(['pendiente', 'asignada', 'en_curso']),
            or_(*condiciones),
        ).order_by(OrdenTrabajo.fechaCreacion.desc()).all()
        for ot in ots:
            _enrich_ot(ot)

    return render_template('mobile/qr_result.html',
                           activo_nombre=activo.nombre, equipo_tipo=equipo_tipo,
                           equipo_id=equipo_id, ruta=ruta, ots=ots)


def _get_descendant_targets(equipo_tipo, equipo_id):
    """Retorna lista de tuplas (tipo, id) del activo y todos sus descendientes."""
    targets = [(equipo_tipo, equipo_id)]

    if equipo_tipo == 'elemento':
        return targets

    if equipo_tipo == 'maquina':
        for e in Elemento.query.filter_by(maquinaId=equipo_id):
            targets.append(('elemento', e.id))
        return targets

    if equipo_tipo == 'linea':
        for m in Maquina.query.filter_by(lineaId=equipo_id):
            targets.append(('maquina', m.id))
            for e in Elemento.query.filter_by(maquinaId=m.id):
                targets.append(('elemento', e.id))
        return targets

    if equipo_tipo == 'zona':
        for l in Linea.query.filter_by(zonaId=equipo_id):
            targets.append(('linea', l.id))
            for m in Maquina.query.filter_by(lineaId=l.id):
                targets.append(('maquina', m.id))
                for e in Elemento.query.filter_by(maquinaId=m.id):
                    targets.append(('elemento', e.id))
        return targets

    if equipo_tipo == 'planta':
        for z in Zona.query.filter_by(plantaId=equipo_id):
            targets.append(('zona', z.id))
            for l in Linea.query.filter_by(zonaId=z.id):
                targets.append(('linea', l.id))
                for m in Maquina.query.filter_by(lineaId=l.id):
                    targets.append(('maquina', m.id))
                    for e in Elemento.query.filter_by(maquinaId=m.id):
                        targets.append(('elemento', e.id))
        return targets

    return targets


# ---------------------------------------------------------------------------
# Mini API para la vista móvil
# ---------------------------------------------------------------------------

@bp.route('/api/qr-jerarquia')
@movil_required
def api_qr_jerarquia():
    """Devuelve la jerarquía completa de un equipo para pre-fill del formulario."""
    tipo = request.args.get('tipo', '')
    eid = request.args.get('id', type=int)
    if not tipo or not eid:
        return jsonify({'error': 'Parámetros requeridos'}), 400

    result = {'planta': None, 'zona': None, 'linea': None, 'maquina': None, 'elemento': None}

    if tipo == 'elemento':
        elem = Elemento.query.get(eid)
        if not elem:
            return jsonify({'error': 'No encontrado'}), 404
        result['elemento'] = {'id': elem.id, 'nombre': elem.nombre}
        maq = Maquina.query.get(elem.maquinaId)
        if maq:
            result['maquina'] = {'id': maq.id, 'nombre': maq.nombre}
            _fill_jerarquia_up(maq, result)

    elif tipo == 'maquina':
        maq = Maquina.query.get(eid)
        if not maq:
            return jsonify({'error': 'No encontrado'}), 404
        result['maquina'] = {'id': maq.id, 'nombre': maq.nombre}
        _fill_jerarquia_up(maq, result)

    elif tipo == 'linea':
        lin = Linea.query.get(eid)
        if not lin:
            return jsonify({'error': 'No encontrado'}), 404
        result['linea'] = {'id': lin.id, 'nombre': lin.nombre}
        zona = Zona.query.get(lin.zonaId)
        if zona:
            result['zona'] = {'id': zona.id, 'nombre': zona.nombre}
            planta = Planta.query.get(zona.plantaId)
            if planta:
                result['planta'] = {'id': planta.id, 'nombre': planta.nombre}

    elif tipo == 'zona':
        z = Zona.query.get(eid)
        if not z:
            return jsonify({'error': 'No encontrado'}), 404
        result['zona'] = {'id': z.id, 'nombre': z.nombre}
        planta = Planta.query.get(z.plantaId)
        if planta:
            result['planta'] = {'id': planta.id, 'nombre': planta.nombre}

    elif tipo == 'planta':
        p = Planta.query.get(eid)
        if not p:
            return jsonify({'error': 'No encontrado'}), 404
        result['planta'] = {'id': p.id, 'nombre': p.nombre}

    else:
        return jsonify({'error': 'Tipo no válido'}), 400

    return jsonify(result)


def _fill_jerarquia_up(maq, result):
    """Rellena la jerarquía hacia arriba desde una máquina."""
    lin = Linea.query.get(maq.lineaId)
    if lin:
        result['linea'] = {'id': lin.id, 'nombre': lin.nombre}
        zona = Zona.query.get(lin.zonaId)
        if zona:
            result['zona'] = {'id': zona.id, 'nombre': zona.nombre}
            planta = Planta.query.get(zona.plantaId)
            if planta:
                result['planta'] = {'id': planta.id, 'nombre': planta.nombre}


@bp.route('/api/recambios')
@movil_required
def api_recambios():
    """Lista de recambios con stock > 0 para el selector de consumos."""
    q = request.args.get('q', '').strip()
    query = Recambio.query.filter(Recambio.stockActual > 0)
    if q:
        query = query.filter(
            Recambio.nombre.ilike(f'%{q}%') | Recambio.codigo.ilike(f'%{q}%')
        )
    items = query.order_by(Recambio.nombre).limit(50).all()
    return jsonify([{
        'id': r.id,
        'codigo': r.codigo,
        'nombre': r.nombre,
        'stockActual': r.stockActual,
        'unidadMedida': r.unidadMedida,
        'precioUnitario': r.precioUnitario,
    } for r in items])


@bp.route('/api/equipos')
@movil_required
def api_equipos():
    """Equipos filtrados por nivel para los selectores en cascada."""
    nivel = request.args.get('nivel', 'maquina')
    parent_id = request.args.get('parent_id', type=int)

    if nivel == 'zona':
        q = Zona.query
        if parent_id:
            q = q.filter_by(plantaId=parent_id)
        items = q.order_by(Zona.nombre).all()

    elif nivel == 'linea':
        q = Linea.query
        if parent_id:
            q = q.filter_by(zonaId=parent_id)
        items = q.order_by(Linea.nombre).all()

    elif nivel == 'maquina':
        q = Maquina.query
        if parent_id:
            q = q.filter_by(lineaId=parent_id)
        items = q.order_by(Maquina.nombre).all()

    elif nivel == 'elemento':
        q = Elemento.query
        if parent_id:
            q = q.filter_by(maquinaId=parent_id)
        items = q.order_by(Elemento.nombre).all()

    else:
        items = []

    return jsonify([{'id': i.id, 'nombre': i.nombre, 'codigo': i.codigo} for i in items])


@bp.route('/api/ot/<int:orden_id>/tarea/<int:tarea_id>', methods=['POST', 'DELETE'])
@movil_required
def api_tarea_realizada(orden_id, tarea_id):
    """Marca (POST) o desmarca (DELETE) una tarea como realizada en una OT."""
    if request.method == 'POST':
        existente = TareaRealizada.query.filter_by(
            ordenId=orden_id, tareaId=tarea_id
        ).first()
        if not existente:
            tr = TareaRealizada(
                ordenId=orden_id,
                tareaId=tarea_id,
                tecnico=_nombre_tecnico(current_user),
            )
            db.session.add(tr)
            db.session.commit()
        return jsonify({'ok': True, 'realizada': True})
    else:  # DELETE
        TareaRealizada.query.filter_by(
            ordenId=orden_id, tareaId=tarea_id
        ).delete()
        db.session.commit()
        return jsonify({'ok': True, 'realizada': False})
