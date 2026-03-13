"""
Validación de filas parseadas antes de la importación.
Cada función devuelve dict {sheet_name: {'valid': [...], 'errors': [...], 'warnings': [...]}}.

Error/warning items: {'fila': N, 'campo': 'name', 'valor': val, 'motivo': 'reason'}
Las filas válidas incluyen _fila y _update (True si el código ya existe en la BD).
"""
from datetime import datetime, date

from models import (
    db, Empresa, Planta, Zona, Linea, Maquina, Elemento,
    Recambio, Tecnico, Usuario, GamaMantenimiento,
    OrdenTrabajo,
)


# =============================================================================
# HELPERS DE CONVERSIÓN
# =============================================================================

def _parse_date(val):
    """Convierte val a date. Acepta objetos date/datetime o strings DD/MM/AAAA."""
    if val is None or str(val).strip() == '':
        return None, None
    if isinstance(val, datetime):
        return val.date(), None
    if isinstance(val, date):
        return val, None
    s = str(val).strip()
    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(s, fmt).date(), None
        except ValueError:
            pass
    return None, f"Formato de fecha inválido: '{s}' (se espera DD/MM/AAAA)"


def _parse_datetime(val):
    """Convierte val a datetime. Acepta objetos datetime o strings DD/MM/AAAA HH:MM."""
    if val is None or str(val).strip() == '':
        return None, None
    if isinstance(val, datetime):
        return val, None
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day), None
    s = str(val).strip()
    for fmt in (
        '%d/%m/%Y %H:%M',
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%y %H:%M',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%d/%m/%Y',
        '%Y-%m-%d',
    ):
        try:
            return datetime.strptime(s, fmt), None
        except ValueError:
            pass
    return None, f"Formato de fecha/hora inválido: '{s}' (se espera DD/MM/AAAA HH:MM)"


def _parse_float(val):
    """Convierte val a float."""
    if val is None or str(val).strip() == '':
        return None, None
    try:
        # Acepta tanto punto como coma decimal
        return float(str(val).replace(',', '.')), None
    except (ValueError, TypeError):
        return None, f"Valor numérico inválido: '{val}'"


def _parse_int(val):
    """Convierte val a int."""
    if val is None or str(val).strip() == '':
        return None, None
    try:
        f = float(str(val).replace(',', '.'))
        return int(f), None
    except (ValueError, TypeError):
        return None, f"Valor entero inválido: '{val}'"


def _parse_bool(val):
    """Convierte SI/NO (y variantes) a True/False."""
    if val is None or str(val).strip() == '':
        return None, None
    s = str(val).strip().upper()
    if s in ('SI', 'SÍ', 'S', 'YES', 'Y', '1', 'TRUE', 'VERDADERO'):
        return True, None
    if s in ('NO', 'N', '0', 'FALSE', 'FALSO'):
        return False, None
    return None, f"Valor booleano inválido: '{val}' (se espera SI/NO)"


def _check_enum(val, allowed_list, campo):
    """Valida que val esté en allowed_list (insensible a mayúsculas)."""
    if val is None or str(val).strip() == '':
        return None, None
    s = str(val).strip().lower()
    for allowed in allowed_list:
        if s == allowed.lower():
            return allowed, None
    return None, f"Valor inválido para {campo}: '{val}' (permitidos: {', '.join(allowed_list)})"


def _make_error(fila, campo, valor, motivo):
    return {'fila': fila, 'campo': campo, 'valor': valor, 'motivo': motivo}


def _make_warning(fila, campo, valor, motivo):
    return {'fila': fila, 'campo': campo, 'valor': valor, 'motivo': motivo}


def _sheet_result():
    return {'valid': [], 'errors': [], 'warnings': []}


# =============================================================================
# VALIDACIÓN DE ACTIVOS
# =============================================================================

