import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from database.db import get_connection


# =========================================================
# CATÁLOGOS / ESTADOS
# =========================================================
ESTADO_GENERAL_INACTIVO = 0
ESTADO_GENERAL_ACTIVO = 1

ESTADO_OPERACION_ACTIVO = 1
ESTADO_CONTRATO_ACTIVO = 1

TIPO_CLIENTE_GENERAL = "GENERAL"
TIPO_CLIENTE_ESTUDIANTE = "ESTUDIANTE"
TIPOS_CLIENTE = [TIPO_CLIENTE_GENERAL, TIPO_CLIENTE_ESTUDIANTE]

MARCAS_AUTO = [
    "Toyota", "Nissan", "Suzuki", "Hyundai", "Kia", "Chevrolet",
    "Ford", "Volkswagen", "Mitsubishi", "Honda", "Mazda", "Renault",
    "Peugeot", "Fiat", "Jeep", "BMW", "Mercedes-Benz", "Audi", "Otro"
]

MARCAS_MOTO = [
    "Honda", "Yamaha", "Suzuki", "Kawasaki", "Bajaj", "TVS",
    "Hero", "Italika", "Loncin", "Lifan", "Racer", "Boxer", "Otro"
]

COLORES_VEHICULO = [
    "Blanco", "Negro", "Gris", "Plateado", "Rojo", "Azul",
    "Verde", "Amarillo", "Naranja", "Café", "Beige",
    "Guindo", "Dorado", "Otro"
]

COLOR_BG = "#f3f4f6"
COLOR_CARD = "#ffffff"
COLOR_PANEL = "#f8fafc"
COLOR_BORDER = "#e5e7eb"
COLOR_TEXT = "#111827"
COLOR_MUTED = "#6b7280"
COLOR_PRIMARY = "#2563eb"
COLOR_SUCCESS = "#16a34a"
COLOR_WARNING = "#f59e0b"
COLOR_DANGER = "#dc2626"
COLOR_GRAY = "#6b7280"
COLOR_LIGHT_BUTTON = "#e5e7eb"


# =========================================================
# UTILIDADES
# =========================================================
def obtener_usuario_actual_id(user_data):
    if not user_data:
        return 0
    return user_data.get("Usuario") or user_data.get("id") or 0


def obtener_rol_usuario(user_data):
    if not user_data:
        return ""
    return str(
        user_data.get("Rol")
        or user_data.get("rol")
        or user_data.get("Role")
        or user_data.get("role")
        or ""
    ).strip().lower()


def es_usuario_empleado(user_data):
    return obtener_rol_usuario(user_data) == "empleado"


def limpiar_placa_para_busqueda(placa):
    return (placa or "").replace(" ", "").replace("-", "").upper().strip()


def nombre_cliente_completo(nombres, apellidos):
    nombres = (nombres or "").strip()
    apellidos = (apellidos or "").strip()
    return f"{nombres} {apellidos}".strip()


def texto_o_vacio(valor):
    return valor if valor is not None else ""


def datetime_now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


def crear_label(parent, text, font=("Arial", 10, "bold"), fg=COLOR_TEXT, bg=None):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg or parent.cget("bg"))


def crear_entry(parent, width=None):
    entry = tk.Entry(parent, font=("Arial", 11), relief="solid", bd=1, highlightthickness=0)
    if width:
        entry.configure(width=width)
    return entry


def _tabla_existe(cursor, nombre_tabla):
    cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND UPPER(name) = UPPER(?)",
        (nombre_tabla,),
    )
    return cursor.fetchone()[0] > 0


def _columna_existe(cursor, tabla, columna):
    cursor.execute(f"PRAGMA table_info({tabla})")
    return columna in [r[1] for r in cursor.fetchall()]


def _deduplicar_textos(valores):
    resultado = []
    vistos = set()
    for valor in valores:
        texto = str(valor or "").strip()
        if not texto:
            continue
        clave = texto.upper()
        if clave in vistos:
            continue
        vistos.add(clave)
        resultado.append(texto)
    return resultado


def nombre_tipo_desde_id(tipo_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Nombre FROM TIPOVEHICULO WHERE TipoVehiculo = ? LIMIT 1",
            (tipo_id,),
        )
        row = cursor.fetchone()
        return row_get(row, "Nombre", "") or (row[0] if row else "")
    except Exception:
        return ""
    finally:
        if conn:
            conn.close()


# =========================================================
# TIPOS DE VEHÍCULO
# =========================================================
def ensure_tipo_vehiculo_minimo():
    """Garantiza Auto/Moto sin crear valores basura desde otras tablas."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if not _tabla_existe(cursor, "TIPOVEHICULO"):
            return

        datos = [(1, "Auto"), (2, "Moto")]
        for tipo_id, nombre in datos:
            cursor.execute("SELECT TipoVehiculo FROM TIPOVEHICULO WHERE TipoVehiculo = ?", (tipo_id,))
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    """
                    UPDATE TIPOVEHICULO
                    SET Nombre = ?, Estado = 1,
                        UsrFecha = date('now','localtime'),
                        UsrHora = time('now','localtime'),
                        FechaModificacion = datetime('now','localtime')
                    WHERE TipoVehiculo = ?
                    """,
                    (nombre, tipo_id),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO TIPOVEHICULO (
                        TipoVehiculo, Nombre, Estado, Usr,
                        UsrFecha, UsrHora, FechaCreacion, FechaModificacion
                    )
                    VALUES (
                        ?, ?, 1, 0,
                        date('now','localtime'), time('now','localtime'),
                        datetime('now','localtime'), datetime('now','localtime')
                    )
                    """,
                    (tipo_id, nombre),
                )
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def obtener_tipos_vehiculo_desde_bd():
    ensure_tipo_vehiculo_minimo()
    conn = None
    tipos = []
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if _tabla_existe(cursor, "TIPOVEHICULO"):
            cursor.execute(
                """
                SELECT TipoVehiculo, Nombre
                FROM TIPOVEHICULO
                WHERE Estado = ?
                ORDER BY TipoVehiculo ASC
                """,
                (ESTADO_GENERAL_ACTIVO,),
            )
            for row in cursor.fetchall():
                tipo_id = row_get(row, "TipoVehiculo", row[0])
                nombre = row_get(row, "Nombre", row[1])
                tipos.append((tipo_id, nombre))
    except Exception:
        tipos = []
    finally:
        if conn:
            conn.close()

    if not tipos:
        tipos = [(1, "Auto"), (2, "Moto")]

    return tipos


