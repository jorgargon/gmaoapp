"""
Importador: upsert de datos validados en la BD.
Cada función recibe el dict validado (con clave 'valid' por hoja) y retorna
{sheet_name: {'insertadas': N, 'actualizadas': N, 'errores': N}}.
"""
import logging
from datetime import date, datetime

from models import (
    db, Empresa, Planta, Zona, Linea, Maquina, Elemento,
    Recambio, Tecnico, Usuario, GamaMantenimiento, TareaGama,
    ChecklistItem, RecambioGama, OrdenTrabajo,
)

log = logging.getLogger('importacion')


def _sheet_stats():
    return {'insertadas': 0, 'actualizadas': 0, 'errores': 0}


# =============================================================================
# IMPORTAR ACTIVOS
# =============================================================================

def import_activos(validated):
    results = {}

    # --- PLANTAS ---
    sheet_name = 'PLANTAS'
    stats = _sheet_stats()
    rows = validated.get(sheet_name, {}).get('valid', [])

    # Cachés
    empresas_cache = {e.codigo: e for e in Empresa.query.all()}
    plantas_cache = {p.codigo: p for p in Planta.query.all()}

    try:
        for row in rows:
            try:
                codigo = str(row.get('codigo') or '').strip()
                empresa = row.get('_empresa') or empresas_cache.get(
                    str(row.get('empresa_codigo') or '').strip()
                )
                if empresa is None:
                    stats['errores'] += 1
                    continue

                if row.get('_update') and codigo in plantas_cache:
                    p = plantas_cache[codigo]
                    p.nombre = str(row.get('nombre') or '').strip()
                    p.descripcion = str(row.get('descripcion') or '') or None
                    p.direccion = str(row.get('direccion') or '') or None
                    stats['actualizadas'] += 1
                else:
                    p = Planta(
                        empresaId=empresa.id,
                        codigo=codigo,
                        nombre=str(row.get('nombre') or '').strip(),
                        descripcion=str(row.get('descripcion') or '') or None,
                        direccion=str(row.get('direccion') or '') or None,
                    )
                    db.session.add(p)
                    db.session.flush()
                    plantas_cache[codigo] = p
                    stats['insertadas'] += 1
            except Exception as e:
                log.warning(f"Error en fila {row.get('_fila')} de PLANTAS: {e}")
                stats['errores'] += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Error crítico importando PLANTAS: {e}")
        stats['errores'] += len(rows)
        stats['insertadas'] = 0
        stats['actualizadas'] = 0

    results[sheet_name] = stats

    # --- ZONAS ---
    sheet_name = 'ZONAS'
    stats = _sheet_stats()
    rows = validated.get(sheet_name, {}).get('valid', [])
    zonas_cache = {z.codigo: z for z in Zona.query.all()}
    # Refrescar plantas
    plantas_cache = {p.codigo: p for p in Planta.query.all()}

    try:
        for row in rows:
            try:
                codigo = str(row.get('codigo') or '').strip()
                planta_codigo = str(row.get('planta_codigo') or '').strip()
                planta = plantas_cache.get(planta_codigo)
                if planta is None:
                    stats['errores'] += 1
                    continue

                if row.get('_update') and codigo in zonas_cache:
                    z = zonas_cache[codigo]
                    z.nombre = str(row.get('nombre') or '').strip()
                    z.descripcion = str(row.get('descripcion') or '') or None
                    stats['actualizadas'] += 1
                else:
                    z = Zona(
                        plantaId=planta.id,
                        codigo=codigo,
                        nombre=str(row.get('nombre') or '').strip(),
                        descripcion=str(row.get('descripcion') or '') or None,
                    )
                    db.session.add(z)
                    db.session.flush()
                    zonas_cache[codigo] = z
                    stats['insertadas'] += 1
            except Exception as e:
                log.warning(f"Error en fila {row.get('_fila')} de ZONAS: {e}")
                stats['errores'] += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Error crítico importando ZONAS: {e}")
        stats['errores'] += len(rows)
        stats['insertadas'] = 0
        stats['actualizadas'] = 0

    results[sheet_name] = stats

    # --- LINEAS ---
    sheet_name = 'LINEAS'
    stats = _sheet_stats()
    rows = validated.get(sheet_name, {}).get('valid', [])
    lineas_cache = {l.codigo: l for l in Linea.query.all()}
    zonas_cache = {z.codigo: z for z in Zona.query.all()}

    try:
        for row in rows:
            try:
                codigo = str(row.get('codigo') or '').strip()
                zona_codigo = str(row.get('zona_codigo') or '').strip()
                zona = zonas_cache.get(zona_codigo)
                if zona is None:
                    stats['errores'] += 1
                    continue

                if row.get('_update') and codigo in lineas_cache:
                    l = lineas_cache[codigo]
                    l.nombre = str(row.get('nombre') or '').strip()
                    l.descripcion = str(row.get('descripcion') or '') or None
                    stats['actualizadas'] += 1
                else:
                    l = Linea(
                        zonaId=zona.id,
                        codigo=codigo,
                        nombre=str(row.get('nombre') or '').strip(),
                        descripcion=str(row.get('descripcion') or '') or None,
                    )
                    db.session.add(l)
                    db.session.flush()
                    lineas_cache[codigo] = l
                    stats['insertadas'] += 1
            except Exception as e:
                log.warning(f"Error en fila {row.get('_fila')} de LINEAS: {e}")
                stats['errores'] += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Error crítico importando LINEAS: {e}")
        stats['errores'] += len(rows)
        stats['insertadas'] = 0
        stats['actualizadas'] = 0

    results[sheet_name] = stats

    # --- MAQUINAS ---
    sheet_name = 'MAQUINAS'
    stats = _sheet_stats()
    rows = validated.get(sheet_name, {}).get('valid', [])
    maquinas_cache = {m.codigo: m for m in Maquina.query.all()}
    lineas_cache = {l.codigo: l for l in Linea.query.all()}

    try:
        for row in rows:
            try:
                codigo = str(row.get('codigo') or '').strip()
                linea_codigo = str(row.get('linea_codigo') or '').strip()
                linea = lineas_cache.get(linea_codigo)
                if linea is None:
                    stats['errores'] += 1
                    continue

                fecha_inst = row.get('_fecha_instalacion')
                # Si viene como string en el row original
                if fecha_inst is None:
                    from blueprints.importacion.validator import _parse_date
                    fecha_inst, _ = _parse_date(row.get('fecha_instalacion'))

                if row.get('_update') and codigo in maquinas_cache:
                    m = maquinas_cache[codigo]
                    m.nombre = str(row.get('nombre') or '').strip()
                    m.modelo = str(row.get('modelo') or '') or None
                    m.fabricante = str(row.get('fabricante') or '') or None
                    m.numeroSerie = str(row.get('numero_serie') or '') or None
                    m.descripcion = str(row.get('descripcion') or '') or None
                    m.criticidad = row.get('_criticidad', 'media')
                    m.estado = row.get('_estado', 'operativo')
                    if fecha_inst is not None:
                        m.fechaInstalacion = fecha_inst
                    horas = row.get('_horas_operacion')
                    if horas is not None:
                        m.horasOperacion = horas
                    rav = row.get('_rav')
                    if rav is not None:
                        m.rav = rav
                    stats['actualizadas'] += 1
                else:
                    m = Maquina(
                        lineaId=linea.id,
                        codigo=codigo,
                        nombre=str(row.get('nombre') or '').strip(),
                        modelo=str(row.get('modelo') or '') or None,
                        fabricante=str(row.get('fabricante') or '') or None,
                        numeroSerie=str(row.get('numero_serie') or '') or None,
                        descripcion=str(row.get('descripcion') or '') or None,
                        fechaInstalacion=fecha_inst,
                        criticidad=row.get('_criticidad', 'media'),
                        estado=row.get('_estado', 'operativo'),
                        horasOperacion=row.get('_horas_operacion') or 0,
                        rav=row.get('_rav') or 0.0,
                    )
                    db.session.add(m)
                    db.session.flush()
                    maquinas_cache[codigo] = m
                    stats['insertadas'] += 1
            except Exception as e:
                log.warning(f"Error en fila {row.get('_fila')} de MAQUINAS: {e}")
                stats['errores'] += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Error crítico importando MAQUINAS: {e}")
        stats['errores'] += len(rows)
        stats['insertadas'] = 0
        stats['actualizadas'] = 0

    results[sheet_name] = stats

    # --- ELEMENTOS ---
    sheet_name = 'ELEMENTOS'
    stats = _sheet_stats()
    rows = validated.get(sheet_name, {}).get('valid', [])
    elementos_cache = {e.codigo: e for e in Elemento.query.all()}
    maquinas_cache = {m.codigo: m for m in Maquina.query.all()}

    try:
        for row in rows:
            try:
                codigo = str(row.get('codigo') or '').strip()
                maquina_codigo = str(row.get('maquina_codigo') or '').strip()
                maquina = maquinas_cache.get(maquina_codigo)
                if maquina is None:
                    stats['errores'] += 1
                    continue

                if row.get('_update') and codigo in elementos_cache:
                    e = elementos_cache[codigo]
                    e.nombre = str(row.get('nombre') or '').strip()
                    e.tipo = str(row.get('tipo') or '') or None
                    e.descripcion = str(row.get('descripcion') or '') or None
                    e.fabricante = str(row.get('fabricante') or '') or None
                    e.modelo = str(row.get('modelo') or '') or None
                    e.numeroSerie = str(row.get('numero_serie') or '') or None
                    rav = row.get('_rav')
                    if rav is not None:
                        e.rav = rav
                    stats['actualizadas'] += 1
                else:
                    e = Elemento(
                        maquinaId=maquina.id,
                        codigo=codigo,
                        nombre=str(row.get('nombre') or '').strip(),
                        tipo=str(row.get('tipo') or '') or None,
                        descripcion=str(row.get('descripcion') or '') or None,
                        fabricante=str(row.get('fabricante') or '') or None,
                        modelo=str(row.get('modelo') or '') or None,
                        numeroSerie=str(row.get('numero_serie') or '') or None,
                        rav=row.get('_rav') or 0.0,
                    )
                    db.session.add(e)
                    db.session.flush()
                    elementos_cache[codigo] = e
                    stats['insertadas'] += 1
            except Exception as e:
                log.warning(f"Error en fila {row.get('_fila')} de ELEMENTOS: {e}")
                stats['errores'] += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Error crítico importando ELEMENTOS: {e}")
        stats['errores'] += len(rows)
        stats['insertadas'] = 0
        stats['actualizadas'] = 0

    results[sheet_name] = stats
    return results