def validate_activos(data):
    """
    Valida datos de activos en el orden PLANTAS→ZONAS→LINEAS→MAQUINAS→ELEMENTOS.
    Acumula códigos válidos para usarlos como referencias FK en el siguiente nivel.
    """
    results = {}

    # --- PLANTAS ---
    sheet_name = 'PLANTAS'
    res = _sheet_result()
    # Pre-cargar empresas disponibles
    empresas_by_codigo = {e.codigo: e for e in Empresa.query.all()}
    plantas_existentes = {p.codigo: p for p in Planta.query.all()}
    valid_planta_codigos = set(plantas_existentes.keys())  # empezar con existentes

    for row in data.get(sheet_name, []):
        fila = row.get('_fila', '?')
        row_errors = []

        # codigo (obligatorio)
        codigo = str(row.get('codigo') or '').strip()
        if not codigo:
            row_errors.append(_make_error(fila, 'codigo', codigo, 'El código es obligatorio'))

        # nombre (obligatorio)
        nombre = str(row.get('nombre') or '').strip()
        if not nombre:
            row_errors.append(_make_error(fila, 'nombre', nombre, 'El nombre es obligatorio'))

        # empresa_codigo (obligatorio)
        empresa_codigo = str(row.get('empresa_codigo') or '').strip()
        if not empresa_codigo:
            row_errors.append(_make_error(fila, 'empresa_codigo', empresa_codigo, 'El código de empresa es obligatorio'))
        elif empresa_codigo not in empresas_by_codigo:
            row_errors.append(_make_error(fila, 'empresa_codigo', empresa_codigo,
                                          f"Empresa '{empresa_codigo}' no existe en la BD"))

        if row_errors:
            res['errors'].extend(row_errors)
            continue

        vrow = dict(row)
        vrow['_update'] = codigo in plantas_existentes
        vrow['_empresa'] = empresas_by_codigo.get(empresa_codigo)
        valid_planta_codigos.add(codigo)
        res['valid'].append(vrow)

    results[sheet_name] = res

    # --- ZONAS ---
    sheet_name = 'ZONAS'
    res = _sheet_result()
    zonas_existentes = {z.codigo: z for z in Zona.query.all()}
    valid_zona_codigos = set(zonas_existentes.keys())

    for row in data.get(sheet_name, []):
        fila = row.get('_fila', '?')
        row_errors = []

        codigo = str(row.get('codigo') or '').strip()
        if not codigo:
            row_errors.append(_make_error(fila, 'codigo', codigo, 'El código es obligatorio'))

        nombre = str(row.get('nombre') or '').strip()
        if not nombre:
            row_errors.append(_make_error(fila, 'nombre', nombre, 'El nombre es obligatorio'))

        planta_codigo = str(row.get('planta_codigo') or '').strip()
        if not planta_codigo:
            row_errors.append(_make_error(fila, 'planta_codigo', planta_codigo, 'El código de planta es obligatorio'))
        elif planta_codigo not in valid_planta_codigos:
            row_errors.append(_make_error(fila, 'planta_codigo', planta_codigo,
                                          f"Planta '{planta_codigo}' no existe en la BD ni en este fichero"))

        if row_errors:
            res['errors'].extend(row_errors)
            continue

        vrow = dict(row)
        vrow['_update'] = codigo in zonas_existentes
        valid_zona_codigos.add(codigo)
        res['valid'].append(vrow)

    results[sheet_name] = res

    # --- LINEAS ---
    sheet_name = 'LINEAS'
    res = _sheet_result()
    lineas_existentes = {l.codigo: l for l in Linea.query.all()}
    valid_linea_codigos = set(lineas_existentes.keys())

    for row in data.get(sheet_name, []):
        fila = row.get('_fila', '?')
        row_errors = []

        codigo = str(row.get('codigo') or '').strip()
        if not codigo:
            row_errors.append(_make_error(fila, 'codigo', codigo, 'El código es obligatorio'))

        nombre = str(row.get('nombre') or '').strip()
        if not nombre:
            row_errors.append(_make_error(fila, 'nombre', nombre, 'El nombre es obligatorio'))

        zona_codigo = str(row.get('zona_codigo') or '').strip()
        if not zona_codigo:
            row_errors.append(_make_error(fila, 'zona_codigo', zona_codigo, 'El código de zona es obligatorio'))
        elif zona_codigo not in valid_zona_codigos:
            row_errors.append(_make_error(fila, 'zona_codigo', zona_codigo,
                                          f"Zona '{zona_codigo}' no existe en la BD ni en este fichero"))

        if row_errors:
            res['errors'].extend(row_errors)
            continue

        vrow = dict(row)
        vrow['_update'] = codigo in lineas_existentes
        valid_linea_codigos.add(codigo)
        res['valid'].append(vrow)

    results[sheet_name] = res

    # --- MAQUINAS ---
    sheet_name = 'MAQUINAS'
    res = _sheet_result()
    maquinas_existentes = {m.codigo: m for m in Maquina.query.all()}
    valid_maquina_codigos = set(maquinas_existentes.keys())

    for row in data.get(sheet_name, []):
        fila = row.get('_fila', '?')
        row_errors = []
        row_warnings = []

        codigo = str(row.get('codigo') or '').strip()
        if not codigo:
            row_errors.append(_make_error(fila, 'codigo', codigo, 'El código es obligatorio'))

        nombre = str(row.get('nombre') or '').strip()
        if not nombre:
            row_errors.append(_make_error(fila, 'nombre', nombre, 'El nombre es obligatorio'))

        linea_codigo = str(row.get('linea_codigo') or '').strip()
        if not linea_codigo:
            row_errors.append(_make_error(fila, 'linea_codigo', linea_codigo, 'El código de línea es obligatorio'))
        elif linea_codigo not in valid_linea_codigos:
            row_errors.append(_make_error(fila, 'linea_codigo', linea_codigo,
                                          f"Línea '{linea_codigo}' no existe en la BD ni en este fichero"))

        # criticidad
        criticidad_val = row.get('criticidad')
        criticidad, err = _check_enum(criticidad_val, ['alta', 'media', 'baja'], 'criticidad')
        if err:
            row_warnings.append(_make_warning(fila, 'criticidad', criticidad_val, err + ' — se usará "media"'))
            criticidad = 'media'
        elif criticidad is None:
            criticidad = 'media'

        # estado
        estado_val = row.get('estado')
        estado, err = _check_enum(estado_val, ['operativo', 'averiado', 'mantenimiento'], 'estado')
        if err:
            row_warnings.append(_make_warning(fila, 'estado', estado_val, err + ' — se usará "operativo"'))
            estado = 'operativo'
        elif estado is None:
            estado = 'operativo'

        # fecha_instalacion (opcional)
        fecha_inst, err = _parse_date(row.get('fecha_instalacion'))
        if err:
            row_warnings.append(_make_warning(fila, 'fecha_instalacion', row.get('fecha_instalacion'), err))

        # horas_operacion (opcional)
        horas_op_val = row.get('horas_operacion')
        horas_op, err = _parse_int(horas_op_val)
        if err:
            row_warnings.append(_make_warning(fila, 'horas_operacion', horas_op_val, err))

        # rav (opcional)
        rav_val = row.get('rav')
        rav, err = _parse_float(rav_val)
        if err:
            row_warnings.append(_make_warning(fila, 'rav', rav_val, err))

        if row_errors:
            res['errors'].extend(row_errors)
            res['warnings'].extend(row_warnings)
            continue

        vrow = dict(row)
        vrow['_update'] = codigo in maquinas_existentes
        vrow['_criticidad'] = criticidad
        vrow['_estado'] = estado
        vrow['_fecha_instalacion'] = fecha_inst
        vrow['_horas_operacion'] = horas_op or 0
        vrow['_rav'] = rav or 0.0
        valid_maquina_codigos.add(codigo)
        res['valid'].append(vrow)
        res['warnings'].extend(row_warnings)

    results[sheet_name] = res

    # --- ELEMENTOS ---
    sheet_name = 'ELEMENTOS'
    res = _sheet_result()
    elementos_existentes = {e.codigo: e for e in Elemento.query.all()}

    for row in data.get(sheet_name, []):
        fila = row.get('_fila', '?')
        row_errors = []
        row_warnings = []

        codigo = str(row.get('codigo') or '').strip()
        if not codigo:
            row_errors.append(_make_error(fila, 'codigo', codigo, 'El código es obligatorio'))

        nombre = str(row.get('nombre') or '').strip()
        if not nombre:
            row_errors.append(_make_error(fila, 'nombre', nombre, 'El nombre es obligatorio'))

        maquina_codigo = str(row.get('maquina_codigo') or '').strip()
        if not maquina_codigo:
            row_errors.append(_make_error(fila, 'maquina_codigo', maquina_codigo, 'El código de máquina es obligatorio'))
        elif maquina_codigo not in valid_maquina_codigos:
            row_errors.append(_make_error(fila, 'maquina_codigo', maquina_codigo,
                                          f"Máquina '{maquina_codigo}' no existe en la BD ni en este fichero"))

        # rav (opcional)
        rav_val = row.get('rav')
        rav, err = _parse_float(rav_val)
        if err:
            row_warnings.append(_make_warning(fila, 'rav', rav_val, err))

        if row_errors:
            res['errors'].extend(row_errors)
            res['warnings'].extend(row_warnings)
            continue

        vrow = dict(row)
        vrow['_update'] = codigo in elementos_existentes
        vrow['_rav'] = rav or 0.0
        res['valid'].append(vrow)
        res['warnings'].extend(row_warnings)

    results[sheet_name] = res

    return results


