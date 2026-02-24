# Script para cargar datos de prueba en el GMAO
# Ejecutar con: python initData.py

from app import app, db
from models import (Empresa, Planta, Zona, Linea, Maquina, Elemento,
                    Recambio, PlanPreventivo, TareaPreventivo, OrdenTrabajo)
from datetime import date, datetime, timedelta

with app.app_context():
    print("Inicializando base de datos...")
    db.create_all()
    
    # =========================================
    # ESTRUCTURA JERÁRQUICA
    # =========================================
    
    # Empresa
    empresa = Empresa.query.filter_by(codigo='JGG').first()
    if not empresa:
        empresa = Empresa(
            codigo='JGG',
            nombre='JGG Industrial',
            descripcion='Empresa de producción industrial',
            direccion='Polígono Industrial, Nave 15',
            telefono='934 555 123',
            email='info@jggindustrial.com'
        )
        db.session.add(empresa)
        db.session.commit()
        print("✓ Empresa creada")
    
    # Planta
    planta = Planta.query.filter_by(codigo='P01', empresaId=empresa.id).first()
    if not planta:
        planta = Planta(
            empresaId=empresa.id,
            codigo='P01',
            nombre='Planta Principal',
            descripcion='Planta de producción principal',
            direccion='Nave Principal'
        )
        db.session.add(planta)
        db.session.commit()
        print("✓ Planta creada")
    
    # Zonas
    zonas_data = [
        {'codigo': 'PROD', 'nombre': 'Zona de Producción', 'descripcion': 'Área de fabricación'},
        {'codigo': 'ALM', 'nombre': 'Almacén', 'descripcion': 'Zona de almacenaje'},
        {'codigo': 'MANT', 'nombre': 'Taller Mantenimiento', 'descripcion': 'Taller de reparaciones'}
    ]
    
    zonas = {}
    for z_data in zonas_data:
        zona = Zona.query.filter_by(codigo=z_data['codigo'], plantaId=planta.id).first()
        if not zona:
            zona = Zona(plantaId=planta.id, **z_data)
            db.session.add(zona)
        zonas[z_data['codigo']] = zona
    db.session.commit()
    print("✓ Zonas creadas")
    
    # Líneas en zona de producción
    lineas_data = [
        {'codigo': 'L01', 'nombre': 'Línea 1 - Montaje', 'descripcion': 'Línea de montaje principal'},
        {'codigo': 'L02', 'nombre': 'Línea 2 - Envasado', 'descripcion': 'Línea de envasado y embalaje'},
        {'codigo': 'L03', 'nombre': 'Línea 3 - Control Calidad', 'descripcion': 'Línea de inspección'}
    ]
    
    lineas = {}
    for l_data in lineas_data:
        linea = Linea.query.filter_by(codigo=l_data['codigo'], zonaId=zonas['PROD'].id).first()
        if not linea:
            linea = Linea(zonaId=zonas['PROD'].id, **l_data)
            db.session.add(linea)
        lineas[l_data['codigo']] = linea
    db.session.commit()
    print("✓ Líneas creadas")
    
    # Máquinas
    maquinas_data = [
        {
            'codigo': 'ENS01', 'nombre': 'Ensambladora Principal',
            'modelo': 'ENS-2000', 'fabricante': 'MaquiTech',
            'numeroSerie': 'MT-2023-001', 'descripcion': 'Máquina ensambladora automática',
            'criticidad': 'alta', 'estado': 'operativo', 'lineaId': 'L01',
            'fechaInstalacion': date(2020, 3, 15)
        },
        {
            'codigo': 'SOL01', 'nombre': 'Soldadora Automática',
            'modelo': 'WELD-500', 'fabricante': 'WeldPro',
            'numeroSerie': 'WP-2021-045', 'descripcion': 'Soldadora por puntos automática',
            'criticidad': 'alta', 'estado': 'operativo', 'lineaId': 'L01',
            'fechaInstalacion': date(2021, 6, 20)
        },
        {
            'codigo': 'ENV01', 'nombre': 'Envasadora Flow-Pack',
            'modelo': 'FP-300', 'fabricante': 'PackSys',
            'numeroSerie': 'PS-2022-112', 'descripcion': 'Envasadora horizontal',
            'criticidad': 'media', 'estado': 'operativo', 'lineaId': 'L02',
            'fechaInstalacion': date(2022, 1, 10)
        },
        {
            'codigo': 'ETQ01', 'nombre': 'Etiquetadora',
            'modelo': 'LBL-100', 'fabricante': 'LabelTech',
            'numeroSerie': 'LT-2022-089', 'descripcion': 'Etiquetadora automática',
            'criticidad': 'baja', 'estado': 'operativo', 'lineaId': 'L02',
            'fechaInstalacion': date(2022, 2, 5)
        },
        {
            'codigo': 'INS01', 'nombre': 'Cámara de Inspección',
            'modelo': 'VIS-PRO', 'fabricante': 'VisionSys',
            'numeroSerie': 'VS-2023-034', 'descripcion': 'Sistema de visión artificial',
            'criticidad': 'media', 'estado': 'operativo', 'lineaId': 'L03',
            'fechaInstalacion': date(2023, 4, 12)
        },
        {
            'codigo': 'CMP01', 'nombre': 'Compresor Principal',
            'modelo': 'AIR-500', 'fabricante': 'AirTech',
            'numeroSerie': 'AT-2019-078', 'descripcion': 'Compresor de aire 500L',
            'criticidad': 'alta', 'estado': 'operativo', 'lineaId': 'L01',
            'fechaInstalacion': date(2019, 8, 1)
        }
    ]
    
    maquinas = {}
    for m_data in maquinas_data:
        linea_codigo = m_data.pop('lineaId')
        maquina = Maquina.query.filter_by(codigo=m_data['codigo'], lineaId=lineas[linea_codigo].id).first()
        if not maquina:
            maquina = Maquina(lineaId=lineas[linea_codigo].id, **m_data)
            db.session.add(maquina)
        maquinas[m_data['codigo']] = maquina
    db.session.commit()
    print("✓ Máquinas creadas")
    
    # Elementos de las máquinas
    elementos_data = [
        {'codigo': 'MOT01', 'nombre': 'Motor Principal', 'tipo': 'Motor', 'maquina': 'ENS01'},
        {'codigo': 'PLC01', 'nombre': 'PLC Control', 'tipo': 'Electrónico', 'maquina': 'ENS01'},
        {'codigo': 'CIN01', 'nombre': 'Cinta Transportadora', 'tipo': 'Mecánico', 'maquina': 'ENS01'},
        {'codigo': 'TRF01', 'nombre': 'Transformador', 'tipo': 'Eléctrico', 'maquina': 'SOL01'},
        {'codigo': 'ELE01', 'nombre': 'Electrodos', 'tipo': 'Consumible', 'maquina': 'SOL01'},
        {'codigo': 'BOM01', 'nombre': 'Bomba Vacío', 'tipo': 'Mecánico', 'maquina': 'ENV01'},
        {'codigo': 'RES01', 'nombre': 'Resistencias Sellado', 'tipo': 'Eléctrico', 'maquina': 'ENV01'},
        {'codigo': 'CAM01', 'nombre': 'Cámara HD', 'tipo': 'Electrónico', 'maquina': 'INS01'},
        {'codigo': 'FLT01', 'nombre': 'Filtro de Aire', 'tipo': 'Consumible', 'maquina': 'CMP01'},
        {'codigo': 'VLV01', 'nombre': 'Válvula Seguridad', 'tipo': 'Mecánico', 'maquina': 'CMP01'}
    ]
    
    for e_data in elementos_data:
        maquina_codigo = e_data.pop('maquina')
        if maquina_codigo in maquinas:
            elemento = Elemento.query.filter_by(codigo=e_data['codigo'], maquinaId=maquinas[maquina_codigo].id).first()
            if not elemento:
                elemento = Elemento(maquinaId=maquinas[maquina_codigo].id, **e_data)
                db.session.add(elemento)
    db.session.commit()
    print("✓ Elementos creados")
    
    # =========================================
    # RECAMBIOS
    # =========================================
    
    recambios_data = [
        {'codigo': 'REC-001', 'nombre': 'Rodamiento 6205', 'categoria': 'Mecánico', 
         'stockActual': 15, 'stockMinimo': 5, 'stockMaximo': 30, 'ubicacion': 'A1-01',
         'proveedor': 'SKF', 'precioUnitario': 12.50},
        {'codigo': 'REC-002', 'nombre': 'Correa dentada HTD5M', 'categoria': 'Mecánico',
         'stockActual': 8, 'stockMinimo': 3, 'stockMaximo': 20, 'ubicacion': 'A1-02',
         'proveedor': 'Gates', 'precioUnitario': 25.00},
        {'codigo': 'REC-003', 'nombre': 'Fusible 10A', 'categoria': 'Eléctrico',
         'stockActual': 50, 'stockMinimo': 20, 'stockMaximo': 100, 'ubicacion': 'B2-01',
         'proveedor': 'Schneider', 'precioUnitario': 1.20},
        {'codigo': 'REC-004', 'nombre': 'Electrodo soldadura', 'categoria': 'Consumible',
         'stockActual': 100, 'stockMinimo': 50, 'stockMaximo': 500, 'ubicacion': 'C1-01',
         'proveedor': 'Lincoln', 'precioUnitario': 0.80, 'unidadMedida': 'unidad'},
        {'codigo': 'REC-005', 'nombre': 'Filtro aire comprimido', 'categoria': 'Consumible',
         'stockActual': 3, 'stockMinimo': 5, 'stockMaximo': 15, 'ubicacion': 'A2-03',
         'proveedor': 'Atlas Copco', 'precioUnitario': 45.00},
        {'codigo': 'REC-006', 'nombre': 'Aceite hidráulico ISO46', 'categoria': 'Lubricante',
         'stockActual': 20, 'stockMinimo': 10, 'stockMaximo': 50, 'ubicacion': 'D1-01',
         'proveedor': 'Shell', 'precioUnitario': 8.50, 'unidadMedida': 'litro'},
        {'codigo': 'REC-007', 'nombre': 'Sensor inductivo M18', 'categoria': 'Electrónico',
         'stockActual': 6, 'stockMinimo': 4, 'stockMaximo': 15, 'ubicacion': 'B3-02',
         'proveedor': 'Sick', 'precioUnitario': 35.00},
        {'codigo': 'REC-008', 'nombre': 'Resistencia selladora 500W', 'categoria': 'Eléctrico',
         'stockActual': 2, 'stockMinimo': 4, 'stockMaximo': 10, 'ubicacion': 'B2-05',
         'proveedor': 'Watlow', 'precioUnitario': 28.00},
        {'codigo': 'REC-009', 'nombre': 'Junta tórica NBR 50x3', 'categoria': 'Mecánico',
         'stockActual': 25, 'stockMinimo': 10, 'stockMaximo': 50, 'ubicacion': 'A1-10',
         'proveedor': 'Freudenberg', 'precioUnitario': 2.50},
        {'codigo': 'REC-010', 'nombre': 'Contactor 25A', 'categoria': 'Eléctrico',
         'stockActual': 4, 'stockMinimo': 2, 'stockMaximo': 8, 'ubicacion': 'B2-03',
         'proveedor': 'Schneider', 'precioUnitario': 42.00}
    ]
    
    for r_data in recambios_data:
        recambio = Recambio.query.filter_by(codigo=r_data['codigo']).first()
        if not recambio:
            recambio = Recambio(**r_data)
            db.session.add(recambio)
    db.session.commit()
    print("✓ Recambios creados")
    
    # =========================================
    # PLANES DE MANTENIMIENTO PREVENTIVO
    # =========================================
    
    planes_data = [
        {
            'codigo': 'PREV-001', 'nombre': 'Revisión mensual ensambladora',
            'descripcion': 'Revisión general mensual de la ensambladora principal',
            'maquina': 'ENS01', 'frecuenciaTipo': 'dias', 'frecuenciaValor': 30,
            'tiempoEstimado': 120,
            'tareas': [
                'Verificar niveles de lubricación',
                'Inspeccionar estado de correas',
                'Comprobar tensión de cadenas',
                'Revisar conexiones eléctricas',
                'Limpiar filtros de aire'
            ]
        },
        {
            'codigo': 'PREV-002', 'nombre': 'Calibración soldadora',
            'descripcion': 'Calibración semanal de parámetros de soldadura',
            'maquina': 'SOL01', 'frecuenciaTipo': 'dias', 'frecuenciaValor': 7,
            'tiempoEstimado': 45,
            'tareas': [
                'Verificar presión de electrodos',
                'Calibrar tiempo de soldadura',
                'Comprobar corriente de soldadura',
                'Inspeccionar estado de electrodos'
            ]
        },
        {
            'codigo': 'PREV-003', 'nombre': 'Mantenimiento trimestral compresor',
            'descripcion': 'Mantenimiento completo del compresor cada 3 meses',
            'maquina': 'CMP01', 'frecuenciaTipo': 'meses', 'frecuenciaValor': 3,
            'tiempoEstimado': 180,
            'tareas': [
                'Cambiar filtro de aire',
                'Cambiar aceite',
                'Verificar válvula de seguridad',
                'Comprobar correas',
                'Purgar depósito',
                'Verificar juntas y conexiones'
            ]
        },
        {
            'codigo': 'PREV-004', 'nombre': 'Limpieza envasadora',
            'descripcion': 'Limpieza y ajuste semanal de envasadora',
            'maquina': 'ENV01', 'frecuenciaTipo': 'dias', 'frecuenciaValor': 7,
            'tiempoEstimado': 60,
            'tareas': [
                'Limpiar zona de sellado',
                'Verificar temperatura de sellado',
                'Comprobar bobina de film',
                'Ajustar guías de producto'
            ]
        }
    ]
    
    for p_data in planes_data:
        maquina_codigo = p_data.pop('maquina')
        tareas = p_data.pop('tareas')
        
        if maquina_codigo in maquinas:
            plan = PlanPreventivo.query.filter_by(codigo=p_data['codigo']).first()
            if not plan:
                maquina = maquinas[maquina_codigo]
                plan = PlanPreventivo(
                    equipoTipo='maquina',
                    equipoId=maquina.id,
                    maquinaId=maquina.id,  # Para compatibilidad
                    **p_data
                )
                plan.ultimaEjecucion = date.today() - timedelta(days=p_data['frecuenciaValor'] + 5)
                plan.calcularProximaEjecucion()
                db.session.add(plan)
                db.session.commit()
                
                # Añadir tareas
                for i, tarea in enumerate(tareas, 1):
                    t = TareaPreventivo(planId=plan.id, descripcion=tarea, orden=i)
                    db.session.add(t)
    
    db.session.commit()
    print("✓ Planes preventivos creados")
    
    # =========================================
    # ÓRDENES DE TRABAJO DE EJEMPLO
    # =========================================
    
    # Crear algunas OTs de ejemplo
    if OrdenTrabajo.query.count() == 0:
        ots_data = [
            {
                'tipo': 'correctivo', 'prioridad': 'alta', 'estado': 'pendiente',
                'titulo': 'Fallo en motor principal',
                'descripcionProblema': 'El motor hace ruido anormal y vibra excesivamente',
                'maquina': 'ENS01', 'tecnicoAsignado': 'Juan García'
            },
            {
                'tipo': 'correctivo', 'prioridad': 'urgente', 'estado': 'en_curso',
                'titulo': 'Fuga de aire en compresor',
                'descripcionProblema': 'Pérdida de presión por fuga en junta',
                'maquina': 'CMP01', 'tecnicoAsignado': 'Pedro López'
            },
            {
                'tipo': 'preventivo', 'prioridad': 'media', 'estado': 'cerrada',
                'titulo': 'Revisión mensual ensambladora',
                'descripcionProblema': 'Mantenimiento preventivo programado',
                'descripcionSolucion': 'Se realizó revisión completa. Cambio de correa y ajuste de tensores.',
                'maquina': 'ENS01', 'tecnicoAsignado': 'Juan García',
                'tiempoReal': 95
            }
        ]
        
        for ot_data in ots_data:
            maquina_codigo = ot_data.pop('maquina')
            if maquina_codigo in maquinas:
                maquina = maquinas[maquina_codigo]
                ot = OrdenTrabajo(
                    numero=OrdenTrabajo.generarNumero(),
                    equipoTipo='maquina',
                    equipoId=maquina.id,
                    maquinaId=maquina.id,  # Para compatibilidad
                    **ot_data
                )
                if ot.estado == 'en_curso':
                    ot.fechaInicio = datetime.now() - timedelta(hours=2)
                if ot.estado == 'cerrada':
                    ot.fechaFin = datetime.now() - timedelta(days=2)
                db.session.add(ot)
        
        db.session.commit()
        print("✓ Órdenes de trabajo creadas")

    
    print("\n" + "="*50)
    print("¡Datos de prueba cargados correctamente!")
    print("="*50)
    print(f"\nResumen:")
    print(f"  - Empresas: {Empresa.query.count()}")
    print(f"  - Plantas: {Planta.query.count()}")
    print(f"  - Zonas: {Zona.query.count()}")
    print(f"  - Líneas: {Linea.query.count()}")
    print(f"  - Máquinas: {Maquina.query.count()}")
    print(f"  - Elementos: {Elemento.query.count()}")
    print(f"  - Recambios: {Recambio.query.count()}")
    print(f"  - Planes Preventivos: {PlanPreventivo.query.count()}")
    print(f"  - Órdenes de Trabajo: {OrdenTrabajo.query.count()}")
    print(f"\nEjecuta 'python app.py' para iniciar el servidor.")