# =============================================================================
# IMPORTAR GAMAS
# =============================================================================

def import_gamas(validated):
    results = {}

    # --- GAMAS ---
    sheet_name = 'GAMAS'
    stats = _sheet_stats()
    rows = validated.get(sheet_name, {}).get('valid', [])
    gamas_cache = {g.codigo: g for g in GamaMantenimiento.query.all()}

    try:
        for row in rows:
            try:
                codigo = str(row.get('codigo') or '').strip()
                if row.get('_update') and codigo in gamas_cache:
                    g = gamas_cache[codigo]
                    g.nombre = str(row.get('nombre') or '').strip()
                    g.descripcion = str(row.get('descripcion') or '') or None
                    g.tipo = row.get('_tipo', 'preventivo')
                    g.tiempoEstimado = row.get('_tiempo_estimado')
                    g.activo = row.get('_activo', True)
                    stats['actualizadas'] += 1
                else:
                    g = GamaMantenimiento(
                        codigo=codigo,
                        nombre=str(row.get('nombre') or '').strip(),
                        descripcion=str(row.get('descripcion') or '') or None,
                        tipo=row.get('_tipo', 'preventivo'),
                        tiempoEstimado=row.get('_tiempo_estimado'),
                        activo=row.get('_activo', True),
                        fechaCreacion=date.today(),
                    )
                    db.session.add(g)
                    db.session.flush()
                    gamas_cache[codigo] = g
                    stats['insertadas'] += 1
            except Exception as e:
                log.warning(f"Error en fila {row.get('_fila')} de GAMAS: {e}")
                stats['errores'] += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Error crítico importando GAMAS: {e}")
        stats['errores'] += len(rows)
        stats['insertadas'] = 0
        stats['actualizadas'] = 0

    results[sheet_name] = stats

    # Refrescar caché tras commit
    gamas_cache = {g.codigo: g for g in GamaMantenimiento.query.all()}

    # --- TAREAS ---
    sheet_name = 'TAREAS'
    stats = _sheet_stats()
    rows = validated.get(sheet_name, {}).get('valid', [])

    # Caché de tareas existentes indexada por (gamaId, orden)
    tareas_cache = {
        (t.gamaId, t.orden): t
        for t in TareaGama.query.all()
    }

    try:
        for row in rows:
            try:
                gama_codigo = str(row.get('gama_codigo') or '').strip()
                gama = gamas_cache.get(gama_codigo)
                if gama is None:
                    stats['errores'] += 1
                    continue

                orden = row.get('_orden', 1)
                key = (gama.id, orden)

                if key in tareas_cache:
                    t = tareas_cache[key]
                    t.descripcion = str(row.get('descripcion') or '').strip()
                    t.duracionEstimada = row.get('_duracion')
                    t.herramientas = str(row.get('herramientas') or '') or None
                    t.instrucciones = str(row.get('instrucciones') or '') or None
                    stats['actualizadas'] += 1
                else:
                    t = TareaGama(
                        gamaId=gama.id,
                        descripcion=str(row.get('descripcion') or '').strip(),
                        orden=orden,
                        duracionEstimada=row.get('_duracion'),
                        herramientas=str(row.get('herramientas') or '') or None,
                        instrucciones=str(row.get('instrucciones') or '') or None,
                    )
                    db.session.add(t)
                    db.session.flush()
                    tareas_cache[key] = t
                    stats['insertadas'] += 1
            except Exception as e:
                log.warning(f"Error en fila {row.get('_fila')} de TAREAS: {e}")
                stats['errores'] += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Error crítico importando TAREAS: {e}")
        stats['errores'] += len(rows)
        stats['insertadas'] = 0
        stats['actualizadas'] = 0

    results[sheet_name] = stats

    # --- CHECKLIST ---
    sheet_name = 'CHECKLIST'
    stats = _sheet_stats()
    rows = validated.get(sheet_name, {}).get('valid', [])

    checklist_cache = {
        (c.gamaId, c.orden): c
        for c in ChecklistItem.query.all()
    }

    try:
        for row in rows:
            try:
                gama_codigo = str(row.get('gama_codigo') or '').strip()
                gama = gamas_cache.get(gama_codigo)
                if gama is None:
                    stats['errores'] += 1
                    continue

                orden = row.get('_orden', 1)
                key = (gama.id, orden)

                if key in checklist_cache:
                    c = checklist_cache[key]
                    c.descripcion = str(row.get('descripcion') or '').strip()
                    c.tipoRespuesta = row.get('_tipo_respuesta', 'ok_nok')
                    c.unidad = str(row.get('unidad') or '') or None
                    c.generaCorrectivo = row.get('_genera_correctivo', True)
                    stats['actualizadas'] += 1
                else:
                    c = ChecklistItem(
                        gamaId=gama.id,
                        descripcion=str(row.get('descripcion') or '').strip(),
                        orden=orden,
                        tipoRespuesta=row.get('_tipo_respuesta', 'ok_nok'),
                        unidad=str(row.get('unidad') or '') or None,
                        generaCorrectivo=row.get('_genera_correctivo', True),
                    )
                    db.session.add(c)
                    db.session.flush()
                    checklist_cache[key] = c
                    stats['insertadas'] += 1
            except Exception as e:
                log.warning(f"Error en fila {row.get('_fila')} de CHECKLIST: {e}")
                stats['errores'] += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Error crítico importando CHECKLIST: {e}")
        stats['errores'] += len(rows)
        stats['insertadas'] = 0
        stats['actualizadas'] = 0

    results[sheet_name] = stats

    # --- RECAMBIOS DE GAMA ---
    sheet_name = 'RECAMBIOS'
    stats = _sheet_stats()
    rows = validated.get(sheet_name, {}).get('valid', [])

    recambios_cache = {r.codigo: r for r in Recambio.query.all()}
    recambio_gama_cache = {
        (rg.gamaId, rg.recambioId): rg
        for rg in RecambioGama.query.all()
    }

    try:
        for row in rows:
            try:
                gama_codigo = str(row.get('gama_codigo') or '').strip()
                gama = gamas_cache.get(gama_codigo)
                recambio_codigo = str(row.get('recambio_codigo') or '').strip()
                recambio = recambios_cache.get(recambio_codigo)

                if gama is None or recambio is None:
                    stats['errores'] += 1
                    continue

                key = (gama.id, recambio.id)
                if key in recambio_gama_cache:
                    rg = recambio_gama_cache[key]
                    rg.cantidad = row.get('_cantidad', 1.0)
                    rg.observaciones = str(row.get('observaciones') or '') or None
                    stats['actualizadas'] += 1
                else:
                    rg = RecambioGama(
                        gamaId=gama.id,
                        recambioId=recambio.id,
                        cantidad=row.get('_cantidad', 1.0),
                        observaciones=str(row.get('observaciones') or '') or None,
                    )
                    db.session.add(rg)
                    db.session.flush()
                    recambio_gama_cache[key] = rg
                    stats['insertadas'] += 1
            except Exception as e:
                log.warning(f"Error en fila {row.get('_fila')} de RECAMBIOS (gama): {e}")
                stats['errores'] += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Error crítico importando RECAMBIOS de gama: {e}")
        stats['errores'] += len(rows)
        stats['insertadas'] = 0
        stats['actualizadas'] = 0

    results[sheet_name] = stats
    return results