def crear_mapa_tipos():
    rows = obtener_tipos_vehiculo_desde_bd()
    nombre_a_id = {str(nombre): tipo_id for tipo_id, nombre in rows}
    id_a_nombre = {tipo_id: str(nombre) for tipo_id, nombre in rows}
    return rows, nombre_a_id, id_a_nombre


# =========================================================
# BITÁCORA
# =========================================================
def insertar_bitacora(cursor, usr, accion, tabla, registro, descripcion):
    try:
        cursor.execute(
            """
            INSERT INTO BITACORA (
                Usuario, Accion, TablaAfectada, RegistroAfectado, Descripcion,
                FechaEvento, Estado, Usr, UsrFecha, UsrHora,
                FechaCreacion, FechaModificacion
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                date('now','localtime'), time('now','localtime'),
                datetime('now','localtime'), datetime('now','localtime')
            )
            """,
            (usr, accion, tabla, registro, descripcion, datetime_now_text(), ESTADO_GENERAL_ACTIVO, usr),
        )
    except Exception:
        pass


# =========================================================
# VISTA PRINCIPAL
# =========================================================
class VehiclesCustomersView:
    def __init__(self, parent, user_data):
        self.parent = parent
        self.user_data = user_data or {}
        self.tree = None
        self.search_entry = None

    def build(self):
        for widget in self.parent.winfo_children():
            widget.destroy()

        try:
            self.parent.configure(bg=COLOR_BG)
        except Exception:
            pass

        self.build_header()
        self.build_table()
        self.load_records()

    def build_header(self):
        header_frame = tk.Frame(self.parent, bg="white")
        header_frame.pack(fill="x", padx=15, pady=15)

        tk.Label(header_frame, text="Buscar:", font=("Arial", 11, "bold"), bg="white", fg=COLOR_TEXT).pack(side="left", padx=(0, 8))

        self.search_entry = tk.Entry(header_frame, font=("Arial", 11), width=30)
        self.search_entry.pack(side="left", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda event: self.load_records())

        tk.Button(
            header_frame, text="Buscar", font=("Arial", 10, "bold"),
            bg=COLOR_PRIMARY, fg="white", activebackground="#1d4ed8",
            activeforeground="white", bd=0, relief="flat", padx=15, pady=6,
            cursor="hand2", command=self.load_records
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            header_frame, text="Nuevo registro", font=("Arial", 10, "bold"),
            bg=COLOR_SUCCESS, fg="white", activebackground="#15803d",
            activeforeground="white", bd=0, relief="flat", padx=15, pady=6,
            cursor="hand2", command=self.open_new_window
        ).pack(side="right")

    def build_table(self):
        table_frame = tk.Frame(self.parent, bg="white")
        table_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        columns = (
            "Vehiculo", "Placa", "TipoVehiculo", "Modelo", "Color",
            "TipoCliente", "Cliente", "Telefono", "Acciones"
        )

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)

        self.tree.heading("Vehiculo", text="ID")
        self.tree.heading("Placa", text="Placa")
        self.tree.heading("TipoVehiculo", text="Tipo")
        self.tree.heading("Modelo", text="Modelo")
        self.tree.heading("Color", text="Color")
        self.tree.heading("TipoCliente", text="Tipo cliente")
        self.tree.heading("Cliente", text="Cliente")
        self.tree.heading("Telefono", text="Teléfono")
        self.tree.heading("Acciones", text="Acciones")

        self.tree.column("Vehiculo", width=50, anchor="center", stretch=False)
        self.tree.column("Placa", width=95, anchor="center", stretch=False)
        self.tree.column("TipoVehiculo", width=85, anchor="center", stretch=False)
        self.tree.column("Modelo", width=120, anchor="center", stretch=False)
        self.tree.column("Color", width=90, anchor="center", stretch=False)
        self.tree.column("TipoCliente", width=105, anchor="center", stretch=False)
        self.tree.column("Cliente", width=210, anchor="w", stretch=True)
        self.tree.column("Telefono", width=105, anchor="center", stretch=False)
        self.tree.column("Acciones", width=130, anchor="center", stretch=False)

        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.on_double_click)

    def load_records(self):
        if not self.tree:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        search_value = self.search_entry.get().strip().upper() if self.search_entry else ""

        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            tiene_tipo_cliente = _columna_existe(cursor, "CLIENTE", "TipoCliente")

            tipo_cliente_select = "C.TipoCliente" if tiene_tipo_cliente else "'GENERAL' AS TipoCliente"

            query = f"""
                SELECT
                    V.Vehiculo,
                    V.Placa,
                    COALESCE(TV.Nombre, CAST(V.TipoVehiculo AS TEXT)) AS TipoVehiculoNombre,
                    V.Marca AS ModeloVehiculo,
                    V.Color,
                    C.Nombres,
                    C.Apellidos,
                    C.Telefono,
                    {tipo_cliente_select}
                FROM VEHICULO V
                LEFT JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = V.TipoVehiculo
                LEFT JOIN CLIENTE C ON V.Cliente = C.Cliente
                WHERE V.Estado = ?
            """
            params = [ESTADO_GENERAL_ACTIVO]

            if search_value:
                like_value = f"%{search_value}%"
                like_plate_value = f"%{limpiar_placa_para_busqueda(search_value)}%"

                query += """
                    AND (
                        REPLACE(REPLACE(UPPER(IFNULL(V.Placa, '')), ' ', ''), '-', '') LIKE ?
                        OR UPPER(IFNULL(TV.Nombre, CAST(V.TipoVehiculo AS TEXT))) LIKE ?
                        OR UPPER(IFNULL(V.Marca, '')) LIKE ?
                        OR UPPER(IFNULL(V.Modelo, '')) LIKE ?
                        OR UPPER(IFNULL(V.Color, '')) LIKE ?
                        OR UPPER(IFNULL(C.Nombres, '')) LIKE ?
                        OR UPPER(IFNULL(C.Apellidos, '')) LIKE ?
                        OR UPPER(IFNULL(C.Nombres, '') || ' ' || IFNULL(C.Apellidos, '')) LIKE ?
                        OR IFNULL(C.Telefono, '') LIKE ?
                """

                params.extend([
                    like_plate_value, like_value, like_value, like_value, like_value,
                    like_value, like_value, like_value, f"%{search_value}%"
                ])

                if tiene_tipo_cliente:
                    query += " OR UPPER(IFNULL(C.TipoCliente, 'GENERAL')) LIKE ? "
                    params.append(like_value)

                query += ")"

            query += " ORDER BY V.Vehiculo DESC "

            cursor.execute(query, params)
            rows = cursor.fetchall()

            accion_texto = "Doble clic para editar" if es_usuario_empleado(self.user_data) else "Doble clic"

            for row in rows:
                cliente = nombre_cliente_completo(row_get(row, "Nombres"), row_get(row, "Apellidos"))
                tipo_cliente = row_get(row, "TipoCliente", TIPO_CLIENTE_GENERAL) or TIPO_CLIENTE_GENERAL

                self.tree.insert(
                    "", "end",
                    values=(
                        row_get(row, "Vehiculo"),
                        texto_o_vacio(row_get(row, "Placa")),
                        texto_o_vacio(row_get(row, "TipoVehiculoNombre")),
                        texto_o_vacio(row_get(row, "ModeloVehiculo")),
                        texto_o_vacio(row_get(row, "Color")),
                        tipo_cliente,
                        cliente,
                        texto_o_vacio(row_get(row, "Telefono")),
                        accion_texto,
                    )
                )

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los registros.\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def on_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        values = item["values"]
        if not values:
            return

        vehicle_id = values[0]
        plate = values[1]

        if es_usuario_empleado(self.user_data):
            self.edit_record(vehicle_id)
            return

        action_window = tk.Toplevel(self.parent)
        action_window.title("Acciones")
        action_window.geometry("340x220")
        action_window.resizable(True, True)
        action_window.minsize(280, 180)
        action_window.configure(bg="white")
        action_window.grab_set()

        try:
            action_window.transient(self.parent.winfo_toplevel())
        except Exception:
            pass

        centrar_ventana(action_window, 340, 220, self.parent.winfo_toplevel())

        tk.Label(action_window, text=f"Vehículo: {plate}", font=("Arial", 14, "bold"), bg="white", fg=COLOR_TEXT).pack(pady=(20, 14))

        tk.Button(
            action_window, text="Editar", font=("Arial", 11, "bold"), width=18,
            bg=COLOR_WARNING, fg="white", bd=0, relief="flat", cursor="hand2",
            command=lambda: self.edit_record(vehicle_id, action_window)
        ).pack(pady=8)

        tk.Button(
            action_window, text="Eliminar", font=("Arial", 11, "bold"), width=18,
            bg=COLOR_DANGER, fg="white", bd=0, relief="flat", cursor="hand2",
            command=lambda: self.delete_record(vehicle_id, action_window)
        ).pack(pady=8)

        tk.Button(
            action_window, text="Cerrar", font=("Arial", 11, "bold"), width=18,
            bg=COLOR_GRAY, fg="white", bd=0, relief="flat", cursor="hand2",
            command=action_window.destroy
        ).pack(pady=8)

    def open_new_window(self):
        VehicleCustomerFormWindow(self, self.user_data, mode="create").run()

    def edit_record(self, vehicle_id, action_window=None):
        if action_window:
            action_window.destroy()
        VehicleCustomerFormWindow(self, self.user_data, mode="edit", vehicle_id=vehicle_id).run()

    def delete_record(self, vehicle_id, action_window=None):
        if es_usuario_empleado(self.user_data):
            messagebox.showwarning("Acceso denegado", "El usuario empleado no tiene permiso para eliminar registros.")
            return

        if not messagebox.askyesno("Confirmar eliminación", "¿Está seguro de eliminar este registro?\n\nEsta acción no se puede deshacer."):
            return

        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT Placa, Cliente FROM VEHICULO WHERE Vehiculo = ? AND Estado = ?", (vehicle_id, ESTADO_GENERAL_ACTIVO))
            row = cursor.fetchone()
            if not row:
                messagebox.showerror("Error", "No se encontró el vehículo.")
                return

            placa = row_get(row, "Placa")
            cliente_id = row_get(row, "Cliente")

            cursor.execute("SELECT COUNT(*) FROM OPERACION WHERE Vehiculo = ? AND Estado = ?", (vehicle_id, ESTADO_OPERACION_ACTIVO))
            if cursor.fetchone()[0] > 0:
                messagebox.showwarning("No permitido", "No se puede eliminar el vehículo porque tiene operaciones activas.")
                return

            cursor.execute("SELECT COUNT(*) FROM CONTRATO WHERE Vehiculo = ? AND Estado = ?", (vehicle_id, ESTADO_CONTRATO_ACTIVO))
            if cursor.fetchone()[0] > 0:
                messagebox.showwarning("No permitido", "No se puede eliminar el vehículo porque tiene contratos activos.")
                return

            usr = obtener_usuario_actual_id(self.user_data)

            cursor.execute(
                """
                UPDATE VEHICULO
                SET Estado = ?, Cliente = NULL, Usr = ?,
                    UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'),
                    FechaModificacion = datetime('now','localtime')
                WHERE Vehiculo = ?
                """,
                (ESTADO_GENERAL_INACTIVO, usr, vehicle_id),
            )

            self.inactivar_cliente_si_queda_libre(cursor, cliente_id, usr)
            insertar_bitacora(cursor, usr, "ELIMINAR_VEHICULO_CLIENTE", "VEHICULO", vehicle_id, f"Se inactivó el vehículo '{placa}'")

            conn.commit()
            if action_window:
                action_window.destroy()
            messagebox.showinfo("Eliminado", "Registro eliminado correctamente.")
            self.load_records()

        except Exception as e:
            if conn:
                conn.rollback()
            messagebox.showerror("Error", f"No se pudo eliminar el registro.\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def inactivar_cliente_si_queda_libre(self, cursor, cliente_id, usr):
        if not cliente_id:
            return

        cursor.execute("SELECT COUNT(*) FROM VEHICULO WHERE Cliente = ? AND Estado = ?", (cliente_id, ESTADO_GENERAL_ACTIVO))
        vehiculos_activos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM CONTRATO WHERE Cliente = ? AND Estado = ?", (cliente_id, ESTADO_CONTRATO_ACTIVO))
        contratos_activos = cursor.fetchone()[0]

        if vehiculos_activos == 0 and contratos_activos == 0:
            cursor.execute(
                """
                UPDATE CLIENTE
                SET Estado = ?, Usr = ?,
                    UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'),
                    FechaModificacion = datetime('now','localtime')
                WHERE Cliente = ?
                """,
                (ESTADO_GENERAL_INACTIVO, usr, cliente_id),
            )


# =========================================================
# FORMULARIO DE VEHÍCULO / CLIENTE
# =========================================================
class VehicleCustomerFormWindow:
    def __init__(self, view, current_user, mode="create", vehicle_id=None):
        self.view = view
        self.parent = view.parent
        self.current_user = current_user or {}
        self.mode = mode
        self.vehicle_id = vehicle_id

        self.window = tk.Toplevel()
        self.window.title("Nuevo registro" if mode == "create" else "Editar registro")
        self.window.configure(bg=COLOR_BG)
        self.window.resizable(True, True)
        self.window.minsize(700, 500)
        self.window.grab_set()

        try:
            self.window.transient(self.view.parent.winfo_toplevel())
        except Exception:
            pass

        centrar_ventana(self.window, 900, 700, self.view.parent.winfo_toplevel())

        self.tipos_rows, self.tipo_nombre_a_id, self.tipo_id_a_nombre = crear_mapa_tipos()
        nombres_tipo = [nombre for _id, nombre in self.tipos_rows]

        self.entry_placa_numero = None
        self.entry_placa_letras = None
        self.combo_color = None
        self.color_var = tk.StringVar(value=COLORES_VEHICULO[0])
        self.vehicle_type_var = tk.StringVar(value=nombres_tipo[0] if nombres_tipo else "Auto")
        self.marca_var = tk.StringVar(value=MARCAS_AUTO[0])
        self.cliente_modo_var = tk.StringVar(value="nuevo")
        self.tipo_cliente_var = tk.StringVar(value=TIPO_CLIENTE_GENERAL)

        self.entry_buscar_cliente = None
        self.client_tree = None
        self.selected_customer_id = None
        self.loaded_customer_id = None

        self.entry_nombres = None
        self.entry_apellidos = None
        self.entry_telefono = None

        self.combo_tipo_vehiculo = None
        self.combo_marca = None
        self.combo_tipo_cliente = None
        self.new_client_frame = None
        self.existing_client_frame = None
        self.lbl_selected_client = None
        self.scroll_canvas = None
        self.scrollbar = None
        self.scrollable_frame = None

        self.build_ui()

        if self.mode == "edit" and self.vehicle_id:
            self.load_data()
        else:
            self.load_clients()
            self.update_client_mode()

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

    def build_ui(self):
        outer = tk.Frame(self.window, bg=COLOR_BG)
        outer.pack(fill="both", expand=True, padx=16, pady=16)

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

        main = tk.Frame(self.scrollable_frame, bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)

        title = "Nuevo registro" if self.mode == "create" else "Editar registro"
        tk.Label(main, text=title, font=("Arial", 20, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT).pack(anchor="w", padx=22, pady=(14, 3))
        tk.Label(
            main,
            text="Registre el vehículo y seleccione si el cliente es nuevo o ya existe.",
            font=("Arial", 10), bg=COLOR_CARD, fg=COLOR_MUTED
        ).pack(anchor="w", padx=22, pady=(0, 10))

        # Botones fijos abajo: así nunca quedan ocultos aunque cambie el contenido del formulario.
        buttons = tk.Frame(main, bg=COLOR_CARD)
        buttons.pack(side="bottom", anchor="e", padx=22, pady=(8, 16))

        tk.Button(
            buttons, text="Cancelar", font=("Arial", 10, "bold"), bg=COLOR_GRAY, fg="white",
            activebackground="#4b5563", activeforeground="white", bd=0, relief="flat",
            padx=20, pady=8, cursor="hand2", command=self.window.destroy
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            buttons, text="Guardar", font=("Arial", 10, "bold"), bg=COLOR_PRIMARY, fg="white",
            activebackground="#1d4ed8", activeforeground="white", bd=0, relief="flat",
            padx=24, pady=8, cursor="hand2", command=self.confirm_save
        ).pack(side="left")

        content = tk.Frame(main, bg=COLOR_CARD)
        content.pack(fill="both", expand=True, padx=22, pady=(0, 4))
        content.grid_columnconfigure(0, weight=1)

        self.build_vehicle_section(content)
        self.build_customer_section(content)

    def build_vehicle_section(self, parent):
        section = tk.Frame(parent, bg=COLOR_PANEL, highlightbackground=COLOR_BORDER, highlightthickness=1)
        section.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        section.grid_columnconfigure(0, weight=1)
        section.grid_columnconfigure(1, weight=1)

        crear_label(section, "Datos del vehículo", font=("Arial", 14, "bold"), bg=COLOR_PANEL).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(12, 8))

        frame_num = tk.Frame(section, bg=COLOR_PANEL)
        frame_num.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        frame_num.grid_columnconfigure(0, weight=1)
        crear_label(frame_num, "Número de placa *", bg=COLOR_PANEL).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.entry_placa_numero = crear_entry(frame_num)
        self.entry_placa_numero.grid(row=1, column=0, sticky="ew")
        self.entry_placa_numero.bind("<KeyRelease>", self.only_numbers_plate)

        frame_letras = tk.Frame(section, bg=COLOR_PANEL)
        frame_letras.grid(row=1, column=1, sticky="ew", padx=18, pady=(0, 10))
        frame_letras.grid_columnconfigure(0, weight=1)
        crear_label(frame_letras, "Letras *", bg=COLOR_PANEL).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.entry_placa_letras = crear_entry(frame_letras)
        self.entry_placa_letras.grid(row=1, column=0, sticky="ew")
        self.entry_placa_letras.bind("<KeyRelease>", self.only_letters_plate)

        frame_tipo = tk.Frame(section, bg=COLOR_PANEL)
        frame_tipo.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        frame_tipo.grid_columnconfigure(0, weight=1)
        crear_label(frame_tipo, "Tipo de vehículo *", bg=COLOR_PANEL).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.combo_tipo_vehiculo = ttk.Combobox(
            frame_tipo, textvariable=self.vehicle_type_var,
            values=[nombre for _id, nombre in self.tipos_rows], state="readonly", font=("Arial", 10)
        )
        self.combo_tipo_vehiculo.grid(row=1, column=0, sticky="ew")
        self.combo_tipo_vehiculo.bind("<<ComboboxSelected>>", lambda event: self.update_brands())

        frame_marca = tk.Frame(section, bg=COLOR_PANEL)
        frame_marca.grid(row=2, column=1, sticky="ew", padx=18, pady=(0, 10))
        frame_marca.grid_columnconfigure(0, weight=1)
        crear_label(frame_marca, "Modelo", bg=COLOR_PANEL).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.combo_marca = ttk.Combobox(frame_marca, textvariable=self.marca_var, values=MARCAS_AUTO, state="readonly", font=("Arial", 10))
        self.combo_marca.grid(row=1, column=0, sticky="ew")

        frame_color = tk.Frame(section, bg=COLOR_PANEL)
        frame_color.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 10))
        frame_color.grid_columnconfigure(0, weight=1)
        crear_label(frame_color, "Color", bg=COLOR_PANEL).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.combo_color = ttk.Combobox(
            frame_color,
            textvariable=self.color_var,
            values=COLORES_VEHICULO,
            state="readonly",
            font=("Arial", 10)
        )
        self.combo_color.grid(row=1, column=0, sticky="ew")

    def build_customer_section(self, parent):
        section = tk.Frame(parent, bg=COLOR_PANEL, highlightbackground=COLOR_BORDER, highlightthickness=1)
        section.grid(row=1, column=0, sticky="ew")
        section.grid_columnconfigure(0, weight=1)
        section.grid_columnconfigure(1, weight=1)

        crear_label(section, "Datos del cliente", font=("Arial", 14, "bold"), bg=COLOR_PANEL).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(12, 6))

        options = tk.Frame(section, bg=COLOR_PANEL)
        options.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 8))

        tk.Radiobutton(
            options, text="Registrar cliente nuevo", variable=self.cliente_modo_var, value="nuevo",
            bg=COLOR_PANEL, fg=COLOR_TEXT, font=("Arial", 10, "bold"),
            command=self.update_client_mode
        ).pack(side="left", padx=(0, 18))

        tk.Radiobutton(
            options, text="Buscar cliente existente", variable=self.cliente_modo_var, value="existente",
            bg=COLOR_PANEL, fg=COLOR_TEXT, font=("Arial", 10, "bold"),
            command=self.update_client_mode
        ).pack(side="left")

        self.existing_client_frame = tk.Frame(section, bg=COLOR_PANEL)
        self.existing_client_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 8))
        self.existing_client_frame.grid_columnconfigure(0, weight=1)

        search_row = tk.Frame(self.existing_client_frame, bg=COLOR_PANEL)
        search_row.grid(row=0, column=0, sticky="ew")
        search_row.grid_columnconfigure(0, weight=1)

        self.entry_buscar_cliente = crear_entry(search_row)
        self.entry_buscar_cliente.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.entry_buscar_cliente.bind("<KeyRelease>", lambda event: self.load_clients())

        tk.Button(
            search_row, text="Buscar", bg=COLOR_LIGHT_BUTTON, fg=COLOR_TEXT, bd=0,
            relief="flat", padx=12, pady=4, cursor="hand2", command=self.load_clients
        ).grid(row=0, column=1)

        columns = ("Cliente", "Tipo", "Nombre", "Telefono")
        self.client_tree = ttk.Treeview(self.existing_client_frame, columns=columns, show="headings", height=2)
        self.client_tree.grid(row=1, column=0, sticky="ew", pady=(8, 4))
        self.client_tree.heading("Cliente", text="ID")
        self.client_tree.heading("Tipo", text="Tipo")
        self.client_tree.heading("Nombre", text="Cliente")
        self.client_tree.heading("Telefono", text="Teléfono")
        self.client_tree.column("Cliente", width=50, anchor="center", stretch=False)
        self.client_tree.column("Tipo", width=100, anchor="center", stretch=False)
        self.client_tree.column("Nombre", width=350, anchor="w", stretch=True)
        self.client_tree.column("Telefono", width=120, anchor="center", stretch=False)
        self.client_tree.bind("<<TreeviewSelect>>", lambda event: self.on_client_selected())

        self.lbl_selected_client = tk.Label(self.existing_client_frame, text="Cliente seleccionado: ninguno", bg=COLOR_PANEL, fg=COLOR_MUTED, font=("Arial", 9))
        self.lbl_selected_client.grid(row=2, column=0, sticky="w")

        self.new_client_frame = tk.Frame(section, bg=COLOR_PANEL)
        self.new_client_frame.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.new_client_frame.grid_columnconfigure(0, weight=1)
        self.new_client_frame.grid_columnconfigure(1, weight=1)

        frame_tipo_cliente = tk.Frame(self.new_client_frame, bg=COLOR_PANEL)
        frame_tipo_cliente.grid(row=0, column=0, sticky="ew", padx=18, pady=(0, 10))
        frame_tipo_cliente.grid_columnconfigure(0, weight=1)
        crear_label(frame_tipo_cliente, "Tipo de cliente *", bg=COLOR_PANEL).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.combo_tipo_cliente = ttk.Combobox(frame_tipo_cliente, textvariable=self.tipo_cliente_var, values=TIPOS_CLIENTE, state="readonly", font=("Arial", 10))
        self.combo_tipo_cliente.grid(row=1, column=0, sticky="ew")

        self.entry_nombres = self.create_field(self.new_client_frame, "Nombres *", 1, 0)
        self.entry_apellidos = self.create_field(self.new_client_frame, "Apellidos", 1, 1)
        self.entry_telefono = self.create_field(self.new_client_frame, "Teléfono", 2, 0)
        self.entry_telefono.bind("<KeyRelease>", self.only_numbers_phone)

    def create_field(self, parent, label, row, col):
        frame = tk.Frame(parent, bg=COLOR_PANEL)
        frame.grid(row=row, column=col, sticky="ew", padx=18, pady=(0, 10))
        frame.grid_columnconfigure(0, weight=1)

        crear_label(frame, label, bg=COLOR_PANEL).grid(row=0, column=0, sticky="w", pady=(0, 5))
        entry = crear_entry(frame)
        entry.grid(row=1, column=0, sticky="ew")
        return entry

    def update_client_mode(self):
        modo = self.cliente_modo_var.get()

        if modo == "existente":
            self.existing_client_frame.grid()
            self.new_client_frame.grid_remove()
            self.selected_customer_id = None
            self.lbl_selected_client.config(text="Cliente seleccionado: ninguno")
            self.load_clients()
        else:
            self.existing_client_frame.grid_remove()
            self.new_client_frame.grid()
            self.selected_customer_id = None
            self.lbl_selected_client.config(text="Cliente seleccionado: ninguno")
            self.set_new_client_entries_state("normal")
            if self.combo_tipo_cliente:
                self.combo_tipo_cliente.configure(state="readonly")

    def set_new_client_entries_state(self, state):
        widgets = [self.entry_nombres, self.entry_apellidos, self.entry_telefono]
        for widget in widgets:
            if widget:
                widget.configure(state=state)
        if self.combo_tipo_cliente:
            self.combo_tipo_cliente.configure(state="disabled" if state == "disabled" else "readonly")

    def update_brands(self):
        tipo = (self.vehicle_type_var.get() or "").strip().lower()
        marca_actual = self.marca_var.get().strip()

        if tipo == "moto":
            valores = MARCAS_MOTO
        elif tipo == "auto":
            valores = MARCAS_AUTO
        else:
            valores = _deduplicar_textos(MARCAS_AUTO + MARCAS_MOTO + ["Otro"])

        self.combo_marca.configure(values=valores)
        if not marca_actual or marca_actual not in valores:
            self.marca_var.set(valores[0] if valores else "")

    def only_numbers_plate(self, event=None):
        value = self.entry_placa_numero.get()
        filtered = "".join(ch for ch in value if ch.isdigit())[:4]
        if value != filtered:
            self.entry_placa_numero.delete(0, "end")
            self.entry_placa_numero.insert(0, filtered)

    def only_letters_plate(self, event=None):
        value = self.entry_placa_letras.get()
        filtered = "".join(ch for ch in value if ch.isalpha()).upper()[:3]
        if value != filtered:
            self.entry_placa_letras.delete(0, "end")
            self.entry_placa_letras.insert(0, filtered)

    def only_numbers_phone(self, event=None):
        value = self.entry_telefono.get()
        filtered = "".join(ch for ch in value if ch.isdigit())[:8]
        if value != filtered:
            self.entry_telefono.delete(0, "end")
            self.entry_telefono.insert(0, filtered)

    def validate_plate(self):
        numero = self.entry_placa_numero.get().strip()
        letras = self.entry_placa_letras.get().strip().upper()

        if not numero or not letras:
            raise ValueError("La placa es obligatoria.")
        if len(numero) < 2 or len(numero) > 4:
            raise ValueError("La parte numérica de la placa debe tener entre 2 y 4 dígitos.")
        if len(letras) != 3:
            raise ValueError("La placa debe tener exactamente 3 letras.")
        return numero, letras, f"{numero} {letras}"

    def split_plate(self, placa):
        if not placa:
            return "", ""
        cleaned = placa.strip().upper().replace("-", " ")
        parts = cleaned.split()
        if len(parts) >= 2:
            return parts[0][:4], parts[1][:3]
        compact = cleaned.replace(" ", "")
        numero = "".join(ch for ch in compact if ch.isdigit())[:4]
        letras = "".join(ch for ch in compact if ch.isalpha())[:3]
        return numero, letras

    def load_clients(self):
        if not self.client_tree:
            return
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)

        filtro = self.entry_buscar_cliente.get().strip().upper() if self.entry_buscar_cliente else ""

        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            tiene_tipo_cliente = _columna_existe(cursor, "CLIENTE", "TipoCliente")
            tipo_select = "TipoCliente" if tiene_tipo_cliente else "'GENERAL' AS TipoCliente"
            query = f"""
                SELECT Cliente, Nombres, Apellidos, Telefono, {tipo_select}
                FROM CLIENTE
                WHERE Estado = ?
            """
            params = [ESTADO_GENERAL_ACTIVO]

            if filtro:
                like = f"%{filtro}%"
                query += """
                    AND (
                        UPPER(IFNULL(Nombres, '')) LIKE ?
                        OR UPPER(IFNULL(Apellidos, '')) LIKE ?
                        OR UPPER(IFNULL(Nombres, '') || ' ' || IFNULL(Apellidos, '')) LIKE ?
                        OR IFNULL(Telefono, '') LIKE ?
                """
                params.extend([like, like, like, f"%{filtro}%"])
                if tiene_tipo_cliente:
                    query += " OR UPPER(IFNULL(TipoCliente, 'GENERAL')) LIKE ? "
                    params.append(like)
                query += ")"

            query += " ORDER BY Cliente DESC LIMIT 50"
            cursor.execute(query, params)
            rows = cursor.fetchall()

            for row in rows:
                nombre = nombre_cliente_completo(row_get(row, "Nombres"), row_get(row, "Apellidos"))
                self.client_tree.insert(
                    "", "end", iid=str(row_get(row, "Cliente")),
                    values=(
                        row_get(row, "Cliente"),
                        row_get(row, "TipoCliente", TIPO_CLIENTE_GENERAL) or TIPO_CLIENTE_GENERAL,
                        nombre,
                        texto_o_vacio(row_get(row, "Telefono")),
                    )
                )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los clientes.\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def on_client_selected(self):
        selected = self.client_tree.selection()
        if not selected:
            return
        item = self.client_tree.item(selected[0])
        values = item.get("values", [])
        if not values:
            return
        self.selected_customer_id = int(values[0])
        self.lbl_selected_client.config(text=f"Cliente seleccionado: {values[2]} - {values[3]}")

    def get_tipo_vehiculo_id(self):
        nombre = self.vehicle_type_var.get().strip()
        tipo_id = self.tipo_nombre_a_id.get(nombre)
        if tipo_id is None:
            raise ValueError("Debe seleccionar un tipo de vehículo válido.")
        return tipo_id

    def load_data(self):
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            tiene_tipo_cliente = _columna_existe(cursor, "CLIENTE", "TipoCliente")
            tipo_cliente_select = "C.TipoCliente" if tiene_tipo_cliente else "'GENERAL' AS TipoCliente"

            cursor.execute(f"""
                SELECT
                    V.Placa, V.TipoVehiculo, COALESCE(TV.Nombre, CAST(V.TipoVehiculo AS TEXT)) AS TipoVehiculoNombre,
                    V.Marca, V.Color, V.Cliente,
                    C.Nombres, C.Apellidos, C.Telefono, {tipo_cliente_select}
                FROM VEHICULO V
                LEFT JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = V.TipoVehiculo
                LEFT JOIN CLIENTE C ON V.Cliente = C.Cliente
                WHERE V.Vehiculo = ? AND V.Estado = ?
            """, (self.vehicle_id, ESTADO_GENERAL_ACTIVO))

            row = cursor.fetchone()
            if not row:
                messagebox.showerror("Error", "No se encontró el vehículo.")
                self.window.destroy()
                return

            numero, letras = self.split_plate(row_get(row, "Placa"))
            self.entry_placa_numero.insert(0, numero)
            self.entry_placa_letras.insert(0, letras)

            tipo_nombre = row_get(row, "TipoVehiculoNombre") or "Auto"
            if tipo_nombre not in self.tipo_nombre_a_id:
                self.tipo_nombre_a_id[tipo_nombre] = row_get(row, "TipoVehiculo")
                self.tipo_id_a_nombre[row_get(row, "TipoVehiculo")] = tipo_nombre
                self.combo_tipo_vehiculo.configure(values=list(self.tipo_nombre_a_id.keys()))
            self.vehicle_type_var.set(tipo_nombre)
            self.update_brands()

            marca = row_get(row, "Marca") or ""
            if marca:
                valores = list(self.combo_marca.cget("values"))
                if marca not in valores:
                    valores.append(marca)
                    self.combo_marca.configure(values=valores)
                self.marca_var.set(marca)

            color = row_get(row, "Color") or COLORES_VEHICULO[0]
            if color not in COLORES_VEHICULO:
                color = "Otro"
            self.color_var.set(color)

            self.loaded_customer_id = row_get(row, "Cliente")
            self.selected_customer_id = self.loaded_customer_id

            self.tipo_cliente_var.set(row_get(row, "TipoCliente", TIPO_CLIENTE_GENERAL) or TIPO_CLIENTE_GENERAL)
            self.entry_nombres.insert(0, row_get(row, "Nombres") or "")
            self.entry_apellidos.insert(0, row_get(row, "Apellidos") or "")
            self.entry_telefono.insert(0, row_get(row, "Telefono") or "")

            self.load_clients()
            self.cliente_modo_var.set("nuevo")
            self.update_client_mode()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el registro.\n{str(e)}")
            self.window.destroy()
        finally:
            if conn:
                conn.close()

    def confirm_save(self):
        if messagebox.askyesno("Confirmar guardado", "¿Desea guardar este registro?"):
            self.save_data()

    def obtener_placa_existente(self, cursor, placa_normalizada):
        if self.mode == "create":
            params = (placa_normalizada, ESTADO_GENERAL_ACTIVO)
            extra = ""
        else:
            params = (placa_normalizada, self.vehicle_id, ESTADO_GENERAL_ACTIVO)
            extra = " AND V.Vehiculo <> ? "

        cursor.execute(f"""
            SELECT V.Vehiculo, V.Placa, C.Nombres, C.Apellidos, C.Telefono
            FROM VEHICULO V
            LEFT JOIN CLIENTE C ON C.Cliente = V.Cliente
            WHERE REPLACE(REPLACE(UPPER(IFNULL(V.Placa, '')), ' ', ''), '-', '') = ?
              {extra}
              AND V.Estado = ?
            LIMIT 1
        """, params)
        return cursor.fetchone()

    def save_data(self):
        try:
            _numero, _letras, placa = self.validate_plate()
            tipo_vehiculo_id = self.get_tipo_vehiculo_id()
        except ValueError as e:
            messagebox.showwarning("Dato inválido", str(e))
            return

        marca = self.marca_var.get().strip()
        color = self.color_var.get().strip()

        modo_cliente = self.cliente_modo_var.get()
        tipo_cliente = self.tipo_cliente_var.get().strip() or TIPO_CLIENTE_GENERAL
        nombres = self.entry_nombres.get().strip()
        apellidos = self.entry_apellidos.get().strip()
        telefono = self.entry_telefono.get().strip()

        if modo_cliente == "nuevo":
            if not nombres:
                messagebox.showwarning("Dato inválido", "Debe ingresar el nombre del cliente.")
                return
            if tipo_cliente not in TIPOS_CLIENTE:
                messagebox.showwarning("Dato inválido", "Debe seleccionar el tipo de cliente.")
                return
            if telefono and len(telefono) != 8:
                messagebox.showwarning("Dato inválido", "El teléfono debe tener 8 dígitos.")
                return
        else:
            if not self.selected_customer_id:
                messagebox.showwarning("Cliente requerido", "Debe seleccionar un cliente existente.")
                return

        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            placa_normalizada = limpiar_placa_para_busqueda(placa)
            usr = obtener_usuario_actual_id(self.current_user)

            duplicado = self.obtener_placa_existente(cursor, placa_normalizada)
            if duplicado:
                cliente = nombre_cliente_completo(row_get(duplicado, "Nombres"), row_get(duplicado, "Apellidos")) or "Sin cliente"
                telefono_dup = row_get(duplicado, "Telefono") or "Sin teléfono"
                messagebox.showwarning(
                    "Placa existente",
                    f"La placa {row_get(duplicado, 'Placa')} ya está registrada.\n\nCliente: {cliente}\nTeléfono: {telefono_dup}"
                )
                return

            if modo_cliente == "existente":
                cliente_id = self.selected_customer_id
            else:
                cliente_id = self.resolve_customer(cursor, tipo_cliente, nombres, apellidos, telefono, self.loaded_customer_id)

            if self.mode == "create":
                cursor.execute(
                    """
                    INSERT INTO VEHICULO (
                        Cliente, Placa, TipoVehiculo, Marca, Modelo, Color,
                        Anio, NumeroChasis, NumeroMotor, Observacion, Estado, Usr,
                        UsrFecha, UsrHora, FechaCreacion, FechaModificacion
                    )
                    VALUES (
                        ?, ?, ?, ?, NULL, ?,
                        NULL, NULL, NULL, NULL, ?, ?,
                        date('now','localtime'), time('now','localtime'),
                        datetime('now','localtime'), datetime('now','localtime')
                    )
                    """,
                    (cliente_id, placa, tipo_vehiculo_id, marca if marca else None, color if color else None, ESTADO_GENERAL_ACTIVO, usr),
                )
                saved_vehicle_id = cursor.lastrowid
                accion = "CREAR_VEHICULO_CLIENTE"
                descripcion = f"Se creó el vehículo '{placa}'"
                registro = saved_vehicle_id
            else:
                cursor.execute("SELECT Cliente FROM VEHICULO WHERE Vehiculo = ? AND Estado = ?", (self.vehicle_id, ESTADO_GENERAL_ACTIVO))
                row_actual = cursor.fetchone()
                cliente_anterior = row_get(row_actual, "Cliente", self.loaded_customer_id)

                cursor.execute(
                    """
                    UPDATE VEHICULO
                    SET Cliente = ?, Placa = ?, TipoVehiculo = ?, Marca = ?, Color = ?,
                        Usr = ?, UsrFecha = date('now','localtime'),
                        UsrHora = time('now','localtime'),
                        FechaModificacion = datetime('now','localtime')
                    WHERE Vehiculo = ?
                    """,
                    (cliente_id, placa, tipo_vehiculo_id, marca if marca else None, color if color else None, usr, self.vehicle_id),
                )

                if cliente_anterior and cliente_anterior != cliente_id:
                    self.inactivar_cliente_si_queda_libre(cursor, cliente_anterior, usr)

                accion = "EDITAR_VEHICULO_CLIENTE"
                descripcion = f"Se editó el vehículo '{placa}'"
                registro = self.vehicle_id

            insertar_bitacora(cursor, usr, accion, "VEHICULO", registro, descripcion)

            conn.commit()
            messagebox.showinfo("Guardado", "Registro guardado correctamente.")
            self.view.load_records()
            self.window.destroy()

        except Exception as e:
            if conn:
                conn.rollback()
            messagebox.showerror("Error", f"No se pudo guardar el registro.\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def resolve_customer(self, cursor, tipo_cliente, nombres, apellidos, telefono, existing_customer_id=None):
        usr = obtener_usuario_actual_id(self.current_user)
        tiene_tipo_cliente = _columna_existe(cursor, "CLIENTE", "TipoCliente")

        if existing_customer_id:
            if tiene_tipo_cliente:
                cursor.execute(
                    """
                    UPDATE CLIENTE
                    SET Nombres = ?, Apellidos = ?, Telefono = ?, TipoCliente = ?, Estado = ?, Usr = ?,
                        UsrFecha = date('now','localtime'), UsrHora = time('now','localtime'),
                        FechaModificacion = datetime('now','localtime')
                    WHERE Cliente = ?
                    """,
                    (nombres, apellidos if apellidos else None, telefono if telefono else None, tipo_cliente, ESTADO_GENERAL_ACTIVO, usr, existing_customer_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE CLIENTE
                    SET Nombres = ?, Apellidos = ?, Telefono = ?, Estado = ?, Usr = ?,
                        UsrFecha = date('now','localtime'), UsrHora = time('now','localtime'),
                        FechaModificacion = datetime('now','localtime')
                    WHERE Cliente = ?
                    """,
                    (nombres, apellidos if apellidos else None, telefono if telefono else None, ESTADO_GENERAL_ACTIVO, usr, existing_customer_id),
                )
            return existing_customer_id

        if tiene_tipo_cliente:
            cursor.execute(
                """
                INSERT INTO CLIENTE (
                    Nombres, Apellidos, Telefono, TipoCliente, Estado, Usr,
                    UsrFecha, UsrHora, FechaCreacion, FechaModificacion
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    date('now','localtime'), time('now','localtime'),
                    datetime('now','localtime'), datetime('now','localtime')
                )
                """,
                (nombres, apellidos if apellidos else None, telefono if telefono else None, tipo_cliente, ESTADO_GENERAL_ACTIVO, usr),
            )
        else:
            cursor.execute(
                """
                INSERT INTO CLIENTE (
                    Nombres, Apellidos, Telefono, Estado, Usr,
                    UsrFecha, UsrHora, FechaCreacion, FechaModificacion
                )
                VALUES (
                    ?, ?, ?, ?, ?,
                    date('now','localtime'), time('now','localtime'),
                    datetime('now','localtime'), datetime('now','localtime')
                )
                """,
                (nombres, apellidos if apellidos else None, telefono if telefono else None, ESTADO_GENERAL_ACTIVO, usr),
            )

        return cursor.lastrowid

    def inactivar_cliente_si_queda_libre(self, cursor, cliente_id, usr):
        if not cliente_id:
            return

        cursor.execute("SELECT COUNT(*) FROM VEHICULO WHERE Cliente = ? AND Estado = ?", (cliente_id, ESTADO_GENERAL_ACTIVO))
        vehiculos_activos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM CONTRATO WHERE Cliente = ? AND Estado = ?", (cliente_id, ESTADO_CONTRATO_ACTIVO))
        contratos_activos = cursor.fetchone()[0]

        if vehiculos_activos == 0 and contratos_activos == 0:
            cursor.execute(
                """
                UPDATE CLIENTE
                SET Estado = ?, Usr = ?, UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'), FechaModificacion = datetime('now','localtime')
                WHERE Cliente = ?
                """,
                (ESTADO_GENERAL_INACTIVO, usr, cliente_id),
            )

    def run(self):
        self.window.wait_window()