# =============================================================================
# VALIDACIÓN DE GAMAS
# =============================================================================

def validate_gamas(data):
    results = {}

    # --- GAMAS ---
    sheet_name = 'GAMAS'
    res = _sheet_result()
    gamas_existentes = {g.codigo: g for g in GamaMantenimiento.query.all()}
    valid_gama_codigos = set(gamas_existentes.keys())

    TIPOS_GAMA = ['preventivo', 'tecnico_legal', 'calibracion', 'predictivo', 'conductivo']

    for row in data.get(sheet_name, []):
        fila = row.get('_fila', '?')
        row_errors = []
        row_warnings = []

        codigo = str(row.get('codigo') or '').strip()
        if not codigo:
            row_errors.append(_make_error(fila, 'codigo', codigo, 'El código es obligatorio'))

        nombre = str(row.get('nombre') or '').strip()
        if not nombre:
            row_errors.append(_make_error(fila, 'nombre', nombre, 'El nombre es obligatorio'))

        tipo_val = row.get('tipo')
        tipo, err = _check_enum(tipo_val, TIPOS_GAMA, 'tipo')
        if err:
            row_warnings.append(_make_warning(fila, 'tipo', tipo_val, err + ' — se usará "preventivo"'))
            tipo = 'preventivo'
        elif tipo is None:
            tipo = 'preventivo'

        tiempo_val = row.get('tiempo_estimado')
        tiempo, err = _parse_int(tiempo_val)
        if err:
            row_warnings.append(_make_warning(fila, 'tiempo_estimado', tiempo_val, err))

        activo_val = row.get('activo')
        activo, err = _parse_bool(activo_val)
        if err:
            row_warnings.append(_make_warning(fila, 'activo', activo_val, err + ' — se usará True'))
        if activo is None:
            activo = True

        if row_errors:
            res['errors'].extend(row_errors)
            res['warnings'].extend(row_warnings)
            continue

        vrow = dict(row)
        vrow['_update'] = codigo in gamas_existentes
        vrow['_tipo'] = tipo
        vrow['_tiempo_estimado'] = tiempo
        vrow['_activo'] = activo
        valid_gama_codigos.add(codigo)
        res['valid'].append(vrow)
        res['warnings'].extend(row_warnings)

    results[sheet_name] = res

    # --- TAREAS ---
    sheet_name = 'TAREAS'
    res = _sheet_result()

    for row in data.get(sheet_name, []):
        fila = row.get('_fila', '?')
        row_errors = []
        row_warnings = []

        gama_codigo = str(row.get('gama_codigo') or '').strip()
        if not gama_codigo:
            row_errors.append(_make_error(fila, 'gama_codigo', gama_codigo, 'El código de gama es obligatorio'))
        elif gama_codigo not in valid_gama_codigos:
            row_errors.append(_make_error(fila, 'gama_codigo', gama_codigo,
                                          f"Gama '{gama_codigo}' no existe en la BD ni en este fichero"))

        descripcion = str(row.get('descripcion') or '').strip()
        if not descripcion:
            row_errors.append(_make_error(fila, 'descripcion', descripcion, 'La descripción es obligatoria'))

        orden_val = row.get('orden')
        orden, err = _parse_int(orden_val)
        if err:
            row_warnings.append(_make_warning(fila, 'orden', orden_val, err))
        if orden is None:
            orden = 1

        duracion_val = row.get('duracion_estimada')
        duracion, err = _parse_int(duracion_val)
        if err:
            row_warnings.append(_make_warning(fila, 'duracion_estimada', duracion_val, err))

        if row_errors:
            res['errors'].extend(row_errors)
            res['warnings'].extend(row_warnings)
            continue

        vrow = dict(row)
        vrow['_update'] = False  # Se determinará en el importer por gamaId+orden
        vrow['_orden'] = orden
        vrow['_duracion'] = duracion
        res['valid'].append(vrow)
        res['warnings'].extend(row_warnings)

    results[sheet_name] = res

    # --- CHECKLIST ---
    sheet_name = 'CHECKLIST'
    res = _sheet_result()

    # Normalizar tipoRespuesta: si_no/seleccion → ok_nok/texto
    TIPO_RESP_MAP = {
        'ok_nok': 'ok_nok',
        'si_no': 'ok_nok',
        'valor': 'valor',
        'texto': 'texto',
        'seleccion': 'texto',
        'selección': 'texto',
    }

    for row in data.get(sheet_name, []):
        fila = row.get('_fila', '?')
        row_errors = []
        row_warnings = []

        gama_codigo = str(row.get('gama_codigo') or '').strip()
        if not gama_codigo:
            row_errors.append(_make_error(fila, 'gama_codigo', gama_codigo, 'El código de gama es obligatorio'))
        elif gama_codigo not in valid_gama_codigos:
            row_errors.append(_make_error(fila, 'gama_codigo', gama_codigo,
                                          f"Gama '{gama_codigo}' no existe en la BD ni en este fichero"))

        descripcion = str(row.get('descripcion') or '').strip()
        if not descripcion:
            row_errors.append(_make_error(fila, 'descripcion', descripcion, 'La descripción es obligatoria'))

        orden_val = row.get('orden')
        orden, err = _parse_int(orden_val)
        if err:
            row_warnings.append(_make_warning(fila, 'orden', orden_val, err))
        if orden is None:
            orden = 1

        tipo_resp_val = str(row.get('tipo_respuesta') or '').strip().lower()
        tipo_resp = TIPO_RESP_MAP.get(tipo_resp_val, 'ok_nok')
        if tipo_resp_val and tipo_resp_val not in TIPO_RESP_MAP:
            row_warnings.append(_make_warning(fila, 'tipo_respuesta', tipo_resp_val,
                                              f"Valor desconocido, se usará 'ok_nok'"))

        genera_val = row.get('genera_correctivo')
        genera, err = _parse_bool(genera_val)
        if err:
            row_warnings.append(_make_warning(fila, 'genera_correctivo', genera_val, err + ' — se usará True'))
        if genera is None:
            genera = True

        if row_errors:
            res['errors'].extend(row_errors)
            res['warnings'].extend(row_warnings)
            continue

        vrow = dict(row)
        vrow['_update'] = False
        vrow['_orden'] = orden
        vrow['_tipo_respuesta'] = tipo_resp
        vrow['_genera_correctivo'] = genera
        res['valid'].append(vrow)
        res['warnings'].extend(row_warnings)

    results[sheet_name] = res

    # --- RECAMBIOS (de gama) ---
    sheet_name = 'RECAMBIOS'
    res = _sheet_result()
    recambios_existentes = {r.codigo: r for r in Recambio.query.all()}

    for row in data.get(sheet_name, []):
        fila = row.get('_fila', '?')
        row_errors = []
        row_warnings = []

        gama_codigo = str(row.get('gama_codigo') or '').strip()
        if not gama_codigo:
            row_errors.append(_make_error(fila, 'gama_codigo', gama_codigo, 'El código de gama es obligatorio'))
        elif gama_codigo not in valid_gama_codigos:
            row_errors.append(_make_error(fila, 'gama_codigo', gama_codigo,
                                          f"Gama '{gama_codigo}' no existe en la BD ni en este fichero"))

        recambio_codigo = str(row.get('recambio_codigo') or '').strip()
        if not recambio_codigo:
            row_errors.append(_make_error(fila, 'recambio_codigo', recambio_codigo, 'El código de recambio es obligatorio'))
        elif recambio_codigo not in recambios_existentes:
            row_errors.append(_make_error(fila, 'recambio_codigo', recambio_codigo,
                                          f"Recambio '{recambio_codigo}' no existe en la BD"))

        cantidad_val = row.get('cantidad')
        cantidad, err = _parse_float(cantidad_val)
        if err:
            row_warnings.append(_make_warning(fila, 'cantidad', cantidad_val, err))
        if cantidad is None:
            cantidad = 1.0

        if row_errors:
            res['errors'].extend(row_errors)
            res['warnings'].extend(row_warnings)
            continue

        vrow = dict(row)
        vrow['_update'] = False
        vrow['_cantidad'] = cantidad
        res['valid'].append(vrow)
        res['warnings'].extend(row_warnings)

    results[sheet_name] = res

    return results


