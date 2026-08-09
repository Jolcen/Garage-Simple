import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

from database.db import get_connection


# =========================================================
# CATÁLOGOS
# =========================================================
METODO_PAGO_EFECTIVO = 1
METODO_PAGO_QR = 2

METODOS_PAGO = {
    METODO_PAGO_EFECTIVO: "Efectivo",
    METODO_PAGO_QR: "QR",
}

METODOS_PAGO_INV = {v: k for k, v in METODOS_PAGO.items()}

ESTADO_CONTRATO_ACTIVO = 1
ESTADO_PAGO_PENDIENTE = 0
ESTADO_PAGO_PAGADO = 1

COLOR_BG = "#f5f5f5"
COLOR_CARD = "#ffffff"
COLOR_TEXT = "#111111"
COLOR_MUTED = "#666666"
COLOR_PRIMARY = "#111827"
COLOR_BORDER = "#dddddd"
COLOR_DANGER = "#991b1b"

CONFIG_MULTA_TICKET_PERDIDO = "MULTA_TICKET_PERDIDO"
VALOR_DEFAULT_MULTA_TICKET_PERDIDO = 50.00


# =========================================================
# UTILIDADES
# =========================================================
def obtener_usuario_id(user_data):
    user_data = user_data or {}
    return user_data.get("Usuario") or user_data.get("id") or 0


def row_get(row, key, default=None):
    if row is None:
        return default
    try:
        return row[key]
    except Exception:
        try:
            return row[key] if isinstance(key, int) else default
        except Exception:
            return default


def ahora_db():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def nombre_cliente(row):
    nombres = str(row_get(row, "Nombres", "") or "").strip()
    apellidos = str(row_get(row, "Apellidos", "") or "").strip()
    return f"{nombres} {apellidos}".strip()


def _table_columns(cursor, table_name):
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [r[1] for r in cursor.fetchall()]
    except Exception:
        return []


def _table_exists(cursor, table_name):
    try:
        cursor.execute(
            "SELECT COUNT(*) AS Total FROM sqlite_master WHERE type='table' AND name = ?",
            (table_name,),
        )
        row = cursor.fetchone()
        try:
            return int(row["Total"] if row else 0) > 0
        except Exception:
            return int(row[0] if row else 0) > 0
    except Exception:
        return False


def _ensure_ticket_perdido_schema(cursor):
    """
    Refuerzo de compatibilidad.
    El schema.py ya crea CONFIGURACION, TicketPerdido y MontoMultaTicket,
    pero esto evita que el cobro falle si la base antigua aún no fue migrada.
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CONFIGURACION (
            Configuracion INTEGER PRIMARY KEY AUTOINCREMENT,
            Clave TEXT NOT NULL UNIQUE,
            Valor TEXT NOT NULL,
            Descripcion TEXT,
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),
            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT (date('now','localtime')),
            UsrHora TEXT NOT NULL DEFAULT (time('now','localtime')),
            FechaCreacion TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FechaModificacion TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    columnas_operacion = _table_columns(cursor, "OPERACION")
    if "TicketPerdido" not in columnas_operacion:
        cursor.execute("ALTER TABLE OPERACION ADD COLUMN TicketPerdido INTEGER NOT NULL DEFAULT 0 CHECK (TicketPerdido IN (0, 1))")
    if "MontoMultaTicket" not in columnas_operacion:
        cursor.execute("ALTER TABLE OPERACION ADD COLUMN MontoMultaTicket REAL NOT NULL DEFAULT 0 CHECK (MontoMultaTicket >= 0)")

    cursor.execute("""
        INSERT INTO CONFIGURACION (
            Clave, Valor, Descripcion, Estado, Usr, UsrFecha, UsrHora, FechaCreacion, FechaModificacion
        )
        VALUES (
            ?, ?, ?, 1, 0,
            date('now','localtime'),
            time('now','localtime'),
            datetime('now','localtime'),
            datetime('now','localtime')
        )
        ON CONFLICT(Clave) DO NOTHING
    """, (
        CONFIG_MULTA_TICKET_PERDIDO,
        f"{VALOR_DEFAULT_MULTA_TICKET_PERDIDO:.2f}",
        "Multa cobrada cuando el cliente pierde el ticket de parqueo",
    ))


def obtener_valor_configuracion(clave, default=None):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        _ensure_ticket_perdido_schema(cursor)
        cursor.execute("""
            SELECT Valor
            FROM CONFIGURACION
            WHERE Clave = ?
              AND Estado = 1
            LIMIT 1
        """, (clave,))
        row = cursor.fetchone()
        if not row:
            conn.commit()
            return default
        conn.commit()
        return row_get(row, "Valor", row[0])
    except Exception:
        return default
    finally:
        if conn:
            conn.close()


def obtener_multa_ticket_perdido():
    try:
        valor = obtener_valor_configuracion(
            CONFIG_MULTA_TICKET_PERDIDO,
            VALOR_DEFAULT_MULTA_TICKET_PERDIDO,
        )
        monto = float(str(valor).replace(",", "."))
        if monto < 0:
            return VALOR_DEFAULT_MULTA_TICKET_PERDIDO
        return round(monto, 2)
    except Exception:
        return VALOR_DEFAULT_MULTA_TICKET_PERDIDO


def aplicar_ticket_perdido_a_calculo(calculo_base, ticket_perdido=False):
    calculo = dict(calculo_base or {})
    monto_servicios = float(calculo.get("MontoServicios", 0) or 0)

    if ticket_perdido:
        multa = obtener_multa_ticket_perdido()
        calculo["TicketPerdido"] = 1
        calculo["MontoParqueo"] = 0.0
        calculo["MontoMultaTicket"] = round(float(multa), 2)
        calculo["MontoTotal"] = round(float(multa) + monto_servicios, 2)
    else:
        calculo["TicketPerdido"] = 0
        calculo["MontoMultaTicket"] = 0.0
        calculo["MontoTotal"] = round(float(calculo.get("MontoParqueo", 0) or 0) + monto_servicios, 2)

    return calculo


def obtener_vehiculos_texto_contrato(cursor, contrato_id):
    """
    Devuelve placas, colores y modelos agrupados para un contrato.
    Usa CONTRATOVEHICULO cuando existe, y mantiene compatibilidad
    con CONTRATO.Vehiculo si el contrato es antiguo.
    """
    placas = []
    colores = []
    modelos = []

    if _table_exists(cursor, "CONTRATOVEHICULO"):
        cursor.execute("""
            SELECT
                V.Placa,
                V.Color,
                COALESCE(V.Marca, V.Modelo) AS Modelo
            FROM CONTRATOVEHICULO CV
            INNER JOIN VEHICULO V ON V.Vehiculo = CV.Vehiculo
            WHERE CV.Contrato = ?
              AND CV.Estado = 1
            ORDER BY V.Placa ASC
        """, (contrato_id,))

        for row in cursor.fetchall():
            placa = str(row_get(row, "Placa", "") or "").strip()
            color = str(row_get(row, "Color", "") or "").strip()
            modelo = str(row_get(row, "Modelo", "") or "").strip()

            if placa:
                placas.append(placa)
            if color:
                colores.append(color)
            if modelo:
                modelos.append(modelo)

    if not placas:
        cursor.execute("""
            SELECT
                V.Placa,
                V.Color,
                COALESCE(V.Marca, V.Modelo) AS Modelo
            FROM CONTRATO C
            INNER JOIN VEHICULO V ON V.Vehiculo = C.Vehiculo
            WHERE C.Contrato = ?
            LIMIT 1
        """, (contrato_id,))
        row = cursor.fetchone()
        if row:
            placa = str(row_get(row, "Placa", "") or "").strip()
            color = str(row_get(row, "Color", "") or "").strip()
            modelo = str(row_get(row, "Modelo", "") or "").strip()

            if placa:
                placas.append(placa)
            if color:
                colores.append(color)
            if modelo:
                modelos.append(modelo)

    return {
        "placas": ", ".join(placas) if placas else "-",
        "colores": ", ".join(colores) if colores else "",
        "modelos": ", ".join(modelos) if modelos else "",
        "cantidad": len(placas),
    }


def resource_path(relative_path):
    candidates = []

    base_meipass = getattr(sys, "_MEIPASS", None)
    if base_meipass:
        candidates.append(os.path.join(base_meipass, relative_path))

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    candidates.append(os.path.join(project_root, relative_path))
    candidates.append(os.path.join(os.getcwd(), relative_path))

    for path in candidates:
        if os.path.exists(path):
            return path

    return candidates[0]


def buscar_qr_path():
    posibles = [
        "static/qr.png",
        "static/qr.jpg",
        "static/qr.jpeg",
        "static/QR.png",
        "static/QR.jpg",
        "static/qr_pago.png",
        "static/qr_pago.jpg",
    ]
    for rel in posibles:
        path = resource_path(rel)
        if os.path.exists(path):
            return path
    return None


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
            x = (window.winfo_screenwidth() // 2) - (width // 2)
            y = (window.winfo_screenheight() // 2) - (height // 2)

        window.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
    except Exception:
        window.geometry(f"{width}x{height}")


# =========================================================
# CONSULTAS
# =========================================================
def obtener_contrato_para_cobro(contrato_id):
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
                C.MontoContrato,
                C.ModalidadPago,
                C.EstadoPago,
                C.FechaPago,
                C.MontoPagado,
                C.Estado,
                CL.Nombres,
                CL.Apellidos,
                CL.Telefono
            FROM CONTRATO C
            INNER JOIN CLIENTE CL ON CL.Cliente = C.Cliente
            WHERE C.Contrato = ?
        """, (contrato_id,))
        contrato = cursor.fetchone()

        if not contrato:
            return None

        vehiculos = obtener_vehiculos_texto_contrato(cursor, contrato_id)

        # Convertimos a dict para poder añadir datos agrupados aunque sqlite3.Row
        # no permita columnas calculadas fuera del SELECT.
        data = dict(contrato)
        data["Placas"] = vehiculos["placas"]
        data["Colores"] = vehiculos["colores"]
        data["Modelos"] = vehiculos["modelos"]
        data["CantidadVehiculos"] = vehiculos["cantidad"]
        return data

    finally:
        if conn:
            conn.close()


