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
from utils.printer import imprimir_ticket

try:
    from modules.payment import abrir_cobro_operacion
except Exception:
    abrir_cobro_operacion = None


# =========================================================
# CATÁLOGOS
# =========================================================
ESTADO_GENERAL_ACTIVO = 1
ESTADO_GENERAL_INACTIVO = 0

ROL_ADMIN = 1
ROL_EMPLEADO = 2

TIPO_TARIFA_HORA = 1
TIPO_TARIFA_ESCALONADA = 1
TIPO_TARIFA_MENSUAL = 3

TIPO_DIA_LUNES_VIERNES = 1
TIPO_DIA_NORMAL = 1

METODO_PAGO_EFECTIVO = 1
METODO_PAGO_QR = 2

ESTADO_CONTRATO_ACTIVO = 1

ESTADO_OPERACION_ACTIVO = 1
ESTADO_OPERACION_FINALIZADO = 2
ESTADO_OPERACION_CANCELADO = 3

TIPO_OPERACION_NORMAL = 1
TIPO_OPERACION_CONTRATO = 2

TIPO_DETALLE_OPERACION = 1
TIPO_DETALLE_CONTRATO = 2

ESTADO_OPERACION_SERVICIO_PENDIENTE = 1
ESTADO_OPERACION_SERVICIO_EN_PROCESO = 2
ESTADO_OPERACION_SERVICIO_REALIZADO = 3
ESTADO_OPERACION_SERVICIO_CANCELADO = 4

REGISTROS_POR_PAGINA = 25

CONFIG_MULTA_TICKET_PERDIDO = "MULTA_TICKET_PERDIDO"
VALOR_DEFAULT_MULTA_TICKET_PERDIDO = 50.00


# =========================================================
# UTILIDADES
# =========================================================
def ahora_texto():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def obtener_usuario_actual_id(user_data):
    if not user_data:
        return 0
    return user_data.get("Usuario") or user_data.get("id") or 0


def obtener_rol_usuario(user_data):
    if not user_data:
        return ROL_EMPLEADO

    rol = (
        user_data.get("Rol")
        or user_data.get("rol")
        or user_data.get("RolUsuario")
        or user_data.get("role")
        or user_data.get("NombreRol")
        or user_data.get("nombre_rol")
        or user_data.get("TipoRol")
        or user_data.get("tipo_rol")
        or ""
    )

    if isinstance(rol, int):
        return rol

    rol_texto = str(rol).strip().lower()

    if rol_texto in ("1", "admin", "administrador"):
        return ROL_ADMIN

    if rol_texto in ("2", "empleado", "employee"):
        return ROL_EMPLEADO

    return ROL_EMPLEADO


def usuario_es_admin(user_data):
    return obtener_rol_usuario(user_data) == ROL_ADMIN

def limpiar_placa_para_busqueda(placa):
    return placa.replace(" ", "").replace("-", "").upper().strip()


