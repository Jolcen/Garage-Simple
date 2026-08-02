
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import calendar

from database.db import get_connection

try:
    from modules.payment import abrir_cobro_contrato
except Exception:
    abrir_cobro_contrato = None


# =========================================================
# CATÁLOGOS
# =========================================================
ESTADO_INACTIVO = 0
ESTADO_ACTIVO = 1
ESTADO_VENCIDO = 2
ESTADO_SUSPENDIDO = 3
ESTADO_CANCELADO = 4
ESTADO_FINALIZADO = 5

ESTADO_PAGO_PENDIENTE = 0
ESTADO_PAGO_PAGADO = 1

METODO_PAGO = {
    1: "Efectivo",
    2: "QR",
}
METODO_PAGO_INV = {v: k for k, v in METODO_PAGO.items()}

CLASE_ESTANDAR = 1
CLASE_ESPECIAL = 2

CLASE_CONTRATO = {
    CLASE_ESTANDAR: "Estándar",
    CLASE_ESPECIAL: "Especial",
}
CLASE_CONTRATO_INV = {v: k for k, v in CLASE_CONTRATO.items()}

TIPO_TARIFA_HORA = 1
TIPO_TARIFA_NOCTURNA = 2
TIPO_TARIFA_CONTRATO = 3
TIPO_DIA_CONTRATO = 4

TIPO_OPERACION_CONTRATO = 2
ESTADO_OPERACION_FINALIZADO = 2
ESTADO_PAGO_REGISTRADO = 1

TIPO_CLIENTE_TODOS = "Todos"
TIPO_CLIENTE_GENERAL = "GENERAL"
TIPO_CLIENTE_ESTUDIANTE = "ESTUDIANTE"

HORAS_CONTRATO = [3, 6, 9, 12, 24]
MONTOS_FALLBACK_AUTO = {
    3: 250.0,
    6: 300.0,
    9: 350.0,
    12: 400.0,
    24: 500.0,
}

COLOR_BG = "#f5f5f5"
COLOR_CARD = "#ffffff"
COLOR_TEXT = "#111111"
COLOR_MUTED = "#555555"
COLOR_DARK = "#111827"
COLOR_LIGHT = "#ffffff"
COLOR_BORDER = "#9ca3af"
COLOR_DANGER = "#991b1b"


# =========================================================
# FECHAS / UTILIDADES
# =========================================================
def fecha_actual_db():
    return datetime.now().strftime("%Y-%m-%d")


def fecha_actual_form():
    return datetime.now().strftime("%d/%m/%Y")


def fecha_db_a_form(valor):
    if not valor:
        return ""
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return str(valor)


def fecha_form_a_db(valor):
    valor = (valor or "").strip()
    if not valor:
        raise ValueError("La fecha no puede estar vacía.")

    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor, formato).strftime("%Y-%m-%d")
        except ValueError:
            pass

    raise ValueError("La fecha debe tener formato dd/mm/yyyy.")


def sumar_meses_menos_un_dia(fecha_inicio_db, meses):
    """
    Si inicia 02/05/2025 por 1 mes, termina 01/06/2025.
    """
    fecha = datetime.strptime(fecha_inicio_db, "%Y-%m-%d")
    year = fecha.year + (fecha.month - 1 + meses) // 12
    month = (fecha.month - 1 + meses) % 12 + 1
    day = min(fecha.day, calendar.monthrange(year, month)[1])
    nueva = fecha.replace(year=year, month=month, day=day)
    nueva = nueva - timedelta(days=1)
    return nueva.strftime("%Y-%m-%d")


def sumar_dias_db(fecha_db, dias):
    fecha = datetime.strptime(str(fecha_db)[:10], "%Y-%m-%d")
    return (fecha + timedelta(days=dias)).strftime("%Y-%m-%d")


def fecha_base_renovacion(fecha_fin_db):
    """
    Regla de renovación:
    - Si el contrato aún está dentro de su periodo, se amplía desde su fecha fin actual.
    - Si el contrato ya venció, la renovación empieza desde hoy.
    """
    hoy = fecha_actual_db()
    fecha_fin_db = str(fecha_fin_db or "")[:10]
    if fecha_fin_db and fecha_fin_db >= hoy:
        return fecha_fin_db
    return hoy


def contrato_esta_vigente_por_fecha(fecha_fin_db):
    fecha_fin_db = str(fecha_fin_db or "")[:10]
    return bool(fecha_fin_db and fecha_fin_db >= fecha_actual_db())


def obtener_usuario_id(user_data):
    user_data = user_data or {}
    return user_data.get("Usuario") or user_data.get("id") or 0


def obtener_rol_usuario(user_data):
    user_data = user_data or {}
    valor = (
        user_data.get("Rol")
        or user_data.get("rol")
        or user_data.get("Role")
        or user_data.get("role")
        or ""
    )
    if isinstance(valor, int):
        return "admin" if valor == 1 else "empleado"
    return str(valor).strip().lower()


def es_admin(user_data):
    return obtener_rol_usuario(user_data) in ("admin", "administrador")


def es_empleado(user_data):
    return obtener_rol_usuario(user_data) == "empleado"


def row_get(row, key, default=None):
    if row is None:
        return default
    try:
        return row[key]
    except Exception:
        return default


def nombre_cliente(row):
    nombres = str(row_get(row, "Nombres", "") or "").strip()
    apellidos = str(row_get(row, "Apellidos", "") or "").strip()
    return f"{nombres} {apellidos}".strip()


def texto(valor):
    return "" if valor is None else str(valor)


def normalizar(valor):
    return str(valor or "").strip().upper()


def limpiar_placa(valor):
    return str(valor or "").replace(" ", "").replace("-", "").upper().strip()


def centrar_ventana(window, width, height, parent=None):
    window.update_idletasks()
    try:
        if parent:
            parent.update_idletasks()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw // 2) - (width // 2)
            y = py + (ph // 2) - (height // 2)
        else:
            sw = window.winfo_screenwidth()
            sh = window.winfo_screenheight()
            x = (sw // 2) - (width // 2)
            y = (sh // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
    except Exception:
        window.geometry(f"{width}x{height}")


def app_base_path():
    current = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(current, ".."))


def static_path(filename):
    return os.path.join(app_base_path(), "static", filename)


# =========================================================
# ESTILO
# =========================================================
def configurar_estilo_treeview():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        "Contratos.Treeview",
        background="#ffffff",
        foreground="#111111",
        rowheight=28,
        fieldbackground="#ffffff",
        borderwidth=0,
        relief="flat",
        font=("Arial", 10),
    )
    style.configure(
        "Contratos.Treeview.Heading",
        background="#eeeeee",
        foreground="#111111",
        font=("Arial", 10, "bold"),
        borderwidth=1,
        relief="flat",
    )
    style.map(
        "Contratos.Treeview",
        background=[("selected", "#d9e8ff")],
        foreground=[("selected", "#111111")],
    )


def configurar_estilo_combobox():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        "Simple.TCombobox",
        fieldbackground="#ffffff",
        background="#ffffff",
        foreground="#111111",
        arrowcolor="#111111",
        bordercolor="#999999",
        lightcolor="#999999",
        darkcolor="#999999",
        padding=3,
    )


class SimpleButton(tk.Button):
    def __init__(self, master, text, command=None, primary=False, danger=False, **kwargs):
        bg = COLOR_DARK if primary else "#ffffff"
        fg = "#ffffff" if primary else "#111111"
        active_bg = "#374151" if primary else "#eeeeee"

        if danger:
            bg = "#ffffff"
            fg = COLOR_DANGER
            active_bg = "#fee2e2"

        super().__init__(
            master,
            text=text,
            command=command,
            font=("Arial", 10, "bold" if primary else "normal"),
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            bd=1,
            relief="solid",
            padx=14,
            pady=8,
            cursor="hand2",
            **kwargs
        )


# =========================================================
# MIGRACIÓN SUAVE PARA CONTRATOS
# =========================================================
def columna_existe(cursor, tabla, columna):
    cursor.execute(f"PRAGMA table_info({tabla})")
    return columna in [r[1] for r in cursor.fetchall()]


def agregar_columna_si_no_existe(cursor, tabla, columna, definicion):
    if not columna_existe(cursor, tabla, columna):
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")