def registrar_pago_contrato(contrato_id, metodo_pago, usr=0):
    metodo_pago = int(metodo_pago or METODO_PAGO_EFECTIVO)
    if metodo_pago not in (METODO_PAGO_EFECTIVO, METODO_PAGO_QR):
        metodo_pago = METODO_PAGO_EFECTIVO

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Contrato, CodigoContrato, MontoContrato, EstadoPago
            FROM CONTRATO
            WHERE Contrato = ?
        """, (contrato_id,))
        contrato = cursor.fetchone()

        if not contrato:
            raise ValueError("No se encontró el contrato.")

        if int(row_get(contrato, "EstadoPago", 0) or 0) == ESTADO_PAGO_PAGADO:
            raise ValueError("Este contrato ya fue pagado.")

        monto = float(row_get(contrato, "MontoContrato", 0) or 0)
        if monto <= 0:
            raise ValueError("El monto del contrato debe ser mayor a 0.")

        fecha_pago = ahora_db()

        cursor.execute("""
            UPDATE CONTRATO
            SET
                ModalidadPago = ?,
                MetodoPago = ?,
                EstadoPago = ?,
                FechaPago = ?,
                MontoPagado = ?,
                UsuarioPago = ?,
                Estado = ?,
                Usr = ?,
                UsrFecha = date('now','localtime'),
                UsrHora = time('now','localtime'),
                FechaModificacion = datetime('now','localtime')
            WHERE Contrato = ?
        """, (
            metodo_pago,
            metodo_pago,
            ESTADO_PAGO_PAGADO,
            fecha_pago,
            monto,
            usr,
            ESTADO_CONTRATO_ACTIVO,
            usr,
            contrato_id,
        ))

        columnas_pago = _table_columns(cursor, "PAGO")

        if "Contrato" in columnas_pago:
            cursor.execute("""
                INSERT INTO PAGO (
                    Operacion,
                    Contrato,
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
                    NULL,
                    ?,
                    ?,
                    datetime('now','localtime'),
                    ?,
                    ?,
                    ?,
                    1,
                    ?,
                    date('now','localtime'),
                    time('now','localtime'),
                    datetime('now','localtime'),
                    datetime('now','localtime')
                )
            """, (
                contrato_id,
                usr,
                metodo_pago,
                monto,
                f"Pago contrato {row_get(contrato, 'CodigoContrato', contrato_id)}",
                usr,
            ))

        try:
            cursor.execute("""
                INSERT INTO BITACORA (
                    Usuario,
                    Accion,
                    TablaAfectada,
                    RegistroAfectado,
                    Descripcion,
                    FechaEvento,
                    Estado,
                    Usr,
                    UsrFecha,
                    UsrHora,
                    FechaCreacion,
                    FechaModificacion
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    1,
                    ?,
                    date('now','localtime'),
                    time('now','localtime'),
                    datetime('now','localtime'),
                    datetime('now','localtime')
                )
            """, (
                usr,
                "COBRAR_CONTRATO",
                "CONTRATO",
                contrato_id,
                f"Se registró pago de contrato {row_get(contrato, 'CodigoContrato', contrato_id)} por Bs {monto:.2f}",
                fecha_pago,
                usr,
            ))
        except Exception:
            pass

        conn.commit()
        return True

    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# =========================================================
# MODAL DE PAGO
# =========================================================
class PaymentContractWindow(tk.Toplevel):
    def __init__(self, parent, user_data, contrato_id, on_success=None):
        super().__init__(parent)

        self.parent = parent
        self.user_data = user_data or {}
        self.contrato_id = contrato_id
        self.on_success = on_success

        self.contrato = obtener_contrato_para_cobro(contrato_id)
        if not self.contrato:
            messagebox.showerror("Error", "No se encontró el contrato.")
            self.destroy()
            return

        self.var_metodo = tk.StringVar(value="Efectivo")
        self.qr_image_ref = None
        self.qr_frame = None
        self.scroll_canvas = None
        self.scrollbar = None
        self.scrollable_frame = None

        self.title("Cobrar contrato")
        self.configure(bg=COLOR_BG)
        self.resizable(True, True)
        self.minsize(460, 450)
        self.transient(parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._build_ui()
        self._on_metodo_change()
        centrar_ventana(self, 460, 545, parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent)

        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def _bind_mousewheel(self, event):
        try:
            if self.scroll_canvas and self.scroll_canvas.winfo_exists():
                self.scroll_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
                self.scroll_canvas.bind_all("<Button-4>", self._on_mousewheel)
                self.scroll_canvas.bind_all("<Button-5>", self._on_mousewheel)
        except tk.TclError:
            pass

    def _unbind_mousewheel(self, event):
        try:
            if self.scroll_canvas and self.scroll_canvas.winfo_exists():
                self.scroll_canvas.unbind_all("<MouseWheel>")
                self.scroll_canvas.unbind_all("<Button-4>")
                self.scroll_canvas.unbind_all("<Button-5>")
        except tk.TclError:
            pass

    def _on_mousewheel(self, event):
        try:
            if not self.scroll_canvas or not self.scroll_canvas.winfo_exists():
                return
            delta = 0
            if hasattr(event, "delta") and event.delta:
                delta = int(-1 * (event.delta / 120))
            elif getattr(event, "num", None) == 4:
                delta = -1
            elif getattr(event, "num", None) == 5:
                delta = 1
            if delta != 0:
                self.scroll_canvas.yview_scroll(delta, "units")
        except tk.TclError:
            pass

    def _build_ui(self):
        outer = tk.Frame(self, bg=COLOR_BG)
        outer.pack(fill="both", expand=True, padx=14, pady=14)

        self.scroll_canvas = tk.Canvas(outer, bg=COLOR_BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self.scroll_canvas.yview)

        self.scrollable_frame = tk.Frame(self.scroll_canvas, bg=COLOR_BG)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))
        )

        canvas_window = self.scroll_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        def on_canvas_configure(event):
            try:
                if self.scroll_canvas and self.scroll_canvas.winfo_exists():
                    self.scroll_canvas.itemconfig(canvas_window, width=event.width)
            except tk.TclError:
                pass

        self.scroll_canvas.bind("<Configure>", on_canvas_configure)
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.scroll_canvas.bind("<Enter>", self._bind_mousewheel)
        self.scroll_canvas.bind("<Leave>", self._unbind_mousewheel)
        self.scrollable_frame.bind("<Enter>", self._bind_mousewheel)
        self.scrollable_frame.bind("<Leave>", self._unbind_mousewheel)

        card = tk.Frame(self.scrollable_frame, bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        card.columnconfigure(0, weight=1)

        tk.Label(
            card,
            text="Cobro de contrato",
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Arial", 17, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 6))

        cliente = nombre_cliente(self.contrato)
        codigo = row_get(self.contrato, "CodigoContrato", "")
        placas = row_get(self.contrato, "Placas", "") or "-"
        colores = row_get(self.contrato, "Colores", "") or ""
        modelos = row_get(self.contrato, "Modelos", "") or ""
        cantidad_vehiculos = int(row_get(self.contrato, "CantidadVehiculos", 0) or 0)
        monto = float(row_get(self.contrato, "MontoContrato", 0) or 0)

        tk.Label(
            card,
            text=f"Cliente: {cliente}",
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            font=("Arial", 9),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 2))

        tk.Label(
            card,
            text=f"Contrato: {codigo}",
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            font=("Arial", 9),
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 2))

        vehiculos_texto = f"Vehículos: {placas}"
        if cantidad_vehiculos == 1:
            vehiculos_texto = f"Vehículo: {placas}"

        tk.Label(
            card,
            text=vehiculos_texto,
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            font=("Arial", 9),
            wraplength=380,
            justify="left",
        ).grid(row=3, column=0, sticky="w", padx=18, pady=(0, 2))

        row_extra = 4
        if colores:
            tk.Label(
                card,
                text=f"Color(es): {colores}",
                bg=COLOR_CARD,
                fg=COLOR_MUTED,
                font=("Arial", 9),
                wraplength=380,
                justify="left",
            ).grid(row=row_extra, column=0, sticky="w", padx=18, pady=(0, 2))
            row_extra += 1

        if modelos:
            tk.Label(
                card,
                text=f"Modelo(s): {modelos}",
                bg=COLOR_CARD,
                fg=COLOR_MUTED,
                font=("Arial", 9),
                wraplength=380,
                justify="left",
            ).grid(row=row_extra, column=0, sticky="w", padx=18, pady=(0, 8))
            row_extra += 1

        tk.Label(
            card,
            text=f"Bs {monto:.2f}",
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Arial", 22, "bold"),
        ).grid(row=row_extra, column=0, sticky="w", padx=18, pady=(6, 10))
        row_extra += 1

        tk.Label(
            card,
            text="Método de pago",
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Arial", 10, "bold"),
        ).grid(row=row_extra, column=0, sticky="w", padx=18, pady=(0, 4))
        row_extra += 1

        combo = ttk.Combobox(
            card,
            textvariable=self.var_metodo,
            values=["Efectivo", "QR"],
            state="readonly",
            font=("Arial", 10),
        )
        combo.grid(row=row_extra, column=0, sticky="ew", padx=18, pady=(0, 8), ipady=3)
        combo.bind("<<ComboboxSelected>>", lambda _e: self._on_metodo_change())
        row_extra += 1

        self.qr_frame = tk.Frame(card, bg=COLOR_CARD, height=190)
        self.qr_frame.grid(row=row_extra, column=0, sticky="ew", padx=18, pady=(0, 4))
        self.qr_frame.grid_columnconfigure(0, weight=1)
        self.qr_frame.grid_propagate(False)
        row_extra += 1

        footer = tk.Frame(card, bg=COLOR_CARD)
        footer.grid(row=row_extra, column=0, sticky="e", padx=18, pady=(10, 16))

        tk.Button(
            footer,
            text="Confirmar pago",
            bg=COLOR_PRIMARY,
            fg="#ffffff",
            activebackground="#374151",
            activeforeground="#ffffff",
            bd=0,
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.confirmar_pago,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            footer,
            text="Cancelar",
            bg="#ffffff",
            fg=COLOR_TEXT,
            bd=1,
            relief="solid",
            padx=18,
            pady=7,
            cursor="hand2",
            command=self.destroy,
        ).pack(side="left")

    def _clear_qr_frame(self):
        for widget in self.qr_frame.winfo_children():
            widget.destroy()

    def _on_metodo_change(self):
        self._clear_qr_frame()

        if self.var_metodo.get() != "QR":
            tk.Label(
                self.qr_frame,
                text="El pago será registrado como efectivo.",
                bg=COLOR_CARD,
                fg=COLOR_MUTED,
                font=("Arial", 9),
            ).grid(row=0, column=0, sticky="w", pady=(8, 0))
            return

        qr_path = buscar_qr_path()

        if not qr_path:
            tk.Label(
                self.qr_frame,
                text="No se encontró imagen QR en static/qr.png o static/qr.jpg.",
                bg=COLOR_CARD,
                fg=COLOR_DANGER,
                font=("Arial", 9, "bold"),
                wraplength=360,
                justify="left",
            ).grid(row=0, column=0, sticky="w", pady=(8, 0))
            return

        try:
            if Image and ImageTk:
                img = Image.open(qr_path)
                img.thumbnail((155, 155))
                self.qr_image_ref = ImageTk.PhotoImage(img)

                tk.Label(
                    self.qr_frame,
                    image=self.qr_image_ref,
                    bg=COLOR_CARD,
                ).grid(row=0, column=0, pady=(0, 3))

            else:
                if qr_path.lower().endswith(".png"):
                    img = tk.PhotoImage(file=qr_path)
                    try:
                        factor = max(max(img.width(), img.height()) // 155, 1)
                        img = img.subsample(factor, factor)
                    except Exception:
                        pass
                    self.qr_image_ref = img
                    tk.Label(self.qr_frame, image=self.qr_image_ref, bg=COLOR_CARD).grid(row=0, column=0, pady=(0, 3))
                else:
                    raise RuntimeError("Para mostrar JPG se requiere Pillow.")

            tk.Label(
                self.qr_frame,
                text="Escanee el QR y confirme el pago.",
                bg=COLOR_CARD,
                fg=COLOR_MUTED,
                font=("Arial", 8),
                wraplength=350,
                justify="center",
            ).grid(row=1, column=0, sticky="ew")

        except Exception as e:
            tk.Label(
                self.qr_frame,
                text=f"No se pudo mostrar el QR.\n{e}",
                bg=COLOR_CARD,
                fg=COLOR_DANGER,
                font=("Arial", 9),
                wraplength=360,
                justify="left",
            ).grid(row=0, column=0, sticky="w")

    def confirmar_pago(self):
        metodo_txt = self.var_metodo.get().strip()
        metodo = METODOS_PAGO_INV.get(metodo_txt, METODO_PAGO_EFECTIVO)

        if int(row_get(self.contrato, "EstadoPago", 0) or 0) == ESTADO_PAGO_PAGADO:
            messagebox.showwarning("Aviso", "Este contrato ya fue pagado.", parent=self)
            return

        monto = float(row_get(self.contrato, "MontoContrato", 0) or 0)

        placas = row_get(self.contrato, "Placas", "") or "-"
        if not messagebox.askyesno(
            "Confirmar pago",
            f"¿Registrar pago por Bs {monto:.2f} mediante {metodo_txt}?\n\nVehículo(s): {placas}",
            parent=self,
        ):
            return

        try:
            usr = obtener_usuario_id(self.user_data)
            registrar_pago_contrato(self.contrato_id, metodo, usr=usr)

            messagebox.showinfo("Pago registrado", "El pago fue registrado correctamente.", parent=self)

            if callable(self.on_success):
                self.on_success()

            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar el pago.\n\n{e}", parent=self)



# =========================================================
# COBRO DE OPERACIÓN
# =========================================================
ESTADO_GENERAL_ACTIVO = 1
ESTADO_OPERACION_ACTIVO = 1
ESTADO_OPERACION_FINALIZADO = 2
ESTADO_OPERACION_SERVICIO_CANCELADO = 4
TIPO_OPERACION_CONTRATO = 2
TIPO_TARIFA_HORA = 1
TIPO_DIA_NORMAL = 1
TIPO_DETALLE_OPERACION = 1


def formatear_fecha(fecha_texto):
    if not fecha_texto:
        return ""
    try:
        return datetime.strptime(str(fecha_texto), "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(fecha_texto)


def nombre_tipo_operacion(tipo_operacion):
    if int(tipo_operacion or 1) == TIPO_OPERACION_CONTRATO:
        return "Contrato"
    return "Normal"


def obtener_operacion_para_cobro(operacion_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                O.Operacion,
                O.CodigoRetiro,
                O.FechaIngreso,
                O.Tarifa,
                O.Contrato,
                O.TipoOperacion,
                O.Estado,
                V.Vehiculo,
                V.Placa,
                V.TipoVehiculo,
                COALESCE(TV.Nombre, CAST(V.TipoVehiculo AS TEXT)) AS TipoVehiculoNombre
            FROM OPERACION O
            INNER JOIN VEHICULO V ON O.Vehiculo = V.Vehiculo
            LEFT JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = V.TipoVehiculo
            WHERE O.Operacion = ?
              AND O.Estado = ?
        """, (operacion_id, ESTADO_OPERACION_ACTIVO))
        return cursor.fetchone()
    finally:
        if conn:
            conn.close()


