import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageWin

try:
    import win32print
    import win32ui
except ImportError:
    win32print = None
    win32ui = None

try:
    from database.db import get_connection
except Exception:
    get_connection = None


# =========================================================
# CONFIGURACION
# =========================================================

NOMBRE_IMPRESORA = "POS-58"
ANCHO_TICKET = 384

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.normpath(os.path.join(BASE_DIR, ".."))

RUTA_LOGO = os.path.join(PROJECT_DIR, "static", "logo_impresion.png")
RUTA_LOGO = os.path.normpath(RUTA_LOGO)

NOMBRE_GARAJE = "GARAGE"
TITULO_TICKET = "TICKET DE PARQUEO"

CLAVE_MULTA_TICKET_PERDIDO = "MULTA_TICKET_PERDIDO"
MULTA_TICKET_DEFAULT = 50.00


# =========================================================
# CONFIGURACION DESDE BD
# =========================================================

def _table_exists(cursor, table_name):
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name = ?",
            (table_name,),
        )
        return int(cursor.fetchone()[0] or 0) > 0
    except Exception:
        return False


def _column_exists(cursor, table_name, column_name):
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return any(row[1] == column_name for row in cursor.fetchall())
    except Exception:
        return False


def asegurar_configuracion_multa():
    """
    Respaldo para que el ticket no falle aunque schema.py todavía no haya migrado la BD.
    Crea CONFIGURACION y guarda MULTA_TICKET_PERDIDO si no existe.
    """
    if get_connection is None:
        return

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS CONFIGURACION (
                Configuracion INTEGER PRIMARY KEY AUTOINCREMENT,
                Clave TEXT NOT NULL UNIQUE,
                Valor TEXT NOT NULL,
                Descripcion TEXT,
                Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),
                Usr INTEGER NOT NULL DEFAULT 0,
                UsrFecha TEXT NOT NULL DEFAULT (date('now', 'localtime')),
                UsrHora TEXT NOT NULL DEFAULT (time('now', 'localtime')),
                FechaCreacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FechaModificacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO CONFIGURACION (
                Clave,
                Valor,
                Descripcion,
                Estado,
                Usr,
                UsrFecha,
                UsrHora,
                FechaCreacion,
                FechaModificacion
            )
            VALUES (
                ?, ?, ?, 1, 0,
                date('now','localtime'),
                time('now','localtime'),
                datetime('now','localtime'),
                datetime('now','localtime')
            )
        """, (
            CLAVE_MULTA_TICKET_PERDIDO,
            f"{MULTA_TICKET_DEFAULT:.2f}",
            "Monto de multa por pérdida de ticket",
        ))

        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()


def obtener_multa_ticket_perdido():
    """
    Lee la multa desde CONFIGURACION.
    Si no existe o hay error, devuelve 50.00 para no romper impresión.
    """
    if get_connection is None:
        return MULTA_TICKET_DEFAULT

    conn = get_connection()
    cursor = conn.cursor()

    try:
        asegurar_configuracion_multa()

        cursor.execute("""
            SELECT Valor
            FROM CONFIGURACION
            WHERE Clave = ?
              AND Estado = 1
            LIMIT 1
        """, (CLAVE_MULTA_TICKET_PERDIDO,))

        row = cursor.fetchone()
        if not row:
            return MULTA_TICKET_DEFAULT

        try:
            valor = row["Valor"]
        except Exception:
            valor = row[0]

        monto = float(str(valor).replace(",", "."))
        if monto < 0:
            return MULTA_TICKET_DEFAULT

        return monto

    except Exception:
        return MULTA_TICKET_DEFAULT
    finally:
        conn.close()


def actualizar_multa_ticket_perdido(monto, usr=0):
    """
    Función utilitaria para cuando luego agregues pantalla de configuración.
    """
    monto = float(str(monto).replace(",", "."))
    if monto < 0:
        raise ValueError("La multa no puede ser negativa.")

    asegurar_configuracion_multa()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO CONFIGURACION (
                Clave,
                Valor,
                Descripcion,
                Estado,
                Usr,
                UsrFecha,
                UsrHora,
                FechaCreacion,
                FechaModificacion
            )
            VALUES (
                ?, ?, ?, 1, ?,
                date('now','localtime'),
                time('now','localtime'),
                datetime('now','localtime'),
                datetime('now','localtime')
            )
            ON CONFLICT(Clave) DO UPDATE SET
                Valor = excluded.Valor,
                Descripcion = excluded.Descripcion,
                Estado = 1,
                Usr = excluded.Usr,
                UsrFecha = date('now','localtime'),
                UsrHora = time('now','localtime'),
                FechaModificacion = datetime('now','localtime')
        """, (
            CLAVE_MULTA_TICKET_PERDIDO,
            f"{monto:.2f}",
            "Monto de multa por pérdida de ticket",
            usr,
        ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def formatear_monto(monto):
    try:
        monto = float(monto)
    except Exception:
        monto = MULTA_TICKET_DEFAULT

    if monto == int(monto):
        return str(int(monto))

    return f"{monto:.2f}"


def mensaje_multa_ticket(multa_ticket_perdido=None):
    if multa_ticket_perdido is None:
        multa_ticket_perdido = obtener_multa_ticket_perdido()

    return [
        "En caso de perder el ticket",
        f"la multa es de {formatear_monto(multa_ticket_perdido)} Bs."
    ]


# =========================================================
# FUENTES
# =========================================================

def obtener_fuente(size=22, bold=False):
    if bold:
        posibles_fuentes = [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
            r"C:\Windows\Fonts\verdanab.ttf",
            r"C:\Windows\Fonts\tahomabd.ttf",
        ]
    else:
        posibles_fuentes = [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
            r"C:\Windows\Fonts\verdana.ttf",
            r"C:\Windows\Fonts\tahoma.ttf",
        ]

    for ruta in posibles_fuentes:
        if os.path.exists(ruta):
            try:
                return ImageFont.truetype(ruta, size)
            except Exception:
                continue

    return ImageFont.load_default()


# =========================================================
# HELPERS DE DIBUJO
# =========================================================

def text_bbox(draw, text, font):
    return draw.textbbox((0, 0), text, font=font)


def text_width(draw, text, font):
    bbox = text_bbox(draw, text, font)
    return bbox[2] - bbox[0]


def text_height(draw, text, font):
    bbox = text_bbox(draw, text, font)
    return bbox[3] - bbox[1]


def draw_centered_text(draw, y, text, font, fill=0):
    x = (ANCHO_TICKET - text_width(draw, text, font)) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return y + text_height(draw, text, font)


def draw_left_text(draw, x, y, texto, font, fill=0):
    draw.text((x, y), texto, font=font, fill=fill)
    return y + text_height(draw, texto, font)


def draw_separator(draw, y, grosor=2, margen=12):
    for i in range(grosor):
        draw.line((margen, y + i, ANCHO_TICKET - margen, y + i), fill=0, width=1)
    return y + grosor


# =========================================================
# LOGO
# =========================================================

def cargar_logo(max_width=260, max_height=115):
    if not os.path.exists(RUTA_LOGO):
        return None

    try:
        img = Image.open(RUTA_LOGO)

        if img.mode in ("RGBA", "LA"):
            fondo = Image.new("RGBA", img.size, (255, 255, 255, 255))
            fondo.paste(img, (0, 0), img)
            img = fondo.convert("RGB")
        else:
            img = img.convert("RGB")

        img = img.convert("L")

        w, h = img.size
        if w <= 0 or h <= 0:
            return None

        ratio = min(max_width / w, max_height / h)
        nuevo_w = max(1, int(w * ratio))
        nuevo_h = max(1, int(h * ratio))

        img = img.resize((nuevo_w, nuevo_h), Image.LANCZOS)

        img = img.point(lambda p: 0 if p < 220 else 255, "1")

        return img.convert("1")
    except Exception:
        return None


# =========================================================
# CREAR TICKET
# =========================================================

def crear_imagen_ticket(codigo, placa, fecha, hora_ingreso, multa_ticket_perdido=None):
    alto_estimado = 650
    img = Image.new("1", (ANCHO_TICKET, alto_estimado), 255)
    draw = ImageDraw.Draw(img)

    font_logo_text = obtener_fuente(18, bold=True)
    font_titulo = obtener_fuente(17, bold=True)
    font_codigo = obtener_fuente(18, bold=True)
    font_info = obtener_fuente(14, bold=False)
    font_multa = obtener_fuente(12, bold=False)

    y = 6

    # -----------------------------------------------------
    # LOGO
    # -----------------------------------------------------
    logo = cargar_logo(max_width=260, max_height=115)
    if logo:
        logo_x = (ANCHO_TICKET - logo.width) // 2
        img.paste(logo, (logo_x, y))
        y += logo.height + 4
    else:
        y = draw_centered_text(draw, y, NOMBRE_GARAJE, font_logo_text)
        y += 2

    # -----------------------------------------------------
    # TITULO
    # -----------------------------------------------------
    y = draw_centered_text(draw, y, TITULO_TICKET, font_titulo)
    y += 6

    y = draw_separator(draw, y, grosor=2)
    y += 8

    # -----------------------------------------------------
    # CODIGO
    # -----------------------------------------------------
    y = draw_centered_text(draw, y, f"Codigo: {codigo}", font_codigo)
    y += 8

    # -----------------------------------------------------
    # DATOS
    # -----------------------------------------------------
    margen_izq = 22

    y = draw_left_text(draw, margen_izq, y, f"Placa: {placa}", font_info)
    y += 3

    y = draw_left_text(draw, margen_izq, y, f"Fecha: {fecha}", font_info)
    y += 3

    y = draw_left_text(draw, margen_izq, y, f"Hora ingreso: {hora_ingreso}", font_info)
    y += 8

    y = draw_separator(draw, y, grosor=2)
    y += 10

    # -----------------------------------------------------
    # MENSAJE MULTA
    # -----------------------------------------------------
    for linea in mensaje_multa_ticket(multa_ticket_perdido):
        y = draw_centered_text(draw, y, linea, font_multa)
        y += 2

    y += 10

    img = img.crop((0, 0, ANCHO_TICKET, y))
    return img


# =========================================================
# IMPRESION WINDOWS
# =========================================================

def imprimir_imagen_windows(imagen, nombre_impresora=None):
    if nombre_impresora is None:
        nombre_impresora = NOMBRE_IMPRESORA

    hprinter = win32print.OpenPrinter(nombre_impresora)
    try:
        win32print.GetPrinter(hprinter, 2)
    finally:
        win32print.ClosePrinter(hprinter)

    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(nombre_impresora)

    HORZRES = 8
    VERTRES = 10
    PHYSICALWIDTH = 110
    PHYSICALHEIGHT = 111

    printable_area = (
        hdc.GetDeviceCaps(HORZRES),
        hdc.GetDeviceCaps(VERTRES)
    )
    printer_size = (
        hdc.GetDeviceCaps(PHYSICALWIDTH),
        hdc.GetDeviceCaps(PHYSICALHEIGHT)
    )

    bmp = imagen.convert("RGB")
    dib = ImageWin.Dib(bmp)

    img_width, img_height = bmp.size

    escala = min(printable_area[0] / img_width, 1.0)
    scaled_width = int(img_width * escala)
    scaled_height = int(img_height * escala)

    x1 = (printer_size[0] - scaled_width) // 2
    y1 = 0
    x2 = x1 + scaled_width
    y2 = y1 + scaled_height

    hdc.StartDoc("Ticket de Parqueo")
    hdc.StartPage()
    dib.draw(hdc.GetHandleOutput(), (x1, y1, x2, y2))
    hdc.EndPage()
    hdc.EndDoc()
    hdc.DeleteDC()


# =========================================================
# FUNCIONES PRINCIPALES
# =========================================================

def imprimir_ticket(
    codigo,
    placa,
    fecha=None,
    hora_ingreso=None,
    nombre_impresora=None,
    multa_ticket_perdido=None
):
    ahora = datetime.now()

    if not fecha:
        fecha = ahora.strftime("%d/%m/%Y")

    if not hora_ingreso:
        hora_ingreso = ahora.strftime("%H:%M")

    imagen_ticket = crear_imagen_ticket(
        codigo=codigo,
        placa=placa,
        fecha=fecha,
        hora_ingreso=hora_ingreso,
        multa_ticket_perdido=multa_ticket_perdido
    )

    imprimir_imagen_windows(imagen_ticket, nombre_impresora=nombre_impresora)
    return True


def guardar_preview_ticket(
    codigo,
    placa,
    fecha=None,
    hora_ingreso=None,
    ruta_salida=None,
    multa_ticket_perdido=None
):
    ahora = datetime.now()

    if not fecha:
        fecha = ahora.strftime("%d/%m/%Y")

    if not hora_ingreso:
        hora_ingreso = ahora.strftime("%H:%M")

    if ruta_salida is None:
        ruta_salida = os.path.join(BASE_DIR, "ticket_preview.png")

    imagen_ticket = crear_imagen_ticket(
        codigo=codigo,
        placa=placa,
        fecha=fecha,
        hora_ingreso=hora_ingreso,
        multa_ticket_perdido=multa_ticket_perdido
    )
    imagen_ticket.save(ruta_salida)
    return ruta_salida


# =========================================================
# PRUEBA DIRECTA
# =========================================================

# if __name__ == "__main__":
#     try:
#         print("Ruta logo:", RUTA_LOGO)
#         print("Existe logo:", os.path.exists(RUTA_LOGO))
#
#         ruta = guardar_preview_ticket(
#             codigo="ABC12345",
#             placa="1234-ABC",
#             fecha="11/04/2026",
#             hora_ingreso="14:35"
#         )
#         print(f"Vista previa guardada en: {ruta}")
#
#         # imprimir_ticket(
#         #     codigo="ABC12345",
#         #     placa="1234-ABC",
#         #     fecha="11/04/2026",
#         #     hora_ingreso="14:35"
#         # )
#         # print("Ticket impreso correctamente.")
#
#     except Exception as e:
#         print("Error al generar o imprimir el ticket:")
#         print(str(e))