def asegurar_columnas_contrato():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        agregar_columna_si_no_existe(cursor, "CONTRATO", "ClaseContrato", "INTEGER NOT NULL DEFAULT 1")
        agregar_columna_si_no_existe(cursor, "CONTRATO", "TarifaDetalle", "INTEGER")
        agregar_columna_si_no_existe(cursor, "CONTRATO", "HorasPermitidasDia", "INTEGER")
        agregar_columna_si_no_existe(cursor, "CONTRATO", "EstadoPago", "INTEGER NOT NULL DEFAULT 0")
        agregar_columna_si_no_existe(cursor, "CONTRATO", "MetodoPago", "INTEGER")
        agregar_columna_si_no_existe(cursor, "CONTRATO", "FechaPago", "TEXT")
        agregar_columna_si_no_existe(cursor, "CONTRATO", "MontoPagado", "REAL NOT NULL DEFAULT 0")
        agregar_columna_si_no_existe(cursor, "CONTRATO", "UsuarioPago", "INTEGER")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS CONTRATOVEHICULO (
                ContratoVehiculo INTEGER PRIMARY KEY AUTOINCREMENT,
                Contrato INTEGER NOT NULL,
                Vehiculo INTEGER NOT NULL,
                Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),
                Usr INTEGER NOT NULL DEFAULT 0,
                UsrFecha TEXT NOT NULL DEFAULT (date('now', 'localtime')),
                UsrHora TEXT NOT NULL DEFAULT (time('now', 'localtime')),
                FechaCreacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FechaModificacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (Contrato) REFERENCES CONTRATO(Contrato)
                    ON UPDATE CASCADE
                    ON DELETE CASCADE,
                FOREIGN KEY (Vehiculo) REFERENCES VEHICULO(Vehiculo)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT,
                UNIQUE (Contrato, Vehiculo)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS IDX_CONTRATOVEHICULO_Contrato
            ON CONTRATOVEHICULO(Contrato)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS IDX_CONTRATOVEHICULO_Vehiculo
            ON CONTRATOVEHICULO(Vehiculo)
        """)

        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# =========================================================
# DATOS
# =========================================================
def generar_codigo_contrato(clase_contrato):
    prefijo = "EST" if int(clase_contrato) == CLASE_ESTANDAR else "ESP"
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        asegurar_columnas_contrato()
        cursor.execute(
            """
            SELECT IFNULL(MAX(Contrato), 0) + 1 AS Siguiente
            FROM CONTRATO
            WHERE CodigoContrato LIKE ?
            """,
            (f"{prefijo}-%",),
        )
        fila = cursor.fetchone()
        siguiente = int(row_get(fila, "Siguiente", fila[0] if fila else 1) or 1)
        return f"{prefijo}-{siguiente:04d}"
    finally:
        if conn:
            conn.close()


def obtener_clientes():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        tipo_cliente_select = "TipoCliente" if columna_existe(cursor, "CLIENTE", "TipoCliente") else "'GENERAL' AS TipoCliente"
        cursor.execute(f"""
            SELECT Cliente, Nombres, Apellidos, Telefono, {tipo_cliente_select}
            FROM CLIENTE
            WHERE Estado = 1
            ORDER BY Nombres, Apellidos
        """)
        return cursor.fetchall()
    finally:
        if conn:
            conn.close()


def formatear_cliente(row):
    nombre = nombre_cliente(row)
    tipo_cliente = row_get(row, "TipoCliente", "GENERAL") or "GENERAL"
    telefono = row_get(row, "Telefono", "") or ""
    partes = [nombre]
    if tipo_cliente:
        partes.append(tipo_cliente)
    if telefono:
        partes.append(str(telefono))
    return " | ".join(partes)


def obtener_vehiculos():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                V.Vehiculo,
                V.Cliente,
                V.Placa,
                V.TipoVehiculo,
                COALESCE(TV.Nombre, CAST(V.TipoVehiculo AS TEXT)) AS TipoVehiculoNombre,
                V.Marca,
                V.Modelo,
                V.Color,
                C.Nombres,
                C.Apellidos,
                C.Telefono,
                COALESCE(C.TipoCliente, 'GENERAL') AS TipoCliente
            FROM VEHICULO V
            INNER JOIN CLIENTE C ON C.Cliente = V.Cliente
            LEFT JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = V.TipoVehiculo
            WHERE V.Estado = 1
              AND V.Cliente IS NOT NULL
            ORDER BY C.Nombres, C.Apellidos, V.Placa
        """)
        return cursor.fetchall()
    finally:
        if conn:
            conn.close()


def formatear_vehiculo(row):
    placa = str(row_get(row, "Placa", "") or "").strip()
    tipo = str(row_get(row, "TipoVehiculoNombre", "") or "").strip()
    modelo = str(row_get(row, "Marca", "") or row_get(row, "Modelo", "") or "").strip()
    color = str(row_get(row, "Color", "") or "").strip()

    partes = [placa]
    if tipo:
        partes.append(tipo)
    if modelo:
        partes.append(modelo)
    if color:
        partes.append(color)

    return " | ".join(partes)


def vehiculo_display_corto(row):
    placa = str(row_get(row, "Placa", "") or "").strip()
    color = str(row_get(row, "Color", "") or "").strip()
    modelo = str(row_get(row, "Marca", "") or row_get(row, "Modelo", "") or "").strip()
    partes = []
    if placa:
        partes.append(placa)
    if color:
        partes.append(color)
    if modelo:
        partes.append(modelo)
    return " | ".join(partes)


def obtener_vehiculos_contrato(contrato_id):
    asegurar_columnas_contrato()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                V.Vehiculo,
                V.Cliente,
                V.Placa,
                V.TipoVehiculo,
                COALESCE(TV.Nombre, CAST(V.TipoVehiculo AS TEXT)) AS TipoVehiculoNombre,
                V.Marca,
                V.Modelo,
                V.Color
            FROM CONTRATOVEHICULO CV
            INNER JOIN VEHICULO V ON V.Vehiculo = CV.Vehiculo
            LEFT JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = V.TipoVehiculo
            WHERE CV.Contrato = ?
              AND CV.Estado = 1
            ORDER BY V.Placa ASC
        """, (contrato_id,))
        rows = cursor.fetchall()

        if rows:
            return rows

        cursor.execute("""
            SELECT
                V.Vehiculo,
                V.Cliente,
                V.Placa,
                V.TipoVehiculo,
                COALESCE(TV.Nombre, CAST(V.TipoVehiculo AS TEXT)) AS TipoVehiculoNombre,
                V.Marca,
                V.Modelo,
                V.Color
            FROM CONTRATO C
            INNER JOIN VEHICULO V ON V.Vehiculo = C.Vehiculo
            LEFT JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = V.TipoVehiculo
            WHERE C.Contrato = ?
        """, (contrato_id,))
        row = cursor.fetchone()
        return [row] if row else []
    finally:
        if conn:
            conn.close()


def sincronizar_vehiculos_contrato(cursor, contrato_id, vehiculo_ids, usr=0):
    vehiculo_ids_limpios = []
    for vehiculo_id in vehiculo_ids or []:
        try:
            vehiculo_id = int(vehiculo_id)
            if vehiculo_id not in vehiculo_ids_limpios:
                vehiculo_ids_limpios.append(vehiculo_id)
        except Exception:
            pass

    if not vehiculo_ids_limpios:
        raise ValueError("Debes seleccionar al menos un vehículo para el contrato.")

    cursor.execute("DELETE FROM CONTRATOVEHICULO WHERE Contrato = ?", (contrato_id,))

    for vehiculo_id in vehiculo_ids_limpios:
        cursor.execute("""
            INSERT INTO CONTRATOVEHICULO (
                Contrato,
                Vehiculo,
                Estado,
                Usr,
                UsrFecha,
                UsrHora,
                FechaCreacion,
                FechaModificacion
            )
            VALUES (
                ?, ?, 1, ?,
                date('now','localtime'),
                time('now','localtime'),
                datetime('now','localtime'),
                datetime('now','localtime')
            )
        """, (contrato_id, vehiculo_id, usr))


def obtener_vehiculo_principal(vehiculo_ids):
    if not vehiculo_ids:
        return None
    return int(vehiculo_ids[0])


def obtener_tarifas_contrato_auto():
    """
    Devuelve planes estándar por horas permitidas. Usa TARIFADETALLE.HorasPermitidasDia.
    Si no encuentra registros, usa los montos base indicados por el cliente.
    """
    tarifas = {}
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if not columna_existe(cursor, "TARIFADETALLE", "HorasPermitidasDia"):
            return dict(MONTOS_FALLBACK_AUTO)

        cursor.execute("""
            SELECT
                TD.TarifaDetalle,
                TD.HorasPermitidasDia,
                TD.Monto
            FROM TARIFADETALLE TD
            INNER JOIN TARIFA T ON T.Tarifa = TD.Tarifa
            LEFT JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = T.TipoVehiculo
            WHERE T.Estado = 1
              AND TD.Estado = 1
              AND T.TipoTarifa = ?
              AND TD.TipoDia = ?
              AND UPPER(COALESCE(TV.Nombre, CAST(T.TipoVehiculo AS TEXT))) = 'AUTO'
              AND TD.HorasPermitidasDia IS NOT NULL
            ORDER BY TD.HorasPermitidasDia ASC
        """, (TIPO_TARIFA_CONTRATO, TIPO_DIA_CONTRATO))

        for row in cursor.fetchall():
            horas = int(row_get(row, "HorasPermitidasDia", 0) or 0)
            monto = float(row_get(row, "Monto", 0) or 0)
            if horas > 0 and monto > 0:
                tarifas[horas] = {
                    "TarifaDetalle": row_get(row, "TarifaDetalle"),
                    "Monto": monto,
                }
    except Exception:
        tarifas = {}
    finally:
        if conn:
            conn.close()

    if not tarifas:
        return {h: {"TarifaDetalle": None, "Monto": m} for h, m in MONTOS_FALLBACK_AUTO.items()}

    for h, m in MONTOS_FALLBACK_AUTO.items():
        if h not in tarifas:
            tarifas[h] = {"TarifaDetalle": None, "Monto": m}

    return tarifas


def obtener_contrato_por_id(contrato_id):
    asegurar_columnas_contrato()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                C.Contrato,
                C.CodigoContrato,
                C.Cliente,
                C.Vehiculo,
                C.FechaInicio,
                C.FechaFin,
                C.DuracionMes,
                C.MontoContrato,
                C.ModalidadPago,
                C.EspacioAsignado,
                C.Observacion,
                C.Estado,
                C.ClaseContrato,
                C.TarifaDetalle,
                C.HorasPermitidasDia,
                C.EstadoPago,
                C.MetodoPago,
                C.FechaPago,
                C.MontoPagado,
                C.UsuarioPago,
                CL.Nombres,
                CL.Apellidos,
                CL.Telefono,
                COALESCE(CL.TipoCliente, 'GENERAL') AS TipoCliente,
                V.Placa,
                V.TipoVehiculo,
                COALESCE(TV.Nombre, CAST(V.TipoVehiculo AS TEXT)) AS TipoVehiculoNombre,
                V.Marca,
                V.Modelo,
                V.Color
            FROM CONTRATO C
            INNER JOIN CLIENTE CL ON CL.Cliente = C.Cliente
            INNER JOIN VEHICULO V ON V.Vehiculo = C.Vehiculo
            LEFT JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = V.TipoVehiculo
            WHERE C.Contrato = ?
        """, (contrato_id,))
        return cursor.fetchone()
    finally:
        if conn:
            conn.close()


def estado_visible_contrato(row):
    estado = int(row_get(row, "Estado", ESTADO_ACTIVO) or ESTADO_ACTIVO)
    estado_pago = int(row_get(row, "EstadoPago", ESTADO_PAGO_PENDIENTE) or ESTADO_PAGO_PENDIENTE)
    fecha_fin = str(row_get(row, "FechaFin", "") or "")

    if estado == ESTADO_SUSPENDIDO:
        return "Suspendido"
    if estado == ESTADO_VENCIDO:
        return "Vencido"

    try:
        if fecha_fin and fecha_fin < fecha_actual_db():
            return "Vencido"
    except Exception:
        pass

    if estado_pago == ESTADO_PAGO_PAGADO:
        return "Pagado"

    return "Pendiente"


