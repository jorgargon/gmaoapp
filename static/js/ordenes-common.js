/**
 * Logica compartida para la gestión de órdenes de trabajo (OT)
 * Requiere:
 * - jQuery ($)
 * - apiCall (definido en base.html)
 * - openModal/closeModal (base.html)
 * - showToast (base.html)
 * - window.tiposCache (array de tipos de intervención)
 * - window.refreshOrdenesCallback (función para recargar la lista de órdenes)
 */

window.refreshOrdenesCallback = function () {
    console.log('Callback de refresco no definido');
};

// Set de IDs de OTs recién creadas (para resaltado visual temporal)
window._otNuevasIds = new Set();

function setRefreshCallback(callback) {
    window.refreshOrdenesCallback = callback;
}

// Helper para obtener info del tipo desde la cache global o por defecto
function getTipoInfo(codigo) {
    const cache = window.tiposCache || [];
    return cache.find(t => t.codigo === codigo) || { nombre: codigo, icono: 'fa-wrench', color: '#666' };
}

function formatEstado(estado) {
    const nombres = {
        'pendiente': 'Pendiente',
        'en_curso': 'En Curso',
        'cerrado_parcial': 'Cerrado Parcial',
        'cerrada': 'Cerrada',
        'cancelada': 'Cancelada'
    };
    return nombres[estado] || estado;
}


/**
 * Muestra el modal con el detalle de una orden
 * @param {number} id ID de la orden
 */
