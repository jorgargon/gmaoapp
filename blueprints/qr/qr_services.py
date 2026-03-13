"""
Servicios de generación de códigos QR y PDF de etiquetas para activos.
"""
import io
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas as pdf_canvas

from models import Planta, Zona, Linea, Maquina, Elemento


# ─── Generación QR ───────────────────────────────────────────────────────────

def generar_qr_bytes(equipo_tipo, equipo_id, base_url):
    """Genera PNG de un código QR que codifica la URL del activo."""
    url = f"{base_url.rstrip('/')}/movil/qr/{equipo_tipo}/{equipo_id}"
    img = qrcode.make(url, error_correction=qrcode.constants.ERROR_CORRECT_M,
                      box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


# ─── Recolección de activos según filtros ────────────────────────────────────

TIPOS_VALIDOS = ('empresa', 'planta', 'zona', 'linea', 'maquina', 'elemento')


def get_activos_filtrados(planta_id=None, zona_id=None, linea_id=None, maquina_id=None):
    """
    Devuelve lista de dicts {equipoTipo, equipoId, codigo, nombre}
    para todos los activos bajo la selección (desciende la jerarquía completa).
    """
    activos = []

    if maquina_id:
        maq = Maquina.query.get(maquina_id)
        if maq:
            activos.append(_activo_dict('maquina', maq))
            for e in Elemento.query.filter_by(maquinaId=maq.id).order_by(Elemento.nombre):
                activos.append(_activo_dict('elemento', e))
        return activos

    if linea_id:
        lin = Linea.query.get(linea_id)
        if lin:
            activos.append(_activo_dict('linea', lin))
            _add_maquinas_linea(lin.id, activos)
        return activos

    if zona_id:
        z = Zona.query.get(zona_id)
        if z:
            activos.append(_activo_dict('zona', z))
            for lin in Linea.query.filter_by(zonaId=z.id).order_by(Linea.nombre):
                activos.append(_activo_dict('linea', lin))
                _add_maquinas_linea(lin.id, activos)
        return activos

    if planta_id:
        p = Planta.query.get(planta_id)
        if p:
            activos.append(_activo_dict('planta', p))
            for z in Zona.query.filter_by(plantaId=p.id).order_by(Zona.nombre):
                activos.append(_activo_dict('zona', z))
                for lin in Linea.query.filter_by(zonaId=z.id).order_by(Linea.nombre):
                    activos.append(_activo_dict('linea', lin))
                    _add_maquinas_linea(lin.id, activos)
        return activos

    # Sin filtro: todas las plantas y descendientes
    for p in Planta.query.order_by(Planta.nombre):
        activos.append(_activo_dict('planta', p))
        for z in Zona.query.filter_by(plantaId=p.id).order_by(Zona.nombre):
            activos.append(_activo_dict('zona', z))
            for lin in Linea.query.filter_by(zonaId=z.id).order_by(Linea.nombre):
                activos.append(_activo_dict('linea', lin))
                _add_maquinas_linea(lin.id, activos)

    return activos


def _add_maquinas_linea(linea_id, activos):
    for maq in Maquina.query.filter_by(lineaId=linea_id).order_by(Maquina.nombre):
        activos.append(_activo_dict('maquina', maq))
        for e in Elemento.query.filter_by(maquinaId=maq.id).order_by(Elemento.nombre):
            activos.append(_activo_dict('elemento', e))


def _activo_dict(tipo, obj):
    return {
        'equipoTipo': tipo,
        'equipoId': obj.id,
        'codigo': obj.codigo,
        'nombre': obj.nombre,
    }


# ─── Helpers para filtros cascada ────────────────────────────────────────────

def get_plantas():
    return [{'id': p.id, 'nombre': p.nombre}
            for p in Planta.query.order_by(Planta.nombre).all()]


def get_zonas(planta_id):
    q = Zona.query.order_by(Zona.nombre)
    if planta_id:
        q = q.filter_by(plantaId=planta_id)
    return [{'id': z.id, 'nombre': z.nombre} for z in q.all()]


def get_lineas(zona_id):
    q = Linea.query.order_by(Linea.nombre)
    if zona_id:
        q = q.filter_by(zonaId=zona_id)
    return [{'id': l.id, 'nombre': l.nombre} for l in q.all()]


def get_maquinas(linea_id):
    q = Maquina.query.order_by(Maquina.nombre)
    if linea_id:
        q = q.filter_by(lineaId=linea_id)
    return [{'id': m.id, 'nombre': m.nombre} for m in q.all()]


# ─── Generación PDF de etiquetas ─────────────────────────────────────────────

# Etiqueta 70x37mm — 3 columnas x 8 filas = 24/pág A4
LABEL_W = 70 * mm
LABEL_H = 37 * mm
COLS = 3
ROWS = 8
PAGE_W, PAGE_H = A4  # 210x297 mm

# Márgenes para centrar la rejilla en A4
MARGIN_X = (PAGE_W - COLS * LABEL_W) / 2
MARGIN_Y = (PAGE_H - ROWS * LABEL_H) / 2

QR_SIZE = 23 * mm
QR_MARGIN = 4 * mm
TEXT_LEFT = QR_MARGIN + QR_SIZE + 4 * mm


def generar_pdf_etiquetas(activos, base_url):
    """Genera PDF A4 con etiquetas QR de 70x37mm (24 por página)."""
    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)

    total = len(activos)
    per_page = COLS * ROWS

    for idx, activo in enumerate(activos):
        page_idx = idx % per_page
        if idx > 0 and page_idx == 0:
            c.showPage()

        col = page_idx % COLS
        row = page_idx // COLS

        # Posición de la esquina inferior-izquierda de la etiqueta
        x = MARGIN_X + col * LABEL_W
        y = PAGE_H - MARGIN_Y - (row + 1) * LABEL_H

        _draw_label(c, x, y, activo, base_url)

    c.save()
    buf.seek(0)
    return buf