def obtener_contratos(busqueda="", estado_visible="Todos", clase="Todos", tipo_cliente="Todos"):
    asegurar_columnas_contrato()

    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
            SELECT
                C.Contrato,
                C.CodigoContrato,
                C.Cliente,
                C.Vehiculo,
                C.FechaInicio,
                C.FechaFin,
                C.DuracionMes,
                C.MontoContrato,
                C.ModalidadPago,
                C.Estado,
                C.ClaseContrato,
                C.HorasPermitidasDia,
                C.EstadoPago,
                C.MetodoPago,
                C.FechaPago,
                C.MontoPagado,
                CL.Nombres,
                CL.Apellidos,
                CL.Telefono,
                COALESCE(CL.TipoCliente, 'GENERAL') AS TipoCliente,

                COALESCE(GROUP_CONCAT(DISTINCT VV.Placa), V.Placa) AS Placa,
                COALESCE(GROUP_CONCAT(DISTINCT NULLIF(VV.Color, '')), V.Color) AS Color,
                COALESCE(
                    GROUP_CONCAT(DISTINCT NULLIF(COALESCE(VV.Marca, VV.Modelo), '')),
                    COALESCE(V.Marca, V.Modelo)
                ) AS Marca,

                COALESCE(TV.Nombre, CAST(V.TipoVehiculo AS TEXT)) AS TipoVehiculoNombre
            FROM CONTRATO C
            INNER JOIN CLIENTE CL ON CL.Cliente = C.Cliente
            INNER JOIN VEHICULO V ON V.Vehiculo = C.Vehiculo
            LEFT JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = V.TipoVehiculo

            LEFT JOIN CONTRATOVEHICULO CV
                   ON CV.Contrato = C.Contrato
                  AND CV.Estado = 1

            LEFT JOIN VEHICULO VV
                   ON VV.Vehiculo = CV.Vehiculo

            WHERE 1 = 1
        """
        params = []

        if busqueda.strip():
            like = f"%{busqueda.strip()}%"
            query += """
                AND (
                    C.CodigoContrato LIKE ?
                    OR V.Placa LIKE ?
                    OR EXISTS (
                        SELECT 1
                        FROM CONTRATOVEHICULO CVB
                        INNER JOIN VEHICULO VB ON VB.Vehiculo = CVB.Vehiculo
                        WHERE CVB.Contrato = C.Contrato
                          AND CVB.Estado = 1
                          AND (
                              VB.Placa LIKE ?
                              OR VB.Color LIKE ?
                              OR VB.Marca LIKE ?
                              OR VB.Modelo LIKE ?
                          )
                    )
                    OR CL.Nombres LIKE ?
                    OR CL.Apellidos LIKE ?
                    OR CL.Telefono LIKE ?
                )
            """
            params.extend([like, like, like, like, like, like, like, like, like])

        if clase != "Todos":
            query += " AND C.ClaseContrato = ? "
            params.append(CLASE_CONTRATO_INV.get(clase, CLASE_ESTANDAR))

        if tipo_cliente != "Todos":
            query += " AND UPPER(COALESCE(CL.TipoCliente, 'GENERAL')) = ? "
            params.append(tipo_cliente.upper())

        query += """
            GROUP BY
                C.Contrato,
                C.CodigoContrato,
                C.Cliente,
                C.Vehiculo,
                C.FechaInicio,
                C.FechaFin,
                C.DuracionMes,
                C.MontoContrato,
                C.ModalidadPago,
                C.Estado,
                C.ClaseContrato,
                C.HorasPermitidasDia,
                C.EstadoPago,
                C.MetodoPago,
                C.FechaPago,
                C.MontoPagado,
                CL.Nombres,
                CL.Apellidos,
                CL.Telefono,
                CL.TipoCliente,
                V.Placa,
                V.Color,
                V.Marca,
                V.Modelo,
                TV.Nombre,
                V.TipoVehiculo
            ORDER BY C.Contrato DESC
        """

        cursor.execute(query, params)
        filas = cursor.fetchall()

        if estado_visible != "Todos":
            filas = [f for f in filas if estado_visible_contrato(f) == estado_visible]

        return filas

    finally:
        if conn:
            conn.close()


def existe_contrato_vigente_vehiculo(vehiculo, excluir_contrato=None):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
            SELECT COUNT(*)
            FROM CONTRATOVEHICULO CV
            INNER JOIN CONTRATO C ON C.Contrato = CV.Contrato
            WHERE CV.Vehiculo = ?
              AND CV.Estado = 1
              AND C.Estado IN (?, ?)
              AND C.FechaFin >= date('now','localtime')
        """
        params = [vehiculo, ESTADO_ACTIVO, ESTADO_SUSPENDIDO]

        if excluir_contrato is not None:
            query += " AND C.Contrato <> ? "
            params.append(excluir_contrato)

        cursor.execute(query, params)
        total = int(cursor.fetchone()[0] or 0)

        if total > 0:
            return True

        query_legacy = """
            SELECT COUNT(*)
            FROM CONTRATO C
            WHERE C.Vehiculo = ?
              AND C.Estado IN (?, ?)
              AND C.FechaFin >= date('now','localtime')
        """
        params_legacy = [vehiculo, ESTADO_ACTIVO, ESTADO_SUSPENDIDO]

        if excluir_contrato is not None:
            query_legacy += " AND C.Contrato <> ? "
            params_legacy.append(excluir_contrato)

        cursor.execute(query_legacy, params_legacy)
        return int(cursor.fetchone()[0] or 0) > 0

    finally:
        if conn:
            conn.close()


def validar_vehiculos_sin_contrato_vigente(vehiculo_ids, excluir_contrato=None):
    ocupados = []
    for vehiculo_id in vehiculo_ids:
        if existe_contrato_vigente_vehiculo(vehiculo_id, excluir_contrato=excluir_contrato):
            ocupados.append(vehiculo_id)

    if not ocupados:
        return

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in ocupados)
        cursor.execute(f"""
            SELECT Placa
            FROM VEHICULO
            WHERE Vehiculo IN ({placeholders})
            ORDER BY Placa
        """, ocupados)
        placas = [row["Placa"] for row in cursor.fetchall()]
    finally:
        if conn:
            conn.close()

    if placas:
        raise ValueError("Estos vehículos ya tienen contrato vigente: " + ", ".join(placas))

    raise ValueError("Uno o más vehículos seleccionados ya tienen contrato vigente.")


def generar_codigo_operacion_contrato(cursor, contrato_id):
    base = f"OPC-{contrato_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    codigo = base
    intento = 1
    while True:
        cursor.execute("SELECT COUNT(*) AS Cantidad FROM OPERACION WHERE CodigoOperacion = ?", (codigo,))
        fila = cursor.fetchone()
        cantidad = int(row_get(fila, "Cantidad", fila[0] if fila else 0) or 0)
        if cantidad == 0:
            return codigo
        intento += 1
        codigo = f"{base}-{intento}"


def obtener_tarifa_para_operacion_contrato(cursor, vehiculo_id):
    """
    OPERACION.Tarifa es NOT NULL. Para registrar el pago se usa cualquier tarifa activa
    del tipo de vehículo. Si no existe, se busca la primera tarifa activa.
    """
    cursor.execute("""
        SELECT T.Tarifa
        FROM VEHICULO V
        INNER JOIN TARIFA T ON T.TipoVehiculo = V.TipoVehiculo
        WHERE V.Vehiculo = ?
          AND T.Estado = 1
        ORDER BY T.TipoTarifa ASC, T.Tarifa ASC
        LIMIT 1
    """, (vehiculo_id,))
    row = cursor.fetchone()
    if row:
        return row_get(row, "Tarifa", row[0])

    cursor.execute("""
        SELECT Tarifa
        FROM TARIFA
        WHERE Estado = 1
        ORDER BY Tarifa ASC
        LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        return row_get(row, "Tarifa", row[0])

    raise ValueError("No existe una tarifa activa para registrar la operación de pago.")


def registrar_pago_contrato(cursor, contrato_id, metodo_pago, usr=0):
    contrato = obtener_contrato_por_id(contrato_id)
    if not contrato:
        raise ValueError("No se encontró el contrato.")

    monto = float(row_get(contrato, "MontoContrato", 0) or 0)
    if monto <= 0:
        raise ValueError("El monto del contrato debe ser mayor a 0.")

    tarifa_id = obtener_tarifa_para_operacion_contrato(cursor, row_get(contrato, "Vehiculo"))
    codigo_operacion = generar_codigo_operacion_contrato(cursor, contrato_id)
    obs = f"Pago contrato {row_get(contrato, 'CodigoContrato')}"

    cursor.execute("""
        INSERT INTO OPERACION (
            CodigoOperacion,
            Vehiculo,
            Cliente,
            Tarifa,
            Contrato,
            UsuarioIngreso,
            UsuarioSalida,
            FechaIngreso,
            FechaSalida,
            TipoOperacion,
            MinutosEstadia,
            MontoParqueo,
            MontoServicios,
            MontoTotal,
            Estado,
            CodigoRetiro,
            Observacion,
            MotivoCancelacion,
            Usr,
            UsrFecha,
            UsrHora,
            FechaCreacion,
            FechaModificacion
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?,
            datetime('now','localtime'),
            datetime('now','localtime'),
            ?, ?, ?, ?, ?, ?,
            NULL, ?, NULL, ?,
            date('now','localtime'),
            time('now','localtime'),
            datetime('now','localtime'),
            datetime('now','localtime')
        )
    """, (
        codigo_operacion,
        row_get(contrato, "Vehiculo"),
        row_get(contrato, "Cliente"),
        tarifa_id,
        contrato_id,
        usr,
        usr,
        TIPO_OPERACION_CONTRATO,
        0,
        monto,
        0,
        monto,
        ESTADO_OPERACION_FINALIZADO,
        obs,
        usr,
    ))

    operacion_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO PAGO (
            Operacion,
            Usuario,
            FechaPago,
            MetodoPago,
            Monto,
            Observacion,
            Estado,
            Usr,
            UsrFecha,
            UsrHora,
            FechaCreacion,
            FechaModificacion
        )
        VALUES (
            ?, ?,
            datetime('now','localtime'),
            ?, ?, ?, ?,
            ?,
            date('now','localtime'),
            time('now','localtime'),
            datetime('now','localtime'),
            datetime('now','localtime')
        )
    """, (
        operacion_id,
        usr,
        metodo_pago,
        monto,
        obs,
        ESTADO_PAGO_REGISTRADO,
        usr,
    ))

    cursor.execute("""
        UPDATE CONTRATO
        SET
            EstadoPago = ?,
            MetodoPago = ?,
            FechaPago = datetime('now','localtime'),
            MontoPagado = ?,
            UsuarioPago = ?,
            ModalidadPago = ?,
            Estado = ?,
            Usr = ?,
            UsrFecha = date('now','localtime'),
            UsrHora = time('now','localtime'),
            FechaModificacion = datetime('now','localtime')
        WHERE Contrato = ?
    """, (
        ESTADO_PAGO_PAGADO,
        metodo_pago,
        monto,
        usr,
        metodo_pago,
        ESTADO_ACTIVO,
        usr,
        contrato_id,
    ))

    return cursor.lastrowid