async function verOrden(id) {
    try {
        const o = await apiCall(`/api/orden/${id}`);

        const estadoFlow = ['pendiente', 'en_curso', 'cerrado_parcial', 'cerrada'];

        const currentIdx = estadoFlow.indexOf(o.estado);

        let html = `
        <div class="otDetalle">
            <!-- Cabecera -->
            <div class="otDetalleHeader">
                <div class="otDetalleNumero">
                    <span class="codigoTag large">${o.numero}</span>
                    <span class="tag tag-${o.tipo}">${o.tipo}</span>
                    <span class="tag tag-${o.prioridad}">${o.prioridad}</span>
                </div>
                <div class="otDetalleEstado">
                    <span class="estado-${o.estado} large">${formatEstado(o.estado)}</span>
                </div>
            </div>
            
            <!-- Flow de estados -->
            <div class="estadoFlow">
                ${estadoFlow.map((e, i) => `
                    <div class="estadoStep ${i <= currentIdx ? 'completed' : ''} ${i === currentIdx ? 'current' : ''}">
                        <div class="estadoCircle">${i < currentIdx ? '<i class="fas fa-check"></i>' : (i + 1)}</div>
                        <span>${formatEstado(e)}</span>
                    </div>
                `).join('<div class="estadoLine"></div>')}
            </div>
            
            <!-- Información -->
            <div class="infoGrid">
                <div class="infoItem full">
                    <label>Título</label>
                    <span>${o.titulo}</span>
                </div>
                <div class="infoItem full">
                    <label>Ubicación del Equipo</label>
                    <span style="color: #6c757d; font-family: monospace;">${o.equipoRuta || '-'}</span>
                </div>
                <div class="infoItem">
                    <label>Equipo</label>
                    <span>${o.equipoNombre || o.maquinaNombre || '-'}</span>
                </div>
                <div class="infoItem">
                    <label>Técnico</label>
                    <span>${o.tecnicoAsignado || 'Sin asignar'}</span>
                </div>
                <div class="infoItem full">
                    <label>Descripción del Problema</label>
                    <span>${o.descripcionProblema || '-'}</span>
                </div>
            </div>
            
            <!-- Fechas -->
            <div class="fechasGrid">
                <div class="fechaItem">
                    <i class="fas fa-plus-circle"></i>
                    <span>Creación</span>
                    <strong>${o.fechaCreacion ? new Date(o.fechaCreacion).toLocaleString('es-ES') : '-'}</strong>
                </div>
                <div class="fechaItem">
                    <i class="fas fa-calendar"></i>
                    <span>Programada</span>
                    <strong>${o.fechaProgramada ? new Date(o.fechaProgramada).toLocaleString('es-ES') : '-'}</strong>
                </div>
                <div class="fechaItem">
                    <i class="fas fa-play-circle"></i>
                    <span>Inicio</span>
                    <strong>${o.fechaInicio ? new Date(o.fechaInicio).toLocaleString('es-ES') : '-'}</strong>
                </div>
                <div class="fechaItem">
                    <i class="fas fa-stop-circle"></i>
                    <span>Fin</span>
                    <strong>${o.fechaFin ? new Date(o.fechaFin).toLocaleString('es-ES') : '-'}</strong>
                </div>
            </div>
            
            ${o.estado !== 'cerrada' && o.estado !== 'cancelada' ? `
                <!-- Control de Tiempo -->
                <div class="tiempoControles">
                    <button class="btn btnSuccess" onclick="iniciarTrabajo(${o.id})">
                        <i class="fas fa-play"></i> Iniciar Trabajo
                    </button>
                    <button class="btn btnWarning" onclick="pausarTrabajo(${o.id})">
                        <i class="fas fa-pause"></i> Pausar
                    </button>
                </div>
            ` : ''}

            ${o.tipo === 'preventivo' && o.gamaTareas && o.gamaTareas.length > 0 ? `
            <!-- Operaciones a Realizar (Gama) -->
            <div class="consumosSection">
                <h4><i class="fas fa-list-ol"></i> Operaciones a Realizar
                    ${o.gamaNombre ? `<small style="font-weight:normal;color:#666;"> — ${o.gamaNombre}</small>` : ''}
                </h4>
                <ol class="tareasList">
                    ${o.gamaTareas.map(t => `
                        <li>
                            <div class="tareaItem">
                                <div class="tareaDesc">${t.descripcion}</div>
                                ${t.duracionEstimada ? `<span class="tareaDuracion">${t.duracionEstimada} min</span>` : ''}
                                ${t.herramientas ? `<div class="tareaHerramientas"><i class="fas fa-tools"></i> ${t.herramientas}</div>` : ''}
                            </div>
                        </li>
                    `).join('')}
                </ol>
            </div>
            ` : ''}

            ${o.tipo === 'preventivo' && o.checklistItems && o.checklistItems.length > 0 ? `
            <!-- Checklist de Verificación -->
            <div class="consumosSection" id="checklistSection">
                <h4><i class="fas fa-clipboard-check"></i> Checklist de Verificación</h4>
                ${o.estado !== 'cerrada' && o.estado !== 'cancelada' ? `
                <p style="font-size:12px;color:#e65100;margin-bottom:10px;">
                    <i class="fas fa-exclamation-triangle"></i> Los items marcados <strong>NOK</strong> con <i class="fas fa-bolt"></i> generarán automáticamente una OT correctiva al cerrar esta OT.
                </p>
                ` : ''}
                <table class="dataTable small" id="checklistTable">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Verificación</th>
                            <th>Respuesta</th>
                            ${o.estado !== 'cerrada' && o.estado !== 'cancelada' ? '<th>Obs.</th>' : '<th>Observaciones</th>'}
                        </tr>
                    </thead>
                    <tbody>
                        ${o.checklistItems.map((ci, idx) => {
            const respGuardada = (o.respuestasChecklist || []).find(r => r.checklistItemId === ci.id) || {};
            const iconoCorrect = ci.generaCorrectivo ? '<i class="fas fa-bolt" title="Genera OT correctiva si NOK" style="color:#e65100;font-size:10px;"></i>' : '';
            if (o.estado === 'cerrada' || o.estado === 'cancelada') {
                return `
                                <tr>
                                    <td>${ci.orden}</td>
                                    <td>${ci.descripcion} ${iconoCorrect}</td>
                                    <td>${respGuardada.respuesta ? renderRespuestaTag(respGuardada.respuesta) : '-'}</td>
                                    <td>${respGuardada.observaciones || '-'}</td>
                                </tr>`;
            }
            if (ci.tipoRespuesta === 'ok_nok') {
                return `
                                <tr>
                                    <td>${ci.orden}</td>
                                    <td>${ci.descripcion} ${iconoCorrect}</td>
                                    <td>
                                        <select class="formControl" id="cl_resp_${ci.id}" style="width:90px;">
                                            <option value="">--</option>
                                            <option value="ok" ${respGuardada.respuesta === 'ok' ? 'selected' : ''}>✅ OK</option>
                                            <option value="nok" ${respGuardada.respuesta === 'nok' ? 'selected' : ''}>❌ NOK</option>
                                            <option value="na" ${respGuardada.respuesta === 'na' ? 'selected' : ''}>N/A</option>
                                        </select>
                                    </td>
                                    <td><input type="text" class="formControl" id="cl_obs_${ci.id}" value="${respGuardada.observaciones || ''}" placeholder="Obs..."></td>
                                </tr>`;
            } else if (ci.tipoRespuesta === 'valor') {
                return `
                                <tr>
                                    <td>${ci.orden}</td>
                                    <td>${ci.descripcion} ${iconoCorrect}</td>
                                    <td><input type="number" class="formControl" id="cl_resp_${ci.id}" value="${respGuardada.respuesta || ''}" placeholder="${ci.unidad || 'valor'}" style="width:100px;"></td>
                                    <td><input type="text" class="formControl" id="cl_obs_${ci.id}" value="${respGuardada.observaciones || ''}" placeholder="Obs..."></td>
                                </tr>`;
            } else {
                return `
                                <tr>
                                    <td>${ci.orden}</td>
                                    <td>${ci.descripcion} ${iconoCorrect}</td>
                                    <td colspan="2"><input type="text" class="formControl" id="cl_resp_${ci.id}" value="${respGuardada.respuesta || ''}" placeholder="Respuesta..."></td>
                                </tr>`;
            }
        }).join('')}
                    </tbody>
                </table>
                ${o.estado !== 'cerrada' && o.estado !== 'cancelada' ? `
                <button class="btn btnSm btnOutline" onclick="guardarChecklist(${o.id})" style="margin-top:8px;">
                    <i class="fas fa-save"></i> Guardar Checklist
                </button>` : ''}
            </div>
            ` : ''}
            
            <!-- Registros de Tiempo -->
            <div class="consumosSection">
                <h4><i class="fas fa-clock"></i> Tiempos Registrados</h4>
                ${o.registrosTiempo && o.registrosTiempo.length > 0 ? `
                    <table class="dataTable small">
                        <thead>
                            <tr><th>Técnico</th><th>Inicio</th><th>Fin</th><th>Duración</th></tr>
                        </thead>
                        <tbody>
                            ${o.registrosTiempo.map(r => `
                                <tr class="${r.enCurso ? 'enCurso' : ''}">
                                    <td>${r.tecnico} ${r.enCurso ? '<span class="tecnicoActivo">En curso</span>' : ''}</td>
                                    <td>${r.inicio ? new Date(r.inicio).toLocaleString('es-ES') : '-'}</td>
                                    <td>${r.fin ? new Date(r.fin).toLocaleString('es-ES') : '-'}</td>
                                    <td><strong>${r.duracionHoras}h</strong></td>
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr>
                                <td colspan="3"><strong>Total</strong></td>
                                <td><strong>${formatoEspanol(o.registrosTiempo.reduce((sum, r) => sum + r.duracionHoras, 0), 2)}h</strong></td>
                            </tr>
                        </tfoot>
                    </table>
                ` : '<p class="emptyState small">Sin tiempos registrados</p>'}
                ${o.estado !== 'cerrada' && o.estado !== 'cancelada' ? `
                    <button class="btn btnSm btnOutline" onclick="iniciarTrabajo(${o.id})" style="margin-top: 10px;">
                        <i class="fas fa-plus"></i> Añadir Tiempo
                    </button>
                ` : ''}
            </div>
            
            ${o.estado === 'cerrada' || o.estado === 'cerrado_parcial' ? `
                <!-- Solución -->
                <div class="solucionBox">
                    <h4><i class="fas fa-check-circle"></i> Solución</h4>
                    <p>${o.descripcionSolucion || 'No especificada'}</p>
                    ${o.tiempoReal ? `<p><strong>Tiempo de intervención:</strong> ${o.tiempoReal} horas</p>` : ''}
                    ${o.tiempoParada ? `<p><strong>Tiempo de parada:</strong> ${o.tiempoParada} horas</p>` : ''}
                    ${(() => {
                    let kpis = '';
                    if (o.fechaCreacion && o.fechaInicio) {
                        const hrs = formatoEspanol((new Date(o.fechaInicio) - new Date(o.fechaCreacion)) / 3600000, 2);
                        if (hrs >= 0) kpis += `<p><strong>Tiempo de reacción:</strong> ${hrs} horas</p>`;
                    }
                    if (o.fechaInicio && o.fechaFin) {
                        const hrs = formatoEspanol((new Date(o.fechaFin) - new Date(o.fechaInicio)) / 3600000, 2);
                        if (hrs >= 0) kpis += `<p><strong>Tiempo de reparación:</strong> ${hrs} horas</p>`;
                    }
                    return kpis;
                })()}
                </div>
            ` : ''}
            
            <!-- Coste Externo -->
            <div class="consumosSection">
                <h4><i class="fas fa-industry"></i> Costes Externos</h4>
                ${renderCostesExternos(o)}
                ${o.estado !== 'cerrada' && o.estado !== 'cancelada' ? '<button class="btn btnSm btnOutline" onclick="agregarCosteExterno(' + o.id + ')" style="margin-top:10px"><i class="fas fa-plus"></i> A\u00f1adir Coste Externo</button>' : ''}
            </div>

            <!-- Consumos -->
            <div class="consumosSection">
                <h4><i class="fas fa-puzzle-piece"></i> Recambios Consumidos</h4>
                ${o.consumos && o.consumos.length > 0 ? `
                    <table class="dataTable small">
                        <thead>
                            <tr><th>Recambio</th><th>Cantidad</th><th>Precio Unit.</th><th>Total</th></tr>
                        </thead>
                        <tbody>
                            ${o.consumos.map(c => `
                                <tr>
                                    <td>${c.recambioNombre}</td>
                                    <td>${c.cantidad}</td>
                                    <td>${c.precioUnitario ? formatoEspanol(c.precioUnitario, 2) : '-'} €</td>
                                    <td>${formatoEspanol((c.cantidad * c.precioUnitario) || 0, 2)} €</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ` : '<p class="emptyState small">Sin consumos registrados</p>'}
                ${o.estado !== 'cerrada' && o.estado !== 'cancelada' ? `
                    <button class="btn btnSm btnOutline" onclick="agregarConsumoOT(${o.id})" style="margin-top: 10px;">
                        <i class="fas fa-plus"></i> Añadir Consumo
                    </button>

                ` : ''}
            </div>
        </div>
    `;

        const deleteFallback = window.USER_NIVEL !== 'tecnico' ? `
            <button class="btn btnDanger" onclick="eliminarOT(${o.id})" style="margin-right: auto;">
                <i class="fas fa-trash"></i> Eliminar
            </button>` : `<div style="margin-right: auto;"></div>`;

        let footer = `
            ${deleteFallback}
            <button class="btn btnSecondary" onclick="closeModal()">Cerrar</button>
        `;


        if (o.estado !== 'cerrada' && o.estado !== 'cancelada') {
            let accionBtn = '';
            if (o.estado === 'pendiente') {
                accionBtn = `<button class="btn btnPrimary" onclick="avanzarEstadoOT(${o.id}, '${o.estado}')">
                    <i class="fas fa-play"></i> Iniciar Trabajo
                </button>`;
            } else if (o.estado === 'en_curso') {
                accionBtn = `<button class="btn btnWarning" onclick="finalizarTrabajo(${o.id})">
                    <i class="fas fa-flag-checkered"></i> Finalizar Trabajo
                </button>`;
            } else if (o.estado === 'cerrado_parcial') {
                const revertirBtn = `<button class="btn btnWarning" onclick="revertirEnCurso(${o.id})" style="margin-right: 5px;">
                    <i class="fas fa-undo"></i> Revertir a En Curso
                </button>`;

                const cierreDefinitivoBtn = (window.USER_NIVEL !== 'tecnico' || window.TECNICO_PUEDE_CERRAR) ? `
                <button class="btn btnSuccess" onclick="cerrarOT(${o.id})">
                    <i class="fas fa-check-double"></i> Cierre Definitivo
                </button>` : '';

                accionBtn = revertirBtn + cierreDefinitivoBtn;
            }

            const eliminarBtn = window.USER_NIVEL !== 'tecnico' ? `
            <button class="btn btnDanger" onclick="eliminarOT(${o.id})" style="margin-right: auto;">
                <i class="fas fa-trash"></i> Eliminar
            </button>` : `<div style="margin-right: auto;"></div>`;

            footer = `
            ${eliminarBtn}
            <button class="btn btnOutline" onclick="closeModal(); editarOT(${o.id})">
                <i class="fas fa-edit"></i> Editar
            </button>
            ${accionBtn}
            <button class="btn btnSecondary" onclick="closeModal()">Cerrar</button>
            `;
        }


        openModal(`OT ${o.numero}`, html, footer);

    } catch (error) {
        showToast('Error al cargar detalle de orden: ' + error.message, 'error');
    }
}

async function mostrarFormularioOT(orden = null, maquinaIdPreset = null, tipoPreset = 'correctivo', equipoTipoPreset = 'maquina') {
    const esEdicion = orden !== null;
    let equipoSeleccionado = null;
    const buscarTipo = orden?.equipoTipo || equipoTipoPreset;
    const buscarId = orden?.equipoId || maquinaIdPreset;

    if (buscarTipo && buscarId) {
        try {
            const equipos = await apiCall('/api/equipos-lista');
            equipoSeleccionado = equipos.find(e => e.tipo === buscarTipo && e.id == buscarId);
        } catch (e) { }
    }

    const tiposCache = window.tiposCache || [];
    const tipoActual = orden?.tipo || tipoPreset || 'correctivo';
    const opcionesTipo = tiposCache.map(t =>
        `<option value="${t.codigo}" ${tipoActual === t.codigo ? 'selected' : ''}>${t.nombre}</option>`
    ).join('');

    const html = `
    <form id="formOT" onsubmit="event.preventDefault(); return false;">
        <div class="formRow">
            <div class="formGroup">
                <label>Tipo *</label>
                <select id="otTipo" class="formControl" required>
                    ${opcionesTipo}
                </select>
            </div>
            <div class="formGroup">
                <label>Prioridad *</label>
                <select id="otPrioridad" class="formControl" required>
                    <option value="baja" ${orden?.prioridad === 'baja' ? 'selected' : ''}>Baja</option>
                    <option value="media" ${(!orden || orden?.prioridad === 'media') ? 'selected' : ''}>Media</option>
                    <option value="alta" ${orden?.prioridad === 'alta' ? 'selected' : ''}>Alta</option>
                    <option value="urgente" ${orden?.prioridad === 'urgente' ? 'selected' : ''}>Urgente</option>
                </select>
            </div>
        </div>
        
        <div class="formGroup">
            <label>Activo *</label>
            <div class="treePicker" onclick="abrirSelectorArbol()">
                <span id="equipoSeleccionadoTexto">${equipoSeleccionado ? `${equipoSeleccionado.icono} ${equipoSeleccionado.ruta}` : 'Haz clic para seleccionar...'}</span>
                <i class="fas fa-sitemap"></i>
            </div>
            <input type="hidden" id="otEquipoTipo" value="${orden?.equipoTipo || equipoTipoPreset || ''}">
            <input type="hidden" id="otEquipoId" value="${orden?.equipoId || maquinaIdPreset || ''}">
        </div>


        <div class="formGroup">
            <label>Título *</label>
            <input type="text" id="otTitulo" class="formControl" value="${orden?.titulo || ''}" 
                   placeholder="Descripción breve del problema o trabajo" required>
        </div>
        <div class="formGroup">
            <label>Descripción del Problema</label>
            <textarea id="otDescripcion" class="formControl" rows="3" 
                      placeholder="Detalle el problema o los trabajos a realizar">${orden?.descripcionProblema || ''}</textarea>
        </div>
        <div class="formRow">
            <div class="formGroup">
                <label>Técnico Asignado</label>
                <input type="text" id="otTecnico" class="formControl" value="${orden?.tecnicoAsignado || ''}"
                       placeholder="Nombre del técnico">
            </div>
            <div class="formGroup">
                <label>Tiempo Estimado (horas)</label>
                <input type="number" id="otTiempoEst" class="formControl" value="${orden?.tiempoEstimado || ''}" min="0" step="0.5">
            </div>
        </div>

        <div class="formGroup">
            <label>Fecha Programada</label>
            <input type="date" id="otFechaProg" class="formControl" 
                   value="${orden?.fechaProgramada ? orden.fechaProgramada.slice(0, 10) : ''}">
        </div>
    </form>
`;

    const footer = `
    <button class="btn btnSecondary" onclick="closeModal()">Cancelar</button>
    <button class="btn btnPrimary" onclick="guardarOT(${orden?.id || 'null'})">${esEdicion ? 'Guardar' : 'Crear OT'}</button>
`;

    openModal(esEdicion ? 'Editar Orden de Trabajo' : 'Nueva Orden de Trabajo', html, footer);
}

async function guardarOT(id) {
    const equipoTipo = document.getElementById('otEquipoTipo').value;
    const equipoId = document.getElementById('otEquipoId').value;

    const data = {
        tipo: document.getElementById('otTipo').value,
        prioridad: document.getElementById('otPrioridad').value,
        equipoTipo: equipoTipo,
        equipoId: parseInt(equipoId),
        titulo: document.getElementById('otTitulo').value,
        descripcionProblema: document.getElementById('otDescripcion').value,
        tecnicoAsignado: document.getElementById('otTecnico').value,
        tiempoEstimado: parseInt(document.getElementById('otTiempoEst').value) || null
    };

    const fechaProg = document.getElementById('otFechaProg').value;
    if (fechaProg) data.fechaProgramada = fechaProg;

    if (!equipoTipo || !equipoId || !data.titulo) {
        showToast('Completa los campos obligatorios', 'error');
        return;
    }

    try {
        if (id) {
            await apiCall(`/api/orden/${id}`, 'PUT', data);
            showToast('Orden actualizada', 'success');
        } else {
            const result = await apiCall('/api/orden', 'POST', data);
            // Marcar como nueva para resaltado visual
            window._otNuevasIds.add(result.id);
            console.log('[DEBUG] OT nueva creada, ID añadido al Set:', result.id, 'Set:', [...window._otNuevasIds]);
            setTimeout(() => window._otNuevasIds.delete(result.id), 30000);
            showToast(`OT ${result.numero} creada`, 'success');
        }
        closeModal();
        if (window.refreshOrdenesCallback) window.refreshOrdenesCallback();

    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function editarOT(id) {
    const orden = await apiCall(`/api/orden/${id}`);
    mostrarFormularioOT(orden);
}

async function eliminarOT(id) {
    if (!confirm('¿Estás seguro de que quieres eliminar esta orden de trabajo? Esta acción no se puede deshacer y eliminará todos los datos asociados (tiempos, consumos, etc.).')) {
        return;
    }

    try {
        await apiCall(`/api/orden/${id}`, 'DELETE');
        closeModal();
        if (window.refreshOrdenesCallback) window.refreshOrdenesCallback();
        showToast('Orden eliminada correctamente', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function avanzarEstadoOT(id, estadoActual) {
    // Pendiente → En curso: iniciar trabajo directamente
    if (estadoActual === 'pendiente') {
        return iniciarTrabajo(id);
    }
    // En curso → Cerrado parcial: finalizar trabajo
    if (estadoActual === 'en_curso') {
        return finalizarTrabajo(id);
    }
    // Fallback directo
    const siguienteEstado = { 'cerrado_parcial': 'cerrada' };
    const nuevo = siguienteEstado[estadoActual];
    if (!nuevo) return;
    try {
        await apiCall(`/api/orden/${id}/estado`, 'PUT', { estado: nuevo });
        closeModal();
        if (window.refreshOrdenesCallback) window.refreshOrdenesCallback();
        showToast(`Estado cambiado a ${formatEstado(nuevo)}`, 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function revertirEnCurso(id) {
    if (!confirm('¿Seguro que deseas revertir la orden a "En Curso"? Esto eliminará la fecha de fin de la orden.')) return;
    try {
        await apiCall(`/api/orden/${id}/estado`, 'PUT', { estado: 'en_curso' });
        closeModal();
        if (window.refreshOrdenesCallback) window.refreshOrdenesCallback();
        showToast('Orden revertida a En Curso', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function finalizarTrabajo(ordenId) {
    // Abre el modal para que el técnico documente el cierre parcial
    const html = `
    <form id="formCerrarParcial" onsubmit="event.preventDefault(); return false;">
        <div class="formGroup">
            <label>Descripción del Problema / Solución *</label>
            <textarea id="cerrarSolucion" class="formControl" rows="4" 
                      placeholder="Describa el problema encontrado y la solución aplicada" required></textarea>
        </div>
        <div class="formGroup">
            <label>Tiempo de Parada de Máquina (horas) *</label>
            <input type="number" id="cerrarTiempoParada" class="formControl" min="0" step="0.5" 
                   placeholder="Horas de máquina parada" required>
        </div>
        <div class="formGroup">
            <label>Observaciones</label>
            <textarea id="cerrarObs" class="formControl" rows="2"></textarea>
        </div>
    </form>
    `;

    const footer = `
    <button class="btn btnSecondary" onclick="closeModal(); verOrden(${ordenId})">Cancelar</button>
    <button class="btn btnWarning" onclick="confirmarFinalizarTrabajo(${ordenId})">
        <i class="fas fa-flag-checkered"></i> Confirmar Cierre Parcial
    </button>
    `;

    openModal('Finalizar Trabajo (Cierre Parcial)', html, footer);
}

async function confirmarFinalizarTrabajo(id) {
    const solucion = document.getElementById('cerrarSolucion').value;
    const tiempoParadaInput = document.getElementById('cerrarTiempoParada').value;

    if (!solucion.trim()) {
        showToast('Debe indicar el problema / solución', 'error');
        return;
    }
    if (tiempoParadaInput === '') {
        showToast('Debe indicar el tiempo de parada de máquina', 'error');
        return;
    }

    try {
        await apiCall(`/api/orden/${id}`, 'PUT', {
            descripcionSolucion: solucion,
            tiempoParada: parseFloat(tiempoParadaInput) || 0,
            observaciones: document.getElementById('cerrarObs').value
        });

        // Guardar checklist si hay items pendientes
        await _autoGuardarChecklist(id);

        const resultado = await apiCall(`/api/orden/${id}/estado`, 'PUT', { estado: 'cerrado_parcial' });

        closeModal();
        if (window.refreshOrdenesCallback) window.refreshOrdenesCallback();
        showToast('Trabajo finalizado. Pendiente de cierre definitivo por el responsable.', 'success');

        // Notificar al usuario sobre OTs correctivas generadas automáticamente
        if (resultado.otsCorrectivas && resultado.otsCorrectivas.length > 0) {
            setTimeout(() => {
                showToast(`⚠️ ${resultado.mensajeCorrectivos}`, 'warning');
            }, 800);
        }
        if (resultado.nuevaOT) {
            setTimeout(() => {
                showToast(`📅 ${resultado.mensajeOT}`, 'info');
            }, 1600);
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function asignarTecnicoOT(id) {
    // Cargar lista de técnicos para el selector
    let tecnicoOpts = '';
    try {
        const tecnicos = await apiCall('/api/tecnicos');
        if (tecnicos && tecnicos.length) {
            tecnicoOpts = tecnicos
                .filter(t => t.activo !== false)
                .map(t => `<option value="${t.nombre} ${t.apellidos || ''}">${t.nombre} ${t.apellidos || ''}</option>`)
                .join('');
        }
    } catch (e) { /* si falla, solo campo texto */ }

    const html = `
    <div class="formGroup">
        <label>Técnico asignado *</label>
        ${tecnicoOpts
            ? `<select id="tecnicoAsignado" class="formControl" required>
                   <option value="">-- Selecciona técnico --</option>
                   ${tecnicoOpts}
                   <option value="__otro__">Otro (introducir manualmente)</option>
               </select>
               <input type="text" id="tecnicoManual" class="formControl" style="display:none;margin-top:8px;"
                      placeholder="Nombre del técnico">`
            : `<input type="text" id="tecnicoManual" class="formControl" placeholder="Nombre del técnico" required>`
        }
    </div>`;

    if (tecnicoOpts) {
        // Mostrar campo manual si se elige "Otro"
        setTimeout(() => {
            const sel = document.getElementById('tecnicoAsignado');
            if (sel) sel.addEventListener('change', () => {
                document.getElementById('tecnicoManual').style.display =
                    sel.value === '__otro__' ? 'block' : 'none';
            });
        }, 100);
    }

    const footer = `
        <button class="btn btnSecondary" onclick="closeModal(); verOrden(${id})">Cancelar</button>
        <button class="btn btnPrimary" onclick="confirmarAsignacionOT(${id})">
            <i class="fas fa-user-check"></i> Asignar y Avanzar
        </button>`;

    openModal('Asignar Técnico', html, footer);
}

async function confirmarAsignacionOT(id) {
    const sel = document.getElementById('tecnicoAsignado');
    const manual = document.getElementById('tecnicoManual');
    let tecnico = '';

    if (sel) {
        tecnico = sel.value === '__otro__' ? (manual ? manual.value.trim() : '') : sel.value.trim();
    } else if (manual) {
        tecnico = manual.value.trim();
    }

    if (!tecnico) {
        showToast('Selecciona o introduce un técnico', 'error');
        return;
    }

    try {
        await apiCall(`/api/orden/${id}`, 'PUT', { tecnicoAsignado: tecnico });
        await apiCall(`/api/orden/${id}/estado`, 'PUT', { estado: 'asignada' });
        closeModal();
        if (window.refreshOrdenesCallback) window.refreshOrdenesCallback();
        showToast(`OT asignada a ${tecnico}`, 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

function cerrarOT(id) {
    // Cierre Definitivo (solo confirmación, la info ya está en el cerrado_parcial)
    if (!confirm('¿Realizar el Cierre Definitivo de esta Orden de Trabajo?')) return;
    confirmarCierreDefinitivo(id);
}

async function confirmarCierreDefinitivo(id) {
    try {
        await apiCall(`/api/orden/${id}/estado`, 'PUT', { estado: 'cerrada' });
        closeModal();
        if (window.refreshOrdenesCallback) window.refreshOrdenesCallback();
        showToast('Cierre definitivo realizado correctamente', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function iniciarTrabajo(ordenId) {
    // Cargar técnicos para el selector
    let tecnicoOpts = '';
    try {
        const tecnicos = await apiCall('/api/tecnicos');
        if (tecnicos && tecnicos.length) {
            tecnicoOpts = tecnicos
                .filter(t => t.activo !== false)
                .map(t => {
                    const nombreCompleto = `${t.nombre} ${t.apellidos || ''}`.trim();
                    const isSelected = window.USER_TECNICO_NOMBRE && (window.USER_TECNICO_NOMBRE === nombreCompleto || window.USER_TECNICO_NOMBRE === t.nombre);
                    return `<option value="${nombreCompleto}" ${isSelected ? 'selected' : ''}>${nombreCompleto}</option>`;
                })
                .join('');
        }
    } catch (e) { }

    const html = `
    <div class="formGroup">
        <label>¿Quién inicia el trabajo? *</label>
        ${tecnicoOpts
            ? `<select id="iniciarTecnico" class="formControl" required>
                   <option value="">-- Selecciona --</option>
                   ${tecnicoOpts}
                   <option value="__otro__">Otro</option>
               </select>
               <input type="text" id="iniciarTecnicoManual" class="formControl" style="display:none;margin-top:8px;"
                      placeholder="Nombre">`
            : `<input type="text" id="iniciarTecnicoManual" class="formControl" placeholder="Tu nombre" required value="${window.USER_TECNICO_NOMBRE || ''}">`
        }
    </div>`;

    if (tecnicoOpts) {
        setTimeout(() => {
            const sel = document.getElementById('iniciarTecnico');
            if (sel) sel.addEventListener('change', () => {
                document.getElementById('iniciarTecnicoManual').style.display =
                    sel.value === '__otro__' ? 'block' : 'none';
            });
        }, 100);
    }

    const footer = `
        <button class="btn btnSecondary" onclick="closeModal(); verOrden(${ordenId})">Cancelar</button>
        <button class="btn btnSuccess" onclick="confirmarIniciarTrabajo(${ordenId})">
            <i class="fas fa-play"></i> Iniciar Trabajo
        </button>`;

    openModal('Iniciar Trabajo', html, footer);
}

async function confirmarIniciarTrabajo(ordenId) {
    const sel = document.getElementById('iniciarTecnico');
    const manual = document.getElementById('iniciarTecnicoManual');
    let tecnico = '';
    if (sel) {
        tecnico = sel.value === '__otro__' ? (manual ? manual.value.trim() : '') : sel.value.trim();
    } else if (manual) {
        tecnico = manual.value.trim();
    }
    if (!tecnico) { showToast('Indica quién realiza el trabajo', 'error'); return; }

    try {
        const result = await apiCall(`/api/orden/${ordenId}/iniciar`, 'POST', { tecnico });
        showToast(result.mensaje, 'success');
        closeModal();
        verOrden(ordenId);
        if (window.refreshOrdenesCallback) window.refreshOrdenesCallback();
    } catch (error) {
        showToast(error.message || error.error, 'error');
    }
}

async function pausarTrabajo(ordenId) {
    // Cargar técnicos para el selector
    let tecnicoOpts = '';
    try {
        const tecnicos = await apiCall('/api/tecnicos');
        if (tecnicos && tecnicos.length) {
            tecnicoOpts = tecnicos
                .filter(t => t.activo !== false)
                .map(t => {
                    const nombreCompleto = `${t.nombre} ${t.apellidos || ''}`.trim();
                    const isSelected = window.USER_TECNICO_NOMBRE && (window.USER_TECNICO_NOMBRE === nombreCompleto || window.USER_TECNICO_NOMBRE === t.nombre);
                    return `<option value="${nombreCompleto}" ${isSelected ? 'selected' : ''}>${nombreCompleto}</option>`;
                })
                .join('');
        }
    } catch (e) { }

    const html = `
    <div class="formGroup">
        <label>¿Quién pausa el trabajo? *</label>
        ${tecnicoOpts
            ? `<select id="pausarTecnico" class="formControl" required>
                   <option value="">-- Selecciona --</option>
                   ${tecnicoOpts}
                   <option value="__otro__">Otro</option>
               </select>
               <input type="text" id="pausarTecnicoManual" class="formControl" style="display:none;margin-top:8px;"
                      placeholder="Nombre">`
            : `<input type="text" id="pausarTecnicoManual" class="formControl" placeholder="Tu nombre" required value="${window.USER_TECNICO_NOMBRE || ''}">`
        }
    </div>`;

    if (tecnicoOpts) {
        setTimeout(() => {
            const sel = document.getElementById('pausarTecnico');
            if (sel) sel.addEventListener('change', () => {
                document.getElementById('pausarTecnicoManual').style.display =
                    sel.value === '__otro__' ? 'block' : 'none';
            });
        }, 100);
    }

    const footer = `
        <button class="btn btnSecondary" onclick="closeModal(); verOrden(${ordenId})">Cancelar</button>
        <button class="btn btnWarning" onclick="confirmarPausarTrabajo(${ordenId})">
            <i class="fas fa-pause"></i> Pausar Trabajo
        </button>`;

    openModal('Pausar Trabajo', html, footer);
}

async function confirmarPausarTrabajo(ordenId) {
    const sel = document.getElementById('pausarTecnico');
    const manual = document.getElementById('pausarTecnicoManual');
    let tecnico = '';
    if (sel) {
        tecnico = sel.value === '__otro__' ? (manual ? manual.value.trim() : '') : sel.value.trim();
    } else if (manual) {
        tecnico = manual.value.trim();
    }
    if (!tecnico) { showToast('Indica quién pausa el trabajo', 'error'); return; }

    try {
        const result = await apiCall(`/api/orden/${ordenId}/pausar`, 'POST', { tecnico });
        showToast(`${result.mensaje}. Duración: ${result.duracionSesion}h`, 'success');
        closeModal();
        verOrden(ordenId);
        if (window.refreshOrdenesCallback) window.refreshOrdenesCallback();
    } catch (error) {
        showToast(error.message || error.error, 'error');
    }
}

async function agregarConsumoOT(ordenId) {
    const recambios = await apiCall('/api/recambios');

    const html = `
    <form id="formConsumo" onsubmit="event.preventDefault(); return false;">
        <div class="formGroup" style="position:relative;">
            <label>Recambio *</label>
            <input type="text" id="consumoBusqueda" class="formControl" placeholder="Buscar por nombre o código..."
                   autocomplete="off" oninput="filtrarRecambios()" onblur="setTimeout(()=>ocultarSugerencias(),200)">
            <input type="hidden" id="consumoRecambioId">
            <ul id="consumoSugerencias" style="
                display:none; position:absolute; top:100%; left:0; right:0;
                background:var(--cardBg,#1e2130); border:1px solid var(--border,#333);
                border-radius:6px; max-height:200px; overflow-y:auto;
                list-style:none; margin:2px 0 0; padding:0; z-index:9999;
                box-shadow:0 4px 12px rgba(0,0,0,.3);
            "></ul>
            <small id="stockInfo" class="textMuted"></small>
        </div>
        <div class="formGroup">
            <label>Cantidad *</label>
            <input type="number" id="consumoCantidad" class="formControl" value="1" min="1" required>
        </div>
    </form>
`;

    const footer = `
    <button class="btn btnSecondary" onclick="closeModal(); verOrden(${ordenId})">Cancelar</button>
    <button class="btn btnPrimary" onclick="confirmarConsumo(${ordenId})">Añadir Consumo</button>
`;

    openModal('Añadir Consumo de Recambio', html, footer);

    // Guardar lista de recambios en una variable accesible
    window._recambiosCache = recambios;
}

function filtrarRecambios() {
    const query = document.getElementById('consumoBusqueda').value.toLowerCase().trim();
    const lista = document.getElementById('consumoSugerencias');
    const recambios = window._recambiosCache || [];

    // Limpiar selección previa al escribir
    document.getElementById('consumoRecambioId').value = '';
    document.getElementById('stockInfo').textContent = '';

    if (!query) { lista.style.display = 'none'; return; }

    const filtrados = recambios.filter(r =>
        r.nombre.toLowerCase().includes(query) || (r.codigo && r.codigo.toLowerCase().includes(query))
    ).slice(0, 20);

    if (!filtrados.length) { lista.style.display = 'none'; return; }

    lista.innerHTML = filtrados.map(r => `
        <li onclick="seleccionarRecambio(${r.id}, '${(r.codigo + ' - ' + r.nombre).replace(/'/g, "\\'")}', ${r.stockActual})"
            style="padding:8px 12px; cursor:pointer; border-bottom:1px solid var(--border,#333);"
            onmouseover="this.style.background='rgba(255,255,255,.06)'"
            onmouseout="this.style.background=''">
            <span style="font-weight:600;">${r.codigo}</span> — ${r.nombre}
            <span class="textMuted" style="float:right; font-size:.85em;">Stock: ${r.stockActual}</span>
        </li>
    `).join('');
    lista.style.display = 'block';
}

function seleccionarRecambio(id, texto, stock) {
    document.getElementById('consumoBusqueda').value = texto;
    document.getElementById('consumoRecambioId').value = id;
    document.getElementById('consumoSugerencias').style.display = 'none';
    document.getElementById('stockInfo').textContent = `Stock disponible: ${stock}`;
}

function ocultarSugerencias() {
    const lista = document.getElementById('consumoSugerencias');
    if (lista) lista.style.display = 'none';
}

async function confirmarConsumo(ordenId) {
    const recambioId = document.getElementById('consumoRecambioId').value;
    const cantidad = parseInt(document.getElementById('consumoCantidad').value);

    if (!recambioId) {
        showToast('Selecciona un recambio de la lista', 'error');
        return;
    }
    if (!cantidad) {
        showToast('Indica la cantidad', 'error');
        return;
    }

    try {
        await apiCall(`/api/orden/${ordenId}/consumo`, 'POST', { recambioId, cantidad });
        closeModal();
        verOrden(ordenId);
        showToast('Consumo añadido correctamente', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ─── Helper: renderiza la tabla de costes externos ─────────────────────────
function renderCostesExternos(o) {
    let costes = [];
    if (o.costesExternosJson) {
        try { costes = JSON.parse(o.costesExternosJson); } catch (e) { }
    } else if (o.costeTallerExterno) {
        costes = [{ proveedor: o.proveedorExterno || '', descripcion: o.descripcionTallerExterno || '', coste: o.costeTallerExterno }];
    }
    if (costes.length === 0) {
        return '<p class="emptyState small">Sin costes externos registrados</p>';
    }
    const total = costes.reduce(function (s, c) { return s + (c.coste || 0); }, 0);
    const canDel = o.estado !== 'cerrada' && o.estado !== 'cancelada';
    let rows = '';
    costes.forEach(function (c, idx) {
        const delBtn = canDel
            ? '<td><button class="btn btnSm btnDanger" onclick="eliminarCosteExternoItem(' + o.id + ',' + idx + ')" title="Eliminar"><i class="fas fa-trash"></i></button></td>'
            : '';
        rows += '<tr><td>' + (c.proveedor || '-') + '</td><td>' + (c.descripcion || '-') + '</td><td><strong>' + formatoEspanol(c.coste, 2) + ' \u20ac</strong></td>' + delBtn + '</tr>';
    });
    const extraTh = canDel ? '<th></th>' : '';
    const extraTd = canDel ? '<td></td>' : '';
    return '<table class="dataTable small"><thead><tr><th>Proveedor</th><th>Descripci\u00f3n</th><th>Coste</th>' + extraTh + '</tr></thead><tbody>' + rows + '</tbody><tfoot><tr><td colspan="2"><strong>Total</strong></td><td><strong>' + formatoEspanol(total, 2) + ' \u20ac</strong></td>' + extraTd + '</tr></tfoot></table>';
}

async function agregarCosteExterno(ordenId) {
    const html = `
    <form id="formCosteExterno" onsubmit="event.preventDefault(); return false;">
        <div class="formGroup">
            <label>Proveedor / Taller</label>
            <input type="text" id="ceProveedor" class="formControl" placeholder="Nombre del taller o proveedor">
        </div>
        <div class="formGroup">
            <label>Coste (€) *</label>
            <input type="number" id="ceCoste" class="formControl" step="0.01" min="0" required>
        </div>
        <div class="formGroup">
            <label>Descripción del trabajo</label>
            <textarea id="ceDescripcion" class="formControl" rows="2" placeholder="Descripción del trabajo realizado por el externo"></textarea>
        </div>
    </form>
`;

    const footer = `
    <button class="btn btnSecondary" onclick="closeModal(); verOrden(${ordenId})">Cancelar</button>
    <button class="btn btnPrimary" onclick="confirmarCosteExterno(${ordenId})">Guardar Coste</button>
`;

    openModal('Añadir Coste Externo', html, footer);
}

async function confirmarCosteExterno(ordenId) {
    const proveedor = document.getElementById('ceProveedor').value;
    const coste = parseFloat(document.getElementById('ceCoste').value);
    const descripcion = document.getElementById('ceDescripcion').value;

    if (!document.getElementById('ceCoste').value || isNaN(coste)) {
        showToast('Debe indicar el coste', 'error');
        return;
    }

    try {
        await apiCall(`/api/orden/${ordenId}/coste-externo`, 'POST', { proveedor, coste, descripcion });
        showToast('Coste externo añadido', 'success');
        closeModal();
        verOrden(ordenId);
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function eliminarCosteExternoItem(ordenId, idx) {
    if (!confirm('¿Eliminar este coste externo?')) return;
    try {
        await apiCall(`/api/orden/${ordenId}/coste-externo/${idx}`, 'DELETE');
        showToast('Coste eliminado', 'success');
        verOrden(ordenId);
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// =========================================
// SELECTOR DE ÁRBOL COLAPSABLE
// =========================================


async function abrirSelectorArbol() {
    // Crear el contenido del modal secundario
    const treeHtml = `
        <div id="arbolEquipos" style="min-height: 300px; max-height: 400px; overflow: auto;"></div>
    `;

    const treeFooter = `
        <button class="btn btnSecondary" onclick="cerrarSelectorArbol()">Cancelar</button>
        <button class="btn btnPrimary" onclick="confirmarSeleccion()">Seleccionar</button>
    `;

    // Guardar el modal actual y abrir uno nuevo
    const modalActual = document.querySelector('.modalContent').innerHTML;
    window.modalAnterior = modalActual;

    // Guardar los valores actuales de los campos del formulario (los selects pierden su valor al restaurar innerHTML)
    // Excluir inputs hidden: los gestiona el árbol selector y no deben sobreescribirse
    window.formSnapshot = {};
    document.querySelectorAll('.modalContent select, .modalContent input:not([type="hidden"]), .modalContent textarea').forEach(el => {
        if (el.id) window.formSnapshot[el.id] = el.value;
    });

    // Mostrar modal de árbol
    document.querySelector('.modalContent').innerHTML = `
        <div class="modalHeader">
            <h3>Seleccionar Activo</h3>
            <button class="modalClose" onclick="cerrarSelectorArbol()">&times;</button>
        </div>
        <div class="modalBody">${treeHtml}</div>
        <div class="modalFooter">${treeFooter}</div>
    `;

    // Cargar datos y crear árbol
    try {
        const treeData = await apiCall('/getActivosTree');

        $('#arbolEquipos').jstree({
            'core': {
                'data': treeData,
                'themes': {
                    'dots': true,
                    'icons': true
                }
            },
            'plugins': ['wholerow']
        }).on('select_node.jstree', function (e, data) {
            window.nodoSeleccionado = data.node;
        });

    } catch (e) {
        console.error('Error cargando árbol:', e);
    }
}

function cerrarSelectorArbol() {
    // Restaurar modal anterior
    if (window.modalAnterior) {
        document.querySelector('.modalContent').innerHTML = window.modalAnterior;
        // Restaurar valores de los campos (innerHTML reset al atributo 'selected' original)
        if (window.formSnapshot) {
            Object.entries(window.formSnapshot).forEach(([id, val]) => {
                const el = document.getElementById(id);
                if (el) el.value = val;
            });
        }
    }
}

function confirmarSeleccion() {
    if (!window.nodoSeleccionado) {
        showToast('Selecciona un activo del árbol', 'warning');
        return;
    }

    const node = window.nodoSeleccionado;
    const id = node.id;
    const parts = id.split('-');  // El ID tiene formato: tipo-id (ej: zona-3)
    const tipo = parts[0];
    const equipoId = parts[1];


    // Construir ruta para mostrar
    const iconos = { empresa: '🏢', planta: '🏭', zona: '📍', linea: '⚡', maquina: '⚙️', elemento: '🔧' };
    const ruta = node.parents.slice(0, -1).reverse().map(pId => {
        const pNode = $('#arbolEquipos').jstree('get_node', pId);
        return pNode ? pNode.text : '';
    }).join(' > ');

    const textoCompleto = ruta ? `${ruta} > ${node.text}` : node.text;
    const textoMostrar = `${iconos[tipo] || ''} ${textoCompleto}`;

    // Actualizar el HTML guardado antes de restaurarlo
    if (window.modalAnterior) {
        // Reemplazar valores en el HTML guardado
        // Puede que no funcione si el value tiene comillas o cosas raras, pero para IDs simples vale.
        // Mejor usar DOMParser si fuera complejo, pero esto es un hack rápido que funcionaba en ordenes.html
        // Una mejor manera es restaurar y luego setear valores.

        let parser = new DOMParser();
        let doc = parser.parseFromString(window.modalAnterior, 'text/html');

        // Pero window.modalAnterior es string HTML innerHTML.
        // Vamos a mantener la logica original de strings replace que funcionaba

        window.modalAnterior = window.modalAnterior
            .replace(/id="otEquipoTipo" value="[^"]*"/, `id="otEquipoTipo" value="${tipo}"`)
            .replace(/id="otEquipoId" value="[^"]*"/, `id="otEquipoId" value="${equipoId}"`)
            // Regex para el span es mas complicado porque contiene texto variable.
            // Buscamos id="equipoSeleccionadoTexto">...</span>
            .replace(/id="equipoSeleccionadoTexto">.*?<\/span>/, `id="equipoSeleccionadoTexto">${textoMostrar}</span>`);
    }

    // Restaurar modal con valores actualizados
    cerrarSelectorArbol();

    // Limpiar nodo seleccionado
    window.nodoSeleccionado = null;

    // IMPORTANTE: Al restaurar el modal, los eventos se pierden si se asignaron con addEventListener.
    // Los onclick en HTML atributos funcionan.
}

// =========================================
// CHECKLIST HELPERS
// =========================================

/**
 * Recoge las respuestas actuales del checklist del DOM y las envía al backend.
 * @param {number} ordenId
 * @param {Array} checklistItems - lista de items con {id, tipoRespuesta}
 */
async function _autoGuardarChecklist(ordenId) {
    // Buscar todos los campos de checklist en el DOM
    const inputs = document.querySelectorAll('[id^="cl_resp_"]');
    if (!inputs || inputs.length === 0) return; // No hay checklist activo
    const respuestas = [];
    inputs.forEach(el => {
        const itemId = parseInt(el.id.replace('cl_resp_', ''));
        const obsEl = document.getElementById(`cl_obs_${itemId}`);
        respuestas.push({
            checklistItemId: itemId,
            respuesta: el.value,
            observaciones: obsEl ? obsEl.value : ''
        });
    });
    if (respuestas.length === 0) return;
    try {
        await apiCall(`/api/orden/${ordenId}/checklist`, 'POST', respuestas);
    } catch (e) {
        console.warn('No se pudo guardar el checklist automáticamente:', e);
    }
}

async function guardarChecklist(ordenId) {
    const inputs = document.querySelectorAll('[id^="cl_resp_"]');
    const respuestas = [];
    inputs.forEach(el => {
        const itemId = parseInt(el.id.replace('cl_resp_', ''));
        const obsEl = document.getElementById(`cl_obs_${itemId}`);
        respuestas.push({
            checklistItemId: itemId,
            respuesta: el.value,
            observaciones: obsEl ? obsEl.value : ''
        });
    });
    try {
        await apiCall(`/api/orden/${ordenId}/checklist`, 'POST', respuestas);
        showToast('Checklist guardado', 'success');
    } catch (e) {
        showToast('Error al guardar checklist', 'error');
    }
}

function renderRespuestaTag(resp) {
    if (!resp) return '-';
    if (resp === 'ok') return '<span class="tag tag-success">✅ OK</span>';
    if (resp === 'nok') return '<span class="tag tag-danger">❌ NOK</span>';
    if (resp === 'na') return '<span class="tag tag-muted">N/A</span>';
    return `<span class="tag tag-info">${resp}</span>`;
}