# =============================================================================
# VALIDACIÓN DE HISTÓRICO DE OTs
# =============================================================================

def validate_historico(data):
    results = {}
    sheet_name = 'ORDENES'
    res = _sheet_result()

    ots_existentes = {ot.numero: ot for ot in OrdenTrabajo.query.all()}

    TIPOS_OT = ['correctivo', 'preventivo', 'tecnico_legal', 'calibracion', 'predictivo']
    PRIORIDADES = ['urgente', 'alta', 'media', 'baja']
    ESTADOS = ['pendiente', 'asignada', 'en_curso', 'cerrada', 'cancelada', 'abierta']
    ESTADOS_MAP = {
        'pendiente': 'pendiente',
        'asignada': 'asignada',
        'en_curso': 'en_curso',
        'cerrada': 'cerrada',
        'cancelada': 'cancelada',
        'abierta': 'pendiente',  # normalizar
    }
    EQUIPO_TIPOS = ['empresa', 'planta', 'zona', 'linea', 'maquina', 'elemento']

    for row in data.get(sheet_name, []):
        fila = row.get('_fila', '?')
        row_errors = []
        row_warnings = []

        numero = str(row.get('numero') or '').strip()
        if not numero:
            row_errors.append(_make_error(fila, 'numero', numero, 'El número de OT es obligatorio'))

        titulo = str(row.get('titulo') or '').strip()
        if not titulo:
            row_errors.append(_make_error(fila, 'titulo', titulo, 'El título es obligatorio'))

        tipo_val = row.get('tipo')
        tipo, err = _check_enum(tipo_val, TIPOS_OT, 'tipo')
        if err:
            row_errors.append(_make_error(fila, 'tipo', tipo_val, err))

        equipo_tipo_val = row.get('equipo_tipo')
        equipo_tipo, err = _check_enum(equipo_tipo_val, EQUIPO_TIPOS, 'equipo_tipo')
        if err:
            row_errors.append(_make_error(fila, 'equipo_tipo', equipo_tipo_val, err))

        equipo_id_val = row.get('equipo_id')
        equipo_id, err = _parse_int(equipo_id_val)
        if err:
            row_errors.append(_make_error(fila, 'equipo_id', equipo_id_val, err))
        elif equipo_id is None and equipo_tipo is not None:
            row_errors.append(_make_error(fila, 'equipo_id', equipo_id_val, 'equipo_id es obligatorio cuando se indica equipo_tipo'))

        prioridad_val = row.get('prioridad')
        prioridad, err = _check_enum(prioridad_val, PRIORIDADES, 'prioridad')
        if err:
            row_warnings.append(_make_warning(fila, 'prioridad', prioridad_val, err + ' — se usará "media"'))
            prioridad = 'media'
        elif prioridad is None:
            prioridad = 'media'

        estado_val = str(row.get('estado') or '').strip().lower()
        estado = ESTADOS_MAP.get(estado_val)
        if estado is None:
            if estado_val:
                row_warnings.append(_make_warning(fila, 'estado', estado_val,
                                                  f"Estado desconocido, se usará 'pendiente'"))
            estado = 'pendiente'

        fecha_creacion_val = row.get('fecha_creacion')
        fecha_creacion, err = _parse_datetime(fecha_creacion_val)
        if err:
            row_warnings.append(_make_warning(fila, 'fecha_creacion', fecha_creacion_val, err))
        if fecha_creacion is None:
            from datetime import datetime as dt
            fecha_creacion = dt.now()

        fecha_programada_val = row.get('fecha_programada')
        fecha_programada, err = _parse_datetime(fecha_programada_val)
        if err:
            row_warnings.append(_make_warning(fila, 'fecha_programada', fecha_programada_val, err))

        fecha_inicio_val = row.get('fecha_inicio')
        fecha_inicio, err = _parse_datetime(fecha_inicio_val)
        if err:
            row_warnings.append(_make_warning(fila, 'fecha_inicio', fecha_inicio_val, err))

        fecha_fin_val = row.get('fecha_fin')
        fecha_fin, err = _parse_datetime(fecha_fin_val)
        if err:
            row_warnings.append(_make_warning(fila, 'fecha_fin', fecha_fin_val, err))

        tiempo_parada_val = row.get('tiempo_parada')
        tiempo_parada, err = _parse_float(tiempo_parada_val)
        if err:
            row_warnings.append(_make_warning(fila, 'tiempo_parada', tiempo_parada_val, err))

        if row_errors:
            res['errors'].extend(row_errors)
            res['warnings'].extend(row_warnings)
            continue

        vrow = dict(row)
        vrow['_update'] = numero in ots_existentes
        vrow['_tipo'] = tipo
        vrow['_prioridad'] = prioridad
        vrow['_estado'] = estado
        vrow['_equipo_tipo'] = equipo_tipo
        vrow['_equipo_id'] = equipo_id
        vrow['_fecha_creacion'] = fecha_creacion
        vrow['_fecha_programada'] = fecha_programada
        vrow['_fecha_inicio'] = fecha_inicio
        vrow['_fecha_fin'] = fecha_fin
        vrow['_tiempo_parada'] = tiempo_parada
        res['valid'].append(vrow)
        res['warnings'].extend(row_warnings)

    results[sheet_name] = res
    return results