def obtener_total_servicios_operacion(cursor, operacion_id):
    cursor.execute("""
        SELECT COALESCE(SUM(Subtotal), 0) AS TotalServicios
        FROM OPERACIONSERVICIO
        WHERE Operacion = ?
          AND Estado != ?
    """, (operacion_id, ESTADO_OPERACION_SERVICIO_CANCELADO))
    row = cursor.fetchone()
    return float(row_get(row, "TotalServicios", 0) or 0)


def calcular_monto_parqueo_operacion(tipo_operacion, tipo_vehiculo_id, minutos_estadia):
    if int(tipo_operacion or 1) == TIPO_OPERACION_CONTRATO:
        return 0.0

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TD.Monto
            FROM TARIFA T
            INNER JOIN TARIFADETALLE TD ON T.Tarifa = TD.Tarifa
            WHERE T.Estado = ?
              AND T.TipoVehiculo = ?
              AND T.TipoTarifa = ?
              AND TD.Estado = ?
              AND TD.TipoDia = ?
              AND ? BETWEEN TD.MinutoInicio AND TD.MinutoFin
            ORDER BY TD.TarifaDetalle ASC
            LIMIT 1
        """, (
            ESTADO_GENERAL_ACTIVO,
            tipo_vehiculo_id,
            TIPO_TARIFA_HORA,
            ESTADO_GENERAL_ACTIVO,
            TIPO_DIA_NORMAL,
            minutos_estadia,
        ))
        row = cursor.fetchone()
        if row:
            return float(row_get(row, "Monto", 0) or 0)

        cursor.execute("""
            SELECT TD.Monto
            FROM TARIFA T
            INNER JOIN TARIFADETALLE TD ON T.Tarifa = TD.Tarifa
            WHERE T.Estado = ?
              AND T.TipoVehiculo = ?
              AND T.TipoTarifa = ?
              AND TD.Estado = ?
              AND TD.TipoDia = ?
            ORDER BY TD.MinutoFin DESC
            LIMIT 1
        """, (
            ESTADO_GENERAL_ACTIVO,
            tipo_vehiculo_id,
            TIPO_TARIFA_HORA,
            ESTADO_GENERAL_ACTIVO,
            TIPO_DIA_NORMAL,
        ))
        row = cursor.fetchone()
        if row:
            return float(row_get(row, "Monto", 0) or 0)

        raise ValueError("No existe detalle de tarifa por hora configurado para este tipo de vehículo.")
    finally:
        if conn:
            conn.close()


def calcular_operacion_para_cobro(operacion):
    fecha_ingreso = datetime.strptime(row_get(operacion, "FechaIngreso"), "%Y-%m-%d %H:%M:%S")
    fecha_salida = datetime.now()
    minutos = max(1, int((fecha_salida - fecha_ingreso).total_seconds() / 60))

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        monto_servicios = obtener_total_servicios_operacion(cursor, row_get(operacion, "Operacion"))
    finally:
        if conn:
            conn.close()

    monto_parqueo = calcular_monto_parqueo_operacion(
        row_get(operacion, "TipoOperacion"),
        row_get(operacion, "TipoVehiculo"),
        minutos,
    )

    total = round(float(monto_parqueo) + float(monto_servicios), 2)

    return {
        "FechaSalida": fecha_salida.strftime("%Y-%m-%d %H:%M:%S"),
        "MinutosEstadia": minutos,
        "MontoParqueo": round(float(monto_parqueo), 2),
        "MontoServicios": round(float(monto_servicios), 2),
        "MontoMultaTicket": 0.0,
        "TicketPerdido": 0,
        "MontoTotal": total,
    }


def registrar_pago_operacion(operacion_id, metodo_pago, calculo, usr=0):
    metodo_pago = int(metodo_pago or METODO_PAGO_EFECTIVO)
    if metodo_pago not in (METODO_PAGO_EFECTIVO, METODO_PAGO_QR):
        metodo_pago = METODO_PAGO_EFECTIVO

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Operacion, CodigoRetiro, Contrato, Estado
            FROM OPERACION
            WHERE Operacion = ?
        """, (operacion_id,))
        operacion = cursor.fetchone()
        if not operacion:
            raise ValueError("No se encontró la operación.")
        if int(row_get(operacion, "Estado", 0) or 0) != ESTADO_OPERACION_ACTIVO:
            raise ValueError("La operación ya no está activa o ya fue cobrada.")

        total = float(calculo["MontoTotal"] or 0)
        if total <= 0:
            raise ValueError("El total es Bs 0.00. No hay parqueo ni servicios para cobrar.")

        _ensure_ticket_perdido_schema(cursor)
        columnas_operacion = _table_columns(cursor, "OPERACION")
        ticket_perdido = int(calculo.get("TicketPerdido", 0) or 0)
        monto_multa = round(float(calculo.get("MontoMultaTicket", 0) or 0), 2)

        if "TicketPerdido" in columnas_operacion and "MontoMultaTicket" in columnas_operacion:
            cursor.execute("""
                UPDATE OPERACION
                SET
                    UsuarioSalida = ?,
                    FechaSalida = ?,
                    MinutosEstadia = ?,
                    MontoParqueo = ?,
                    MontoServicios = ?,
                    TicketPerdido = ?,
                    MontoMultaTicket = ?,
                    MontoTotal = ?,
                    Estado = ?,
                    Usr = ?,
                    UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'),
                    FechaModificacion = datetime('now','localtime')
                WHERE Operacion = ?
            """, (
                usr,
                calculo["FechaSalida"],
                calculo["MinutosEstadia"],
                calculo["MontoParqueo"],
                calculo["MontoServicios"],
                ticket_perdido,
                monto_multa,
                total,
                ESTADO_OPERACION_FINALIZADO,
                usr,
                operacion_id,
            ))
        else:
            cursor.execute("""
                UPDATE OPERACION
                SET
                    UsuarioSalida = ?,
                    FechaSalida = ?,
                    MinutosEstadia = ?,
                    MontoParqueo = ?,
                    MontoServicios = ?,
                    MontoTotal = ?,
                    Estado = ?,
                    Usr = ?,
                    UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'),
                    FechaModificacion = datetime('now','localtime')
                WHERE Operacion = ?
            """, (
                usr,
                calculo["FechaSalida"],
                calculo["MinutosEstadia"],
                calculo["MontoParqueo"],
                calculo["MontoServicios"],
                total,
                ESTADO_OPERACION_FINALIZADO,
                usr,
                operacion_id,
            ))

        columnas_pago = _table_columns(cursor, "PAGO")
        contrato_id = row_get(operacion, "Contrato")

        if "Contrato" in columnas_pago:
            cursor.execute("""
                INSERT INTO PAGO (
                    Operacion,
                    Contrato,
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
                    ?, ?, ?, ?, ?, ?, ?, 1, ?,
                    date('now','localtime'),
                    time('now','localtime'),
                    datetime('now','localtime'),
                    datetime('now','localtime')
                )
            """, (
                operacion_id,
                contrato_id,
                usr,
                calculo["FechaSalida"],
                metodo_pago,
                total,
                f"Cobro de operación. Código de retiro: {row_get(operacion, 'CodigoRetiro', '')}" + (". Ticket perdido" if ticket_perdido else ""),
                usr,
            ))
        else:
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
                    ?, ?, ?, ?, ?, ?, 1, ?,
                    date('now','localtime'),
                    time('now','localtime'),
                    datetime('now','localtime'),
                    datetime('now','localtime')
                )
            """, (
                operacion_id,
                usr,
                calculo["FechaSalida"],
                metodo_pago,
                total,
                f"Cobro de operación. Código de retiro: {row_get(operacion, 'CodigoRetiro', '')}" + (". Ticket perdido" if ticket_perdido else ""),
                usr,
            ))

        try:
            cursor.execute("""
                INSERT INTO BITACORA (
                    Usuario,
                    Accion,
                    TablaAfectada,
                    RegistroAfectado,
                    Descripcion,
                    FechaEvento,
                    Estado,
                    Usr,
                    UsrFecha,
                    UsrHora,
                    FechaCreacion,
                    FechaModificacion
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, 1, ?,
                    date('now','localtime'),
                    time('now','localtime'),
                    datetime('now','localtime'),
                    datetime('now','localtime')
                )
            """, (
                usr,
                "COBRAR_OPERACION",
                "OPERACION",
                operacion_id,
                f"Se cobró la operación {operacion_id} por Bs {total:.2f}" + (f". Ticket perdido: multa Bs {monto_multa:.2f}" if ticket_perdido else ""),
                calculo["FechaSalida"],
                usr,
            ))
        except Exception:
            pass

        conn.commit()
        return True

    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


class PaymentOperationWindow(tk.Toplevel):
    def __init__(self, parent, user_data, operacion_id, on_success=None):
        super().__init__(parent)

        self.parent = parent
        self.user_data = user_data or {}
        self.operacion_id = operacion_id
        self.on_success = on_success
        self.var_metodo = tk.StringVar(value="Efectivo")
        self.var_ticket_perdido = tk.IntVar(value=0)
        self.qr_image_ref = None
        self.qr_frame = None
        self.lbl_parqueo_valor = None
        self.lbl_multa_valor = None
        self.lbl_servicios_valor = None
        self.lbl_total_valor = None
        self.chk_ticket_perdido = None
        self.scroll_canvas = None
        self.scrollbar = None
        self.scrollable_frame = None

        self.operacion = obtener_operacion_para_cobro(operacion_id)
        if not self.operacion:
            messagebox.showerror("Error", "La operación no existe o ya no está activa.")
            self.destroy()
            return

        self.calculo_base = calcular_operacion_para_cobro(self.operacion)
        self.calculo = aplicar_ticket_perdido_a_calculo(self.calculo_base, False)

        self.title("Cobrar operación")
        self.configure(bg=COLOR_BG)
        self.resizable(True, True)
        self.minsize(480, 500)
        self.transient(parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._build_ui()
        self._on_metodo_change()
        centrar_ventana(self, 480, 575, parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent)

        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def _bind_mousewheel(self, event):
        try:
            if self.scroll_canvas and self.scroll_canvas.winfo_exists():
                self.scroll_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
                self.scroll_canvas.bind_all("<Button-4>", self._on_mousewheel)
                self.scroll_canvas.bind_all("<Button-5>", self._on_mousewheel)
        except tk.TclError:
            pass

    def _unbind_mousewheel(self, event):
        try:
            if self.scroll_canvas and self.scroll_canvas.winfo_exists():
                self.scroll_canvas.unbind_all("<MouseWheel>")
                self.scroll_canvas.unbind_all("<Button-4>")
                self.scroll_canvas.unbind_all("<Button-5>")
        except tk.TclError:
            pass

    def _on_mousewheel(self, event):
        try:
            if not self.scroll_canvas or not self.scroll_canvas.winfo_exists():
                return
            delta = 0
            if hasattr(event, "delta") and event.delta:
                delta = int(-1 * (event.delta / 120))
            elif getattr(event, "num", None) == 4:
                delta = -1
            elif getattr(event, "num", None) == 5:
                delta = 1
            if delta != 0:
                self.scroll_canvas.yview_scroll(delta, "units")
        except tk.TclError:
            pass

    def _build_ui(self):
        outer = tk.Frame(self, bg=COLOR_BG)
        outer.pack(fill="both", expand=True, padx=14, pady=14)

        self.scroll_canvas = tk.Canvas(outer, bg=COLOR_BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self.scroll_canvas.yview)

        self.scrollable_frame = tk.Frame(self.scroll_canvas, bg=COLOR_BG)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))
        )

        canvas_window = self.scroll_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        def on_canvas_configure(event):
            try:
                if self.scroll_canvas and self.scroll_canvas.winfo_exists():
                    self.scroll_canvas.itemconfig(canvas_window, width=event.width)
            except tk.TclError:
                pass

        self.scroll_canvas.bind("<Configure>", on_canvas_configure)
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.scroll_canvas.bind("<Enter>", self._bind_mousewheel)
        self.scroll_canvas.bind("<Leave>", self._unbind_mousewheel)
        self.scrollable_frame.bind("<Enter>", self._bind_mousewheel)
        self.scrollable_frame.bind("<Leave>", self._unbind_mousewheel)

        card = tk.Frame(self.scrollable_frame, bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        card.columnconfigure(0, weight=1)

        codigo = row_get(self.operacion, "CodigoRetiro", "")
        titulo_cobro = f"Cobro de parqueo ({codigo})"
        if int(row_get(self.operacion, "TipoOperacion", 1) or 1) == TIPO_OPERACION_CONTRATO:
            titulo_cobro = f"Cobro de servicios ({codigo})"

        tk.Label(
            card,
            text=titulo_cobro,
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Arial", 17, "bold")
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 8))

        tipo_vehiculo = row_get(self.operacion, "TipoVehiculoNombre", "")
        rows = [
            ("Placa", row_get(self.operacion, "Placa", "")),
            ("Tipo vehículo", tipo_vehiculo),
            ("Ingreso", formatear_fecha(row_get(self.operacion, "FechaIngreso", ""))),
            ("Salida", formatear_fecha(self.calculo["FechaSalida"])),
            ("Tiempo", f"{self.calculo['MinutosEstadia']} min"),
        ]

        info = tk.Frame(card, bg=COLOR_CARD)
        info.grid(row=1, column=0, sticky="ew", padx=18)
        info.columnconfigure(1, weight=1)

        fila_info = 0
        for label, value in rows:
            tk.Label(
                info,
                text=f"{label}:",
                bg=COLOR_CARD,
                fg=COLOR_TEXT,
                font=("Arial", 9, "bold"),
                width=16,
                anchor="w"
            ).grid(row=fila_info, column=0, sticky="w", pady=1)

            tk.Label(
                info,
                text=str(value),
                bg=COLOR_CARD,
                fg=COLOR_MUTED,
                font=("Arial", 9),
                anchor="w"
            ).grid(row=fila_info, column=1, sticky="w", padx=(8, 0), pady=1)
            fila_info += 1

        tk.Label(info, text="Parqueo:", bg=COLOR_CARD, fg=COLOR_TEXT, font=("Arial", 9, "bold"), width=16, anchor="w").grid(row=fila_info, column=0, sticky="w", pady=1)
        self.lbl_parqueo_valor = tk.Label(info, text="", bg=COLOR_CARD, fg=COLOR_MUTED, font=("Arial", 9), anchor="w")
        self.lbl_parqueo_valor.grid(row=fila_info, column=1, sticky="w", padx=(8, 0), pady=1)
        fila_info += 1

        tk.Label(info, text="Multa ticket:", bg=COLOR_CARD, fg=COLOR_TEXT, font=("Arial", 9, "bold"), width=16, anchor="w").grid(row=fila_info, column=0, sticky="w", pady=1)
        self.lbl_multa_valor = tk.Label(info, text="", bg=COLOR_CARD, fg=COLOR_MUTED, font=("Arial", 9), anchor="w")
        self.lbl_multa_valor.grid(row=fila_info, column=1, sticky="w", padx=(8, 0), pady=1)
        fila_info += 1

        tk.Label(info, text="Servicios:", bg=COLOR_CARD, fg=COLOR_TEXT, font=("Arial", 9, "bold"), width=16, anchor="w").grid(row=fila_info, column=0, sticky="w", pady=1)
        self.lbl_servicios_valor = tk.Label(info, text="", bg=COLOR_CARD, fg=COLOR_MUTED, font=("Arial", 9), anchor="w")
        self.lbl_servicios_valor.grid(row=fila_info, column=1, sticky="w", padx=(8, 0), pady=1)

        es_contrato = int(row_get(self.operacion, "TipoOperacion", 1) or 1) == TIPO_OPERACION_CONTRATO

        if not es_contrato:
            ticket_frame = tk.Frame(card, bg=COLOR_CARD)
            ticket_frame.grid(row=2, column=0, sticky="ew", padx=18, pady=(10, 2))
            self.chk_ticket_perdido = tk.Checkbutton(
                ticket_frame,
                text=f"Ticket perdido: cobrar multa Bs {obtener_multa_ticket_perdido():.2f}",
                variable=self.var_ticket_perdido,
                command=self._actualizar_calculo_ticket_perdido,
                bg=COLOR_CARD,
                fg=COLOR_TEXT,
                activebackground=COLOR_CARD,
                activeforeground=COLOR_TEXT,
                font=("Arial", 10, "bold"),
                anchor="w",
            )
            self.chk_ticket_perdido.pack(anchor="w")

            tk.Label(
                ticket_frame,
                text="Al marcar esta opción no se cobra parqueo; se cobra la multa y los servicios extra.",
                bg=COLOR_CARD,
                fg=COLOR_MUTED,
                font=("Arial", 8),
                wraplength=400,
                justify="left",
            ).pack(anchor="w", pady=(0, 2))
        else:
            self.var_ticket_perdido.set(0)
            tk.Label(
                card,
                text="Vehículo con contrato: solo se cobran servicios. La multa por ticket perdido aplica al parqueo normal.",
                bg=COLOR_CARD,
                fg=COLOR_MUTED,
                font=("Arial", 8),
                wraplength=400,
                justify="left",
            ).grid(row=2, column=0, sticky="w", padx=18, pady=(10, 2))

        self.lbl_total_valor = tk.Label(
            card,
            text="",
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Arial", 22, "bold")
        )
        self.lbl_total_valor.grid(row=3, column=0, sticky="w", padx=18, pady=(8, 8))

        tk.Label(
            card,
            text="Método de pago",
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Arial", 10, "bold")
        ).grid(row=4, column=0, sticky="w", padx=18, pady=(0, 4))

        combo = ttk.Combobox(
            card,
            textvariable=self.var_metodo,
            values=["Efectivo", "QR"],
            state="readonly",
            font=("Arial", 10)
        )
        combo.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 8), ipady=3)
        combo.bind("<<ComboboxSelected>>", lambda _e: self._on_metodo_change())

        self.qr_frame = tk.Frame(card, bg=COLOR_CARD, height=48)
        self.qr_frame.grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 4))
        self.qr_frame.columnconfigure(0, weight=1)
        self.qr_frame.grid_propagate(False)

        footer = tk.Frame(card, bg=COLOR_CARD)
        footer.grid(row=7, column=0, sticky="e", padx=18, pady=(6, 14))

        self._actualizar_calculo_ticket_perdido()

        tk.Button(
            footer,
            text="Confirmar cobro",
            bg=COLOR_PRIMARY,
            fg="#ffffff",
            bd=0,
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
            command=self.confirmar
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            footer,
            text="Cancelar",
            bg="#ffffff",
            fg=COLOR_TEXT,
            bd=1,
            relief="solid",
            padx=18,
            pady=7,
            cursor="hand2",
            command=self.destroy
        ).pack(side="left")

    def _actualizar_calculo_ticket_perdido(self):
        ticket_perdido = bool(self.var_ticket_perdido.get())
        es_contrato = int(row_get(self.operacion, "TipoOperacion", 1) or 1) == TIPO_OPERACION_CONTRATO

        if es_contrato:
            ticket_perdido = False
            self.var_ticket_perdido.set(0)

        self.calculo = aplicar_ticket_perdido_a_calculo(self.calculo_base, ticket_perdido)

        if self.lbl_parqueo_valor:
            self.lbl_parqueo_valor.configure(text=f"Bs {self.calculo['MontoParqueo']:.2f}")
        if self.lbl_multa_valor:
            self.lbl_multa_valor.configure(text=f"Bs {self.calculo['MontoMultaTicket']:.2f}")
        if self.lbl_servicios_valor:
            self.lbl_servicios_valor.configure(text=f"Bs {self.calculo['MontoServicios']:.2f}")
        if self.lbl_total_valor:
            self.lbl_total_valor.configure(text=f"Bs {self.calculo['MontoTotal']:.2f}")

    def _clear_qr_frame(self):
        for widget in self.qr_frame.winfo_children():
            widget.destroy()

    def _on_metodo_change(self):
        self._clear_qr_frame()
        if self.var_metodo.get() != "QR":
            self.qr_frame.configure(height=48)
            tk.Label(
                self.qr_frame,
                text="El cobro será registrado como efectivo.",
                bg=COLOR_CARD,
                fg=COLOR_MUTED,
                font=("Arial", 9)
            ).grid(row=0, column=0, sticky="w", pady=(8, 0))
            return

        self.qr_frame.configure(height=175)
        qr_path = buscar_qr_path()
        if not qr_path:
            tk.Label(self.qr_frame, text="No se encontró imagen QR en static/qr.png o static/qr.jpg.", bg=COLOR_CARD, fg=COLOR_DANGER, font=("Arial", 9, "bold"), wraplength=360, justify="left").grid(row=0, column=0, sticky="w", pady=(8, 0))
            return

        try:
            if Image and ImageTk:
                img = Image.open(qr_path)
                img.thumbnail((145, 145))
                self.qr_image_ref = ImageTk.PhotoImage(img)
                tk.Label(self.qr_frame, image=self.qr_image_ref, bg=COLOR_CARD).grid(row=0, column=0, pady=(0, 3))
            else:
                if not qr_path.lower().endswith(".png"):
                    raise RuntimeError("Para mostrar JPG se requiere Pillow.")
                img = tk.PhotoImage(file=qr_path)
                factor = max(max(img.width(), img.height()) // 145, 1)
                img = img.subsample(factor, factor)
                self.qr_image_ref = img
                tk.Label(self.qr_frame, image=self.qr_image_ref, bg=COLOR_CARD).grid(row=0, column=0, pady=(0, 3))

            tk.Label(self.qr_frame, text="Escanee el QR y confirme el cobro.", bg=COLOR_CARD, fg=COLOR_MUTED, font=("Arial", 8)).grid(row=1, column=0, sticky="ew")
        except Exception as e:
            tk.Label(self.qr_frame, text=f"No se pudo mostrar el QR.\n{e}", bg=COLOR_CARD, fg=COLOR_DANGER, font=("Arial", 9), wraplength=360, justify="left").grid(row=0, column=0, sticky="w")

    def confirmar(self):
        metodo_txt = self.var_metodo.get().strip()
        metodo = METODOS_PAGO_INV.get(metodo_txt, METODO_PAGO_EFECTIVO)
        total = float(self.calculo["MontoTotal"] or 0)

        if total <= 0:
            messagebox.showwarning("Sin monto", "No hay monto para cobrar.", parent=self)
            return

        detalle_confirmacion = f"¿Registrar cobro por Bs {total:.2f} mediante {metodo_txt}?"
        if int(self.calculo.get("TicketPerdido", 0) or 0) == 1:
            detalle_confirmacion += (
                f"\n\nTicket perdido:\n"
                f"- Parqueo: Bs {self.calculo['MontoParqueo']:.2f}\n"
                f"- Multa: Bs {self.calculo['MontoMultaTicket']:.2f}\n"
                f"- Servicios: Bs {self.calculo['MontoServicios']:.2f}"
            )

        if not messagebox.askyesno("Confirmar cobro", detalle_confirmacion, parent=self):
            return

        try:
            usr = obtener_usuario_id(self.user_data)
            registrar_pago_operacion(self.operacion_id, metodo, self.calculo, usr=usr)
            messagebox.showinfo("Cobro registrado", "El cobro fue registrado correctamente.", parent=self)
            if callable(self.on_success):
                self.on_success()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar el cobro.\n\n{e}", parent=self)


# =========================================================
# API SIMPLE PARA USAR DESDE contracts.py / operations.py
# =========================================================
def abrir_cobro_contrato(parent, user_data, contrato_id, on_success=None):
    return PaymentContractWindow(parent, user_data, contrato_id, on_success=on_success)


def abrir_cobro_operacion(parent, user_data, operacion_id, on_success=None):
    return PaymentOperationWindow(parent, user_data, operacion_id, on_success=on_success)


PaymentWindow = PaymentContractWindow
PaymentOperation = PaymentOperationWindow