# =============================================================================
# IMPORTAR HISTÓRICO OTs
# =============================================================================

def import_historico(validated):
    results = {}
    sheet_name = 'ORDENES'
    stats = _sheet_stats()
    rows = validated.get(sheet_name, {}).get('valid', [])

    ots_cache = {ot.numero: ot for ot in OrdenTrabajo.query.all()}

    try:
        for row in rows:
            try:
                numero = str(row.get('numero') or '').strip()
                equipo_tipo = row.get('_equipo_tipo') or str(row.get('equipo_tipo') or '').strip()
                equipo_id = row.get('_equipo_id')

                if not equipo_tipo or equipo_id is None:
                    stats['errores'] += 1
                    continue

                if row.get('_update') and numero in ots_cache:
                    ot = ots_cache[numero]
                    ot.titulo = str(row.get('titulo') or '').strip()
                    ot.tipo = row.get('_tipo', 'correctivo')
                    ot.prioridad = row.get('_prioridad', 'media')
                    ot.estado = row.get('_estado', 'pendiente')
                    ot.equipoTipo = equipo_tipo
                    ot.equipoId = equipo_id
                    ot.descripcionProblema = str(row.get('descripcion_problema') or '') or None
                    ot.descripcionSolucion = str(row.get('descripcion_solucion') or '') or None
                    ot.observaciones = str(row.get('observaciones') or '') or None
                    ot.tecnicoAsignado = str(row.get('tecnico_asignado') or '') or None
                    fecha_creacion = row.get('_fecha_creacion')
                    if fecha_creacion:
                        ot.fechaCreacion = fecha_creacion
                    ot.fechaProgramada = row.get('_fecha_programada')
                    ot.fechaInicio = row.get('_fecha_inicio')
                    ot.fechaFin = row.get('_fecha_fin')
                    ot.tiempoParada = row.get('_tiempo_parada')
                    stats['actualizadas'] += 1
                else:
                    ot = OrdenTrabajo(
                        numero=numero,
                        titulo=str(row.get('titulo') or '').strip(),
                        tipo=row.get('_tipo', 'correctivo'),
                        prioridad=row.get('_prioridad', 'media'),
                        estado=row.get('_estado', 'pendiente'),
                        equipoTipo=equipo_tipo,
                        equipoId=equipo_id,
                        descripcionProblema=str(row.get('descripcion_problema') or '') or None,
                        descripcionSolucion=str(row.get('descripcion_solucion') or '') or None,
                        observaciones=str(row.get('observaciones') or '') or None,
                        tecnicoAsignado=str(row.get('tecnico_asignado') or '') or None,
                        fechaCreacion=row.get('_fecha_creacion') or datetime.now(),
                        fechaProgramada=row.get('_fecha_programada'),
                        fechaInicio=row.get('_fecha_inicio'),
                        fechaFin=row.get('_fecha_fin'),
                        tiempoParada=row.get('_tiempo_parada'),
                    )
                    db.session.add(ot)
                    db.session.flush()
                    ots_cache[numero] = ot
                    stats['insertadas'] += 1
            except Exception as e:
                log.warning(f"Error en fila {row.get('_fila')} de ORDENES: {e}")
                stats['errores'] += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Error crítico importando ORDENES: {e}")
        stats['errores'] += len(rows)
        stats['insertadas'] = 0
        stats['actualizadas'] = 0

    results[sheet_name] = stats
    return results


