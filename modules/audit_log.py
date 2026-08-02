import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from database.db import get_connection


# =========================================================
# CATÁLOGOS
# =========================================================
ESTADO_INACTIVO = 0
ESTADO_ACTIVO = 1


def formatear_fecha(valor):
    """
    Convierte fechas de BD a formato visual DD/MM/YYYY o DD/MM/YYYY HH:MM.
    """
    if not valor:
        return ""

    texto = str(valor).strip()

    formatos = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ]

    for formato in formatos:
        try:
            if "%H" in formato:
                fecha = datetime.strptime(texto[:19], formato)
                return fecha.strftime("%d/%m/%Y %H:%M")

            fecha = datetime.strptime(texto[:10], formato)
            return fecha.strftime("%d/%m/%Y")
        except Exception:
            pass

    if "-" in texto and len(texto) >= 10:
        partes = texto[:10].split("-")
        if len(partes) == 3:
            resto = texto[10:16]
            return f"{partes[2]}/{partes[1]}/{partes[0]}{resto}"

    return texto


def convertir_fecha_busqueda_a_bd(valor):
    """
    Convierte DD/MM/YYYY a YYYY-MM-DD para buscar en SQLite.
    """
    valor = str(valor or "").strip()

    if not valor:
        return ""

    try:
        return datetime.strptime(valor, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


class AuditLogView:
    def __init__(self, parent, user_data):
        self.parent = parent
        self.user_data = user_data

        self.search_entry = None
        self.entry_from = None
        self.entry_to = None
        self.tree = None

    def build(self):
        if self.user_data["rol"] != "admin":
            self.build_access_denied()
            return

        self.build_filters()
        self.build_table()
        self.load_logs()

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
            text="Solo el administrador puede ver la bitácora.",
            font=("Arial", 11),
            bg="white",
            fg="#4b5563"
        ).pack()

    def build_filters(self):
        filters_frame = tk.Frame(self.parent, bg="white")
        filters_frame.pack(fill="x", padx=15, pady=15)

        tk.Label(
            filters_frame,
            text="Buscar:",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#111827"
        ).grid(row=0, column=0, padx=(5, 5), pady=5, sticky="w")

        self.search_entry = tk.Entry(filters_frame, font=("Arial", 10), width=24)
        self.search_entry.grid(row=0, column=1, padx=(0, 12), pady=5, sticky="w")
        self.search_entry.bind("<KeyRelease>", lambda event: self.load_logs())

        tk.Label(
            filters_frame,
            text="Desde (DD/MM/YYYY):",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#111827"
        ).grid(row=0, column=2, padx=(5, 5), pady=5, sticky="w")

        self.entry_from = tk.Entry(filters_frame, font=("Arial", 10), width=14)
        self.entry_from.grid(row=0, column=3, padx=(0, 12), pady=5, sticky="w")

        tk.Label(
            filters_frame,
            text="Hasta (DD/MM/YYYY):",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#111827"
        ).grid(row=0, column=4, padx=(5, 5), pady=5, sticky="w")

        self.entry_to = tk.Entry(filters_frame, font=("Arial", 10), width=14)
        self.entry_to.grid(row=0, column=5, padx=(0, 12), pady=5, sticky="w")

        tk.Button(
            filters_frame,
            text="Buscar",
            font=("Arial", 10, "bold"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            bd=0,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.load_logs
        ).grid(row=0, column=6, padx=8, pady=5)

        tk.Button(
            filters_frame,
            text="Limpiar",
            font=("Arial", 10, "bold"),
            bg="#6b7280",
            fg="white",
            activebackground="#4b5563",
            activeforeground="white",
            bd=0,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.clear_filters
        ).grid(row=0, column=7, padx=8, pady=5)

    def build_table(self):
        table_frame = tk.Frame(self.parent, bg="white")
        table_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        columns = (
            "Bitacora",
            "UsuarioNombre",
            "Accion",
            "TablaAfectada",
            "RegistroAfectado",
            "Descripcion",
            "FechaEvento"
        )

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)

        self.tree.heading("Bitacora", text="ID")
        self.tree.heading("UsuarioNombre", text="Usuario")
        self.tree.heading("Accion", text="Acción")
        self.tree.heading("TablaAfectada", text="Tabla")
        self.tree.heading("RegistroAfectado", text="Registro")
        self.tree.heading("Descripcion", text="Descripción")
        self.tree.heading("FechaEvento", text="Fecha")

        self.tree.column("Bitacora", width=55, anchor="center", stretch=False)
        self.tree.column("UsuarioNombre", width=150, anchor="w", stretch=False)
        self.tree.column("Accion", width=180, anchor="center", stretch=False)
        self.tree.column("TablaAfectada", width=110, anchor="center", stretch=False)
        self.tree.column("RegistroAfectado", width=80, anchor="center", stretch=False)
        self.tree.column("Descripcion", width=420, anchor="w", stretch=False)
        self.tree.column("FechaEvento", width=160, anchor="center", stretch=False)

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

    def clear_filters(self):
        self.search_entry.delete(0, tk.END)
        self.entry_from.delete(0, tk.END)
        self.entry_to.delete(0, tk.END)
        self.load_logs()

    def validar_rango_fechas(self, date_from_text, date_to_text):
        date_from_bd = convertir_fecha_busqueda_a_bd(date_from_text)
        date_to_bd = convertir_fecha_busqueda_a_bd(date_to_text)

        if date_from_text and date_from_bd is None:
            messagebox.showwarning(
                "Fecha inválida",
                "La fecha 'Desde' debe estar en formato DD/MM/YYYY.\nEjemplo: 29/04/2026"
            )
            return None, None, False

        if date_to_text and date_to_bd is None:
            messagebox.showwarning(
                "Fecha inválida",
                "La fecha 'Hasta' debe estar en formato DD/MM/YYYY.\nEjemplo: 29/04/2026"
            )
            return None, None, False

        if date_from_bd and date_to_bd and date_from_bd > date_to_bd:
            messagebox.showwarning(
                "Rango inválido",
                "La fecha 'Desde' no puede ser mayor que la fecha 'Hasta'."
            )
            return None, None, False

        return date_from_bd, date_to_bd, True

    def load_logs(self):
        if not self.tree:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        search_value = self.search_entry.get().strip().upper() if self.search_entry else ""
        date_from_text = self.entry_from.get().strip() if self.entry_from else ""
        date_to_text = self.entry_to.get().strip() if self.entry_to else ""

        date_from, date_to, ok = self.validar_rango_fechas(date_from_text, date_to_text)
        if not ok:
            return

        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            query = """
                SELECT
                    B.Bitacora,
                    U.Nombre AS UsuarioNombre,
                    B.Accion,
                    B.TablaAfectada,
                    B.RegistroAfectado,
                    B.Descripcion,
                    B.FechaEvento
                FROM BITACORA B
                LEFT JOIN USUARIO U ON B.Usuario = U.Usuario
                WHERE B.Estado = ?
            """
            params = [ESTADO_ACTIVO]

            if search_value:
                like_value = f"%{search_value}%"
                query += """
                    AND (
                        UPPER(IFNULL(U.Nombre, '')) LIKE ?
                        OR UPPER(IFNULL(B.Accion, '')) LIKE ?
                        OR UPPER(IFNULL(B.TablaAfectada, '')) LIKE ?
                        OR UPPER(IFNULL(B.Descripcion, '')) LIKE ?
                    )
                """
                params.extend([like_value, like_value, like_value, like_value])

            if date_from:
                query += " AND date(B.FechaEvento) >= date(?) "
                params.append(date_from)

            if date_to:
                query += " AND date(B.FechaEvento) <= date(?) "
                params.append(date_to)

            query += " ORDER BY B.FechaEvento DESC, B.Bitacora DESC "

            cursor.execute(query, params)
            rows = cursor.fetchall()

            for row in rows:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        row["Bitacora"],
                        row["UsuarioNombre"] if row["UsuarioNombre"] else "-",
                        row["Accion"] if row["Accion"] else "",
                        row["TablaAfectada"] if row["TablaAfectada"] else "",
                        row["RegistroAfectado"] if row["RegistroAfectado"] is not None else "",
                        row["Descripcion"] if row["Descripcion"] else "",
                        formatear_fecha(row["FechaEvento"])
                    )
                )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cargar la bitácora.\n{str(e)}"
            )
        finally:
            if conn:
                conn.close()