# =============================================================================
# VALIDACIÓN DE RECAMBIOS
# =============================================================================

def validate_recambios(data):
    results = {}
    sheet_name = 'RECAMBIOS'
    res = _sheet_result()

    recambios_existentes = {r.codigo: r for r in Recambio.query.all()}

    for row in data.get(sheet_name, []):
        fila = row.get('_fila', '?')
        row_errors = []
        row_warnings = []

        codigo = str(row.get('codigo') or '').strip()
        if not codigo:
            row_errors.append(_make_error(fila, 'codigo', codigo, 'El código es obligatorio'))

        nombre = str(row.get('nombre') or '').strip()
        if not nombre:
            row_errors.append(_make_error(fila, 'nombre', nombre, 'El nombre es obligatorio'))

        stock_actual_val = row.get('stock_actual')
        stock_actual, err = _parse_float(stock_actual_val)
        if err:
            row_warnings.append(_make_warning(fila, 'stock_actual', stock_actual_val, err))

        stock_minimo_val = row.get('stock_minimo')
        stock_minimo, err = _parse_float(stock_minimo_val)
        if err:
            row_warnings.append(_make_warning(fila, 'stock_minimo', stock_minimo_val, err))

        stock_maximo_val = row.get('stock_maximo')
        stock_maximo, err = _parse_float(stock_maximo_val)
        if err:
            row_warnings.append(_make_warning(fila, 'stock_maximo', stock_maximo_val, err))

        precio_val = row.get('precio_unitario')
        precio, err = _parse_float(precio_val)
        if err:
            row_warnings.append(_make_warning(fila, 'precio_unitario', precio_val, err))

        activo_val = row.get('activo')
        activo, err = _parse_bool(activo_val)
        if err:
            row_warnings.append(_make_warning(fila, 'activo', activo_val, err + ' — se usará True'))
        if activo is None:
            activo = True

        fecha_alta_val = row.get('fecha_alta')
        fecha_alta, err = _parse_date(fecha_alta_val)
        if err:
            row_warnings.append(_make_warning(fila, 'fecha_alta', fecha_alta_val, err))

        if row_errors:
            res['errors'].extend(row_errors)
            res['warnings'].extend(row_warnings)
            continue

        vrow = dict(row)
        vrow['_update'] = codigo in recambios_existentes
        vrow['_stock_actual'] = stock_actual if stock_actual is not None else 0.0
        vrow['_stock_minimo'] = stock_minimo if stock_minimo is not None else 0.0
        vrow['_stock_maximo'] = stock_maximo if stock_maximo is not None else 100.0
        vrow['_precio_unitario'] = precio if precio is not None else 0.0
        vrow['_activo'] = activo
        vrow['_fecha_alta'] = fecha_alta
        res['valid'].append(vrow)
        res['warnings'].extend(row_warnings)

    results[sheet_name] = res
    return results