def formatear_fecha(fecha_texto):
    if not fecha_texto:
        return ""
    try:
        return datetime.strptime(fecha_texto, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except Exception:
        return fecha_texto


def nombre_tipo_operacion(tipo_operacion):
    if tipo_operacion == TIPO_OPERACION_CONTRATO:
        return "Contrato"
    return "Normal"


def nombre_estado_operacion(estado):
    if estado == ESTADO_OPERACION_ACTIVO:
        return "Ingresado"
    if estado == ESTADO_OPERACION_FINALIZADO:
        return "Finalizado"
    if estado == ESTADO_OPERACION_CANCELADO:
        return "Cancelado"
    return "N/D"


def estado_operacion_desde_texto(texto):
    texto = (texto or "").strip().lower()
    if texto in ("todos", "todo", ""):
        return None
    if texto in ("ingresado", "activo"):
        return ESTADO_OPERACION_ACTIVO
    if texto == "finalizado":
        return ESTADO_OPERACION_FINALIZADO
    if texto == "cancelado":
        return ESTADO_OPERACION_CANCELADO
    return None


def nombre_metodo_pago(metodo):
    if metodo == METODO_PAGO_EFECTIVO:
        return "Efectivo"
    if metodo == METODO_PAGO_QR:
        return "QR"
    return "N/D"


def centrar_ventana(win, width, height):
    try:
        win.update_idletasks()
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        x = int((screen_w - width) / 2)
        y = int((screen_h - height) / 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
    except Exception:
        win.geometry(f"{width}x{height}")


def tabla_existe(cursor, tabla):
    try:
        cursor.execute(
            "SELECT COUNT(*) AS Total FROM sqlite_master WHERE type='table' AND name = ?",
            (tabla,),
        )
        row = cursor.fetchone()
        return int(row["Total"] if row else 0) > 0
    except Exception:
        return False


def columna_existe(cursor, tabla, columna):
    try:
        if not tabla_existe(cursor, tabla):
            return False
        cursor.execute(f"PRAGMA table_info({tabla})")
        return columna in [row[1] for row in cursor.fetchall()]
    except Exception:
        return False


def asegurar_configuracion_multa_ticket():
    """
    Garantiza que exista CONFIGURACION y el valor editable de multa.
    Esto evita que el ticket falle si la base todavía no fue migrada.
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
            INSERT OR IGNORE INTO CONFIGURACION (
                Clave, Valor, Descripcion, Estado, Usr, UsrFecha, UsrHora, FechaCreacion, FechaModificacion
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
            "Multa por pérdida de ticket de parqueo",
        ))

        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def obtener_multa_ticket_perdido():
    """Devuelve la multa editable desde CONFIGURACION. Si no existe, usa Bs 50.00."""
    asegurar_configuracion_multa_ticket()

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
        """, (CONFIG_MULTA_TICKET_PERDIDO,))
        row = cursor.fetchone()
        if not row:
            return float(VALOR_DEFAULT_MULTA_TICKET_PERDIDO)

        try:
            valor = row["Valor"]
        except Exception:
            valor = row[0]

        valor = str(valor or "").replace(",", ".").strip()
        multa = float(valor)
        if multa < 0:
            return float(VALOR_DEFAULT_MULTA_TICKET_PERDIDO)
        return multa
    except Exception:
        return float(VALOR_DEFAULT_MULTA_TICKET_PERDIDO)
    finally:
        if conn:
            conn.close()


# =========================================================
# VISTA PRINCIPAL
# =========================================================
class OperationsView:
    def __init__(self, parent, user_data):
        self.parent = parent
        self.user_data = user_data

        self.search_plate_entry = None
        self.search_code_entry = None
        self.estado_filter_combo = None
        self.estado_filter_var = tk.StringVar(value="Todos")
        self.tree = None

        self.pagination_frame = None
        self.prev_button = None
        self.next_button = None
        self.page_label = None
        self.total_label = None
        self.current_page = 1
        self.page_size = REGISTROS_POR_PAGINA
        self.total_records = 0
        self.total_pages = 1

        self.user_role = obtener_rol_usuario(user_data)

        if self.user_role == ROL_EMPLEADO:
            self.estado_filter_var.set("Ingresado")

    def build(self):
        self.build_header()
        self.build_table()
        self.build_pagination()
        self.load_operations()

    def build_header(self):
        header_frame = tk.Frame(self.parent, bg="white")
        header_frame.pack(fill="x", padx=15, pady=15)
        header_frame.grid_columnconfigure(8, weight=1)

        tk.Label(
            header_frame,
            text="Buscar placa:",
            font=("Arial", 11, "bold"),
            bg="white",
            fg="#111827"
        ).grid(row=0, column=0, padx=(0, 8), pady=5, sticky="w")

        self.search_plate_entry = tk.Entry(header_frame, font=("Arial", 11), width=18)
        self.search_plate_entry.grid(row=0, column=1, padx=(0, 12), pady=5, sticky="w")
        self.search_plate_entry.bind("<KeyRelease>", lambda event: self.reset_page_and_load())

        tk.Label(
            header_frame,
            text="Código retiro:",
            font=("Arial", 11, "bold"),
            bg="white",
            fg="#111827"
        ).grid(row=0, column=2, padx=(0, 8), pady=5, sticky="w")

        self.search_code_entry = tk.Entry(header_frame, font=("Arial", 11), width=14)
        self.search_code_entry.grid(row=0, column=3, padx=(0, 12), pady=5, sticky="w")
        self.search_code_entry.bind("<KeyRelease>", lambda event: self.reset_page_and_load())

        next_col = 4

        # El empleado solo debe ver operaciones ingresadas.
        # Por eso no se muestra el selector de estado para este rol.
        if self.user_role == ROL_ADMIN:
            tk.Label(
                header_frame,
                text="Estado:",
                font=("Arial", 11, "bold"),
                bg="white",
                fg="#111827"
            ).grid(row=0, column=next_col, padx=(0, 8), pady=5, sticky="w")

            self.estado_filter_combo = ttk.Combobox(
                header_frame,
                textvariable=self.estado_filter_var,
                values=["Todos", "Ingresado", "Finalizado", "Cancelado"],
                state="readonly",
                font=("Arial", 11),
                width=14
            )
            self.estado_filter_combo.grid(row=0, column=next_col + 1, padx=(0, 12), pady=5, sticky="w")
            self.estado_filter_combo.bind("<<ComboboxSelected>>", lambda event: self.reset_page_and_load())
            next_col += 2
        else:
            self.estado_filter_combo = None
            self.estado_filter_var.set("Ingresado")

        tk.Button(
            header_frame,
            text="Buscar",
            font=("Arial", 10, "bold"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            bd=0,
            relief="flat",
            padx=15,
            pady=6,
            cursor="hand2",
            command=self.reset_page_and_load
        ).grid(row=0, column=next_col, padx=(0, 10), pady=5)

        tk.Button(
            header_frame,
            text="Nuevo",
            font=("Arial", 10, "bold"),
            bg="#16a34a",
            fg="white",
            activebackground="#15803d",
            activeforeground="white",
            bd=0,
            relief="flat",
            padx=18,
            pady=6,
            cursor="hand2",
            command=self.open_new_operation_window
        ).grid(row=0, column=9, padx=(10, 0), pady=5, sticky="e")

    def build_table(self):
        table_frame = tk.Frame(self.parent, bg="white")
        table_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        columns = (
            "Operacion",
            "CodigoRetiro",
            "Placa",
            "TipoVehiculo",
            "FechaIngreso",
            "TipoOperacion",
            "Servicios",
            "Estado",
            "Acciones",
        )

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)
        self.tree.pack(fill="both", expand=True, side="left")

        headings = {
            "Operacion": "ID",
            "CodigoRetiro": "Código retiro",
            "Placa": "Placa",
            "TipoVehiculo": "Tipo",
            "FechaIngreso": "Ingreso",
            "TipoOperacion": "Modalidad",
            "Servicios": "Servicios",
            "Estado": "Estado",
            "Acciones": "Acciones",
        }

        for col, text in headings.items():
            self.tree.heading(col, text=text)

        self.tree.column("Operacion", width=55, anchor="center", stretch=False)
        self.tree.column("CodigoRetiro", width=110, anchor="center", stretch=False)
        self.tree.column("Placa", width=110, anchor="center", stretch=False)
        self.tree.column("TipoVehiculo", width=110, anchor="center", stretch=False)
        self.tree.column("FechaIngreso", width=145, anchor="center", stretch=False)
        self.tree.column("TipoOperacion", width=100, anchor="center", stretch=False)
        self.tree.column("Servicios", width=260, anchor="w", stretch=True)
        self.tree.column("Estado", width=90, anchor="center", stretch=False)
        self.tree.column("Acciones", width=110, anchor="center", stretch=False)

        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar_y.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.tree.bind("<Double-1>", self.on_double_click)

    def build_pagination(self):
        self.pagination_frame = tk.Frame(self.parent, bg="white")
        self.pagination_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.total_label = tk.Label(
            self.pagination_frame,
            text="Registros: 0",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#374151"
        )
        self.total_label.pack(side="left")

        controls = tk.Frame(self.pagination_frame, bg="white")
        controls.pack(side="right")

        self.prev_button = tk.Button(
            controls,
            text="Anterior",
            font=("Arial", 10, "bold"),
            bg="#e5e7eb",
            fg="#111827",
            activebackground="#d1d5db",
            activeforeground="#111827",
            bd=0,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.previous_page
        )
        self.prev_button.pack(side="left", padx=(0, 8))

        self.page_label = tk.Label(
            controls,
            text="Página 1 de 1",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#111827"
        )
        self.page_label.pack(side="left", padx=8)

        self.next_button = tk.Button(
            controls,
            text="Siguiente",
            font=("Arial", 10, "bold"),
            bg="#e5e7eb",
            fg="#111827",
            activebackground="#d1d5db",
            activeforeground="#111827",
            bd=0,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.next_page
        )
        self.next_button.pack(side="left", padx=(8, 0))

    def reset_page_and_load(self):
        self.current_page = 1
        self.load_operations()

    def previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_operations()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_operations()

    def update_pagination_controls(self):
        if not self.page_label:
            return

        self.page_label.config(text=f"Página {self.current_page} de {self.total_pages}")
        self.total_label.config(text=f"Registros: {self.total_records}")

        if self.current_page <= 1:
            self.prev_button.config(state="disabled", cursor="arrow")
        else:
            self.prev_button.config(state="normal", cursor="hand2")

        if self.current_page >= self.total_pages:
            self.next_button.config(state="disabled", cursor="arrow")
        else:
            self.next_button.config(state="normal", cursor="hand2")

    def load_operations(self):
        if not self.tree:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        placa_filter = self.search_plate_entry.get().strip().upper() if self.search_plate_entry else ""
        codigo_filter = self.search_code_entry.get().strip() if self.search_code_entry else ""

        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            base_from = """
                FROM OPERACION O
                INNER JOIN VEHICULO V ON O.Vehiculo = V.Vehiculo
                LEFT JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = V.TipoVehiculo
                WHERE 1 = 1
            """
            params = []

            if self.user_role == ROL_EMPLEADO:
                base_from += " AND O.Estado = ? "
                params.append(ESTADO_OPERACION_ACTIVO)
            else:
                estado_seleccionado = estado_operacion_desde_texto(self.estado_filter_var.get())
                if estado_seleccionado is not None:
                    base_from += " AND O.Estado = ? "
                    params.append(estado_seleccionado)

            if placa_filter:
                base_from += " AND REPLACE(REPLACE(UPPER(V.Placa), ' ', ''), '-', '') LIKE ? "
                params.append(f"%{limpiar_placa_para_busqueda(placa_filter)}%")

            if codigo_filter:
                base_from += " AND O.CodigoRetiro LIKE ? "
                params.append(f"%{codigo_filter}%")

            count_query = "SELECT COUNT(*) AS Total " + base_from
            cursor.execute(count_query, params)
            row_total = cursor.fetchone()
            self.total_records = int(row_total["Total"] if row_total else 0)

            self.total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)

            if self.current_page > self.total_pages:
                self.current_page = self.total_pages

            if self.current_page < 1:
                self.current_page = 1

            offset = (self.current_page - 1) * self.page_size

            query = """
                SELECT
                    O.Operacion,
                    O.CodigoRetiro,
                    V.Placa,
                    COALESCE(TV.Nombre, CAST(V.TipoVehiculo AS TEXT)) AS TipoVehiculo,
                    O.FechaIngreso,
                    O.TipoOperacion,
                    O.Estado
            """ + base_from + """
                ORDER BY O.FechaIngreso DESC
                LIMIT ? OFFSET ?
            """

            data_params = list(params)
            data_params.extend([self.page_size, offset])

            cursor.execute(query, data_params)
            operations = cursor.fetchall()

            for operation in operations:
                operacion_id = operation["Operacion"]
                servicios = self.get_operation_services(operacion_id, cursor)

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        operacion_id,
                        operation["CodigoRetiro"],
                        operation["Placa"],
                        operation["TipoVehiculo"],
                        formatear_fecha(operation["FechaIngreso"]),
                        nombre_tipo_operacion(operation["TipoOperacion"]),
                        servicios,
                        nombre_estado_operacion(operation["Estado"]),
                        "Doble clic"
                    )
                )

            self.update_pagination_controls()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar las operaciones.\\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def get_operation_services(self, operation_id, cursor):
        cursor.execute("""
            SELECT TipoOperacion
            FROM OPERACION
            WHERE Operacion = ?
            LIMIT 1
        """, (operation_id,))
        op_row = cursor.fetchone()
        tipo_operacion = op_row["TipoOperacion"] if op_row else TIPO_OPERACION_NORMAL

        cursor.execute("""
            SELECT S.Nombre
            FROM OPERACIONSERVICIO OS
            INNER JOIN SERVICIO S ON OS.Servicio = S.Servicio
            WHERE OS.Operacion = ?
              AND OS.Estado != ?
            ORDER BY S.Nombre ASC
        """, (operation_id, ESTADO_OPERACION_SERVICIO_CANCELADO))
        rows = cursor.fetchall()

        service_names = [row["Nombre"] for row in rows]

        if tipo_operacion == TIPO_OPERACION_CONTRATO:
            if not service_names:
                return "Contrato"
            return "Contrato, " + ", ".join(service_names)

        if not service_names:
            return "Parqueo"

        return "Parqueo, " + ", ".join(service_names)

    def on_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        values = item["values"]

        if not values:
            return

        operation_id = values[0]
        codigo_retiro = values[1]
        estado_operacion = self.get_operation_state(operation_id)
        estado_nombre = nombre_estado_operacion(estado_operacion)
        es_activa = estado_operacion == ESTADO_OPERACION_ACTIVO

        action_window = tk.Toplevel(self.parent)
        action_window.title("Acciones")
        action_window.resizable(True, True)
        action_window.minsize(300, 350)
        action_window.configure(bg="white")
        centrar_ventana(action_window, 340, 390 if es_activa else 300)
        action_window.grab_set()

        tk.Label(
            action_window,
            text=f"Operación #{operation_id}",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#111827"
        ).pack(pady=(20, 8))

        tk.Label(
            action_window,
            text=f"Código de retiro: {codigo_retiro}",
            font=("Arial", 11, "bold"),
            bg="white",
            fg="#2563eb"
        ).pack(pady=(0, 6))

        tk.Label(
            action_window,
            text=f"Estado: {estado_nombre}",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#374151"
        ).pack(pady=(0, 14))

        if es_activa:
            tk.Button(
                action_window,
                text="Editar",
                font=("Arial", 11, "bold"),
                width=18,
                bg="#f59e0b",
                fg="white",
                bd=0,
                relief="flat",
                cursor="hand2",
                command=lambda: self.edit_operation(operation_id, action_window)
            ).pack(pady=6)

            tk.Button(
                action_window,
                text="Cobrar",
                font=("Arial", 11, "bold"),
                width=18,
                bg="#16a34a",
                fg="white",
                bd=0,
                relief="flat",
                cursor="hand2",
                command=lambda: self.open_charge_window(operation_id, action_window)
            ).pack(pady=6)

        tk.Button(
            action_window,
            text="Reimprimir ticket",
            font=("Arial", 11, "bold"),
            width=18,
            bg="#2563eb",
            fg="white",
            bd=0,
            relief="flat",
            cursor="hand2",
            command=lambda: self.reprint_ticket(operation_id)
        ).pack(pady=6)

        if es_activa:
            tk.Button(
                action_window,
                text="Cancelar operación",
                font=("Arial", 11, "bold"),
                width=18,
                bg="#dc2626",
                fg="white",
                bd=0,
                relief="flat",
                cursor="hand2",
                command=lambda: self.cancel_operation(operation_id, action_window)
            ).pack(pady=6)

        tk.Button(
            action_window,
            text="Cerrar",
            font=("Arial", 11, "bold"),
            width=18,
            bg="#6b7280",
            fg="white",
            bd=0,
            relief="flat",
            cursor="hand2",
            command=action_window.destroy
        ).pack(pady=6)

    def get_operation_state(self, operation_id):
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT Estado FROM OPERACION WHERE Operacion = ? LIMIT 1", (operation_id,))
            row = cursor.fetchone()
            return row["Estado"] if row else None
        finally:
            if conn:
                conn.close()

    def open_new_operation_window(self):
        OperationFormWindow(self, self.user_data, mode="create").run()

    def edit_operation(self, operation_id, action_window=None):
        if action_window:
            action_window.destroy()
        OperationFormWindow(self, self.user_data, mode="edit", operation_id=operation_id).run()

    def cancel_operation(self, operation_id, action_window=None):
        if action_window:
            action_window.destroy()
        CancelOperationWindow(self, self.user_data, operation_id).run()

    def open_charge_window(self, operation_id, action_window=None):
        if action_window:
            action_window.destroy()
        try:
            if abrir_cobro_operacion is None:
                raise Exception("No se pudo cargar modules/payment.py")

            abrir_cobro_operacion(
                self.parent,
                self.user_data,
                operation_id,
                on_success=self.load_operations,
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def reprint_ticket(self, operation_id):
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            datos = self.get_operation_ticket_data(cursor, operation_id)

            if not datos:
                messagebox.showwarning("No encontrado", "No se encontró la operación para reimprimir.")
                return

            TicketPreviewWindow(self.parent, datos).run()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir la vista previa del ticket.\n{str(e)}"
            )

        finally:
            if conn:
                conn.close()

    def get_operation_ticket_data(self, cursor, operation_id):
        cursor.execute("""
            SELECT
                O.Operacion,
                O.CodigoRetiro,
                O.FechaIngreso,
                V.Placa
            FROM OPERACION O
            INNER JOIN VEHICULO V ON O.Vehiculo = V.Vehiculo
            WHERE O.Operacion = ?
            LIMIT 1
        """, (operation_id,))

        return cursor.fetchone()