def insertar_contrato(data, usr=0):
    asegurar_columnas_contrato()

    vehiculo_ids = data.get("Vehiculos") or [data.get("Vehiculo")]
    vehiculo_ids = [int(v) for v in vehiculo_ids if v is not None]

    if not vehiculo_ids:
        raise ValueError("Debes seleccionar al menos un vehículo.")

    validar_vehiculos_sin_contrato_vigente(vehiculo_ids)

    vehiculo_principal = obtener_vehiculo_principal(vehiculo_ids)

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO CONTRATO (
                Cliente,
                Vehiculo,
                CodigoContrato,
                FechaInicio,
                FechaFin,
                DuracionMes,
                MontoContrato,
                ModalidadPago,
                EspacioAsignado,
                Observacion,
                Estado,
                ClaseContrato,
                TarifaDetalle,
                HorasPermitidasDia,
                EstadoPago,
                MetodoPago,
                FechaPago,
                MontoPagado,
                UsuarioPago,
                Usr,
                UsrFecha,
                UsrHora,
                FechaCreacion,
                FechaModificacion
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, NULL, NULL, 0, NULL,
                ?, date('now','localtime'), time('now','localtime'),
                datetime('now','localtime'), datetime('now','localtime')
            )
        """, (
            data["Cliente"],
            vehiculo_principal,
            data["CodigoContrato"],
            data["FechaInicio"],
            data["FechaFin"],
            data["DuracionMes"],
            data["MontoContrato"],
            None,
            None,
            data.get("Observacion"),
            ESTADO_ACTIVO,
            data["ClaseContrato"],
            data.get("TarifaDetalle"),
            data.get("HorasPermitidasDia"),
            ESTADO_PAGO_PENDIENTE,
            usr,
        ))

        contrato_id = cursor.lastrowid
        sincronizar_vehiculos_contrato(cursor, contrato_id, vehiculo_ids, usr)

        conn.commit()
        return contrato_id

    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def actualizar_contrato(contrato_id, data, usr=0):
    asegurar_columnas_contrato()

    vehiculo_ids = data.get("Vehiculos") or [data.get("Vehiculo")]
    vehiculo_ids = [int(v) for v in vehiculo_ids if v is not None]

    if not vehiculo_ids:
        raise ValueError("Debes seleccionar al menos un vehículo.")

    validar_vehiculos_sin_contrato_vigente(vehiculo_ids, excluir_contrato=contrato_id)

    vehiculo_principal = obtener_vehiculo_principal(vehiculo_ids)

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE CONTRATO
            SET
                Cliente = ?,
                Vehiculo = ?,
                CodigoContrato = ?,
                FechaInicio = ?,
                FechaFin = ?,
                DuracionMes = ?,
                MontoContrato = ?,
                Estado = ?,
                ClaseContrato = ?,
                TarifaDetalle = ?,
                HorasPermitidasDia = ?,
                Usr = ?,
                UsrFecha = date('now','localtime'),
                UsrHora = time('now','localtime'),
                FechaModificacion = datetime('now','localtime')
            WHERE Contrato = ?
        """, (
            data["Cliente"],
            vehiculo_principal,
            data["CodigoContrato"],
            data["FechaInicio"],
            data["FechaFin"],
            data["DuracionMes"],
            data["MontoContrato"],
            ESTADO_ACTIVO,
            data["ClaseContrato"],
            data.get("TarifaDetalle"),
            data.get("HorasPermitidasDia"),
            usr,
            contrato_id,
        ))

        sincronizar_vehiculos_contrato(cursor, contrato_id, vehiculo_ids, usr)

        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def marcar_contrato_pendiente_pago(contrato_id, usr=0):
    """
    Se usa al renovar: el contrato queda nuevamente pendiente y luego se abre payment.py.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE CONTRATO
            SET
                EstadoPago = ?,
                MetodoPago = NULL,
                ModalidadPago = NULL,
                FechaPago = NULL,
                MontoPagado = 0,
                UsuarioPago = NULL,
                Estado = ?,
                Usr = ?,
                UsrFecha = date('now','localtime'),
                UsrHora = time('now','localtime'),
                FechaModificacion = datetime('now','localtime')
            WHERE Contrato = ?
            """, (ESTADO_PAGO_PENDIENTE, ESTADO_ACTIVO, usr, contrato_id))
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def abrir_modal_pago(parent, user_data, contrato_id, on_success=None):
    """Abre el módulo real de pagos. Ya no usa el modal temporal interno."""
    if abrir_cobro_contrato is None:
        messagebox.showerror(
            "Módulo de cobro",
            "No se pudo cargar modules/payment.py. Verifica que el archivo exista en la carpeta modules."
        )
        return
    abrir_cobro_contrato(parent, user_data, contrato_id, on_success=on_success)


def cambiar_estado_contrato(contrato_id, nuevo_estado, usr=0):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if int(nuevo_estado) == ESTADO_SUSPENDIDO:
            # Al suspender, el contrato deja de estar vigente y se puede volver a cobrar.
            # Por eso se limpia el estado de pago para que no aparezca "ya está pagado".
            cursor.execute("""
                UPDATE CONTRATO
                SET
                    Estado = ?,
                    EstadoPago = ?,
                    MetodoPago = NULL,
                    ModalidadPago = NULL,
                    FechaPago = NULL,
                    MontoPagado = 0,
                    UsuarioPago = NULL,
                    Usr = ?,
                    UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'),
                    FechaModificacion = datetime('now','localtime')
                WHERE Contrato = ?
            """, (nuevo_estado, ESTADO_PAGO_PENDIENTE, usr, contrato_id))
        else:
            cursor.execute("""
                UPDATE CONTRATO
                SET
                    Estado = ?,
                    Usr = ?,
                    UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'),
                    FechaModificacion = datetime('now','localtime')
                WHERE Contrato = ?
            """, (nuevo_estado, usr, contrato_id))

        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def tabla_existe(cursor, tabla):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,))
    return cursor.fetchone() is not None


def _quote_ident(nombre):
    return '"' + str(nombre).replace('"', '""') + '"'


def _tablas_usuario(cursor):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    return [r[0] for r in cursor.fetchall()]


def _columnas_tabla(cursor, tabla):
    cursor.execute(f"PRAGMA table_info({_quote_ident(tabla)})")
    return [r[1] for r in cursor.fetchall()]


def _pk_principal(cursor, tabla):
    cursor.execute(f"PRAGMA table_info({_quote_ident(tabla)})")
    columnas_pk = []
    for r in cursor.fetchall():
        # r: cid, name, type, notnull, dflt_value, pk
        if int(r[5] or 0) > 0:
            columnas_pk.append((int(r[5]), r[1]))
    columnas_pk.sort()
    if len(columnas_pk) == 1:
        return columnas_pk[0][1]
    if "rowid" not in _columnas_tabla(cursor, tabla):
        return "rowid"
    return None


def _valor_columna(row, columna):
    try:
        return row[columna]
    except Exception:
        try:
            return row[columna.lower()]
        except Exception:
            return None


def _borrar_registros_con_dependencias(cursor, tabla, columna, valores, visitados=None):
    """
    Borra registros respetando las FOREIGN KEY aunque no tengan ON DELETE CASCADE.
    Primero busca tablas hijas que referencian a la tabla actual y las elimina.
    """
    valores = [v for v in (valores or []) if v is not None]
    if not valores:
        return

    visitados = visitados or set()
    tabla_q = _quote_ident(tabla)
    columna_q = _quote_ident(columna)
    placeholders = ",".join("?" for _ in valores)

    try:
        cursor.execute(
            f"SELECT rowid AS __rowid__, * FROM {tabla_q} WHERE {columna_q} IN ({placeholders})",
            valores,
        )
        filas = cursor.fetchall()
    except Exception:
        cursor.execute(
            f"SELECT * FROM {tabla_q} WHERE {columna_q} IN ({placeholders})",
            valores,
        )
        filas = cursor.fetchall()

    if not filas:
        return

    tablas = _tablas_usuario(cursor)
    for tabla_hija in tablas:
        if tabla_hija == tabla:
            continue

        try:
            cursor.execute(f"PRAGMA foreign_key_list({_quote_ident(tabla_hija)})")
            fks = cursor.fetchall()
        except Exception:
            continue

        for fk in fks:
            # PRAGMA foreign_key_list: id, seq, table, from, to, on_update, on_delete, match
            tabla_padre = fk[2]
            columna_hija = fk[3]
            columna_padre = fk[4]

            if tabla_padre != tabla:
                continue

            if not columna_padre:
                columna_padre = _pk_principal(cursor, tabla)
            if not columna_padre:
                continue

            valores_padre = []
            for fila in filas:
                valor = _valor_columna(fila, columna_padre)
                if valor is not None and valor not in valores_padre:
                    valores_padre.append(valor)

            if not valores_padre:
                continue

            clave = (tabla_hija, columna_hija, tuple(map(str, valores_padre)))
            if clave in visitados:
                continue
            visitados.add(clave)

            _borrar_registros_con_dependencias(
                cursor,
                tabla_hija,
                columna_hija,
                valores_padre,
                visitados=visitados,
            )

    cursor.execute(
        f"DELETE FROM {tabla_q} WHERE {columna_q} IN ({placeholders})",
        valores,
    )


