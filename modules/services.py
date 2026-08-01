import tkinter as tk
from tkinter import ttk, messagebox

from database.db import get_connection


# =========================================================
# CATÁLOGOS
# =========================================================
ESTADO_INACTIVO = 0
ESTADO_ACTIVO = 1

ESTADO_TEXTO = {
    ESTADO_ACTIVO: "Activo",
    ESTADO_INACTIVO: "Inactivo",
}


# =========================================================
# UTILIDADES
# =========================================================
def obtener_usuario_actual_id(user_data):
    if not user_data:
        return 0
    return user_data.get("Usuario") or user_data.get("id") or 0


def ahora_texto():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =========================================================
# VISTA PRINCIPAL
# =========================================================
class ServicesView:
    def __init__(self, parent, user_data):
        self.parent = parent
        self.user_data = user_data

        self.tree = None
        self.search_entry = None

    def build(self):
        if self.user_data["rol"] != "admin":
            self.build_access_denied()
            return

        self.build_header()
        self.build_table()
        self.load_services()

    def build_access_denied(self):
        container = tk.Frame(self.parent, bg="white")
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text="Acceso restringido",
            font=("Arial", 18, "bold"),
            bg="white",
            fg="#b91c1c"
        ).pack(pady=(80, 10))

        tk.Label(
            container,
            text="Solo el administrador puede gestionar servicios.",
            font=("Arial", 11),
            bg="white",
            fg="#4b5563"
        ).pack()

    def build_header(self):
        header_frame = tk.Frame(self.parent, bg="white")
        header_frame.pack(fill="x", padx=15, pady=15)

        tk.Label(
            header_frame,
            text="Buscar servicio:",
            font=("Arial", 11, "bold"),
            bg="white",
            fg="#111827"
        ).pack(side="left", padx=(0, 8))

        self.search_entry = tk.Entry(header_frame, font=("Arial", 11), width=25)
        self.search_entry.pack(side="left", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda event: self.load_services())

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
            command=self.load_services
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            header_frame,
            text="Nuevo servicio",
            font=("Arial", 10, "bold"),
            bg="#16a34a",
            fg="white",
            activebackground="#15803d",
            activeforeground="white",
            bd=0,
            relief="flat",
            padx=15,
            pady=6,
            cursor="hand2",
            command=self.open_new_service_window
        ).pack(side="right")

    def build_table(self):
        table_frame = tk.Frame(self.parent, bg="white")
        table_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        columns = (
            "Servicio",
            "Nombre",
            "Descripcion",
            "Precio",
            "Duracion",
            "Estado",
            "Acciones"
        )

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)

        self.tree.heading("Servicio", text="ID")
        self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("Descripcion", text="Descripción")
        self.tree.heading("Precio", text="Precio")
        self.tree.heading("Duracion", text="Duración estimada")
        self.tree.heading("Estado", text="Estado")
        self.tree.heading("Acciones", text="Acciones")

        self.tree.column("Servicio", width=55, anchor="center", stretch=False)
        self.tree.column("Nombre", width=170, anchor="w", stretch=False)
        self.tree.column("Descripcion", width=320, anchor="w", stretch=False)
        self.tree.column("Precio", width=100, anchor="center", stretch=False)
        self.tree.column("Duracion", width=140, anchor="center", stretch=False)
        self.tree.column("Estado", width=90, anchor="center", stretch=False)
        self.tree.column("Acciones", width=110, anchor="center", stretch=False)

        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)

        self.tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.on_double_click)

    def load_services(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        search_value = self.search_entry.get().strip().upper() if self.search_entry else ""

        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                Servicio,
                Nombre,
                Descripcion,
                Precio,
                DuracionEstimada,
                Estado
            FROM SERVICIO
            WHERE 1 = 1
        """
        params = []

        if search_value:
            like_value = f"%{search_value}%"
            query += """
                AND (
                    UPPER(IFNULL(Nombre, '')) LIKE ?
                    OR UPPER(IFNULL(Descripcion, '')) LIKE ?
                )
            """
            params.extend([like_value, like_value])

        query += " ORDER BY Servicio ASC "

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            duracion = f"{row['DuracionEstimada']} min" if row["DuracionEstimada"] is not None else "-"
            self.tree.insert(
                "",
                "end",
                values=(
                    row["Servicio"],
                    row["Nombre"],
                    row["Descripcion"] if row["Descripcion"] else "",
                    f"Bs {float(row['Precio']):.2f}",
                    duracion,
                    ESTADO_TEXTO.get(row["Estado"], "N/D"),
                    "Doble clic"
                )
            )

    def on_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        values = item["values"]
        if not values:
            return

        service_id = values[0]
        service_name = values[1]
        current_status = values[5]

        action_window = tk.Toplevel(self.parent)
        action_window.title("Acciones de servicio")
        action_window.geometry("340x270")
        action_window.resizable(True, True)
        action_window.minsize(280, 220)
        action_window.configure(bg="white")
        action_window.grab_set()

        tk.Label(
            action_window,
            text=f"Servicio: {service_name}",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#111827",
            wraplength=260
        ).pack(pady=(20, 10))

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
            command=lambda: self.confirm_edit(service_id, action_window)
        ).pack(pady=8)

        estado_actual = ESTADO_ACTIVO if current_status == "Activo" else ESTADO_INACTIVO
        toggle_text = "Inactivar" if estado_actual == ESTADO_ACTIVO else "Activar"
        toggle_color = "#dc2626" if estado_actual == ESTADO_ACTIVO else "#16a34a"

        tk.Button(
            action_window,
            text=toggle_text,
            font=("Arial", 11, "bold"),
            width=18,
            bg=toggle_color,
            fg="white",
            bd=0,
            relief="flat",
            cursor="hand2",
            command=lambda: self.toggle_service_status(service_id, estado_actual, action_window)
        ).pack(pady=8)

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
        ).pack(pady=8)

    def confirm_edit(self, service_id, action_window=None):
        confirmed = messagebox.askyesno(
            "Confirmar edición",
            "¿Desea editar este servicio?"
        )
        if not confirmed:
            return
        self.edit_service(service_id, action_window)

    def open_new_service_window(self):
        ServiceFormWindow(self, self.user_data, mode="create").run()

    def edit_service(self, service_id, action_window=None):
        if action_window:
            action_window.destroy()
        ServiceFormWindow(self, self.user_data, mode="edit", service_id=service_id).run()

    def toggle_service_status(self, service_id, current_status, action_window=None):
        if action_window:
            action_window.destroy()

        new_status = ESTADO_INACTIVO if current_status == ESTADO_ACTIVO else ESTADO_ACTIVO
        new_status_text = ESTADO_TEXTO[new_status]

        confirm = messagebox.askyesno(
            "Confirmar cambio",
            f"¿Desea cambiar el estado del servicio a '{new_status_text}'?"
        )
        if not confirm:
            return

        conn = get_connection()
        cursor = conn.cursor()

        try:
            usr = obtener_usuario_actual_id(self.user_data)

            cursor.execute("""
                UPDATE SERVICIO
                SET
                    Estado = ?,
                    Usr = ?,
                    UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'),
                    FechaModificacion = datetime('now','localtime')
                WHERE Servicio = ?
            """, (new_status, usr, service_id))

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
                "CAMBIAR_ESTADO_SERVICIO",
                "SERVICIO",
                service_id,
                f"Se cambió el estado del servicio {service_id} a {new_status_text}",
                ahora_texto(),
                ESTADO_ACTIVO,
                usr
            ))

            conn.commit()
            messagebox.showinfo("Estado actualizado", "El estado del servicio fue actualizado.")
            self.load_services()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"No se pudo actualizar el estado.\n{str(e)}")

        finally:
            conn.close()


# =========================================================
# FORMULARIO SERVICIO
# =========================================================
class ServiceFormWindow:
    def __init__(self, services_view, current_user, mode="create", service_id=None):
        self.services_view = services_view
        self.current_user = current_user
        self.mode = mode
        self.service_id = service_id

        self.window = tk.Toplevel()
        self.window.title("Nuevo servicio" if mode == "create" else "Editar servicio")
        self.window.geometry("460x500")
        self.window.resizable(True, True)
        self.window.configure(bg="white")
        self.window.grab_set()

        self.entry_nombre = None
        self.text_descripcion = None
        self.entry_precio = None
        self.entry_duracion = None

        self.build_ui()

        if self.mode == "edit" and self.service_id:
            self.load_service_data()

    def build_ui(self):
        title = "Nuevo servicio" if self.mode == "create" else "Editar servicio"

        tk.Label(
            self.window,
            text=title,
            font=("Arial", 16, "bold"),
            bg="white",
            fg="#111827"
        ).pack(pady=(20, 20))

        form = tk.Frame(self.window, bg="white")
        form.pack(padx=30, fill="x")

        tk.Label(form, text="Nombre *", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(0, 5))
        self.entry_nombre = tk.Entry(form, font=("Arial", 11))
        self.entry_nombre.pack(fill="x", pady=(0, 12))

        tk.Label(form, text="Descripción", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(0, 5))
        self.text_descripcion = tk.Text(form, font=("Arial", 11), height=4)
        self.text_descripcion.pack(fill="x", pady=(0, 12))

        tk.Label(form, text="Precio (Bs) *", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(0, 5))
        self.entry_precio = tk.Entry(form, font=("Arial", 11))
        self.entry_precio.pack(fill="x", pady=(0, 12))

        tk.Label(form, text="Duración estimada (minutos)", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(0, 5))
        self.entry_duracion = tk.Entry(form, font=("Arial", 11))
        self.entry_duracion.pack(fill="x", pady=(0, 12))

        tk.Label(
            form,
            text="La duración es opcional. Puede dejarla vacía.",
            font=("Arial", 9),
            bg="white",
            fg="#6b7280"
        ).pack(anchor="w", pady=(0, 12))

        buttons = tk.Frame(self.window, bg="white")
        buttons.pack(pady=20)

        tk.Button(
            buttons,
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
            command=self.confirm_save
        ).grid(row=0, column=0, padx=10)

        tk.Button(
            buttons,
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
            command=self.window.destroy
        ).grid(row=0, column=1, padx=10)

    def load_service_data(self):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT Nombre, Descripcion, Precio, DuracionEstimada
            FROM SERVICIO
            WHERE Servicio = ?
        """, (self.service_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            messagebox.showerror("Error", "No se encontró el servicio.")
            self.window.destroy()
            return

        self.entry_nombre.insert(0, row["Nombre"])
        self.text_descripcion.insert("1.0", row["Descripcion"] if row["Descripcion"] else "")
        self.entry_precio.insert(0, str(row["Precio"]))
        self.entry_duracion.insert(0, "" if row["DuracionEstimada"] is None else str(row["DuracionEstimada"]))

    def confirm_save(self):
        confirmed = messagebox.askyesno(
            "Confirmar guardado",
            "¿Desea guardar este servicio?"
        )
        if not confirmed:
            return

        self.save_service()

    def save_service(self):
        nombre = self.entry_nombre.get().strip()
        descripcion = self.text_descripcion.get("1.0", "end").strip()
        precio_str = self.entry_precio.get().strip()
        duracion_str = self.entry_duracion.get().strip()

        if not nombre or not precio_str:
            messagebox.showwarning("Datos requeridos", "Nombre y precio son obligatorios.")
            return

        try:
            precio = float(precio_str)
        except ValueError:
            messagebox.showwarning("Dato inválido", "El precio debe ser numérico.")
            return

        if precio < 0:
            messagebox.showwarning("Dato inválido", "El precio no puede ser negativo.")
            return

        duracion = None
        if duracion_str:
            try:
                duracion = int(duracion_str)
            except ValueError:
                messagebox.showwarning("Dato inválido", "La duración debe ser un número entero.")
                return

            if duracion < 0:
                messagebox.showwarning("Dato inválido", "La duración no puede ser negativa.")
                return

        conn = get_connection()
        cursor = conn.cursor()

        try:
            usr = obtener_usuario_actual_id(self.current_user)

            if self.mode == "create":
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM SERVICIO
                    WHERE UPPER(Nombre) = ?
                """, (nombre.upper(),))
                if cursor.fetchone()[0] > 0:
                    messagebox.showwarning("Servicio existente", "Ya existe un servicio con ese nombre.")
                    return

                cursor.execute("""
                    INSERT INTO SERVICIO (
                        Nombre,
                        Descripcion,
                        Precio,
                        DuracionEstimada,
                        Estado,
                        Usr,
                        UsrFecha,
                        UsrHora,
                        FechaCreacion,
                        FechaModificacion
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?,
                        date('now','localtime'),
                        time('now','localtime'),
                        datetime('now','localtime'),
                        datetime('now','localtime')
                    )
                """, (
                    nombre,
                    descripcion if descripcion else None,
                    precio,
                    duracion,
                    ESTADO_ACTIVO,
                    usr
                ))

                new_service_id = cursor.lastrowid

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
                    "CREAR_SERVICIO",
                    "SERVICIO",
                    new_service_id,
                    f"Se creó el servicio '{nombre}'",
                    ahora_texto(),
                    ESTADO_ACTIVO,
                    usr
                ))

            else:
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM SERVICIO
                    WHERE UPPER(Nombre) = ? AND Servicio != ?
                """, (nombre.upper(), self.service_id))
                if cursor.fetchone()[0] > 0:
                    messagebox.showwarning("Servicio existente", "Ya existe un servicio con ese nombre.")
                    return

                cursor.execute("""
                    UPDATE SERVICIO
                    SET
                        Nombre = ?,
                        Descripcion = ?,
                        Precio = ?,
                        DuracionEstimada = ?,
                        Usr = ?,
                        UsrFecha = date('now','localtime'),
                        UsrHora = time('now','localtime'),
                        FechaModificacion = datetime('now','localtime')
                    WHERE Servicio = ?
                """, (
                    nombre,
                    descripcion if descripcion else None,
                    precio,
                    duracion,
                    usr,
                    self.service_id
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
                    "EDITAR_SERVICIO",
                    "SERVICIO",
                    self.service_id,
                    f"Se editó el servicio '{nombre}'",
                    ahora_texto(),
                    ESTADO_ACTIVO,
                    usr
                ))

            conn.commit()
            messagebox.showinfo("Guardado", "Servicio guardado correctamente.")
            self.services_view.load_services()
            self.window.destroy()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"No se pudo guardar el servicio.\n{str(e)}")

        finally:
            conn.close()

    def run(self):
        pass