# =========================================================
# VISTA PREVIA DE TICKET
# =========================================================
class TicketPreviewWindow:
    def __init__(self, parent, ticket_data):
        self.parent = parent
        self.ticket_data = ticket_data

        self.window = tk.Toplevel(parent)
        self.window.title("Vista previa de ticket")
        self.window.resizable(True, True)
        self.window.minsize(390, 500)
        self.window.configure(bg="white")
        centrar_ventana(self.window, 390, 590)
        self.window.grab_set()

        self.canvas = None
        self.logo_img = None
        self.fecha_ticket = ""
        self.hora_ticket = ""
        self.multa_ticket_perdido = obtener_multa_ticket_perdido()
        self.preparar_fechas()
        self.build_ui()

    def preparar_fechas(self):
        fecha_ingreso = self.ticket_data["FechaIngreso"]
        try:
            fecha_dt = datetime.strptime(fecha_ingreso, "%Y-%m-%d %H:%M:%S")
            self.fecha_ticket = fecha_dt.strftime("%d/%m/%Y")
            self.hora_ticket = fecha_dt.strftime("%H:%M")
        except Exception:
            self.fecha_ticket = fecha_ingreso
            self.hora_ticket = ""

    def ruta_base_app(self):
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.getcwd()

    def buscar_logo_impresion(self):
        base = self.ruta_base_app()
        candidatos = [
            os.path.join(base, "static", "logo_impresion.png"),
            os.path.join(base, "static", "logo_impresion.jpg"),
            os.path.join(base, "static", "logo_impresion.jpeg"),
            os.path.join(base, "static", "logo_impresion.gif"),
            os.path.join(base, "static", "logo_impresion"),
        ]

        for ruta in candidatos:
            if os.path.exists(ruta):
                return ruta

        return None

    def cargar_logo_canvas(self, max_width=90, max_height=45):
        ruta_logo = self.buscar_logo_impresion()
        if not ruta_logo:
            return None

        try:
            if Image and ImageTk:
                img = Image.open(ruta_logo)
                img.thumbnail((max_width, max_height))
                return ImageTk.PhotoImage(img)

            img = tk.PhotoImage(file=ruta_logo)
            ancho = max(1, img.width())
            alto = max(1, img.height())
            factor = max(1, int(max(ancho / max_width, alto / max_height)))
            if factor > 1:
                img = img.subsample(factor, factor)
            return img

        except Exception:
            return None

    def build_ui(self):
        tk.Label(
            self.window,
            text="Vista previa de ticket",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#111827"
        ).pack(pady=(15, 8))

        self.canvas = tk.Canvas(
            self.window,
            width=300,
            height=405,
            bg="white",
            highlightthickness=1,
            highlightbackground="#9ca3af"
        )
        self.canvas.pack(pady=(0, 15))
        self.draw_ticket_image()

        buttons = tk.Frame(self.window, bg="white")
        buttons.pack(pady=(0, 18))

        tk.Button(
            buttons,
            text="Imprimir",
            font=("Arial", 11, "bold"),
            bg="#16a34a",
            fg="white",
            activebackground="#15803d",
            activeforeground="white",
            bd=0,
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
            command=self.print_ticket
        ).grid(row=0, column=0, padx=8)

        tk.Button(
            buttons,
            text="Cancelar",
            font=("Arial", 11, "bold"),
            bg="#6b7280",
            fg="white",
            activebackground="#4b5563",
            activeforeground="white",
            bd=0,
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
            command=self.window.destroy
        ).grid(row=0, column=1, padx=8)

    def draw_ticket_image(self):
        c = self.canvas
        c.delete("all")

        codigo = self.ticket_data["CodigoRetiro"] or "N/D"
        placa = self.ticket_data["Placa"] or "N/D"

        # Ticket compacto. El aviso de multa queda dentro del borde, sin agrandar todo.
        c.create_rectangle(16, 12, 284, 392, outline="#111827")

        self.logo_img = self.cargar_logo_canvas(max_width=70, max_height=32)
        if self.logo_img:
            c.create_image(150, 38, image=self.logo_img)
            titulo_y = 78
        else:
            titulo_y = 48

        c.create_text(150, titulo_y, text="TICKET DE PARQUEO", font=("Arial", 13, "bold"), fill="#111827")
        c.create_line(38, titulo_y + 24, 262, titulo_y + 24, fill="#111827")

        c.create_text(150, titulo_y + 55, text="CÓDIGO DE RETIRO", font=("Arial", 9, "bold"), fill="#111827")
        c.create_text(150, titulo_y + 82, text=str(codigo), font=("Arial", 18, "bold"), fill="#111827")

        c.create_line(38, titulo_y + 110, 262, titulo_y + 110, fill="#d1d5db")

        info_y = titulo_y + 140
        c.create_text(62, info_y, text="Placa:", font=("Arial", 9, "bold"), anchor="w", fill="#111827")
        c.create_text(150, info_y, text=str(placa), font=("Arial", 10), anchor="w", fill="#111827")

        c.create_text(62, info_y + 30, text="Fecha:", font=("Arial", 9, "bold"), anchor="w", fill="#111827")
        c.create_text(150, info_y + 30, text=self.fecha_ticket, font=("Arial", 10), anchor="w", fill="#111827")

        c.create_text(62, info_y + 60, text="Hora:", font=("Arial", 9, "bold"), anchor="w", fill="#111827")
        c.create_text(150, info_y + 60, text=self.hora_ticket, font=("Arial", 10), anchor="w", fill="#111827")

        c.create_line(38, info_y + 84, 262, info_y + 84, fill="#d1d5db")
        c.create_text(150, info_y + 108, text="Conserve este ticket", font=("Arial", 9, "bold"), fill="#111827")

        c.create_line(38, info_y + 128, 262, info_y + 128, fill="#d1d5db")
        texto_multa = f"la multa será de Bs {self.multa_ticket_perdido:.2f}"
        c.create_text(150, info_y + 150, text="Si se pierde el ticket", font=("Arial", 8, "bold"), fill="#111827")
        c.create_text(150, info_y + 166, text=texto_multa, font=("Arial", 8, "bold"), fill="#111827")

    def print_ticket(self):
        try:
            codigo = self.ticket_data["CodigoRetiro"] or "N/D"
            try:
                imprimir_ticket(
                    codigo=codigo,
                    placa=self.ticket_data["Placa"],
                    fecha=self.fecha_ticket,
                    hora_ingreso=self.hora_ticket,
                    multa_ticket_perdido=self.multa_ticket_perdido
                )
            except TypeError:
                # Compatibilidad temporal hasta reemplazar utils/printer.py.
                imprimir_ticket(
                    codigo=codigo,
                    placa=self.ticket_data["Placa"],
                    fecha=self.fecha_ticket,
                    hora_ingreso=self.hora_ticket
                )

            messagebox.showinfo(
                "Ticket impreso",
                f"Se imprimió correctamente el ticket.\n\nCódigo: {codigo}"
            )
            self.window.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo imprimir el ticket.\n{str(e)}"
            )

    def run(self):
        pass

