import tkinter as tk
from tkinter import ttk, messagebox

from database.db import get_connection
from utils.common import centrar_ventana


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
COLOR_BG = "#f5f5f5"
COLOR_CARD = "#ffffff"
COLOR_TEXT = "#111111"
COLOR_MUTED = "#666666"
COLOR_PRIMARY = "#111827"
COLOR_DANGER = "#991b1b"
COLOR_BORDER = "#d1d5db"

ESTADO_ACTIVO = 1
ESTADO_INACTIVO = 0

CONFIG_MULTA_TICKET_PERDIDO = "MULTA_TICKET_PERDIDO"
VALOR_DEFAULT_MULTA_TICKET_PERDIDO = 50.00


# =========================================================
# UTILIDADES BD
# =========================================================
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


def obtener_usuario_id(user_data):
    user_data = user_data or {}
    return user_data.get("Usuario") or user_data.get("id") or 0


def tabla_existe(cursor, tabla):
    cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name = ?",
        (tabla,),
    )
    return int(cursor.fetchone()[0] or 0) > 0


def columna_existe(cursor, tabla, columna):
    if not tabla_existe(cursor, tabla):
        return False
    cursor.execute(f"PRAGMA table_info({tabla})")
    return columna in [row[1] for row in cursor.fetchall()]


def asegurar_tablas_configuracion():
    """
    Refuerzo de seguridad para que el módulo funcione aunque la BD todavía no
    haya sido inicializada con el schema.py nuevo.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
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
            CREATE UNIQUE INDEX IF NOT EXISTS IDX_CONFIGURACION_Clave
            ON CONFIGURACION(Clave)
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
            CONFIG_MULTA_TICKET_PERDIDO,
            f"{VALOR_DEFAULT_MULTA_TICKET_PERDIDO:.2f}",
            "Monto de multa cuando el cliente pierde el ticket de parqueo",
        ))

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS TIPOVEHICULO (
                TipoVehiculo INTEGER PRIMARY KEY AUTOINCREMENT,
                Nombre TEXT NOT NULL UNIQUE,
                Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),

                Usr INTEGER NOT NULL DEFAULT 0,
                UsrFecha TEXT NOT NULL DEFAULT (date('now', 'localtime')),
                UsrHora TEXT NOT NULL DEFAULT (time('now', 'localtime')),
                FechaCreacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FechaModificacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)

        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def obtener_configuracion(clave, default=None):
    asegurar_tablas_configuracion()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Valor
            FROM CONFIGURACION
            WHERE Clave = ?
              AND Estado = 1
            LIMIT 1
        """, (clave,))
        row = cursor.fetchone()
        if not row:
            return default
        return row_get(row, "Valor", row_get(row, 0, default))
    finally:
        if conn:
            conn.close()


def actualizar_configuracion(clave, valor, descripcion=None, usr=0):
    asegurar_tablas_configuracion()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
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
                Descripcion = COALESCE(excluded.Descripcion, CONFIGURACION.Descripcion),
                Estado = 1,
                Usr = excluded.Usr,
                UsrFecha = date('now','localtime'),
                UsrHora = time('now','localtime'),
                FechaModificacion = datetime('now','localtime')
        """, (clave, str(valor), descripcion, usr))
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def obtener_multa_ticket_perdido():
    valor = obtener_configuracion(
        CONFIG_MULTA_TICKET_PERDIDO,
        f"{VALOR_DEFAULT_MULTA_TICKET_PERDIDO:.2f}",
    )
    try:
        return float(str(valor).replace(",", "."))
    except Exception:
        return VALOR_DEFAULT_MULTA_TICKET_PERDIDO


# =========================================================
# TIPOS DE VEHÍCULO
# =========================================================
def obtener_tipos_vehiculo():
    asegurar_tablas_configuracion()
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                TipoVehiculo,
                Nombre,
                Estado
            FROM TIPOVEHICULO
            ORDER BY TipoVehiculo ASC
        """)
        return cursor.fetchall()
    finally:
        if conn:
            conn.close()