# =============================================================================
# IMPORTAR RECAMBIOS
# =============================================================================

def import_recambios(validated):
    results = {}
    sheet_name = 'RECAMBIOS'
    stats = _sheet_stats()
    rows = validated.get(sheet_name, {}).get('valid', [])

    recambios_cache = {r.codigo: r for r in Recambio.query.all()}

    try:
        for row in rows:
            try:
                codigo = str(row.get('codigo') or '').strip()
                if row.get('_update') and codigo in recambios_cache:
                    r = recambios_cache[codigo]
                    r.nombre = str(row.get('nombre') or '').strip()
                    r.descripcion = str(row.get('descripcion') or '') or None
                    r.categoria = str(row.get('categoria') or '') or None
                    r.stockActual = row.get('_stock_actual', 0.0)
                    r.stockMinimo = row.get('_stock_minimo', 0.0)
                    r.stockMaximo = row.get('_stock_maximo', 100.0)
                    r.ubicacion = str(row.get('ubicacion') or '') or None
                    r.proveedor = str(row.get('proveedor') or '') or None
                    r.codigoProveedor = str(row.get('codigo_proveedor') or '') or None
                    r.precioUnitario = row.get('_precio_unitario', 0.0)
                    r.unidadMedida = str(row.get('unidad_medida') or 'unidad') or 'unidad'
                    r.activo = row.get('_activo', True)
                    if row.get('_fecha_alta'):
                        r.fechaAlta = row['_fecha_alta']
                    stats['actualizadas'] += 1
                else:
                    r = Recambio(
                        codigo=codigo,
                        nombre=str(row.get('nombre') or '').strip(),
                        descripcion=str(row.get('descripcion') or '') or None,
                        categoria=str(row.get('categoria') or '') or None,
                        stockActual=row.get('_stock_actual', 0.0),
                        stockMinimo=row.get('_stock_minimo', 0.0),
                        stockMaximo=row.get('_stock_maximo', 100.0),
                        ubicacion=str(row.get('ubicacion') or '') or None,
                        proveedor=str(row.get('proveedor') or '') or None,
                        codigoProveedor=str(row.get('codigo_proveedor') or '') or None,
                        precioUnitario=row.get('_precio_unitario', 0.0),
                        unidadMedida=str(row.get('unidad_medida') or 'unidad') or 'unidad',
                        fechaAlta=row.get('_fecha_alta') or date.today(),
                        activo=row.get('_activo', True),
                    )
                    db.session.add(r)
                    db.session.flush()
                    recambios_cache[codigo] = r
                    stats['insertadas'] += 1
            except Exception as e:
                log.warning(f"Error en fila {row.get('_fila')} de RECAMBIOS: {e}")
                stats['errores'] += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Error crítico importando RECAMBIOS: {e}")
        stats['errores'] += len(rows)
        stats['insertadas'] = 0
        stats['actualizadas'] = 0

    results[sheet_name] = stats
    return results