# =========================================================
# FORMULARIO DE OPERACIÓN
# =========================================================
class OperationFormWindow:
    def __init__(self, operations_view, user_data, mode="create", operation_id=None):
        self.operations_view = operations_view
        self.parent = operations_view
        self.user_data = user_data
        self.mode = mode
        self.operation_id = operation_id

        self.window = tk.Toplevel()
        self.window.title("Nueva operación" if mode == "create" else "Editar operación")
        self.window.minsize(540, 560)
        self.window.resizable(True, True)
        self.window.configure(bg="white")
        centrar_ventana(self.window, 590, 660)
        self.window.grab_set()

        self.entry_placa_numero = None
        self.entry_placa_letras = None
        self.entry_cliente = None
        self.text_observaciones = None
        self.contract_notice_label = None
        self.vehicle_type_combo = None

        self.vehicle_type_var = tk.StringVar(value="")
        self.vehicle_types_data = []
        self.vehicle_type_map = {}
        self.service_vars = {}
        self.services_data = []

        self.loaded_vehicle_id = None
        self.loaded_customer_id = None
        self.loaded_contract_id = None
        self.detected_contract_id = None
        self.detected_contract_text = ""
        self._plate_after_id = None

        self.scroll_canvas = None
        self.scrollbar = None
        self.scrollable_frame = None

        self.build_ui()

        if self.mode == "edit" and self.operation_id:
            self.load_data()

        self.window.protocol("WM_DELETE_WINDOW", self.safe_close)

    def safe_close(self):
        self._unbind_mousewheel()
        try:
            if self._plate_after_id:
                self.window.after_cancel(self._plate_after_id)
                self._plate_after_id = None
        except Exception:
            pass
        try:
            if self.window and self.window.winfo_exists():
                self.window.destroy()
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

    def _bind_mousewheel(self, event=None):
        try:
            if self.scroll_canvas and self.scroll_canvas.winfo_exists():
                self.scroll_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
                self.scroll_canvas.bind_all("<Button-4>", self._on_mousewheel)
                self.scroll_canvas.bind_all("<Button-5>", self._on_mousewheel)
        except tk.TclError:
            pass

    def _unbind_mousewheel(self, event=None):
        try:
            if self.scroll_canvas and self.scroll_canvas.winfo_exists():
                self.scroll_canvas.unbind_all("<MouseWheel>")
                self.scroll_canvas.unbind_all("<Button-4>")
                self.scroll_canvas.unbind_all("<Button-5>")
        except tk.TclError:
            pass

    def build_scrollable_form(self):
        outer = tk.Frame(self.window, bg="white")
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        self.scroll_canvas = tk.Canvas(outer, bg="white", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self.scroll_canvas.yview)

        self.scrollable_frame = tk.Frame(self.scroll_canvas, bg="white")

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

        return self.scrollable_frame

    def build_ui(self):
        form = self.build_scrollable_form()

        title = "Nueva operación" if self.mode == "create" else "Editar operación"

        tk.Label(
            form,
            text=title,
            font=("Arial", 16, "bold"),
            bg="white",
            fg="#111827"
        ).pack(pady=(10, 10))

        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        tk.Label(
            form,
            text=f"Hora actual: {now_str}",
            font=("Arial", 10),
            bg="white",
            fg="#374151"
        ).pack(pady=(0, 15))

        content = tk.Frame(form, bg="white")
        content.pack(fill="both", expand=True, padx=20)

        tk.Label(content, text="Placa *", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(0, 5))

        plate_frame = tk.Frame(content, bg="white")
        plate_frame.pack(fill="x", pady=(0, 6))

        tk.Label(plate_frame, text="Número", font=("Arial", 10), bg="white").pack(side="left", padx=(0, 6))
        self.entry_placa_numero = tk.Entry(plate_frame, font=("Arial", 11), width=10)
        self.entry_placa_numero.pack(side="left", padx=(0, 16))
        self.entry_placa_numero.bind("<KeyRelease>", self.only_numbers_plate)

        tk.Label(plate_frame, text="Letras", font=("Arial", 10), bg="white").pack(side="left", padx=(0, 6))
        self.entry_placa_letras = tk.Entry(plate_frame, font=("Arial", 11), width=8)
        self.entry_placa_letras.pack(side="left")
        self.entry_placa_letras.bind("<KeyRelease>", self.only_letters_plate)

        self.contract_notice_label = tk.Label(
            content,
            text="",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#15803d",
            justify="left",
            wraplength=500
        )
        self.contract_notice_label.pack(anchor="w", pady=(0, 12))


        tk.Label(
            content,
            text="Tipo de vehículo *",
            font=("Arial", 11, "bold"),
            bg="white"
        ).pack(anchor="w", pady=(0, 5))

        vehicle_frame = tk.Frame(content, bg="white")
        vehicle_frame.pack(fill="x", pady=(0, 14))

        self.load_active_vehicle_types()

        if not self.vehicle_types_data:
            tk.Label(
                vehicle_frame,
                text="No hay tipos de vehículo con tarifa por hora activa.",
                font=("Arial", 10),
                bg="white",
                fg="#dc2626"
            ).pack(anchor="w")
        else:
            self.vehicle_type_combo = ttk.Combobox(
                vehicle_frame,
                textvariable=self.vehicle_type_var,
                values=self.vehicle_types_data,
                state="readonly",
                font=("Arial", 11),
                width=30
            )
            self.vehicle_type_combo.pack(anchor="w")

        tk.Label(content, text="Servicios extra", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(0, 5))
        services_frame = tk.Frame(content, bg="white")
        services_frame.pack(fill="x", pady=(0, 14))

        self.load_active_services()
        if not self.services_data:
            tk.Label(
                services_frame,
                text="No hay servicios activos registrados.",
                font=("Arial", 10),
                bg="white",
                fg="#6b7280"
            ).pack(anchor="w")
        else:
            for service in self.services_data:
                var = tk.BooleanVar(value=False)
                self.service_vars[service["Servicio"]] = var
                tk.Checkbutton(
                    services_frame,
                    text=f"{service['Nombre']} (Bs {float(service['Precio']):.2f})",
                    variable=var,
                    bg="white",
                    font=("Arial", 11)
                ).pack(anchor="w", pady=3)


        buttons_frame = tk.Frame(form, bg="white")
        buttons_frame.pack(pady=18)

        tk.Button(
            buttons_frame,
            text="Guardar",
            font=("Arial", 11, "bold"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            bd=0,
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
            command=self.save_operation
        ).grid(row=0, column=0, padx=10)

        tk.Button(
            buttons_frame,
            text="Cancelar",
            font=("Arial", 11, "bold"),
            bg="#dc2626",
            fg="white",
            activebackground="#b91c1c",
            activeforeground="white",
            bd=0,
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
            command=self.safe_close
        ).grid(row=0, column=1, padx=10)

    def only_numbers_plate(self, event=None):
        value = self.entry_placa_numero.get()
        filtered = "".join(ch for ch in value if ch.isdigit())[:4]
        if value != filtered:
            self.entry_placa_numero.delete(0, "end")
            self.entry_placa_numero.insert(0, filtered)
        self.schedule_contract_detection()

    def only_letters_plate(self, event=None):
        value = self.entry_placa_letras.get()
        filtered = "".join(ch for ch in value if ch.isalpha()).upper()[:3]
        if value != filtered:
            self.entry_placa_letras.delete(0, "end")
            self.entry_placa_letras.insert(0, filtered)
        self.schedule_contract_detection()

    def schedule_contract_detection(self):
        try:
            if self._plate_after_id:
                self.window.after_cancel(self._plate_after_id)
        except Exception:
            pass
        self._plate_after_id = self.window.after(350, self.detect_contract_by_current_plate)

    def validate_plate(self):
        numero = self.entry_placa_numero.get().strip()
        letras = self.entry_placa_letras.get().strip().upper()

        if not numero or not letras:
            raise ValueError("Debe ingresar la placa completa.")

        if not numero.isdigit():
            raise ValueError("La parte numérica de la placa solo debe contener números.")

        if len(numero) < 2 or len(numero) > 4:
            raise ValueError("La parte numérica de la placa debe tener entre 2 y 4 dígitos.")

        if not letras.isalpha():
            raise ValueError("La parte de letras de la placa solo debe contener letras.")

        if len(letras) != 3:
            raise ValueError("La placa debe tener exactamente 3 letras.")

        return f"{numero} {letras}"

    def split_plate(self, placa):
        if not placa:
            return "", ""

        cleaned = placa.strip().upper().replace("-", " ")
        parts = cleaned.split()

        if len(parts) >= 2:
            return parts[0], parts[1]

        compact = cleaned.replace(" ", "")
        numero = "".join(ch for ch in compact if ch.isdigit())
        letras = "".join(ch for ch in compact if ch.isalpha())
        return numero[:4], letras[:3]

    def get_selected_service_ids(self):
        return [service_id for service_id, var in self.service_vars.items() if var.get()]

    def load_active_vehicle_types(self):
        """
        Carga tipos de vehículo desde TIPOVEHICULO y guarda un mapa:
            texto visible -> ID TipoVehiculo

        Esto evita el error FOREIGN KEY, porque VEHICULO.TipoVehiculo
        ahora es INTEGER y apunta a TIPOVEHICULO.TipoVehiculo.
        """
        conn = None

        self.vehicle_types_data = []
        self.vehicle_type_map = {}

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT
                    TV.TipoVehiculo,
                    TV.Nombre
                FROM TIPOVEHICULO TV
                INNER JOIN TARIFA T ON T.TipoVehiculo = TV.TipoVehiculo
                WHERE TV.Estado = 1
                  AND T.Estado = 1
                  AND T.TipoTarifa = ?
                ORDER BY TV.Nombre ASC
            """, (TIPO_TARIFA_ESCALONADA,))
            rows = cursor.fetchall()

            # Si aún no hay tarifa, por lo menos cargar el catálogo activo.
            if not rows:
                cursor.execute("""
                    SELECT TipoVehiculo, Nombre
                    FROM TIPOVEHICULO
                    WHERE Estado = 1
                    ORDER BY Nombre ASC
                """)
                rows = cursor.fetchall()

            for row in rows:
                nombre = str(row["Nombre"] or "").strip()
                tipo_id = row["TipoVehiculo"]
                if not nombre:
                    continue
                self.vehicle_types_data.append(nombre)
                self.vehicle_type_map[nombre] = tipo_id

        finally:
            if conn:
                conn.close()

        if self.vehicle_types_data and not self.vehicle_type_var.get():
            self.vehicle_type_var.set(self.vehicle_types_data[0])

    def load_active_services(self):
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT Servicio, Nombre, Precio
                FROM SERVICIO
                WHERE Estado = ?
                ORDER BY Nombre ASC
            """, (ESTADO_GENERAL_ACTIVO,))
            rows = cursor.fetchall()
        finally:
            if conn:
                conn.close()

        self.services_data = rows

    def detect_contract_by_current_plate(self):
        self._plate_after_id = None

        numero = self.entry_placa_numero.get().strip()
        letras = self.entry_placa_letras.get().strip().upper()

        self.detected_contract_id = None
        self.detected_contract_text = ""

        if not numero or not letras or len(letras) != 3:
            self.update_contract_notice()
            return

        placa = f"{numero} {letras}"

        conn = None

        try:
            conn = get_connection()
            cursor = conn.cursor()

            vehiculo_id = self.get_vehicle_id_by_plate(cursor, placa)
            if not vehiculo_id:
                self.update_contract_notice()
                return

            contract = self.get_active_contract_data_for_vehicle(cursor, vehiculo_id)
            if contract:
                self.detected_contract_id = contract["Contrato"]
                self.detected_contract_text = (
                    f"Vehículo con contrato habilitado: {contract['CodigoContrato']} "
                    f"hasta {self.format_date_only(contract['FechaFin'])}. "
                    "El parqueo no se cobrará. Solo se permite registrar operación si selecciona un servicio extra."
                )

        finally:
            if conn:
                conn.close()

        self.update_contract_notice()

    def update_contract_notice(self):
        if not self.contract_notice_label:
            return

        if self.detected_contract_id:
            self.contract_notice_label.configure(
                text=self.detected_contract_text,
                fg="#15803d"
            )
        else:
            self.contract_notice_label.configure(text="")

    def format_date_only(self, fecha):
        if not fecha:
            return ""
        try:
            return datetime.strptime(fecha[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return fecha

    def load_data(self):
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    O.Operacion,
                    O.Vehiculo,
                    O.Cliente,
                    O.Contrato,
                    V.Placa,
                    V.TipoVehiculo,
                    COALESCE(TV.Nombre, CAST(V.TipoVehiculo AS TEXT)) AS TipoVehiculoNombre
                FROM OPERACION O
                INNER JOIN VEHICULO V ON O.Vehiculo = V.Vehiculo
                LEFT JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = V.TipoVehiculo
                WHERE O.Operacion = ? AND O.Estado = ?
            """, (self.operation_id, ESTADO_OPERACION_ACTIVO))
            row = cursor.fetchone()

            if not row:
                messagebox.showerror("Error", "No se encontró la operación activa.")
                self.safe_close()
                return

            self.loaded_vehicle_id = row["Vehiculo"]
            self.loaded_customer_id = row["Cliente"]
            self.loaded_contract_id = row["Contrato"]

            numero, letras = self.split_plate(row["Placa"])
            self.entry_placa_numero.insert(0, numero)
            self.entry_placa_letras.insert(0, letras)

            tipo_actual = row["TipoVehiculoNombre"] if row["TipoVehiculoNombre"] else ""
            if tipo_actual and tipo_actual not in self.vehicle_types_data:
                self.vehicle_types_data.append(tipo_actual)
                self.vehicle_type_map[tipo_actual] = row["TipoVehiculo"]
                self.vehicle_types_data = sorted(set(self.vehicle_types_data))
                if self.vehicle_type_combo:
                    self.vehicle_type_combo.configure(values=self.vehicle_types_data)
            self.vehicle_type_var.set(tipo_actual if tipo_actual else (self.vehicle_types_data[0] if self.vehicle_types_data else ""))


            cursor.execute("""
                SELECT Servicio
                FROM OPERACIONSERVICIO
                WHERE Operacion = ? AND Estado != ?
            """, (self.operation_id, ESTADO_OPERACION_SERVICIO_CANCELADO))
            selected_ids = {r["Servicio"] for r in cursor.fetchall()}

            for service_id, var in self.service_vars.items():
                var.set(service_id in selected_ids)

            contract = self.get_active_contract_data_for_vehicle(cursor, self.loaded_vehicle_id)
            if contract:
                self.detected_contract_id = contract["Contrato"]
                self.detected_contract_text = (
                    f"Vehículo con contrato habilitado: {contract['CodigoContrato']} "
                    f"hasta {self.format_date_only(contract['FechaFin'])}. "
                    "El parqueo no se cobrará. Solo se permite guardar si hay servicio extra."
                )
                self.update_contract_notice()

        finally:
            if conn:
                conn.close()

    def save_operation(self):
        try:
            placa = self.validate_plate()
        except ValueError as e:
            messagebox.showwarning("Dato inválido", str(e))
            return

        cliente_nombre = ""
        tipo_vehiculo = self.vehicle_type_var.get().strip()
        tipo_vehiculo_id = self.vehicle_type_map.get(tipo_vehiculo)
        observaciones = ""
        selected_service_ids = self.get_selected_service_ids()

        if not tipo_vehiculo or tipo_vehiculo_id is None:
            messagebox.showwarning(
                "Dato requerido",
                "Debe seleccionar un tipo de vehículo con tarifa activa."
            )
            return

        conn = None

        try:
            conn = get_connection()
            cursor = conn.cursor()

            usr = obtener_usuario_actual_id(self.user_data)

            if self.mode == "create":
                vehiculo_id = self.get_or_create_vehicle(cursor, placa, tipo_vehiculo_id)
                contrato_data = self.get_active_contract_data_for_vehicle(cursor, vehiculo_id)
                contrato_id = contrato_data["Contrato"] if contrato_data else None
                cliente_id = contrato_data["Cliente"] if contrato_data else None

                if contrato_id and not selected_service_ids:
                    conn.rollback()
                    messagebox.showwarning(
                        "Contrato activo",
                        "Este vehículo tiene contrato activo.\n\n"
                        "No se cobrará parqueo, por eso no se puede guardar una operación solo de parqueo.\n"
                        "Seleccione al menos un servicio extra para registrar la operación."
                    )
                    return

                tipo_operacion = TIPO_OPERACION_CONTRATO if contrato_id else TIPO_OPERACION_NORMAL
                tarifa_id = self.get_main_tariff_for_vehicle(cursor, tipo_vehiculo_id)

                codigo_operacion = self.generate_operation_code(cursor)
                codigo_retiro = self.generate_pickup_code(cursor)
                fecha_ingreso = ahora_texto()

                cursor.execute("""
                    INSERT INTO OPERACION (
                        CodigoOperacion,
                        Vehiculo,
                        Cliente,
                        Tarifa,
                        Contrato,
                        UsuarioIngreso,
                        FechaIngreso,
                        TipoOperacion,
                        Estado,
                        CodigoRetiro,
                        Observacion,
                        Usr,
                        UsrFecha,
                        UsrHora,
                        FechaCreacion,
                        FechaModificacion
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        date('now','localtime'),
                        time('now','localtime'),
                        datetime('now','localtime'),
                        datetime('now','localtime')
                    )
                """, (
                    codigo_operacion,
                    vehiculo_id,
                    cliente_id,
                    tarifa_id,
                    contrato_id,
                    usr,
                    fecha_ingreso,
                    tipo_operacion,
                    ESTADO_OPERACION_ACTIVO,
                    codigo_retiro,
                    observaciones if observaciones else None,
                    usr
                ))

                operacion_id = cursor.lastrowid
                self.replace_services(cursor, operacion_id)

                detalle_bitacora = f"Se creó la operación {operacion_id} para placa {placa} con código de retiro {codigo_retiro}"
                if contrato_id:
                    detalle_bitacora += ". Vehículo con contrato activo; solo se cobrarán servicios."

                self.insert_bitacora(
                    cursor,
                    usr,
                    "CREAR_OPERACION",
                    "OPERACION",
                    operacion_id,
                    detalle_bitacora,
                    fecha_ingreso
                )

                conn.commit()

                # Abrir vista previa del ticket automáticamente después del ingreso
                ticket_data = {
                    "Operacion": operacion_id,
                    "CodigoRetiro": codigo_retiro,
                    "FechaIngreso": fecha_ingreso,
                    "Placa": placa,
                }
                TicketPreviewWindow(self.parent, ticket_data).run()

            else:
                vehiculo_id = self.loaded_vehicle_id
                contrato_data = self.get_active_contract_data_for_vehicle(cursor, vehiculo_id)
                contrato_id = contrato_data["Contrato"] if contrato_data else None
                cliente_id = contrato_data["Cliente"] if contrato_data else None

                if contrato_id and not selected_service_ids:
                    conn.rollback()
                    messagebox.showwarning(
                        "Contrato activo",
                        "Este vehículo tiene contrato activo.\n\n"
                        "No se cobrará parqueo, por eso no se puede guardar una operación solo de parqueo.\n"
                        "Seleccione al menos un servicio extra para guardar la operación."
                    )
                    return

                tipo_operacion = TIPO_OPERACION_CONTRATO if contrato_id else TIPO_OPERACION_NORMAL
                tarifa_id = self.get_main_tariff_for_vehicle(cursor, tipo_vehiculo_id)

                cursor.execute("""
                    UPDATE VEHICULO
                    SET
                        Placa = ?,
                        TipoVehiculo = ?,
                        Usr = ?,
                        UsrFecha = date('now','localtime'),
                        UsrHora = time('now','localtime'),
                        FechaModificacion = datetime('now','localtime')
                    WHERE Vehiculo = ?
                """, (placa, tipo_vehiculo_id, usr, vehiculo_id))

                cursor.execute("""
                    UPDATE OPERACION
                    SET
                        Cliente = ?,
                        Tarifa = ?,
                        Contrato = ?,
                        TipoOperacion = ?,
                        Observacion = ?,
                        Usr = ?,
                        UsrFecha = date('now','localtime'),
                        UsrHora = time('now','localtime'),
                        FechaModificacion = datetime('now','localtime')
                    WHERE Operacion = ?
                """, (
                    cliente_id,
                    tarifa_id,
                    contrato_id,
                    tipo_operacion,
                    observaciones if observaciones else None,
                    usr,
                    self.operation_id
                ))

                self.replace_services(cursor, self.operation_id)

                self.insert_bitacora(
                    cursor,
                    usr,
                    "EDITAR_OPERACION",
                    "OPERACION",
                    self.operation_id,
                    f"Se editó la operación {self.operation_id} para placa {placa}",
                    ahora_texto()
                )

                conn.commit()
                messagebox.showinfo("Guardado", "Operación actualizada correctamente.")

            self.operations_view.load_operations()
            self.safe_close()

        except Exception as e:
            if conn:
                conn.rollback()
            messagebox.showerror("Error", f"No se pudo guardar la operación.\n{str(e)}")

        finally:
            if conn:
                conn.close()

    def get_vehicle_id_by_plate(self, cursor, placa):
        cursor.execute("""
            SELECT Vehiculo
            FROM VEHICULO
            WHERE REPLACE(REPLACE(UPPER(Placa), ' ', ''), '-', '') = ?
            LIMIT 1
        """, (limpiar_placa_para_busqueda(placa),))
        row = cursor.fetchone()
        return row["Vehiculo"] if row else None

    def get_or_create_vehicle(self, cursor, placa, tipo_vehiculo):
        vehiculo_id = self.get_vehicle_id_by_plate(cursor, placa)
        usr = obtener_usuario_actual_id(self.user_data)

        if vehiculo_id:
            cursor.execute("""
                UPDATE VEHICULO
                SET
                    TipoVehiculo = ?,
                    Placa = ?,
                    Usr = ?,
                    UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'),
                    FechaModificacion = datetime('now','localtime')
                WHERE Vehiculo = ?
            """, (tipo_vehiculo, placa, usr, vehiculo_id))
            return vehiculo_id

        cursor.execute("""
            INSERT INTO VEHICULO (
                Placa,
                TipoVehiculo,
                Estado,
                Usr,
                UsrFecha,
                UsrHora,
                FechaCreacion,
                FechaModificacion
            )
            VALUES (
                ?, ?, ?, ?,
                date('now','localtime'),
                time('now','localtime'),
                datetime('now','localtime'),
                datetime('now','localtime')
            )
        """, (
            placa,
            tipo_vehiculo,
            ESTADO_GENERAL_ACTIVO,
            usr
        ))
        return cursor.lastrowid

    def get_or_create_customer_by_name(self, cursor, nombre, existing_customer_id=None):
        if not nombre:
            return None

        usr = obtener_usuario_actual_id(self.user_data)

        if existing_customer_id:
            cursor.execute("""
                UPDATE CLIENTE
                SET
                    Nombres = ?,
                    Usr = ?,
                    UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'),
                    FechaModificacion = datetime('now','localtime')
                WHERE Cliente = ?
            """, (nombre, usr, existing_customer_id))
            return existing_customer_id

        cursor.execute("""
            INSERT INTO CLIENTE (
                Nombres,
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
        """, (
            nombre,
            ESTADO_GENERAL_ACTIVO,
            usr
        ))
        return cursor.lastrowid

    def get_main_tariff_for_vehicle(self, cursor, tipo_vehiculo_id):
        cursor.execute("""
            SELECT Tarifa
            FROM TARIFA
            WHERE Estado = ?
              AND TipoVehiculo = ?
              AND TipoTarifa = ?
            ORDER BY Tarifa ASC
            LIMIT 1
        """, (
            ESTADO_GENERAL_ACTIVO,
            tipo_vehiculo_id,
            TIPO_TARIFA_ESCALONADA
        ))
        row = cursor.fetchone()

        if not row:
            raise Exception("No existe una tarifa por hora activa para el tipo de vehículo seleccionado.")

        return row["Tarifa"]

    def get_active_contract_for_vehicle(self, cursor, vehiculo_id):
        contract = self.get_active_contract_data_for_vehicle(cursor, vehiculo_id)
        return contract["Contrato"] if contract else None

    def get_active_contract_data_for_vehicle(self, cursor, vehiculo_id):
        hoy = datetime.now().strftime("%Y-%m-%d")

        # Nuevo esquema:
        # Un contrato puede tener varios vehículos mediante CONTRATOVEHICULO.
        # Solo se considera habilitado si el contrato está pagado.
        if tabla_existe(cursor, "CONTRATOVEHICULO"):
            cursor.execute("""
                SELECT
                    C.Contrato,
                    C.CodigoContrato,
                    C.Cliente,
                    C.FechaInicio,
                    C.FechaFin,
                    C.MontoContrato
                FROM CONTRATO C
                INNER JOIN CONTRATOVEHICULO CV ON CV.Contrato = C.Contrato
                WHERE CV.Vehiculo = ?
                  AND CV.Estado = 1
                  AND C.Estado = ?
                  AND C.EstadoPago = 1
                  AND C.FechaInicio <= ?
                  AND C.FechaFin >= ?
                ORDER BY C.Contrato DESC
                LIMIT 1
            """, (
                vehiculo_id,
                ESTADO_CONTRATO_ACTIVO,
                hoy,
                hoy
            ))
            row = cursor.fetchone()
            if row:
                return row

        # Compatibilidad con contratos antiguos:
        # si aún no existe relación en CONTRATOVEHICULO, se revisa CONTRATO.Vehiculo.
        cursor.execute("""
            SELECT
                Contrato,
                CodigoContrato,
                Cliente,
                FechaInicio,
                FechaFin,
                MontoContrato
            FROM CONTRATO
            WHERE Vehiculo = ?
              AND Estado = ?
              AND EstadoPago = 1
              AND FechaInicio <= ?
              AND FechaFin >= ?
            ORDER BY Contrato DESC
            LIMIT 1
        """, (
            vehiculo_id,
            ESTADO_CONTRATO_ACTIVO,
            hoy,
            hoy
        ))
        row = cursor.fetchone()

        return row

    def replace_services(self, cursor, operacion_id):
        cursor.execute("DELETE FROM OPERACIONSERVICIO WHERE Operacion = ?", (operacion_id,))

        selected_service_ids = self.get_selected_service_ids()
        usr = obtener_usuario_actual_id(self.user_data)

        for service_id in selected_service_ids:
            cursor.execute("""
                SELECT Precio
                FROM SERVICIO
                WHERE Servicio = ? AND Estado = ?
            """, (service_id, ESTADO_GENERAL_ACTIVO))
            row = cursor.fetchone()

            if not row:
                continue

            precio = float(row["Precio"])

            cursor.execute("""
                INSERT INTO OPERACIONSERVICIO (
                    Operacion,
                    Servicio,
                    Cantidad,
                    PrecioUnitario,
                    Subtotal,
                    Estado,
                    Usr,
                    UsrFecha,
                    UsrHora,
                    FechaCreacion,
                    FechaModificacion
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    date('now','localtime'),
                    time('now','localtime'),
                    datetime('now','localtime'),
                    datetime('now','localtime')
                )
            """, (
                operacion_id,
                service_id,
                1,
                precio,
                precio,
                ESTADO_OPERACION_SERVICIO_PENDIENTE,
                usr
            ))

    def insert_bitacora(self, cursor, usr, accion, tabla, registro, descripcion, fecha_evento):
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
                ?, ?, ?, ?, ?, ?, ?, ?,
                date('now','localtime'),
                time('now','localtime'),
                datetime('now','localtime'),
                datetime('now','localtime')
            )
        """, (
            usr,
            accion,
            tabla,
            registro,
            descripcion,
            fecha_evento,
            ESTADO_GENERAL_ACTIVO,
            usr
        ))

    def generate_operation_code(self, cursor):
        while True:
            code = "OP-" + datetime.now().strftime("%Y%m%d%H%M%S%f")[:17]
            cursor.execute("SELECT 1 FROM OPERACION WHERE CodigoOperacion = ?", (code,))
            if not cursor.fetchone():
                return code

    def generate_pickup_code(self, cursor):
        while True:
            code = datetime.now().strftime("%H%M%S")
            cursor.execute("""
                SELECT 1
                FROM OPERACION
                WHERE CodigoRetiro = ? AND Estado = ?
            """, (code, ESTADO_OPERACION_ACTIVO))
            if not cursor.fetchone():
                return code

    def run(self):
        pass


# =========================================================
# CANCELAR OPERACIÓN
# =========================================================
class CancelOperationWindow:
    def __init__(self, operations_view, user_data, operation_id):
        self.operations_view = operations_view
        self.parent = operations_view
        self.user_data = user_data
        self.operation_id = operation_id

        self.window = tk.Toplevel()
        self.window.title("Cancelar operación")
        self.window.resizable(True, True)
        self.window.minsize(420, 250)
        self.window.configure(bg="white")
        centrar_ventana(self.window, 420, 290)
        self.window.grab_set()

        self.text_reason = None

        self.build_ui()

    def build_ui(self):
        tk.Label(
            self.window,
            text="Cancelar operación",
            font=("Arial", 16, "bold"),
            bg="white",
            fg="#111827"
        ).pack(pady=(20, 12))

        tk.Label(
            self.window,
            text="Motivo de cancelación *",
            font=("Arial", 11, "bold"),
            bg="white"
        ).pack(anchor="w", padx=30)

        self.text_reason = tk.Text(self.window, font=("Arial", 11), height=6)
        self.text_reason.pack(fill="x", padx=30, pady=(8, 16))

        buttons = tk.Frame(self.window, bg="white")
        buttons.pack(pady=10)

        tk.Button(
            buttons,
            text="Confirmar cancelación",
            font=("Arial", 11, "bold"),
            bg="#dc2626",
            fg="white",
            bd=0,
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.confirm_cancel
        ).grid(row=0, column=0, padx=8)

        tk.Button(
            buttons,
            text="Cerrar",
            font=("Arial", 11, "bold"),
            bg="#6b7280",
            fg="white",
            bd=0,
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.window.destroy
        ).grid(row=0, column=1, padx=8)

    def confirm_cancel(self):
        reason = self.text_reason.get("1.0", "end").strip()

        if not reason:
            messagebox.showwarning("Dato requerido", "Debe ingresar el motivo de cancelación.")
            return

        conn = None

        try:
            conn = get_connection()
            cursor = conn.cursor()

            now_str = ahora_texto()
            usr = obtener_usuario_actual_id(self.user_data)

            cursor.execute("""
                UPDATE OPERACION
                SET
                    Estado = ?,
                    MotivoCancelacion = ?,
                    FechaSalida = ?,
                    Usr = ?,
                    UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'),
                    FechaModificacion = datetime('now','localtime')
                WHERE Operacion = ? AND Estado = ?
            """, (
                ESTADO_OPERACION_CANCELADO,
                reason,
                now_str,
                usr,
                self.operation_id,
                ESTADO_OPERACION_ACTIVO
            ))

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
                    ?, ?, ?, ?, ?, ?, ?, ?,
                    date('now','localtime'),
                    time('now','localtime'),
                    datetime('now','localtime'),
                    datetime('now','localtime')
                )
            """, (
                usr,
                "CANCELAR_OPERACION",
                "OPERACION",
                self.operation_id,
                f"Se canceló la operación {self.operation_id}. Motivo: {reason}",
                now_str,
                ESTADO_GENERAL_ACTIVO,
                usr
            ))

            conn.commit()
            messagebox.showinfo("Operación cancelada", "La operación fue cancelada correctamente.")
            self.window.destroy()
            self.operations_view.load_operations()

        except Exception as e:
            if conn:
                conn.rollback()
            messagebox.showerror("Error", f"No se pudo cancelar la operación.\n{str(e)}")

        finally:
            if conn:
                conn.close()

    def run(self):
        pass