def _draw_label(c, x, y, activo, base_url):
    """Dibuja una etiqueta individual en la posición (x, y)."""
    # Borde punteado de corte
    c.saveState()
    c.setStrokeColor(colors.HexColor('#CCCCCC'))
    c.setDash(2, 2)
    c.rect(x, y, LABEL_W, LABEL_H, stroke=1, fill=0)
    c.restoreState()

    # Generar QR en memoria
    url = f"{base_url.rstrip('/')}/movil/qr/{activo['equipoTipo']}/{activo['equipoId']}"
    qr_img = qrcode.make(url, error_correction=qrcode.constants.ERROR_CORRECT_M,
                         box_size=10, border=1)
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format='PNG')
    qr_buf.seek(0)

    from reportlab.lib.utils import ImageReader
    qr_reader = ImageReader(qr_buf)

    # QR a la izquierda, centrado verticalmente
    qr_y = y + (LABEL_H - QR_SIZE) / 2
    c.drawImage(qr_reader, x + QR_MARGIN, qr_y, QR_SIZE, QR_SIZE)

    # Texto a la derecha del QR
    text_x = x + TEXT_LEFT
    text_max_w = LABEL_W - TEXT_LEFT - 3 * mm

    # Código en negrita
    c.setFont('Helvetica-Bold', 9)
    codigo = activo['codigo'] or ''
    c.drawString(text_x, y + LABEL_H - 12 * mm, _truncate(codigo, text_max_w, c))

    # Nombre
    c.setFont('Helvetica', 7.5)
    nombre = activo['nombre'] or ''
    # Si el nombre es largo, dividir en dos líneas
    lines = _wrap_text(nombre, text_max_w, c)
    line_y = y + LABEL_H - 18 * mm
    for line in lines[:2]:
        c.drawString(text_x, line_y, line)
        line_y -= 9

    # Tipo de activo en gris pequeño
    c.setFont('Helvetica', 6)
    c.setFillColor(colors.HexColor('#888888'))
    tipo_label = {'planta': 'Planta', 'zona': 'Zona', 'linea': 'Línea',
                  'maquina': 'Máquina', 'elemento': 'Elemento'}.get(activo['equipoTipo'], '')
    c.drawString(text_x, y + 3 * mm, tipo_label)
    c.setFillColor(colors.black)


def _truncate(text, max_w, c):
    """Trunca texto si excede el ancho máximo."""
    if c.stringWidth(text) <= max_w:
        return text
    while text and c.stringWidth(text + '…') > max_w:
        text = text[:-1]
    return text + '…'


def _wrap_text(text, max_w, c):
    """Divide texto en líneas que quepan en max_w."""
    words = text.split()
    lines = []
    current = ''
    for word in words:
        test = f"{current} {word}".strip()
        if c.stringWidth(test) <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or ['']