# =============================================================================
# IMPORTAR TÉCNICOS
# =============================================================================

def import_tecnicos(validated):
    results = {}
    sheet_name = 'TECNICOS'
    stats = _sheet_stats()
    rows = validated.get(sheet_name, {}).get('valid', [])

    # Caché indexada por (nombre_lower, apellidos_lower)
    tecnicos_cache = {
        (t.nombre.strip().lower(), (t.apellidos or '').strip().lower()): t
        for t in Tecnico.query.all()
    }

    try:
        for row in rows:
            try:
                nombre = str(row.get('nombre') or '').strip()
                apellidos = str(row.get('apellidos') or '').strip()
                key = (nombre.lower(), apellidos.lower())

                if row.get('_update') and key in tecnicos_cache:
                    t = tecnicos_cache[key]
                    t.especialidad = str(row.get('especialidad') or '') or None
                    t.telefono = str(row.get('telefono') or '') or None
                    t.tipo_tecnico = row.get('_tipo_tecnico', 'interno')
                    t.activo = row.get('_activo', True)
                    coste = row.get('_coste_hora')
                    if coste is not None:
                        t.costeHora = coste
                    stats['actualizadas'] += 1
                else:
                    t = Tecnico(
                        nombre=nombre,
                        apellidos=apellidos or None,
                        especialidad=str(row.get('especialidad') or '') or None,
                        telefono=str(row.get('telefono') or '') or None,
                        tipo_tecnico=row.get('_tipo_tecnico', 'interno'),
                        activo=row.get('_activo', True),
                        costeHora=row.get('_coste_hora'),
                    )
                    db.session.add(t)
                    db.session.flush()
                    tecnicos_cache[key] = t
                    stats['insertadas'] += 1
            except Exception as e:
                log.warning(f"Error en fila {row.get('_fila')} de TECNICOS: {e}")
                stats['errores'] += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Error crítico importando TECNICOS: {e}")
        stats['errores'] += len(rows)
        stats['insertadas'] = 0
        stats['actualizadas'] = 0

    results[sheet_name] = stats
    return results