# =============================================================================
# VALIDACIÓN DE TÉCNICOS
# =============================================================================

def validate_tecnicos(data):
    results = {}
    sheet_name = 'TECNICOS'
    res = _sheet_result()

    # Para upsert: clave = nombre+apellidos
    tecnicos_existentes = {
        (t.nombre.strip().lower(), (t.apellidos or '').strip().lower()): t
        for t in Tecnico.query.all()
    }

    for row in data.get(sheet_name, []):
        fila = row.get('_fila', '?')
        row_errors = []
        row_warnings = []

        nombre = str(row.get('nombre') or '').strip()
        if not nombre:
            row_errors.append(_make_error(fila, 'nombre', nombre, 'El nombre es obligatorio'))

        apellidos = str(row.get('apellidos') or '').strip()

        tipo_val = row.get('tipo_tecnico')
        tipo_tecnico, err = _check_enum(tipo_val, ['interno', 'externo'], 'tipo_tecnico')
        if err:
            row_warnings.append(_make_warning(fila, 'tipo_tecnico', tipo_val, err + ' — se usará "interno"'))
            tipo_tecnico = 'interno'
        elif tipo_tecnico is None:
            tipo_tecnico = 'interno'

        activo_val = row.get('activo')
        activo, err = _parse_bool(activo_val)
        if err:
            row_warnings.append(_make_warning(fila, 'activo', activo_val, err + ' — se usará True'))
        if activo is None:
            activo = True

        coste_val = row.get('coste_hora')
        coste, err = _parse_float(coste_val)
        if err:
            row_warnings.append(_make_warning(fila, 'coste_hora', coste_val, err))

        if row_errors:
            res['errors'].extend(row_errors)
            res['warnings'].extend(row_warnings)
            continue

        clave = (nombre.lower(), apellidos.lower())
        vrow = dict(row)
        vrow['_update'] = clave in tecnicos_existentes
        vrow['_tipo_tecnico'] = tipo_tecnico
        vrow['_activo'] = activo
        vrow['_coste_hora'] = coste
        res['valid'].append(vrow)
        res['warnings'].extend(row_warnings)

    results[sheet_name] = res
    return results