def existe_tipo_vehiculo_nombre(nombre, excluir_id=None):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
            SELECT COUNT(*) AS Total
            FROM TIPOVEHICULO
            WHERE UPPER(TRIM(Nombre)) = UPPER(TRIM(?))
        """
        params = [nombre]
        if excluir_id is not None:
            query += " AND TipoVehiculo <> ? "
            params.append(excluir_id)
        cursor.execute(query, params)
        row = cursor.fetchone()
        return int(row_get(row, "Total", row_get(row, 0, 0)) or 0) > 0
    finally:
        if conn:
            conn.close()


def guardar_tipo_vehiculo(nombre, estado=ESTADO_ACTIVO, tipo_id=None, usr=0):
    asegurar_tablas_configuracion()
    nombre = str(nombre or "").strip()
    if not nombre:
        raise ValueError("Debes ingresar el nombre del tipo de vehículo.")

    estado = int(estado)
    if estado not in (ESTADO_ACTIVO, ESTADO_INACTIVO):
        estado = ESTADO_ACTIVO

    if existe_tipo_vehiculo_nombre(nombre, excluir_id=tipo_id):
        raise ValueError("Ya existe un tipo de vehículo con ese nombre.")

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if tipo_id:
            cursor.execute("""
                UPDATE TIPOVEHICULO
                SET
                    Nombre = ?,
                    Estado = ?,
                    Usr = ?,
                    UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'),
                    FechaModificacion = datetime('now','localtime')
                WHERE TipoVehiculo = ?
            """, (nombre, estado, usr, tipo_id))
        else:
            cursor.execute("""
                INSERT INTO TIPOVEHICULO (
                    Nombre,
                    Estado,
                    Usr,
                    UsrFecha,
                    UsrHora,
                    FechaCreacion,
                    FechaModificacion
                )
                VALUES (
                    ?, ?, ?,
                    date('now','localtime'),
                    time('now','localtime'),
                    datetime('now','localtime'),
                    datetime('now','localtime')
                )
            """, (nombre, estado, usr))

        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def tipo_vehiculo_en_uso(tipo_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        total = 0
        if tabla_existe(cursor, "VEHICULO"):
            cursor.execute("SELECT COUNT(*) FROM VEHICULO WHERE TipoVehiculo = ?", (tipo_id,))
            total += int(cursor.fetchone()[0] or 0)
        if tabla_existe(cursor, "TARIFA"):
            cursor.execute("SELECT COUNT(*) FROM TARIFA WHERE TipoVehiculo = ?", (tipo_id,))
            total += int(cursor.fetchone()[0] or 0)
        return total > 0
    finally:
        if conn:
            conn.close()


def eliminar_tipo_vehiculo(tipo_id):
    asegurar_tablas_configuracion()
    if tipo_vehiculo_en_uso(tipo_id):
        raise ValueError(
            "Este tipo de vehículo ya está en uso. No se eliminará para evitar errores; puedes dejarlo inactivo."
        )

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM TIPOVEHICULO WHERE TipoVehiculo = ?", (tipo_id,))
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# =========================================================
# ESTILOS
# =========================================================
def configurar_estilos():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        "Config.Treeview",
        background="#ffffff",
        foreground="#111111",
        rowheight=28,
        fieldbackground="#ffffff",
        borderwidth=0,
        relief="flat",
        font=("Arial", 10),
    )
    style.configure(
        "Config.Treeview.Heading",
        background="#eeeeee",
        foreground="#111111",
        font=("Arial", 10, "bold"),
        borderwidth=1,
        relief="flat",
    )
    style.map(
        "Config.Treeview",
        background=[("selected", "#d9e8ff")],
        foreground=[("selected", "#111111")],
    )


class SimpleButton(tk.Button):
    def __init__(self, master, text, command=None, primary=False, danger=False, **kwargs):
        bg = COLOR_PRIMARY if primary else "#ffffff"
        fg = "#ffffff" if primary else COLOR_TEXT
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
            padx=13,
            pady=7,
            cursor="hand2",
            **kwargs,
        )


# =========================================================
# MODAL TIPO VEHÍCULO
# =========================================================
class TipoVehiculoForm(tk.Toplevel):
    def __init__(self, parent, user_data, on_save, tipo=None):
        super().__init__(parent)
        self.parent = parent
        self.user_data = user_data or {}
        self.on_save = on_save
        self.tipo = tipo

        self.var_nombre = tk.StringVar(value=row_get(tipo, "Nombre", "") if tipo else "")
        self.var_estado = tk.StringVar(
            value="Activo" if int(row_get(tipo, "Estado", ESTADO_ACTIVO) or ESTADO_ACTIVO) == ESTADO_ACTIVO else "Inactivo"
        )

        self.title("Tipo de vehículo")
        self.configure(bg=COLOR_BG)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._build_ui()
        self._center(380, 240)

        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def _center(self, width, height):
        self.update_idletasks()
        try:
            parent = self.master.winfo_toplevel()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw // 2) - (width // 2)
            y = py + (ph // 2) - (height // 2)
            self.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
        except Exception:
            self.geometry(f"{width}x{height}")

    def _build_ui(self):
        main = tk.Frame(self, bg=COLOR_CARD, bd=1, relief="solid")
        main.pack(fill="both", expand=True, padx=16, pady=16)
        main.columnconfigure(0, weight=1)

        title = "Editar tipo de vehículo" if self.tipo else "Nuevo tipo de vehículo"
        tk.Label(
            main,
            text=title,
            font=("Arial", 15, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 12))

        tk.Label(
            main,
            text="Nombre",
            font=("Arial", 10, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 4))

        entry = tk.Entry(main, textvariable=self.var_nombre, font=("Arial", 10), relief="solid", bd=1)
        entry.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10), ipady=6)

        tk.Label(
            main,
            text="Estado",
            font=("Arial", 10, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
        ).grid(row=3, column=0, sticky="w", padx=16, pady=(0, 4))

        combo = ttk.Combobox(
            main,
            textvariable=self.var_estado,
            values=["Activo", "Inactivo"],
            state="readonly",
            font=("Arial", 10),
        )
        combo.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 12), ipady=4)

        footer = tk.Frame(main, bg=COLOR_CARD)
        footer.grid(row=5, column=0, sticky="e", padx=16, pady=(4, 14))

        SimpleButton(footer, text="Cancelar", command=self.destroy).pack(side="right", padx=(8, 0))
        SimpleButton(footer, text="Guardar", primary=True, command=self.guardar).pack(side="right")

        entry.focus_set()

    def guardar(self):
        try:
            tipo_id = row_get(self.tipo, "TipoVehiculo") if self.tipo else None
            estado = ESTADO_ACTIVO if self.var_estado.get() == "Activo" else ESTADO_INACTIVO
            usr = obtener_usuario_id(self.user_data)
            guardar_tipo_vehiculo(
                nombre=self.var_nombre.get(),
                estado=estado,
                tipo_id=tipo_id,
                usr=usr,
            )
            if callable(self.on_save):
                self.on_save()
            self.destroy()
            messagebox.showinfo("Guardado", "Tipo de vehículo guardado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


# =========================================================
# DIALOGO DE PREVIEW QR
# =========================================================
class QRPreviewDialog:
    def __init__(self, parent_view, user_data):
        self.parent_view = parent_view
        self.user_data = user_data or {}
        self.ruta_seleccionada = None
        self.qr_image_ref = None

        self.window = tk.Toplevel()
        self.window.title("Actualizar QR de Pago")
        self.window.configure(bg=COLOR_BG)
        self.window.resizable(False, False)
        self.window.grab_set()

        try:
            self.window.transient(parent_view.winfo_toplevel())
        except Exception:
            pass

        self._build_ui()
        self._cargar_qr_actual()
        centrar_ventana(self.window, 320, 380, parent_view.winfo_toplevel())

        try:
            self.window.grab_set()
            self.window.focus_force()
        except Exception:
            pass

    def _build_ui(self):
        frame = tk.Frame(self.window, bg=COLOR_BG)
        frame.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(
            frame,
            text="QR de Pago",
            font=("Arial", 13, "bold"),
            bg=COLOR_BG,
            fg=COLOR_TEXT,
        ).pack(anchor="w", pady=(0, 10))

        # Preview del QR
        self.preview_frame = tk.Frame(frame, bg=COLOR_CARD, bd=1, relief="solid")
        self.preview_frame.pack(fill="x", pady=(0, 12))

        self.preview_label = tk.Label(
            self.preview_frame,
            text="Cargando QR actual...",
            font=("Arial", 9),
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
        )
        self.preview_label.pack(padx=10, pady=10)

        # Botones
        btn_frame = tk.Frame(frame, bg=COLOR_BG)
        btn_frame.pack(fill="x")

        SimpleButton(
            btn_frame,
            text="Seleccionar",
            command=self._seleccionar,
        ).pack(side="left", padx=(0, 4))

        SimpleButton(
            btn_frame,
            text="Guardar",
            primary=True,
            command=self._guardar,
        ).pack(side="left", padx=(4, 4))

        SimpleButton(
            btn_frame,
            text="Cancelar",
            command=self._cancelar,
        ).pack(side="left", padx=(4, 0))

    def _buscar_qr_actual(self):
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        static_dir = os.path.join(base_dir, "static")
        for nombre in ["qr.png", "qr.jpg", "qr.jpeg"]:
            ruta = os.path.join(static_dir, nombre)
            if os.path.exists(ruta):
                return ruta
        return None

    def _cargar_qr_actual(self):
        ruta = self._buscar_qr_actual()
        if not ruta:
            self.preview_label.config(text="No se encontró imagen QR")
            return
        self._mostrar_preview(ruta)

    def _mostrar_preview(self, ruta):
        try:
            from PIL import Image, ImageTk
            img = Image.open(ruta)
            img.thumbnail((200, 200))
            self.qr_image_ref = ImageTk.PhotoImage(img)
            self.preview_label.config(image=self.qr_image_ref, text="")
        except ImportError:
            self.preview_label.config(text="Pillow no instalado")
        except Exception as e:
            self.preview_label.config(text=f"Error: {e}")

    def _seleccionar(self):
        from tkinter import filedialog
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen QR",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif")]
        )
        if ruta:
            self.ruta_seleccionada = ruta
            self._mostrar_preview(ruta)

    def _guardar(self):
        import shutil
        import os

        if not self.ruta_seleccionada:
            messagebox.showwarning("Aviso", "Primero selecciona una imagen.", parent=self.window)
            return

        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            static_dir = os.path.join(base_dir, "static")
            os.makedirs(static_dir, exist_ok=True)

            for ext in [".png", ".jpg", ".jpeg"]:
                ruta_vieja = os.path.join(static_dir, f"qr{ext}")
                if os.path.exists(ruta_vieja):
                    os.remove(ruta_vieja)

            shutil.copy2(self.ruta_seleccionada, os.path.join(static_dir, "qr.jpg"))
            self.window.destroy()
            messagebox.showinfo("Éxito", "QR actualizado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}", parent=self.window)

    def _cancelar(self):
        self.window.destroy()


# =========================================================
# VISTA PRINCIPAL
# =========================================================
class ConfigurationView(tk.Frame):
    def __init__(self, parent, user_data=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.user_data = user_data or {}
        self.configure(bg=COLOR_BG)

        self.var_multa = tk.StringVar()
        self.tree = None
        self.tipos_cache = []

    def build(self):
        asegurar_tablas_configuracion()
        configurar_estilos()
        self._build_ui()
        self.cargar_configuracion()
        self.cargar_tipos_vehiculo()
        self.pack(fill="both", expand=True)

    def _build_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        container = tk.Frame(self, bg=COLOR_BG)
        container.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        self._build_card_config(container)
        self._build_card_tipos(container)

    def _build_card_config(self, parent):
        card = tk.Frame(parent, bg=COLOR_CARD, bd=1, relief="solid")
        card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        # --- COLUMNA IZQUIERDA: MULTA ---
        left = tk.Frame(card, bg=COLOR_CARD)
        left.grid(row=0, column=0, sticky="nsew", padx=(14, 7), pady=12)
        left.columnconfigure(1, weight=1)

        tk.Label(
            left,
            text="Multa por pérdida de ticket",
            font=("Arial", 13, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

        tk.Label(
            left,
            text="Se usa en ticket impreso y cobro 'Ticket perdido'.",
            font=("Arial", 9),
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))

        tk.Label(
            left,
            text="Monto Bs:",
            font=("Arial", 10, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
        ).grid(row=2, column=0, sticky="w", pady=(0, 14))

        input_frame = tk.Frame(left, bg=COLOR_CARD)
        input_frame.grid(row=2, column=1, columnspan=2, sticky="w", pady=(0, 14))

        entry = tk.Entry(
            input_frame,
            textvariable=self.var_multa,
            font=("Arial", 10),
            relief="solid",
            bd=1,
            width=14,
        )
        entry.pack(side="left", ipady=6)

        SimpleButton(
            input_frame,
            text="Guardar",
            primary=True,
            command=self.guardar_multa,
        ).pack(side="left", padx=(10, 0))

        # --- COLUMNA DERECHA: QR ---
        right = tk.Frame(card, bg=COLOR_CARD)
        right.grid(row=0, column=1, sticky="nsew", padx=(7, 14), pady=12)
        right.columnconfigure(0, weight=1)

        tk.Label(
            right,
            text="QR de Pago",
            font=("Arial", 13, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        tk.Label(
            right,
            text="Imagen QR que se muestra al cliente.",
            font=("Arial", 9),
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(0, 10))

        SimpleButton(
            right,
            text="Actualizar QR",
            primary=True,
            command=self.actualizar_qr,
        ).grid(row=2, column=0, sticky="w", pady=(0, 0))

    def _build_card_tipos(self, parent):
        card = tk.Frame(parent, bg=COLOR_CARD, bd=1, relief="solid")
        card.grid(row=2, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        header = tk.Frame(card, bg=COLOR_CARD)
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        header.columnconfigure(0, weight=1)

        tk.Label(
            header,
            text="Tipos de vehículo",
            font=("Arial", 13, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
        ).grid(row=0, column=0, sticky="w")

        SimpleButton(
            header,
            text="Nuevo tipo",
            primary=True,
            command=self.nuevo_tipo,
        ).grid(row=0, column=1, sticky="e")

        tk.Label(
            card,
            text="Puedes crear, editar o dejar inactivo un tipo. Si ya está usado por vehículos o tarifas, no se elimina para evitar errores.",
            font=("Arial", 9),
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 8))

        table_frame = tk.Frame(card, bg=COLOR_CARD)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 10))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("TipoVehiculo", "Nombre", "Estado")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Config.Treeview",
        )
        self.tree.heading("TipoVehiculo", text="ID")
        self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("Estado", text="Estado")

        self.tree.column("TipoVehiculo", width=70, minwidth=50, anchor="center", stretch=False)
        self.tree.column("Nombre", width=260, minwidth=120, anchor="w", stretch=True)
        self.tree.column("Estado", width=110, minwidth=80, anchor="center", stretch=False)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<Double-1>", lambda _e: self.editar_tipo())

        footer = tk.Frame(card, bg=COLOR_CARD)
        footer.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))

        SimpleButton(footer, text="Editar", command=self.editar_tipo).pack(side="left", padx=(0, 8))
        SimpleButton(footer, text="Activar/Inactivar", command=self.cambiar_estado_tipo).pack(side="left", padx=(0, 8))
        SimpleButton(footer, text="Eliminar", danger=True, command=self.eliminar_tipo).pack(side="left")
        SimpleButton(footer, text="Actualizar", command=self.cargar_tipos_vehiculo).pack(side="right")

    def cargar_configuracion(self):
        multa = obtener_multa_ticket_perdido()
        self.var_multa.set(f"{multa:.2f}")

    def guardar_multa(self):
        try:
            texto_monto = self.var_multa.get().strip().replace(",", ".")
            monto = float(texto_monto)
            if monto < 0:
                raise ValueError("El monto no puede ser negativo.")
            usr = obtener_usuario_id(self.user_data)
            actualizar_configuracion(
                CONFIG_MULTA_TICKET_PERDIDO,
                f"{monto:.2f}",
                "Monto de multa cuando el cliente pierde el ticket de parqueo",
                usr=usr,
            )
            self.var_multa.set(f"{monto:.2f}")
            messagebox.showinfo("Guardado", "Multa actualizada correctamente.")
        except ValueError as e:
            messagebox.showwarning("Dato inválido", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la multa.\n\n{e}")

    def actualizar_qr(self):
        """Abre modal de actualización de QR."""
        QRPreviewDialog(self, self.user_data)

    def cargar_tipos_vehiculo(self):
        if self.tree is None:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.tipos_cache = obtener_tipos_vehiculo()
        for row in self.tipos_cache:
            estado_txt = "Activo" if int(row_get(row, "Estado", ESTADO_ACTIVO) or ESTADO_ACTIVO) == ESTADO_ACTIVO else "Inactivo"
            self.tree.insert(
                "",
                "end",
                iid=str(row_get(row, "TipoVehiculo")),
                values=(
                    row_get(row, "TipoVehiculo"),
                    row_get(row, "Nombre", ""),
                    estado_txt,
                ),
            )

    def _tipo_seleccionado_id(self):
        if not self.tree:
            return None
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecciona un tipo de vehículo.")
            return None
        return int(sel[0])

    def _tipo_por_id(self, tipo_id):
        for row in self.tipos_cache:
            if int(row_get(row, "TipoVehiculo", 0) or 0) == int(tipo_id):
                return row
        return None

    def nuevo_tipo(self):
        TipoVehiculoForm(self, self.user_data, self.cargar_tipos_vehiculo)

    def editar_tipo(self):
        tipo_id = self._tipo_seleccionado_id()
        if tipo_id is None:
            return
        tipo = self._tipo_por_id(tipo_id)
        if not tipo:
            messagebox.showerror("Error", "No se encontró el tipo seleccionado.")
            return
        TipoVehiculoForm(self, self.user_data, self.cargar_tipos_vehiculo, tipo=tipo)

    def cambiar_estado_tipo(self):
        tipo_id = self._tipo_seleccionado_id()
        if tipo_id is None:
            return

        tipo = self._tipo_por_id(tipo_id)
        if not tipo:
            messagebox.showerror("Error", "No se encontró el tipo seleccionado.")
            return

        estado_actual = int(row_get(tipo, "Estado", ESTADO_ACTIVO) or ESTADO_ACTIVO)
        nuevo_estado = ESTADO_INACTIVO if estado_actual == ESTADO_ACTIVO else ESTADO_ACTIVO
        accion = "inactivar" if nuevo_estado == ESTADO_INACTIVO else "activar"

        if not messagebox.askyesno("Confirmar", f"¿Deseas {accion} este tipo de vehículo?"):
            return

        try:
            usr = obtener_usuario_id(self.user_data)
            guardar_tipo_vehiculo(
                nombre=row_get(tipo, "Nombre", ""),
                estado=nuevo_estado,
                tipo_id=tipo_id,
                usr=usr,
            )
            self.cargar_tipos_vehiculo()
            messagebox.showinfo("Guardado", "Estado actualizado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def eliminar_tipo(self):
        tipo_id = self._tipo_seleccionado_id()
        if tipo_id is None:
            return

        if not messagebox.askyesno(
            "Confirmar",
            "¿Deseas eliminar este tipo de vehículo?\n\nSi está usado por vehículos o tarifas, no se eliminará.",
        ):
            return

        try:
            eliminar_tipo_vehiculo(tipo_id)
            self.cargar_tipos_vehiculo()
            messagebox.showinfo("Eliminado", "Tipo de vehículo eliminado correctamente.")
        except Exception as e:
            messagebox.showwarning("No eliminado", str(e))


# Alias por si tu dashboard usa otro nombre al importar.
ConfigurationWindow = ConfigurationView
ConfigView = ConfigurationView
ConfiguracionView = ConfigurationView