# =============================================================================
# IMPORTAR USUARIOS
# =============================================================================

def import_usuarios(validated):
    results = {}
    sheet_name = 'USUARIOS'
    stats = _sheet_stats()
    rows = validated.get(sheet_name, {}).get('valid', [])

    usuarios_cache = {u.username: u for u in Usuario.query.all()}

    try:
        for row in rows:
            try:
                username = str(row.get('username') or '').strip()
                password = row.get('_password', '')

                if row.get('_update') and username in usuarios_cache:
                    u = usuarios_cache[username]
                    u.nombre = str(row.get('nombre') or '').strip()
                    u.apellidos = str(row.get('apellidos') or '') or None
                    u.nivel = row.get('_nivel', 'tecnico')
                    u.activo = row.get('_activo', True)
                    if password:
                        u.set_password(password)
                    stats['actualizadas'] += 1
                else:
                    u = Usuario(
                        username=username,
                        nombre=str(row.get('nombre') or '').strip(),
                        apellidos=str(row.get('apellidos') or '') or None,
                        nivel=row.get('_nivel', 'tecnico'),
                        activo=row.get('_activo', True),
                        fechaAlta=datetime.now(),
                    )
                    if password:
                        u.set_password(password)
                    else:
                        u.set_password('changeme')  # Contraseña temporal
                    db.session.add(u)
                    db.session.flush()
                    usuarios_cache[username] = u
                    stats['insertadas'] += 1
            except Exception as e:
                log.warning(f"Error en fila {row.get('_fila')} de USUARIOS: {e}")
                stats['errores'] += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Error crítico importando USUARIOS: {e}")
        stats['errores'] += len(rows)
        stats['insertadas'] = 0
        stats['actualizadas'] = 0

    results[sheet_name] = stats
    return results