# =============================================================================
# VALIDACIÓN DE USUARIOS
# =============================================================================

def validate_usuarios(data):
    results = {}
    sheet_name = 'USUARIOS'
    res = _sheet_result()

    usuarios_existentes = {u.username: u for u in Usuario.query.all()}

    NIVELES = ['tecnico', 'responsable', 'admin']

    for row in data.get(sheet_name, []):
        fila = row.get('_fila', '?')
        row_errors = []
        row_warnings = []

        username = str(row.get('username') or '').strip()
        if not username:
            row_errors.append(_make_error(fila, 'username', username, 'El username es obligatorio'))

        nombre = str(row.get('nombre') or '').strip()
        if not nombre:
            row_errors.append(_make_error(fila, 'nombre', nombre, 'El nombre es obligatorio'))

        # Password solo obligatorio para nuevos usuarios
        password = str(row.get('password') or '').strip()
        is_update = username in usuarios_existentes
        if not is_update and not password:
            row_errors.append(_make_error(fila, 'password', '', 'La contraseña es obligatoria para nuevos usuarios'))

        nivel_val = row.get('nivel')
        nivel, err = _check_enum(nivel_val, NIVELES, 'nivel')
        if err:
            row_warnings.append(_make_warning(fila, 'nivel', nivel_val, err + ' — se usará "tecnico"'))
            nivel = 'tecnico'
        elif nivel is None:
            nivel = 'tecnico'

        activo_val = row.get('activo')
        activo, err = _parse_bool(activo_val)
        if err:
            row_warnings.append(_make_warning(fila, 'activo', activo_val, err + ' — se usará True'))
        if activo is None:
            activo = True

        if row_errors:
            res['errors'].extend(row_errors)
            res['warnings'].extend(row_warnings)
            continue

        vrow = dict(row)
        vrow['_update'] = is_update
        vrow['_nivel'] = nivel
        vrow['_activo'] = activo
        vrow['_password'] = password
        res['valid'].append(vrow)
        res['warnings'].extend(row_warnings)

    results[sheet_name] = res
    return results
