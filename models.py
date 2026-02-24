# Definición de los modelos de datos para la aplicación GMAO usando SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import hashlib

db = SQLAlchemy()

# =============================================================================
# MODELO DE JERARQUÍA DE ACTIVOS
# =============================================================================

# Modelo para representar una Empresa (nivel superior de jerarquía)
class Empresa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    direccion = db.Column(db.String(200))
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100))
    plantas = db.relationship('Planta', backref='empresa', lazy=True, cascade='all, delete-orphan')

# Modelo para representar una Planta, dependiente de una Empresa
class Planta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empresaId = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    codigo = db.Column(db.String(10), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    direccion = db.Column(db.String(200))
    zonas = db.relationship('Zona', backref='planta', lazy=True, cascade='all, delete-orphan')

# Modelo para representar una Zona dentro de una Planta
class Zona(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plantaId = db.Column(db.Integer, db.ForeignKey('planta.id'), nullable=False)
    codigo = db.Column(db.String(10), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    lineas = db.relationship('Linea', backref='zona', lazy=True, cascade='all, delete-orphan')

# Modelo para representar una Línea dentro de una Zona
class Linea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zonaId = db.Column(db.Integer, db.ForeignKey('zona.id'), nullable=False)
    codigo = db.Column(db.String(10), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    maquinas = db.relationship('Maquina', backref='linea', lazy=True, cascade='all, delete-orphan')

# Modelo para representar una Máquina dentro de una Línea
class Maquina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lineaId = db.Column(db.Integer, db.ForeignKey('linea.id'), nullable=False)
    codigo = db.Column(db.String(10), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(50))
    fabricante = db.Column(db.String(50))
    numeroSerie = db.Column(db.String(50))
    descripcion = db.Column(db.Text)
    fechaInstalacion = db.Column(db.Date)
    criticidad = db.Column(db.String(20), default='media')  # alta, media, baja
    estado = db.Column(db.String(20), default='operativo')  # operativo, averiado, mantenimiento
    horasOperacion = db.Column(db.Integer, default=0)  # Contador de horas
    rav = db.Column(db.Float, default=0.0)             # Valor de reposición (RAV)
    elementos = db.relationship('Elemento', backref='maquina', lazy=True, cascade='all, delete-orphan')
    ordenesTrabajo = db.relationship('OrdenTrabajo', backref='maquina', lazy=True)
    planesPreventivos = db.relationship('PlanPreventivo', backref='maquina', lazy=True)
    recambiosAsociados = db.relationship('RecambioEquipo', backref='maquina', lazy=True)

# Modelo para representar un Elemento dentro de una Máquina
class Elemento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    maquinaId = db.Column(db.Integer, db.ForeignKey('maquina.id'), nullable=False)
    codigo = db.Column(db.String(10), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50))
    descripcion = db.Column(db.Text)
    fabricante = db.Column(db.String(50))
    modelo = db.Column(db.String(50))
    numeroSerie = db.Column(db.String(50))
    rav = db.Column(db.Float, default=0.0)             # Valor de reposición (RAV)

# =============================================================================
# MODELO DE RECAMBIOS Y STOCK
# =============================================================================

class Recambio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    categoria = db.Column(db.String(50))
    stockActual = db.Column(db.Float, default=0.0)
    stockMinimo = db.Column(db.Float, default=0.0)
    stockMaximo = db.Column(db.Float, default=100.0)
    ubicacion = db.Column(db.String(100))
    proveedor = db.Column(db.String(100))
    codigoProveedor = db.Column(db.String(50))
    precioUnitario = db.Column(db.Float, default=0)
    unidadMedida = db.Column(db.String(20), default='unidad')
    fechaAlta = db.Column(db.Date, default=date.today)
    activo = db.Column(db.Boolean, default=True)
    
    movimientos = db.relationship('MovimientoStock', backref='recambio', lazy=True)
    equiposAsociados = db.relationship('RecambioEquipo', backref='recambio', lazy=True)
    consumos = db.relationship('ConsumoRecambio', backref='recambio', lazy=True)
    
    @property
    def stockBajo(self):
        return self.stockActual <= self.stockMinimo

# Relación M:N entre Recambios y Máquinas
class RecambioEquipo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recambioId = db.Column(db.Integer, db.ForeignKey('recambio.id'), nullable=False)
    maquinaId = db.Column(db.Integer, db.ForeignKey('maquina.id'), nullable=False)
    cantidadRecomendada = db.Column(db.Float, default=1.0)
    notas = db.Column(db.Text)

# Historial de movimientos de stock
class MovimientoStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recambioId = db.Column(db.Integer, db.ForeignKey('recambio.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # entrada, salida, ajuste
    subTipo = db.Column(db.String(50))  # compra, devolucion_sin_uso, ajuste_inventario, consumo_ot, etc.
    cantidad = db.Column(db.Float, nullable=False)
    stockAnterior = db.Column(db.Float)
    stockPosterior = db.Column(db.Float)
    fecha = db.Column(db.DateTime, default=datetime.now)
    motivo = db.Column(db.String(200))
    documentoRef = db.Column(db.String(50))  # Nº albarán, OT, etc.
    usuario = db.Column(db.String(100))

# =============================================================================
# TIPOS DE INTERVENCIÓN CONFIGURABLES
# =============================================================================

class TipoIntervencion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), unique=True, nullable=False)  # ej: "correctivo", "preventivo"
    nombre = db.Column(db.String(100), nullable=False)  # Nombre para mostrar
    descripcion = db.Column(db.String(255))
    icono = db.Column(db.String(50), nullable=False)  # Clase FontAwesome, ej: "fa-wrench"
    color = db.Column(db.String(20), default='#1976d2')  # Color para etiquetas
    activo = db.Column(db.Boolean, default=True)
    orden = db.Column(db.Integer, default=0)  # Para ordenar en listados
    fechaCreacion = db.Column(db.DateTime, default=datetime.now)

# =============================================================================
# MODELO DE ÓRDENES DE TRABAJO
# =============================================================================

class OrdenTrabajo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # correctivo, preventivo
    prioridad = db.Column(db.String(20), default='media')  # urgente, alta, media, baja
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, asignada, en_curso, cerrada, cancelada
    
    # Fechas
    fechaCreacion = db.Column(db.DateTime, default=datetime.now)
    fechaProgramada = db.Column(db.DateTime)
    fechaInicio = db.Column(db.DateTime)
    fechaFin = db.Column(db.DateTime)
    
    # Descripciones
    titulo = db.Column(db.String(200), nullable=False)
    descripcionProblema = db.Column(db.Text)
    descripcionSolucion = db.Column(db.Text)
    observaciones = db.Column(db.Text)
    
    # Relaciones - Equipo puede ser cualquier nivel de la jerarquía
    equipoTipo = db.Column(db.String(20), nullable=False)  # empresa, planta, zona, linea, maquina, elemento
    equipoId = db.Column(db.Integer, nullable=False)
    
    # Campo legacy para compatibilidad (deprecated, usar equipoTipo/equipoId)
    maquinaId = db.Column(db.Integer, db.ForeignKey('maquina.id'), nullable=True)
    elementoId = db.Column(db.Integer, db.ForeignKey('elemento.id'))
    
    # Referencias a mantenimiento preventivo
    planPreventivoId = db.Column(db.Integer, db.ForeignKey('plan_preventivo.id'))  # LEGACY - Deprecado
    asignacionGamaId = db.Column(db.Integer, db.ForeignKey('asignacion_gama.id'))  # LEGACY - Deprecado

    # Preventivo autocontenido: gama + frecuencia directamente en la OT
    gamaId          = db.Column(db.Integer, db.ForeignKey('gama_mantenimiento.id'), nullable=True)
    frecuenciaTipo  = db.Column(db.String(20))   # 'dias' | 'semanas' | 'meses'
    frecuenciaValor = db.Column(db.Integer)       # número entero

    gama = db.relationship('GamaMantenimiento', foreign_keys=[gamaId])

    
    # Trabajo realizado
    tecnicoAsignado = db.Column(db.String(100))  # Técnico principal (legacy)
    tiempoEstimado = db.Column(db.Float)  # horas
    tiempoReal = db.Column(db.Float)  # horas (calculado de registros)
    tiempoParada = db.Column(db.Float)  # horas de parada de máquina
    
    # Coste de talleres externos
    costeTallerExterno = db.Column(db.Float, default=0)  # Total acumulado (calculado)
    descripcionTallerExterno = db.Column(db.Text)  # LEGACY - primer coste
    proveedorExterno = db.Column(db.String(100))   # LEGACY - primer coste
    costesExternosJson = db.Column(db.Text)  # JSON list de {proveedor, descripcion, coste}

    
    # Auditoría
    creadoPor = db.Column(db.String(100))
    cerradoPor = db.Column(db.String(100))
    
    # Relaciones
    consumos = db.relationship('ConsumoRecambio', backref='ordenTrabajo', lazy=True, cascade='all, delete-orphan')
    registrosTiempo = db.relationship('RegistroTiempo', backref='ordenTrabajo', lazy=True, cascade='all, delete-orphan')
    respuestasChecklist = db.relationship('RespuestaChecklist', backref='ordenTrabajo', lazy=True, cascade='all, delete-orphan')
    
    @staticmethod
    def generarNumero():
        """Genera un número de OT con formato AAXXXXX (AA = año, XXXXX = contador anual)"""
        anio = date.today().strftime('%y')  # Últimas 2 cifras del año
        
        # Buscar la última OT del año actual
        ultima = OrdenTrabajo.query.filter(
            OrdenTrabajo.numero.like(f'{anio}%')
        ).order_by(OrdenTrabajo.numero.desc()).first()
        
        if ultima:
            try:
                # Extraer el contador de los últimos 5 dígitos
                secuencia = int(ultima.numero[2:]) + 1
            except:
                secuencia = 1
        else:
            secuencia = 1
        
        return f'{anio}{secuencia:05d}'

# Consumo de recambios en una OT
class ConsumoRecambio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ordenId = db.Column(db.Integer, db.ForeignKey('orden_trabajo.id'), nullable=False)
    recambioId = db.Column(db.Integer, db.ForeignKey('recambio.id'), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)
    precioUnitario = db.Column(db.Float)
    fecha = db.Column(db.DateTime, default=datetime.now)

# Registro de tiempo de trabajo en una OT
class RegistroTiempo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ordenId = db.Column(db.Integer, db.ForeignKey('orden_trabajo.id'), nullable=False)
    tecnico = db.Column(db.String(100), nullable=False)
    inicio = db.Column(db.DateTime, nullable=False)
    fin = db.Column(db.DateTime)  # NULL si está en curso
    enCurso = db.Column(db.Boolean, default=True)
    
    @property
    def duracionHoras(self):
        """Calcula la duración en horas"""
        if not self.fin:
            return (datetime.now() - self.inicio).total_seconds() / 3600
        return (self.fin - self.inicio).total_seconds() / 3600



# Maestro de Técnicos
class Tecnico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100))
    especialidad = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    tipo_tecnico = db.Column(db.String(20), nullable=False, default='interno')  # interno, externo
    activo = db.Column(db.Boolean, default=True)
    costeHora = db.Column(db.Float)

# =============================================================================
# MODELO DE MANTENIMIENTO PREVENTIVO - NUEVA ARQUITECTURA
# =============================================================================

# Nivel 1: Gamas de Mantenimiento (Catálogo independiente)
class GamaMantenimiento(db.Model):
    """Plantilla de mantenimiento reutilizable - Define qué hacer pero no cuándo"""
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    tipo = db.Column(db.String(20), default='preventivo') # 'preventivo' o 'tecnico_legal'
    tiempoEstimado = db.Column(db.Integer)  # minutos totales
    activo = db.Column(db.Boolean, default=True)
    fechaCreacion = db.Column(db.Date, default=date.today)
    
    @classmethod
    def generarCodigo(cls, tipo):
        prefijo = 'TL-' if tipo == 'tecnico_legal' else 'PR-'
        
        # Buscar el último número usado para el prefijo correspondiente
        ultima_gama = cls.query.filter(cls.codigo.like(f'{prefijo}%')).order_by(db.desc(cls.codigo)).first()
        
        if ultima_gama:
            try:
                # Extraemos la parte numérica, por ejemplo de 'PR-0042' sacamos '0042'
                ultimo_numero = int(ultima_gama.codigo.split('-')[1])
                nuevo_numero = ultimo_numero + 1
            except (IndexError, ValueError):
                # En caso de que haya algún código con formato incorrecto
                nuevo_numero = 1
        else:
            nuevo_numero = 1
            
        return f'{prefijo}{nuevo_numero:04d}'
    
    # Relaciones
    tareas = db.relationship('TareaGama', backref='gama', lazy=True, cascade='all, delete-orphan', order_by='TareaGama.orden')
    recambios = db.relationship('RecambioGama', backref='gama', lazy=True, cascade='all, delete-orphan')
    asignaciones = db.relationship('AsignacionGama', backref='gama', lazy=True)
    checklistItems = db.relationship('ChecklistItem', backref='gama', lazy=True, cascade='all, delete-orphan', order_by='ChecklistItem.orden')

class TareaGama(db.Model):
    """Tareas incluidas en una gama de mantenimiento"""
    id = db.Column(db.Integer, primary_key=True)
    gamaId = db.Column(db.Integer, db.ForeignKey('gama_mantenimiento.id'), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    orden = db.Column(db.Integer, default=1)
    duracionEstimada = db.Column(db.Integer)  # minutos
    herramientas = db.Column(db.Text)
    instrucciones = db.Column(db.Text)

class RecambioGama(db.Model):
    """Recambios necesarios para una gama de mantenimiento"""
    id = db.Column(db.Integer, primary_key=True)
    gamaId = db.Column(db.Integer, db.ForeignKey('gama_mantenimiento.id'), nullable=False)
    recambioId = db.Column(db.Integer, db.ForeignKey('recambio.id'), nullable=False)
    cantidad = db.Column(db.Float, default=1.0)
    observaciones = db.Column(db.Text)
    
    recambio = db.relationship('Recambio')

# Nivel 2: Asignación de Gamas a Equipos (con frecuencia)
class AsignacionGama(db.Model):
    """Asignación de una gama a un equipo con su frecuencia"""
    id = db.Column(db.Integer, primary_key=True)
    gamaId = db.Column(db.Integer, db.ForeignKey('gama_mantenimiento.id'), nullable=False)
    
    # Equipo (puede ser cualquier nivel jerárquico)
    equipoTipo = db.Column(db.String(20), nullable=False)  # empresa, planta, zona, linea, maquina, elemento
    equipoId = db.Column(db.Integer, nullable=False)
    
    # Frecuencia
    frecuenciaTipo = db.Column(db.String(20), default='dias')  # dias, semanas, meses, horas
    frecuenciaValor = db.Column(db.Integer, default=30)
    
    # Programación
    ultimaEjecucion = db.Column(db.Date)
    proximaEjecucion = db.Column(db.Date)
    
    activo = db.Column(db.Boolean, default=True)
    fechaAsignacion = db.Column(db.Date, default=date.today)
    
    # Relación con OTs generadas
    ordenesTrabajo = db.relationship('OrdenTrabajo', backref='asignacionGama', lazy=True)
    
    def calcularProximaEjecucion(self):
        """Calcula la próxima fecha de ejecución basada en la frecuencia"""
        from datetime import timedelta
        
        if not self.ultimaEjecucion:
            self.proximaEjecucion = date.today()
            return
        
        if self.frecuenciaTipo == 'dias':
            self.proximaEjecucion = self.ultimaEjecucion + timedelta(days=self.frecuenciaValor)
        elif self.frecuenciaTipo == 'semanas':
            self.proximaEjecucion = self.ultimaEjecucion + timedelta(weeks=self.frecuenciaValor)
        elif self.frecuenciaTipo == 'meses':
            # Aproximación: 30 días por mes
            self.proximaEjecucion = self.ultimaEjecucion + timedelta(days=self.frecuenciaValor * 30)

class ChecklistItem(db.Model):
    """Item de verificación definido en una gama de mantenimiento"""
    id = db.Column(db.Integer, primary_key=True)
    gamaId = db.Column(db.Integer, db.ForeignKey('gama_mantenimiento.id'), nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    orden = db.Column(db.Integer, default=1)
    tipoRespuesta = db.Column(db.String(20), default='ok_nok')  # 'ok_nok' | 'valor' | 'texto'
    unidad = db.Column(db.String(30))              # para tipo 'valor'
    generaCorrectivo = db.Column(db.Boolean, default=True)   # si NOK -> genera OT correctivo

class RespuestaChecklist(db.Model):
    """Respuesta a un item de checklist en una OT concreta"""
    id = db.Column(db.Integer, primary_key=True)
    ordenId = db.Column(db.Integer, db.ForeignKey('orden_trabajo.id'), nullable=False)
    checklistItemId = db.Column(db.Integer, db.ForeignKey('checklist_item.id'), nullable=False)
    respuesta = db.Column(db.String(100))          # 'ok' | 'nok' | valor libre
    observaciones = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.now)

    item = db.relationship('ChecklistItem')

class TareaRealizada(db.Model):
    """Registra qué tareas de una gama han sido completadas en una OT concreta."""
    id       = db.Column(db.Integer, primary_key=True)
    ordenId  = db.Column(db.Integer, db.ForeignKey('orden_trabajo.id'), nullable=False)
    tareaId  = db.Column(db.Integer, db.ForeignKey('tarea_gama.id'),    nullable=False)
    fecha    = db.Column(db.DateTime, default=datetime.now)
    tecnico  = db.Column(db.String(100))  # quién marcó la tarea

    __table_args__ = (db.UniqueConstraint('ordenId', 'tareaId'),)

# =============================================================================
# MODELO DE MANTENIMIENTO PREVENTIVO - LEGACY (Deprecado, mantener compatibilidad)
# =============================================================================

class PlanPreventivo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    
    # Equipo puede ser cualquier nivel de la jerarquía
    equipoTipo = db.Column(db.String(20), nullable=False)  # empresa, planta, zona, linea, maquina, elemento
    equipoId = db.Column(db.Integer, nullable=False)
    
    # Campo legacy para compatibilidad (deprecated)
    maquinaId = db.Column(db.Integer, db.ForeignKey('maquina.id'), nullable=True)

    
    # Frecuencia
    frecuenciaTipo = db.Column(db.String(20), default='dias')  # dias, semanas, meses, horas
    frecuenciaValor = db.Column(db.Integer, default=30)
    
    # Programación
    ultimaEjecucion = db.Column(db.Date)
    proximaEjecucion = db.Column(db.Date)
    
    # Estado
    activo = db.Column(db.Boolean, default=True)
    tiempoEstimado = db.Column(db.Integer)  # minutos
    
    tareas = db.relationship('TareaPreventivo', backref='plan', lazy=True, order_by='TareaPreventivo.orden')
    ordenesTrabajo = db.relationship('OrdenTrabajo', backref='planPreventivo', lazy=True)
    
    def calcularProximaEjecucion(self):
        """Calcula la próxima fecha de ejecución basada en la frecuencia"""
        from datetime import timedelta
        
        if not self.ultimaEjecucion:
            self.proximaEjecucion = date.today()
            return
        
        if self.frecuenciaTipo == 'dias':
            self.proximaEjecucion = self.ultimaEjecucion + timedelta(days=self.frecuenciaValor)
        elif self.frecuenciaTipo == 'semanas':
            self.proximaEjecucion = self.ultimaEjecucion + timedelta(weeks=self.frecuenciaValor)
        elif self.frecuenciaTipo == 'meses':
            # Aproximación: 30 días por mes
            self.proximaEjecucion = self.ultimaEjecucion + timedelta(days=self.frecuenciaValor * 30)

# Tareas dentro de un plan de mantenimiento
class TareaPreventivo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    planId = db.Column(db.Integer, db.ForeignKey('plan_preventivo.id'), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    orden = db.Column(db.Integer, default=1)
    duracionEstimada = db.Column(db.Integer)  # minutos
    herramientas = db.Column(db.Text)
    recambiosNecesarios = db.Column(db.Text)
    instrucciones = db.Column(db.Text)

# =============================================================================
# MODELO LEGACY - MANTENER COMPATIBILIDAD
# =============================================================================

# Modelo para representar un Activo (legacy - mantener por compatibilidad)
class Activo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empresaId = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=True)
    plantaId = db.Column(db.Integer, db.ForeignKey('planta.id'), nullable=True)
    zonaId = db.Column(db.Integer, db.ForeignKey('zona.id'), nullable=True)
    lineaId = db.Column(db.Integer, db.ForeignKey('linea.id'), nullable=True)
    maquinaId = db.Column(db.Integer, db.ForeignKey('maquina.id'), nullable=True)
    elementoId = db.Column(db.Integer, db.ForeignKey('elemento.id'), nullable=True)
    codigoCompleto = db.Column(db.String(255), unique=True, nullable=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    modelo = db.Column(db.String(50))
    numeroSerie = db.Column(db.String(50))
    fabricante = db.Column(db.String(50))
    estado = db.Column(db.String(50))
    fechaAlta = db.Column(db.Date)
    fechaBaja = db.Column(db.Date)

    def generateCodigoCompleto(self):
        parts = []
        empresa = Empresa.query.get(self.empresaId) if self.empresaId else None
        planta = Planta.query.get(self.plantaId) if self.plantaId else None
        zona = Zona.query.get(self.zonaId) if self.zonaId else None
        linea = Linea.query.get(self.lineaId) if self.lineaId else None
        maquina = Maquina.query.get(self.maquinaId) if self.maquinaId else None
        elemento = Elemento.query.get(self.elementoId) if self.elementoId else None

        if empresa: parts.append(empresa.codigo)
        if planta: parts.append(planta.codigo)
        if zona: parts.append(zona.codigo)
        if linea: parts.append(linea.codigo)
        if maquina: parts.append(maquina.codigo)
        if elemento: parts.append(elemento.codigo)

        self.codigoCompleto = '-'.join(parts) if parts else None

# Modelo para representar una intervención (legacy - mantener por compatibilidad)
class Intervencion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activoId = db.Column(db.Integer, db.ForeignKey('activo.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    descripcion = db.Column(db.Text)
    duracion = db.Column(db.Integer)
    tecnico = db.Column(db.String(100))

    activo = db.relationship('Activo', backref='intervenciones', lazy=True)

# =============================================================================
# CONFIGURACIÓN GENERAL DE LA APLICACIÓN
# =============================================================================

class ConfiguracionGeneral(db.Model):
    """Tabla clave-valor para ajustes globales de la aplicación."""
    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Text)
    descripcion = db.Column(db.String(255))
    tipo = db.Column(db.String(20), default='texto')  # texto, booleano, numero

    @staticmethod
    def obtener(clave, default=None):
        """Devuelve el valor de una clave de configuración."""
        reg = ConfiguracionGeneral.query.filter_by(clave=clave).first()
        if reg is None:
            return default
        if reg.tipo == 'booleano':
            return reg.valor.lower() in ('true', '1', 'si', 'yes')
        return reg.valor

    @staticmethod
    def establecer(clave, valor, descripcion=None, tipo='texto'):
        """Crea o actualiza una clave de configuración."""
        reg = ConfiguracionGeneral.query.filter_by(clave=clave).first()
        if reg is None:
            reg = ConfiguracionGeneral(clave=clave, tipo=tipo)
            if descripcion:
                reg.descripcion = descripcion
            from models import db as _db
            _db.session.add(reg)
        reg.valor = str(valor)
        return reg


# =============================================================================
# USUARIOS Y CONTROL DE ACCESO
# =============================================================================

class Usuario(db.Model):
    """Usuario de la aplicación con nivel de acceso."""
    id = db.Column(db.Integer, primary_key=True)
    # username es el nombre de login único (ej: 'jgarcia', 'admin')
    username = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100))
    password_hash = db.Column(db.String(64))  # SHA-256 hex
    # Nivel: 'tecnico', 'responsable', 'admin'
    nivel = db.Column(db.String(20), nullable=False, default='tecnico')
    # Vínculo opcional con la tabla de técnicos
    tecnicoId = db.Column(db.Integer, db.ForeignKey('tecnico.id'), nullable=True)
    tecnico = db.relationship('Tecnico', backref='usuario', uselist=False)
    activo = db.Column(db.Boolean, default=True)
    fechaAlta = db.Column(db.DateTime, default=datetime.now)
    ultimoAcceso = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()