def eliminar_contrato(contrato_id):
    """
    Elimina el contrato y cualquier registro que lo esté bloqueando por FOREIGN KEY.
    Esto corrige el error: FOREIGN KEY constraint failed.
    """
    asegurar_columnas_contrato()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Contrato FROM CONTRATO WHERE Contrato = ?", (contrato_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("No se encontró el contrato a eliminar.")

        _borrar_registros_con_dependencias(cursor, "CONTRATO", "Contrato", [contrato_id])

        cursor.execute("SELECT COUNT(*) FROM CONTRATO WHERE Contrato = ?", (contrato_id,))
        if int(cursor.fetchone()[0] or 0) > 0:
            raise ValueError("No se pudo eliminar el contrato porque aún tiene registros relacionados.")

        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def cobrar_contrato(contrato_id, metodo_pago, usr=0):
    asegurar_columnas_contrato()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT EstadoPago FROM CONTRATO WHERE Contrato = ?", (contrato_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("No se encontró el contrato.")
        contrato = obtener_contrato_por_id(contrato_id)
        estado = int(row_get(contrato, "Estado", ESTADO_ACTIVO) or ESTADO_ACTIVO)
        estado_pago = int(row_get(row, "EstadoPago", 0) or 0)

        if estado_pago == ESTADO_PAGO_PAGADO and estado not in (ESTADO_SUSPENDIDO, ESTADO_VENCIDO):
            raise ValueError("Este contrato ya está pagado.")

        if estado in (ESTADO_SUSPENDIDO, ESTADO_VENCIDO) and estado_pago == ESTADO_PAGO_PAGADO:
            cursor.execute("""
                UPDATE CONTRATO
                SET EstadoPago = ?, MetodoPago = NULL, ModalidadPago = NULL,
                    FechaPago = NULL, MontoPagado = 0, UsuarioPago = NULL
                WHERE Contrato = ?
            """, (ESTADO_PAGO_PENDIENTE, contrato_id))

        registrar_pago_contrato(cursor, contrato_id, metodo_pago, usr)
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def suspender_contratos_vencidos(usr=0):
    asegurar_columnas_contrato()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE CONTRATO
            SET
                Estado = ?,
                Usr = ?,
                UsrFecha = date('now','localtime'),
                UsrHora = time('now','localtime'),
                FechaModificacion = datetime('now','localtime')
            WHERE Estado = ?
              AND FechaFin < date('now','localtime')
        """, (ESTADO_VENCIDO, usr, ESTADO_ACTIVO))
        conn.commit()
    finally:
        if conn:
            conn.close()

# =========================================================
# FORMULARIO CONTRATO
# =========================================================
class ContractForm(tk.Toplevel):
    def __init__(self, master, user_data, on_save, clase_contrato=CLASE_ESTANDAR, contrato=None, abrir_pago_despues_guardar=False, es_renovacion=False):
        super().__init__(master)
        self.master_view = master
        self.user_data = user_data or {}
        self.on_save = on_save
        self.contrato = contrato
        self.abrir_pago_despues_guardar = bool(abrir_pago_despues_guardar)
        self.es_renovacion = bool(es_renovacion)

        self.clase_contrato = int(row_get(contrato, "ClaseContrato", clase_contrato) or clase_contrato)

        self.clientes = obtener_clientes()
        self.vehiculos = obtener_vehiculos()
        self.clientes_filtrados = list(self.clientes)
        self.vehiculos_filtrados = []
        self.vehiculos_seleccionados_ids = []

        self.mapa_clientes = {}
        self.mapa_vehiculos = {}
        self.tarifas_auto = obtener_tarifas_contrato_auto()
        self.fecha_inicio_original_db = str(row_get(contrato, "FechaInicio", "") or "")[:10] if contrato else ""
        self.fecha_fin_original_db = str(row_get(contrato, "FechaFin", "") or "")[:10] if contrato else ""
        self.horas_originales = row_get(contrato, "HorasPermitidasDia") if contrato else None

        self.title("Contrato")
        self.configure(bg=COLOR_BG)
        self.resizable(True, True)
        self.minsize(700, 500)
        self.transient(master.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        if self.clase_contrato == CLASE_ESTANDAR:
            if self.es_renovacion:
                titulo = "Renovar contrato estándar"
            else:
                titulo = "Nuevo contrato estándar" if not contrato else "Editar contrato estándar"
            codigo = generar_codigo_contrato(CLASE_ESTANDAR) if not contrato else row_get(contrato, "CodigoContrato", "")
            width, height = 920, 680
        else:
            if self.es_renovacion:
                titulo = "Renovar contrato especial"
            else:
                titulo = "Contrato especial" if not contrato else "Editar contrato especial"
            codigo = generar_codigo_contrato(CLASE_ESPECIAL) if not contrato else row_get(contrato, "CodigoContrato", "")
            width, height = 920, 620

        self.titulo = titulo

        self.var_codigo = tk.StringVar(value=codigo)
        self.var_buscar_cliente = tk.StringVar()
        self.var_cliente = tk.StringVar()
        self.var_buscar_vehiculo = tk.StringVar()
        self.var_vehiculo = tk.StringVar()
        self.var_fecha_inicio = tk.StringVar(value=fecha_actual_form())
        self.var_fecha_fin = tk.StringVar(value=fecha_actual_form())
        self.var_duracion = tk.StringVar(value="1")
        self.var_tipo_contrato = tk.StringVar(value="3h")
        self.var_monto = tk.StringVar(value="0.00")

        self.cbo_cliente = None
        self.cbo_vehiculo = None
        self.lst_vehiculos = None
        self.lbl_vehiculos_seleccionados = None
        self.cbo_tipo_contrato = None
        self.btn_guardar = None
        self.entry_fecha_fin = None
        self.entry_monto = None

        configurar_estilo_combobox()
        self._build_ui()
        centrar_ventana(self, width, height, master.winfo_toplevel())

        self._build_mapa_clientes()
        self._cargar_datos_si_edicion()
        self._filtrar_clientes()
        self._aplicar_reglas_renovacion()
        self._recalcular_fin_y_monto()
        self._actualizar_estado_guardar()

        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        title_frame = tk.Frame(self, bg=COLOR_BG)
        title_frame.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 8))
        tk.Label(title_frame, text=self.titulo, font=("Arial", 18, "bold"), bg=COLOR_BG, fg=COLOR_TEXT).pack(anchor="w")

        main = tk.Frame(self, bg=COLOR_CARD, bd=1, relief="solid")
        main.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 8))
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)

        codigo_frame = tk.Frame(main, bg=COLOR_CARD)
        codigo_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(12, 12))
        tk.Label(codigo_frame, text="Código", font=("Arial", 10), bg=COLOR_CARD, fg=COLOR_TEXT).pack()
        tk.Label(codigo_frame, textvariable=self.var_codigo, font=("Arial", 16, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT).pack(pady=(2, 0))

        self._campo_entry(main, "Buscar cliente", self.var_buscar_cliente, 1, 0)
        self._campo_combo(main, "Cliente", self.var_cliente, [], 1, 1, self._on_cliente_change)

        self._campo_lista_vehiculos(main, 2, 0, columnspan=2)

        self._campo_entry(main, "Fecha inicio (dd/mm/yyyy)", self.var_fecha_inicio, 3, 0)

        if self.clase_contrato == CLASE_ESTANDAR:
            self._campo_entry(main, "Fecha fin", self.var_fecha_fin, 3, 1, state="readonly")
            self._campo_entry(main, "Duración en meses", self.var_duracion, 4, 0)
            self._campo_combo(main, "Tipo de contrato", self.var_tipo_contrato, [f"{h}h" for h in HORAS_CONTRATO], 4, 1, lambda: self._recalcular_fin_y_monto())
            self.entry_monto = self._campo_entry(main, "Monto contrato", self.var_monto, 5, 0, state="readonly")
        else:
            self.entry_fecha_fin = self._campo_entry(main, "Fecha fin (dd/mm/yyyy)", self.var_fecha_fin, 3, 1)
            self.entry_monto = self._campo_entry(main, "Monto contrato", self.var_monto, 4, 0)

        footer = tk.Frame(self, bg=COLOR_BG)
        footer.grid(row=2, column=0, sticky="ew", padx=22, pady=(2, 18))
        SimpleButton(footer, text="Cancelar", command=self.destroy).pack(side="right", padx=(8, 0))
        self.btn_guardar = SimpleButton(footer, text="Guardar", primary=True, command=self.guardar)
        self.btn_guardar.pack(side="right")

        self.var_buscar_cliente.trace_add("write", lambda *_: self._filtrar_clientes())
        self.var_fecha_inicio.trace_add("write", lambda *_: self._recalcular_fin_y_monto())
        self.var_fecha_fin.trace_add("write", lambda *_: self._actualizar_estado_guardar())
        self.var_duracion.trace_add("write", lambda *_: self._recalcular_fin_y_monto())
        self.var_monto.trace_add("write", lambda *_: self._actualizar_estado_guardar())

    def _campo_entry(self, parent, label, variable, row, col, state="normal"):
        padx = (18, 9) if col == 0 else (9, 18)
        frame = tk.Frame(parent, bg=COLOR_CARD)
        frame.grid(row=row, column=col, sticky="ew", padx=padx, pady=(0, 12))
        frame.grid_columnconfigure(0, weight=1)

        tk.Label(frame, text=label, font=("Arial", 10, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=0, column=0, sticky="w", pady=(0, 4))
        entry = tk.Entry(frame, textvariable=variable, font=("Arial", 10), relief="solid", bd=1, state=state)
        entry.grid(row=1, column=0, sticky="ew", ipady=6)
        return entry

    def _campo_combo(self, parent, label, variable, values, row, col, command=None):
        padx = (18, 9) if col == 0 else (9, 18)
        frame = tk.Frame(parent, bg=COLOR_CARD)
        frame.grid(row=row, column=col, sticky="ew", padx=padx, pady=(0, 12))
        frame.grid_columnconfigure(0, weight=1)

        tk.Label(frame, text=label, font=("Arial", 10, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=0, column=0, sticky="w", pady=(0, 4))

        combo = ttk.Combobox(frame, textvariable=variable, values=values, state="readonly", font=("Arial", 10), style="Simple.TCombobox")
        combo.grid(row=1, column=0, sticky="ew", ipady=5)
        if command:
            combo.bind("<<ComboboxSelected>>", lambda _e: command())

        if label == "Cliente":
            self.cbo_cliente = combo
        elif label == "Vehículo":
            self.cbo_vehiculo = combo
        elif label == "Tipo de contrato":
            self.cbo_tipo_contrato = combo

        return combo

    def _campo_lista_vehiculos(self, parent, row, col, columnspan=1):
        if columnspan > 1:
            padx = (18, 18)
        else:
            padx = (18, 9) if col == 0 else (9, 18)
        frame = tk.Frame(parent, bg=COLOR_CARD)
        frame.grid(row=row, column=col, columnspan=columnspan, sticky="ew", padx=padx, pady=(0, 12))
        frame.grid_columnconfigure(0, weight=1)

        tk.Label(
            frame,
            text="Vehículos del cliente",
            font=("Arial", 10, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        list_frame = tk.Frame(frame, bg=COLOR_CARD)
        list_frame.grid(row=1, column=0, sticky="ew")
        list_frame.grid_columnconfigure(0, weight=1)

        self.lst_vehiculos = tk.Listbox(
            list_frame,
            height=5,
            selectmode="multiple",
            exportselection=False,
            font=("Arial", 10),
            relief="solid",
            bd=1
        )
        self.lst_vehiculos.grid(row=0, column=0, sticky="ew")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.lst_vehiculos.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.lst_vehiculos.configure(yscrollcommand=scrollbar.set)
        self.lst_vehiculos.bind("<<ListboxSelect>>", lambda _e: self._on_vehiculos_listbox_change())

        self.lbl_vehiculos_seleccionados = tk.Label(
            frame,
            text="Selecciona uno o varios vehículos.",
            font=("Arial", 9),
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            anchor="w"
        )
        self.lbl_vehiculos_seleccionados.grid(row=2, column=0, sticky="ew", pady=(4, 0))

        return self.lst_vehiculos


    def _build_mapa_clientes(self):
        self.mapa_clientes = {formatear_cliente(c): row_get(c, "Cliente") for c in self.clientes_filtrados}

    def _build_mapa_vehiculos(self):
        self.mapa_vehiculos = {formatear_vehiculo(v): row_get(v, "Vehiculo") for v in self.vehiculos_filtrados}

    def _actualizar_label_vehiculos(self):
        if not self.lbl_vehiculos_seleccionados:
            return

        cantidad = len(self.vehiculos_seleccionados_ids)
        if cantidad <= 0:
            self.lbl_vehiculos_seleccionados.configure(text="Selecciona uno o varios vehículos.")
        elif cantidad == 1:
            self.lbl_vehiculos_seleccionados.configure(text="1 vehículo seleccionado.")
        else:
            self.lbl_vehiculos_seleccionados.configure(text=f"{cantidad} vehículos seleccionados.")

    def _on_vehiculos_listbox_change(self):
        self.vehiculos_seleccionados_ids = self._vehiculo_ids_seleccionados()
        self._actualizar_label_vehiculos()
        self._recalcular_fin_y_monto()

    def _filtrar_clientes(self):
        texto_busqueda = normalizar(self.var_buscar_cliente.get())

        if not texto_busqueda:
            self.clientes_filtrados = list(self.clientes)
        else:
            self.clientes_filtrados = []
            for cliente in self.clientes:
                datos = normalizar(f"{formatear_cliente(cliente)}")
                if texto_busqueda in datos:
                    self.clientes_filtrados.append(cliente)

        seleccionado = self.var_cliente.get().strip()
        self._build_mapa_clientes()

        if self.cbo_cliente:
            self.cbo_cliente.configure(values=list(self.mapa_clientes.keys()))

        if seleccionado and seleccionado not in self.mapa_clientes:
            self.var_cliente.set("")
            self.var_vehiculo.set("")

        self._filtrar_vehiculos()

    def _cliente_id_seleccionado(self):
        valor = self.var_cliente.get().strip()
        if not valor or valor not in self.mapa_clientes:
            return None
        return self.mapa_clientes[valor]

    def _vehiculo_ids_seleccionados(self):
        ids = []
        if not self.lst_vehiculos:
            return ids

        textos = list(self.mapa_vehiculos.keys())
        for index in self.lst_vehiculos.curselection():
            try:
                texto_item = textos[int(index)]
                vehiculo_id = self.mapa_vehiculos.get(texto_item)
                if vehiculo_id is not None and vehiculo_id not in ids:
                    ids.append(vehiculo_id)
            except Exception:
                pass

        return ids

    def _vehiculo_rows_seleccionados(self):
        ids = set(self._vehiculo_ids_seleccionados())
        return [v for v in self.vehiculos if row_get(v, "Vehiculo") in ids]

    def _on_cliente_change(self):
        self.var_vehiculo.set("")
        self.vehiculos_seleccionados_ids = []
        self._filtrar_vehiculos()
        self._recalcular_fin_y_monto()

    def _filtrar_vehiculos(self):
        cliente_id = self._cliente_id_seleccionado()

        self.vehiculos_filtrados = []
        for vehiculo in self.vehiculos:
            if cliente_id is None:
                continue

            if row_get(vehiculo, "Cliente") != cliente_id:
                continue

            self.vehiculos_filtrados.append(vehiculo)

        self._build_mapa_vehiculos()

        if self.lst_vehiculos:
            self.lst_vehiculos.delete(0, tk.END)
            textos = list(self.mapa_vehiculos.keys())

            for item in textos:
                self.lst_vehiculos.insert(tk.END, item)

            for idx, item in enumerate(textos):
                vehiculo_id = self.mapa_vehiculos.get(item)
                if vehiculo_id in self.vehiculos_seleccionados_ids:
                    self.lst_vehiculos.selection_set(idx)

        if self.lst_vehiculos:
            seleccion_actual = self._vehiculo_ids_seleccionados()
            if seleccion_actual:
                self.vehiculos_seleccionados_ids = seleccion_actual

        self._actualizar_label_vehiculos()
        self._recalcular_fin_y_monto()

    def _cargar_datos_si_edicion(self):
        if not self.contrato:
            self._filtrar_clientes()
            self.var_cliente.set("")
            self.var_vehiculo.set("")
            self.vehiculos_seleccionados_ids = []
            self.vehiculos_filtrados = []
            self._build_mapa_vehiculos()
            if self.lst_vehiculos:
                self.lst_vehiculos.delete(0, tk.END)
            self._actualizar_label_vehiculos()
            return

        self.var_codigo.set(row_get(self.contrato, "CodigoContrato", ""))
        self.var_duracion.set(str(row_get(self.contrato, "DuracionMes", 1) or 1))

        if self.es_renovacion:
            base_renovacion = fecha_base_renovacion(self.fecha_fin_original_db)
            self.var_fecha_inicio.set(fecha_db_a_form(base_renovacion))

            try:
                duracion_tmp = int(self.var_duracion.get().strip() or 1)
                self.var_fecha_fin.set(fecha_db_a_form(sumar_meses_menos_un_dia(base_renovacion, duracion_tmp)))
            except Exception:
                self.var_fecha_fin.set(fecha_db_a_form(row_get(self.contrato, "FechaFin")))
        else:
            self.var_fecha_inicio.set(fecha_db_a_form(row_get(self.contrato, "FechaInicio")))
            self.var_fecha_fin.set(fecha_db_a_form(row_get(self.contrato, "FechaFin")))

        self.var_monto.set(f"{float(row_get(self.contrato, 'MontoContrato', 0) or 0):.2f}")

        horas = row_get(self.contrato, "HorasPermitidasDia")
        if horas:
            self.var_tipo_contrato.set(f"{int(horas)}h")

        self._filtrar_clientes()

        for texto_cliente, cliente_id in self.mapa_clientes.items():
            if cliente_id == row_get(self.contrato, "Cliente"):
                self.var_cliente.set(texto_cliente)
                break

        vehiculos_contrato = obtener_vehiculos_contrato(row_get(self.contrato, "Contrato"))
        self.vehiculos_seleccionados_ids = [
            row_get(v, "Vehiculo") for v in vehiculos_contrato if row_get(v, "Vehiculo") is not None
        ]

        if not self.vehiculos_seleccionados_ids and row_get(self.contrato, "Vehiculo"):
            self.vehiculos_seleccionados_ids = [row_get(self.contrato, "Vehiculo")]

        self._filtrar_vehiculos()

    def _aplicar_reglas_renovacion(self):
        """
        Si se renueva antes de vencer, solo se permite ampliar el plazo.
        Por eso se bloquea el cambio de tipo de contrato.
        Si ya venció, sí se puede cambiar el tipo de contrato.
        """
        if not self.es_renovacion:
            return

        esta_vigente = contrato_esta_vigente_por_fecha(self.fecha_fin_original_db)

        if self.clase_contrato == CLASE_ESTANDAR and self.cbo_tipo_contrato:
            if esta_vigente:
                if self.horas_originales:
                    self.var_tipo_contrato.set(f"{int(self.horas_originales)}h")
                    self.cbo_tipo_contrato.configure(values=[f"{int(self.horas_originales)}h"], state="disabled")
            else:
                self.cbo_tipo_contrato.configure(values=[f"{h}h" for h in HORAS_CONTRATO], state="readonly")

        # En renovación no se debe reiniciar desde hoy si el contrato sigue vigente.
        # La fecha inicio queda en la fecha fin actual del contrato pagado.
        # Si ya venció, queda en la fecha actual.
        base_renovacion = fecha_base_renovacion(self.fecha_fin_original_db)
        self.var_fecha_inicio.set(fecha_db_a_form(base_renovacion))

    def _horas_seleccionadas(self):
        valor = self.var_tipo_contrato.get().replace("h", "").strip()
        try:
            return int(valor)
        except Exception:
            return 3

    def _recalcular_fin_y_monto(self):
        if self.clase_contrato == CLASE_ESTANDAR:
            try:
                duracion = int(self.var_duracion.get().strip())
                if duracion <= 0:
                    raise ValueError

                if self.es_renovacion and self.fecha_fin_original_db:
                    base_renovacion = fecha_base_renovacion(self.fecha_fin_original_db)
                    self.var_fecha_inicio.set(fecha_db_a_form(base_renovacion))
                    self.var_fecha_fin.set(fecha_db_a_form(sumar_meses_menos_un_dia(base_renovacion, duracion)))
                else:
                    fecha_inicio_db = fecha_form_a_db(self.var_fecha_inicio.get())
                    self.var_fecha_fin.set(fecha_db_a_form(sumar_meses_menos_un_dia(fecha_inicio_db, duracion)))
            except Exception:
                self.var_fecha_fin.set("")

            try:
                duracion = int(self.var_duracion.get().strip())
                horas = self._horas_seleccionadas()
                tarifa = self.tarifas_auto.get(horas)
                if duracion <= 0 or not tarifa:
                    self.var_monto.set("0.00")
                else:
                    self.var_monto.set(f"{float(tarifa['Monto']) * duracion:.2f}")
            except Exception:
                self.var_monto.set("0.00")
        else:
            # Especial: fecha fin y monto son manuales.
            pass

        self._actualizar_estado_guardar()

    def _actualizar_estado_guardar(self):
        if not self.btn_guardar:
            return

        puede = True

        if not self.var_cliente.get().strip() or self.var_cliente.get().strip() not in self.mapa_clientes:
            puede = False
        if len(self._vehiculo_ids_seleccionados()) <= 0:
            puede = False

        try:
            fecha_form_a_db(self.var_fecha_inicio.get())
            fecha_form_a_db(self.var_fecha_fin.get())
        except Exception:
            puede = False

        if self.clase_contrato == CLASE_ESTANDAR:
            try:
                duracion = int(self.var_duracion.get().strip())
                if duracion <= 0:
                    puede = False
            except Exception:
                puede = False

        try:
            if float(self.var_monto.get().strip().replace(",", ".")) <= 0:
                puede = False
        except Exception:
            puede = False

        self.btn_guardar.configure(state="normal" if puede else "disabled")

    def guardar(self):
        try:
            codigo = self.var_codigo.get().strip()
            cliente_texto = self.var_cliente.get().strip()
            fecha_inicio_db = fecha_form_a_db(self.var_fecha_inicio.get())
            fecha_fin_db = fecha_form_a_db(self.var_fecha_fin.get())
            monto = float(self.var_monto.get().strip().replace(",", "."))

            if not codigo:
                raise ValueError("No se pudo generar el código del contrato.")
            if not cliente_texto or cliente_texto not in self.mapa_clientes:
                raise ValueError("Debes seleccionar un cliente válido.")
            if monto <= 0:
                raise ValueError("El monto del contrato debe ser mayor a 0.")

            cliente_id = self.mapa_clientes[cliente_texto]
            vehiculo_ids = self._vehiculo_ids_seleccionados()
            vehiculos = self._vehiculo_rows_seleccionados()

            if not vehiculo_ids:
                raise ValueError("Debes seleccionar al menos un vehículo.")

            if len(vehiculos) != len(vehiculo_ids):
                raise ValueError("No se pudo validar la selección de vehículos.")

            for vehiculo in vehiculos:
                if row_get(vehiculo, "Cliente") != cliente_id:
                    raise ValueError("Todos los vehículos seleccionados deben pertenecer al cliente seleccionado.")

            vehiculo_id = vehiculo_ids[0]

            if self.clase_contrato == CLASE_ESTANDAR:
                for vehiculo in vehiculos:
                    tipo_vehiculo_nombre = normalizar(row_get(vehiculo, "TipoVehiculoNombre", ""))
                    if tipo_vehiculo_nombre != "AUTO":
                        raise ValueError("Los contratos estándar solo aplican para vehículos tipo Auto.")

                duracion = int(self.var_duracion.get().strip())
                horas = self._horas_seleccionadas()

                if self.es_renovacion and contrato_esta_vigente_por_fecha(self.fecha_fin_original_db):
                    if self.horas_originales and int(horas) != int(self.horas_originales):
                        raise ValueError("El contrato aún no venció. Solo puedes ampliar el plazo; el tipo de contrato se cambia únicamente cuando el contrato ya venció.")

                tarifa = self.tarifas_auto.get(horas, {})
                tarifa_detalle = tarifa.get("TarifaDetalle")

                if duracion <= 0:
                    raise ValueError("La duración debe ser mayor a 0.")
            else:
                duracion = 1
                horas = None
                tarifa_detalle = None

                if not es_admin(self.user_data) and not self.contrato:
                    raise ValueError("Solo el administrador puede crear contratos especiales.")

            if self.es_renovacion and self.fecha_fin_original_db:
                fecha_inicio_db = fecha_base_renovacion(self.fecha_fin_original_db)
                if self.clase_contrato == CLASE_ESTANDAR:
                    fecha_fin_db = sumar_meses_menos_un_dia(fecha_inicio_db, duracion)

            data = {
                "Cliente": cliente_id,
                "Vehiculo": vehiculo_id,
                "Vehiculos": vehiculo_ids,
                "CodigoContrato": codigo,
                "FechaInicio": fecha_inicio_db,
                "FechaFin": fecha_fin_db,
                "DuracionMes": duracion,
                "MontoContrato": monto,
                "ClaseContrato": self.clase_contrato,
                "TarifaDetalle": tarifa_detalle,
                "HorasPermitidasDia": horas,
                "Observacion": row_get(self.contrato, "Observacion") if self.contrato else None,
            }

            usr = obtener_usuario_id(self.user_data)

            if self.contrato:
                if es_empleado(self.user_data):
                    if int(row_get(self.contrato, "ClaseContrato", CLASE_ESTANDAR) or CLASE_ESTANDAR) == CLASE_ESPECIAL:
                        raise ValueError("El empleado no puede editar contratos especiales.")
                    if int(row_get(self.contrato, "EstadoPago", 0) or 0) == ESTADO_PAGO_PAGADO and not self.es_renovacion:
                        raise ValueError("El empleado no puede editar contratos ya pagados.")

                contrato_id_actual = row_get(self.contrato, "Contrato")
                actualizar_contrato(contrato_id_actual, data, usr)

                if self.abrir_pago_despues_guardar:
                    marcar_contrato_pendiente_pago(contrato_id_actual, usr)
                    self.on_save()
                    self.destroy()
                    abrir_modal_pago(self.master_view, self.user_data, contrato_id_actual, on_success=self.on_save)
                else:
                    self.on_save()
                    self.destroy()
                    messagebox.showinfo("Éxito", "Contrato actualizado correctamente.")
            else:
                contrato_id = insertar_contrato(data, usr)
                self.on_save()
                self.destroy()

                # Después de crear el contrato pendiente, el cobro se maneja con modules/payment.py.
                abrir_modal_pago(self.master_view, self.user_data, contrato_id, on_success=self.on_save)

        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el contrato.\n\n{e}", parent=self)


# =========================================================
# FORMULARIO DE RENOVACIÓN
# =========================================================
class RenovarContratoForm(ContractForm):
    def __init__(self, master, user_data, contrato, on_save):
        clase = int(row_get(contrato, "ClaseContrato", CLASE_ESTANDAR) or CLASE_ESTANDAR)
        super().__init__(
            master,
            user_data,
            on_save,
            clase_contrato=clase,
            contrato=contrato,
            abrir_pago_despues_guardar=True,
            es_renovacion=True,
        )
        try:
            self.title("Renovar contrato")
        except Exception:
            pass


# =========================================================
# VISTA PRINCIPAL
# =========================================================
class ContractsView(tk.Frame):
    def __init__(self, parent, user_data, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.user_data = user_data or {}
        self.configure(bg=COLOR_BG)

        self.var_busqueda = tk.StringVar()
        self.var_estado = tk.StringVar(value="Todos")
        self.var_clase = tk.StringVar(value="Todos")
        self.var_tipo_cliente = tk.StringVar(value="Todos")

        self.tree = None
        self.scrollbar_y = None

    def build(self):
        asegurar_columnas_contrato()
        suspender_contratos_vencidos(obtener_usuario_id(self.user_data))
        self._build_ui()
        self.cargar_contratos()
        self.pack(fill="both", expand=True)

    def _build_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        configurar_estilo_treeview()
        configurar_estilo_combobox()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        container = tk.Frame(self, bg="#ffffff", bd=1, relief="solid")
        container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        actions = tk.Frame(container, bg="#ffffff")
        actions.grid(row=0, column=0, sticky="ew", padx=14, pady=14)
        actions.columnconfigure(10, weight=1)

        tk.Label(actions, text="Buscar:", font=("Arial", 10, "bold"), bg="#ffffff", fg="#111111").grid(row=0, column=0, padx=(0, 6), sticky="w")
        entry_busqueda = tk.Entry(actions, textvariable=self.var_busqueda, font=("Arial", 10), relief="solid", bd=1, width=22)
        entry_busqueda.grid(row=0, column=1, padx=(0, 10), sticky="w", ipady=6)
        entry_busqueda.bind("<Return>", lambda _e: self.cargar_contratos())
        entry_busqueda.bind("<KeyRelease>", lambda _e: self.cargar_contratos())

        tk.Label(actions, text="Estado:", font=("Arial", 10, "bold"), bg="#ffffff", fg="#111111").grid(row=0, column=2, padx=(0, 6), sticky="w")
        cbo_estado = ttk.Combobox(
            actions,
            textvariable=self.var_estado,
            state="readonly",
            values=["Todos", "Pendiente", "Pagado", "Suspendido", "Vencido"],
            width=13,
            style="Simple.TCombobox",
        )
        cbo_estado.grid(row=0, column=3, padx=(0, 10), sticky="w", ipady=4)
        cbo_estado.bind("<<ComboboxSelected>>", lambda _e: self.cargar_contratos())

        tk.Label(actions, text="Contrato:", font=("Arial", 10, "bold"), bg="#ffffff", fg="#111111").grid(row=0, column=4, padx=(0, 6), sticky="w")
        cbo_clase = ttk.Combobox(
            actions,
            textvariable=self.var_clase,
            state="readonly",
            values=["Todos", "Estándar", "Especial"],
            width=13,
            style="Simple.TCombobox",
        )
        cbo_clase.grid(row=0, column=5, padx=(0, 10), sticky="w", ipady=4)
        cbo_clase.bind("<<ComboboxSelected>>", lambda _e: self.cargar_contratos())

        tk.Label(actions, text="Cliente:", font=("Arial", 10, "bold"), bg="#ffffff", fg="#111111").grid(row=0, column=6, padx=(0, 6), sticky="w")
        cbo_tipo_cliente = ttk.Combobox(
            actions,
            textvariable=self.var_tipo_cliente,
            state="readonly",
            values=["Todos", "GENERAL", "ESTUDIANTE"],
            width=13,
            style="Simple.TCombobox",
        )
        cbo_tipo_cliente.grid(row=0, column=7, padx=(0, 10), sticky="w", ipady=4)
        cbo_tipo_cliente.bind("<<ComboboxSelected>>", lambda _e: self.cargar_contratos())

        SimpleButton(actions, text="Limpiar", command=self.limpiar_filtros).grid(row=0, column=8, padx=(0, 8), sticky="w")

        SimpleButton(actions, text="Nuevo estándar", primary=True, command=lambda: self.abrir_nuevo(CLASE_ESTANDAR)).grid(row=0, column=11, padx=(0, 8), sticky="e")
        SimpleButton(actions, text="Nuevo especial", command=lambda: self.abrir_nuevo(CLASE_ESPECIAL)).grid(row=0, column=12, sticky="e")

        tabla_frame = tk.Frame(container, bg="#ffffff", bd=1, relief="solid")
        tabla_frame.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        tabla_frame.columnconfigure(0, weight=1)
        tabla_frame.rowconfigure(0, weight=1)

        columnas = (
            "Codigo",
            "Cliente",
            "TipoCliente",
            "Telefono",
            "Placa",
            "Color",
            "Modelo",
            "TipoContrato",
            "FechaInicio",
            "FechaFin",
            "Monto",
            "MetodoPago",
            "Estado",
        )

        self.tree = ttk.Treeview(
            tabla_frame,
            columns=columnas,
            show="headings",
            selectmode="browse",
            style="Contratos.Treeview",
        )

        encabezados = {
            "Codigo": "Código",
            "Cliente": "Cliente",
            "TipoCliente": "Tipo cliente",
            "Telefono": "Teléfono",
            "Placa": "Placas",
            "Color": "Colores",
            "Modelo": "Modelos",
            "TipoContrato": "Tipo contrato",
            "FechaInicio": "Fecha inicio",
            "FechaFin": "Fecha fin",
            "Monto": "Monto",
            "MetodoPago": "Método pago",
            "Estado": "Estado",
        }

        anchos = {
            "Codigo": 95,
            "Cliente": 190,
            "TipoCliente": 95,
            "Telefono": 90,
            "Placa": 170,
            "Color": 125,
            "Modelo": 150,
            "TipoContrato": 105,
            "FechaInicio": 90,
            "FechaFin": 90,
            "Monto": 85,
            "MetodoPago": 90,
            "Estado": 90,
        }

        for col in columnas:
            self.tree.heading(col, text=encabezados[col])
            anchor = "w" if col == "Cliente" else "center"
            stretch = col == "Cliente"
            self.tree.column(col, width=anchos[col], minwidth=60, anchor=anchor, stretch=stretch)

        self.scrollbar_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar_y.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Double-1>", lambda _e: self.editar_seleccionado())

        footer = tk.Frame(container, bg="#ffffff")
        footer.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))

        SimpleButton(footer, text="Editar", command=self.editar_seleccionado).pack(side="left", padx=(0, 8))
        SimpleButton(footer, text="Cobrar", primary=True, command=self.cobrar_seleccionado).pack(side="left", padx=(0, 8))
        SimpleButton(footer, text="Renovar", command=self.renovar_seleccionado).pack(side="left", padx=(0, 8))

        if es_admin(self.user_data):
            SimpleButton(footer, text="Suspender", command=lambda: self.cambiar_estado_seleccionado(ESTADO_SUSPENDIDO)).pack(side="left", padx=(0, 8))

    def limpiar_filtros(self):
        self.var_busqueda.set("")
        self.var_estado.set("Todos")
        self.var_clase.set("Todos")
        self.var_tipo_cliente.set("Todos")
        self.cargar_contratos()

    def cargar_contratos(self):
        if self.tree is None:
            return

        suspender_contratos_vencidos(obtener_usuario_id(self.user_data))

        for item in self.tree.get_children():
            self.tree.delete(item)

        filas = obtener_contratos(
            busqueda=self.var_busqueda.get().strip(),
            estado_visible=self.var_estado.get().strip(),
            clase=self.var_clase.get().strip(),
            tipo_cliente=self.var_tipo_cliente.get().strip(),
        )

        for fila in filas:
            cliente = nombre_cliente(fila)
            clase = int(row_get(fila, "ClaseContrato", CLASE_ESTANDAR) or CLASE_ESTANDAR)
            horas = row_get(fila, "HorasPermitidasDia")
            if clase == CLASE_ESTANDAR:
                tipo_contrato = f"{int(horas)}h" if horas else "Estándar"
            else:
                tipo_contrato = "Especial"

            metodo = METODO_PAGO.get(row_get(fila, "MetodoPago"), "Pendiente")
            estado_nombre = estado_visible_contrato(fila)

            modelo = row_get(fila, "Marca") or row_get(fila, "Modelo") or ""

            self.tree.insert(
                "",
                "end",
                iid=str(row_get(fila, "Contrato")),
                values=(
                    row_get(fila, "CodigoContrato"),
                    cliente,
                    row_get(fila, "TipoCliente", "GENERAL"),
                    row_get(fila, "Telefono") or "",
                    row_get(fila, "Placa") or "",
                    row_get(fila, "Color") or "",
                    modelo,
                    tipo_contrato,
                    fecha_db_a_form(row_get(fila, "FechaInicio")),
                    fecha_db_a_form(row_get(fila, "FechaFin")),
                    f"{float(row_get(fila, 'MontoContrato', 0) or 0):.2f}",
                    metodo,
                    estado_nombre,
                ),
            )

    def abrir_nuevo(self, clase_contrato):
        if clase_contrato == CLASE_ESPECIAL and not es_admin(self.user_data):
            messagebox.showwarning("Acceso denegado", "Solo el administrador puede crear contratos especiales.")
            return

        ContractForm(self, self.user_data, self.cargar_contratos, clase_contrato=clase_contrato)

    def _obtener_id_seleccionado(self):
        if not self.tree:
            return None
        seleccionado = self.tree.selection()
        if not seleccionado:
            messagebox.showwarning("Aviso", "Selecciona un contrato.")
            return None
        return int(seleccionado[0])

    def editar_seleccionado(self):
        contrato_id = self._obtener_id_seleccionado()
        if contrato_id is None:
            return

        contrato = obtener_contrato_por_id(contrato_id)
        if not contrato:
            messagebox.showerror("Error", "No se encontró el contrato.")
            return

        if int(row_get(contrato, "Estado", ESTADO_ACTIVO) or ESTADO_ACTIVO) in (ESTADO_SUSPENDIDO, ESTADO_VENCIDO):
            if not es_admin(self.user_data):
                messagebox.showwarning("Aviso", "Solo el administrador puede editar contratos suspendidos o vencidos.")
                return

        if es_empleado(self.user_data):
            if int(row_get(contrato, "ClaseContrato", CLASE_ESTANDAR) or CLASE_ESTANDAR) == CLASE_ESPECIAL:
                messagebox.showwarning("Acceso denegado", "El empleado no puede editar contratos especiales.")
                return
            if int(row_get(contrato, "EstadoPago", 0) or 0) == ESTADO_PAGO_PAGADO:
                messagebox.showwarning("Acceso denegado", "El empleado no puede editar contratos ya pagados.")
                return

        ContractForm(
            self,
            self.user_data,
            self.cargar_contratos,
            clase_contrato=int(row_get(contrato, "ClaseContrato", CLASE_ESTANDAR) or CLASE_ESTANDAR),
            contrato=contrato,
        )

    def cobrar_seleccionado(self):
        contrato_id = self._obtener_id_seleccionado()
        if contrato_id is None:
            return

        contrato = obtener_contrato_por_id(contrato_id)
        if not contrato:
            messagebox.showerror("Error", "No se encontró el contrato.")
            return

        estado = int(row_get(contrato, "Estado", ESTADO_ACTIVO) or ESTADO_ACTIVO)
        estado_pago = int(row_get(contrato, "EstadoPago", 0) or 0)

        if estado_pago == ESTADO_PAGO_PAGADO and estado not in (ESTADO_SUSPENDIDO, ESTADO_VENCIDO):
            messagebox.showinfo("Aviso", "Este contrato ya está pagado.")
            return

        # Si está suspendido o vencido, se permite cobrar para reactivarlo.
        if estado in (ESTADO_SUSPENDIDO, ESTADO_VENCIDO) and estado_pago == ESTADO_PAGO_PAGADO:
            try:
                marcar_contrato_pendiente_pago(contrato_id, obtener_usuario_id(self.user_data))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo preparar el contrato para cobro.\n\n{e}")
                return

        abrir_modal_pago(self, self.user_data, contrato_id, on_success=self.cargar_contratos)

    def renovar_seleccionado(self):
        contrato_id = self._obtener_id_seleccionado()
        if contrato_id is None:
            return

        contrato = obtener_contrato_por_id(contrato_id)
        if not contrato:
            messagebox.showerror("Error", "No se encontró el contrato.")
            return

        if int(row_get(contrato, "ClaseContrato", CLASE_ESTANDAR) or CLASE_ESTANDAR) == CLASE_ESPECIAL and not es_admin(self.user_data):
            messagebox.showwarning("Acceso denegado", "Solo el administrador puede renovar contratos especiales.")
            return

        RenovarContratoForm(self, self.user_data, contrato, self.cargar_contratos)

    def cambiar_estado_seleccionado(self, nuevo_estado):
        if nuevo_estado == ESTADO_SUSPENDIDO and not es_admin(self.user_data):
            messagebox.showwarning("Acceso denegado", "Solo el administrador puede suspender contratos.")
            return

        contrato_id = self._obtener_id_seleccionado()
        if contrato_id is None:
            return

        nombre_estado = "Suspendido" if nuevo_estado == ESTADO_SUSPENDIDO else "Estado"
        ok = messagebox.askyesno("Confirmar", f"¿Deseas cambiar el contrato a '{nombre_estado}'?")
        if not ok:
            return

        try:
            usr = obtener_usuario_id(self.user_data)
            cambiar_estado_contrato(contrato_id, nuevo_estado, usr=usr)
            self.cargar_contratos()
            messagebox.showinfo("Éxito", "Estado actualizado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def eliminar_seleccionado(self):
        if not es_admin(self.user_data):
            messagebox.showwarning("Acceso denegado", "Solo el administrador puede eliminar contratos.")
            return

        contrato_id = self._obtener_id_seleccionado()
        if contrato_id is None:
            return

        ok = messagebox.askyesno("Confirmar", "¿Deseas eliminar este contrato?\n\nEsta acción no se puede deshacer.")
        if not ok:
            return

        try:
            eliminar_contrato(contrato_id)
            self.cargar_contratos()
            messagebox.showinfo("Eliminado", "Contrato eliminado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar el contrato.\n\n{e}")
