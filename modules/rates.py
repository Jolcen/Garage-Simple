import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

try:
    from database.db import get_connection
except Exception:
    from database.db import getConnection as get_connection


# =========================================================
# CATÁLOGOS
# =========================================================
ESTADO_INACTIVO = 0
ESTADO_ACTIVO = 1

TIPO_TARIFA_HORA = 1
TIPO_TARIFA_NOCTURNA = 2
TIPO_TARIFA_CONTRATO = 3

TIPO_DIA_HORA = 1
TIPO_DIA_SABADO = 2
TIPO_DIA_NOCTURNA = 3
TIPO_DIA_CONTRATO = 4

ESTADO_TEXTO = {
    ESTADO_ACTIVO: "Activa",
    ESTADO_INACTIVO: "Inactiva",
}

COLOR_FONDO = "#f7f7f7"
COLOR_PANEL = "white"
COLOR_TEXTO = "#222222"
COLOR_TEXTO_SUAVE = "#555555"
COLOR_BORDE = "#dddddd"
COLOR_BOTON = "#e5e5e5"
COLOR_BOTON_HOVER = "#d9d9d9"
COLOR_TABLA_CABECERA = "#eeeeee"
COLOR_SELECCION = "#e9e9e9"


# =========================================================
# UTILIDADES
# =========================================================
def row_get(row, key, index=None, default=None):
    if row is None:
        return default
    try:
        return row[key]
    except Exception:
        if index is not None:
            try:
                return row[index]
            except Exception:
                return default
        return default


def obtener_usuario_actual_id(user_data):
    if not user_data:
        return 0
    return user_data.get("Usuario") or user_data.get("id") or 0


def usuario_es_admin(user_data):
    if not user_data:
        return False
    rol_texto = str(user_data.get("rol", "")).strip().lower()
    rol_id = user_data.get("RolId") or user_data.get("Rol")
    return rol_texto == "admin" or rol_id == 1


def normalizar_texto(valor):
    return str(valor or "").strip()


def normalizar_nombre_vehiculo(valor):
    valor = normalizar_texto(valor)
    if not valor:
        return "Auto"
    return valor[:1].upper() + valor[1:].lower()


def ahora_texto():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def convertir_fecha_busqueda(texto):
    texto = (texto or "").strip()
    if not texto:
        return ""

    for formato in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return texto


def validar_hora_hhmm(hora):
    if not hora:
        return False
    try:
        hh, mm = hora.split(":")
        hh = int(hh)
        mm = int(mm)
        return 0 <= hh <= 23 and 0 <= mm <= 59
    except Exception:
        return False


def generar_horas_combo(intervalo_minutos=30):
    horas = []
    for total_minutos in range(0, 24 * 60, intervalo_minutos):
        hh = total_minutos // 60
        mm = total_minutos % 60
        horas.append(f"{hh:02d}:{mm:02d}")
    return horas


def centrar_ventana(window, ancho, alto):
    window.update_idletasks()
    pantalla_ancho = window.winfo_screenwidth()
    pantalla_alto = window.winfo_screenheight()
    x = max((pantalla_ancho // 2) - (ancho // 2), 0)
    y = max((pantalla_alto // 2) - (alto // 2), 0)
    window.geometry(f"{ancho}x{alto}+{x}+{y}")


def configurar_treeview():
    style = ttk.Style()
    try:
        style.theme_use("default")
    except Exception:
        pass

    style.configure(
        "Tarifas.Treeview",
        background=COLOR_PANEL,
        foreground=COLOR_TEXTO,
        rowheight=30,
        fieldbackground=COLOR_PANEL,
        borderwidth=0,
        relief="flat",
        font=("Arial", 10),
    )
    style.configure(
        "Tarifas.Treeview.Heading",
        background=COLOR_TABLA_CABECERA,
        foreground=COLOR_TEXTO,
        font=("Arial", 10, "bold"),
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "Tarifas.Treeview",
        background=[("selected", COLOR_SELECCION)],
        foreground=[("selected", COLOR_TEXTO)],
    )


def insertar_bitacora(cursor, usr, accion, tabla, registro, descripcion):
    try:
        cursor.execute(
            """
            INSERT INTO BITACORA (
                Usuario, Accion, TablaAfectada, RegistroAfectado, Descripcion,
                FechaEvento, Estado, Usr, UsrFecha, UsrHora, FechaCreacion, FechaModificacion
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                date('now','localtime'), time('now','localtime'),
                datetime('now','localtime'), datetime('now','localtime')
            )
            """,
            (usr, accion, tabla, registro, descripcion, ahora_texto(), ESTADO_ACTIVO, usr),
        )
    except Exception:
        pass


# =========================================================
# TIPOS DE VEHÍCULO
# =========================================================
def ensure_tipo_vehiculo_table():
    """
    Repara el catálogo para que no aparezcan valores basura como 1, 2, auto, moto.
    El esquema correcto usa IDs:
    1 = Auto
    2 = Moto
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS TIPOVEHICULO (
                TipoVehiculo INTEGER PRIMARY KEY AUTOINCREMENT,
                Nombre TEXT NOT NULL UNIQUE,
                Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),
                Usr INTEGER NOT NULL DEFAULT 0,
                UsrFecha TEXT NOT NULL DEFAULT (date('now','localtime')),
                UsrHora TEXT NOT NULL DEFAULT (time('now','localtime')),
                FechaCreacion TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FechaModificacion TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # Si quedaron textos antiguos en TARIFA/VEHICULO, se convierten a IDs.
        for tabla in ("TARIFA", "VEHICULO"):
            try:
                cursor.execute(f"UPDATE {tabla} SET TipoVehiculo = 1 WHERE LOWER(TRIM(CAST(TipoVehiculo AS TEXT))) = 'auto'")
                cursor.execute(f"UPDATE {tabla} SET TipoVehiculo = 2 WHERE LOWER(TRIM(CAST(TipoVehiculo AS TEXT))) = 'moto'")
            except Exception:
                pass

        # Eliminar duplicados visibles creados por la versión anterior del módulo.
        cursor.execute("""
            DELETE FROM TIPOVEHICULO
            WHERE TipoVehiculo NOT IN (1, 2)
              AND LOWER(TRIM(CAST(Nombre AS TEXT))) IN ('auto', 'moto', '1', '2')
        """)

        # Si existieran Auto/Moto en otros IDs, se limpian antes para evitar UNIQUE.
        cursor.execute("""
            DELETE FROM TIPOVEHICULO
            WHERE TipoVehiculo NOT IN (1, 2)
              AND LOWER(TRIM(Nombre)) IN ('auto', 'moto')
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO TIPOVEHICULO (
                TipoVehiculo, Nombre, Estado, Usr, UsrFecha, UsrHora, FechaCreacion, FechaModificacion
            )
            VALUES (1, 'Auto', 1, 0, date('now','localtime'), time('now','localtime'), datetime('now','localtime'), datetime('now','localtime'))
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO TIPOVEHICULO (
                TipoVehiculo, Nombre, Estado, Usr, UsrFecha, UsrHora, FechaCreacion, FechaModificacion
            )
            VALUES (2, 'Moto', 1, 0, date('now','localtime'), time('now','localtime'), datetime('now','localtime'), datetime('now','localtime'))
        """)

        cursor.execute("""
            UPDATE TIPOVEHICULO
            SET Nombre = 'Auto', Estado = 1, FechaModificacion = datetime('now','localtime')
            WHERE TipoVehiculo = 1
        """)
        cursor.execute("""
            UPDATE TIPOVEHICULO
            SET Nombre = 'Moto', Estado = 1, FechaModificacion = datetime('now','localtime')
            WHERE TipoVehiculo = 2
        """)

        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_tipos_vehiculo(solo_activos=True):
    ensure_tipo_vehiculo_table()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql = """
            SELECT TipoVehiculo, Nombre
            FROM TIPOVEHICULO
            WHERE TRIM(Nombre) <> ''
              AND Nombre NOT GLOB '[0-9]*'
        """
        params = []
        if solo_activos:
            sql += " AND Estado = ?"
            params.append(ESTADO_ACTIVO)
        sql += " ORDER BY TipoVehiculo ASC"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        tipos = []
        for row in rows:
            tipo_id = int(row_get(row, "TipoVehiculo", 0, 0) or 0)
            nombre = normalizar_nombre_vehiculo(row_get(row, "Nombre", 1, ""))
            if tipo_id and nombre:
                tipos.append({"id": tipo_id, "nombre": nombre})

        if not tipos:
            tipos = [{"id": 1, "nombre": "Auto"}, {"id": 2, "nombre": "Moto"}]
        return tipos
    finally:
        conn.close()


def tipo_id_por_nombre(nombre):
    nombre = normalizar_nombre_vehiculo(nombre)
    for item in obtener_tipos_vehiculo(solo_activos=True):
        if item["nombre"].lower() == nombre.lower():
            return item["id"]
    return 1


def nombre_por_tipo_id(tipo_id):
    try:
        tipo_id = int(tipo_id)
    except Exception:
        return normalizar_nombre_vehiculo(tipo_id)
    for item in obtener_tipos_vehiculo(solo_activos=False):
        if item["id"] == tipo_id:
            return item["nombre"]
    return "Auto" if tipo_id == 1 else "Moto" if tipo_id == 2 else str(tipo_id)


# =========================================================
# VISTA PRINCIPAL
# =========================================================
class RatesView:
    def __init__(self, parent, user_data):
        self.parent = parent
        self.user_data = user_data or {}

        self.main_frame = None
        self.vehicle_var = tk.StringVar(value="Auto")
        self.status_filter_var = tk.StringVar(value="Activas")
        self.search_var = tk.StringVar(value="")

        self.vehicle_combo = None
        self.vehicle_map = {}
        self.search_entry = None

        self.hour_tree = None
        self.contract_tree = None
        self.night_tree = None

        self.btn_edit_hour = None
        self.btn_toggle_hour = None
        self.btn_edit_contract = None
        self.btn_toggle_contract = None
        self.btn_edit_night = None
        self.btn_toggle_night = None

    def build(self):
        configurar_treeview()
        ensure_tipo_vehiculo_table()

        self.main_frame = tk.Frame(self.parent, bg=COLOR_FONDO)
        self.main_frame.pack(fill="both", expand=True)

        if not usuario_es_admin(self.user_data):
            self.build_access_denied()
            return

        self.build_toolbar()
        self.build_sections()
        self.load_data()

    def build_access_denied(self):
        container = tk.Frame(self.main_frame, bg=COLOR_PANEL)
        container.pack(fill="both", expand=True, padx=15, pady=15)

        tk.Label(container, text="Acceso restringido", font=("Arial", 18, "bold"), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(pady=(80, 10))
        tk.Label(container, text="Solo el administrador puede gestionar tarifas.", font=("Arial", 11), bg=COLOR_PANEL, fg=COLOR_TEXTO_SUAVE).pack()

    def build_toolbar(self):
        toolbar = tk.Frame(self.main_frame, bg=COLOR_PANEL)
        toolbar.pack(fill="x", padx=15, pady=15)

        tk.Label(toolbar, text="Tipo de vehículo:", font=("Arial", 11, "bold"), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(side="left", padx=(0, 8))

        tipos = obtener_tipos_vehiculo(solo_activos=True)
        self.vehicle_map = {item["nombre"]: item["id"] for item in tipos}
        valores = list(self.vehicle_map.keys())
        if self.vehicle_var.get() not in valores:
            self.vehicle_var.set(valores[0] if valores else "Auto")

        self.vehicle_combo = ttk.Combobox(toolbar, textvariable=self.vehicle_var, values=valores, state="readonly", width=16)
        self.vehicle_combo.pack(side="left", padx=(0, 8))
        self.vehicle_combo.bind("<<ComboboxSelected>>", lambda _e: self.load_data())


        tk.Label(toolbar, text="Buscar:", font=("Arial", 11, "bold"), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(side="left", padx=(0, 8))
        self.search_entry = tk.Entry(toolbar, textvariable=self.search_var, font=("Arial", 10), width=22, relief="solid", bd=1)
        self.search_entry.pack(side="left", padx=(0, 8), ipady=3)
        self.search_entry.bind("<Return>", lambda _e: self.load_data())

        tk.Button(toolbar, text="Buscar", font=("Arial", 10, "bold"), bg=COLOR_BOTON, fg=COLOR_TEXTO,
                  activebackground=COLOR_BOTON_HOVER, activeforeground=COLOR_TEXTO, bd=0, relief="flat",
                  padx=12, pady=6, cursor="hand2", command=self.load_data).pack(side="left", padx=(0, 6))

        tk.Button(toolbar, text="Limpiar", font=("Arial", 10, "bold"), bg=COLOR_TABLA_CABECERA, fg=COLOR_TEXTO,
                  activebackground=COLOR_BORDE, activeforeground=COLOR_TEXTO, bd=0, relief="flat",
                  padx=12, pady=6, cursor="hand2", command=self.clear_search).pack(side="left", padx=(0, 18))

        tk.Label(toolbar, text="Estado:", font=("Arial", 11, "bold"), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(side="left", padx=(0, 8))
        state_combo = ttk.Combobox(toolbar, textvariable=self.status_filter_var, values=["Activas", "Inactivas", "Todas"], state="readonly", width=12)
        state_combo.pack(side="left", padx=(0, 10))
        state_combo.bind("<<ComboboxSelected>>", lambda _e: self.load_data())

    def build_sections(self):
        content = tk.Frame(self.main_frame, bg=COLOR_FONDO)
        content.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        self._build_hour_section(content).grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))
        self._build_contract_section(content).grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        self._build_night_section(content).grid(row=1, column=1, sticky="nsew")

    def _panel(self, parent):
        return tk.Frame(parent, bg=COLOR_PANEL, highlightbackground=COLOR_BORDE, highlightthickness=1, bd=0)

    def _build_hour_section(self, parent):
        panel = self._panel(parent)
        header = tk.Frame(panel, bg=COLOR_PANEL)
        header.pack(fill="x", padx=12, pady=(12, 10))
        tk.Label(header, text="Tarifa por hora", font=("Arial", 14, "bold"), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(side="left")

        self.btn_toggle_hour = tk.Button(header, text="Activar / Inactivar", font=("Arial", 10, "bold"), width=16,
                                         bg=COLOR_BOTON, fg=COLOR_TEXTO, bd=0, relief="flat", cursor="hand2", state="disabled",
                                         command=lambda: self.toggle_selected_detail(self.hour_tree, "hora"))
        self.btn_toggle_hour.pack(side="right")
        self.btn_edit_hour = tk.Button(header, text="Editar", font=("Arial", 10, "bold"), width=10,
                                       bg=COLOR_BOTON, fg=COLOR_TEXTO, bd=0, relief="flat", cursor="hand2", state="disabled",
                                       command=lambda: self.open_selected_detail_form(self.hour_tree, "hora"))
        self.btn_edit_hour.pack(side="right", padx=(0, 8))
        tk.Button(header, text="+ Nueva hora", font=("Arial", 10, "bold"), width=12,
                  bg=COLOR_BOTON, fg=COLOR_TEXTO, bd=0, relief="flat", cursor="hand2",
                  command=lambda: self.open_detail_form("hora")).pack(side="right", padx=(0, 8))

        table_wrap = tk.Frame(panel, bg=COLOR_PANEL)
        table_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        columns = ("Tarifa", "Rango", "Monto", "Estado")
        self.hour_tree = ttk.Treeview(table_wrap, columns=columns, show="headings", style="Tarifas.Treeview")
        self.hour_tree.pack(fill="both", expand=True, side="left")
        for col, text in zip(columns, columns):
            self.hour_tree.heading(col, text=text)
        self.hour_tree.column("Tarifa", width=240, anchor="w", stretch=True)
        self.hour_tree.column("Rango", width=130, anchor="center", stretch=False)
        self.hour_tree.column("Monto", width=110, anchor="e", stretch=False)
        self.hour_tree.column("Estado", width=90, anchor="center", stretch=False)
        yscroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.hour_tree.yview)
        yscroll.pack(side="right", fill="y")
        self.hour_tree.configure(yscrollcommand=yscroll.set)
        self.hour_tree.bind("<<TreeviewSelect>>", lambda _e: self.on_select_grid(self.hour_tree, self.contract_tree, self.night_tree))
        self.hour_tree.bind("<Double-1>", lambda _e: self.open_selected_detail_form(self.hour_tree, "hora"))
        return panel

    def _build_contract_section(self, parent):
        panel = self._panel(parent)
        header = tk.Frame(panel, bg=COLOR_PANEL)
        header.pack(fill="x", padx=12, pady=(12, 10))
        tk.Label(header, text="Tarifa contrato", font=("Arial", 14, "bold"), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(side="left")

        self.btn_toggle_contract = tk.Button(header, text="Activar / Inactivar", font=("Arial", 10, "bold"), width=16,
                                             bg=COLOR_BOTON, fg=COLOR_TEXTO, bd=0, relief="flat", cursor="hand2", state="disabled",
                                             command=lambda: self.toggle_selected_detail(self.contract_tree, "contrato"))
        self.btn_toggle_contract.pack(side="right")
        self.btn_edit_contract = tk.Button(header, text="Editar", font=("Arial", 10, "bold"), width=10,
                                           bg=COLOR_BOTON, fg=COLOR_TEXTO, bd=0, relief="flat", cursor="hand2", state="disabled",
                                           command=lambda: self.open_selected_detail_form(self.contract_tree, "contrato"))
        self.btn_edit_contract.pack(side="right", padx=(0, 8))
        tk.Button(header, text="+ Nueva contrato", font=("Arial", 10, "bold"), width=16,
                  bg=COLOR_BOTON, fg=COLOR_TEXTO, bd=0, relief="flat", cursor="hand2",
                  command=lambda: self.open_detail_form("contrato")).pack(side="right", padx=(0, 8))

        table_wrap = tk.Frame(panel, bg=COLOR_PANEL)
        table_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        columns = ("Tarifa", "Horas", "Monto", "Estado")
        self.contract_tree = ttk.Treeview(table_wrap, columns=columns, show="headings", style="Tarifas.Treeview", height=6)
        self.contract_tree.pack(fill="both", expand=True, side="left")
        self.contract_tree.heading("Tarifa", text="Tarifa")
        self.contract_tree.heading("Horas", text="Horas/día")
        self.contract_tree.heading("Monto", text="Monto mensual")
        self.contract_tree.heading("Estado", text="Estado")
        self.contract_tree.column("Tarifa", width=170, anchor="w", stretch=True)
        self.contract_tree.column("Horas", width=90, anchor="center", stretch=False)
        self.contract_tree.column("Monto", width=105, anchor="e", stretch=False)
        self.contract_tree.column("Estado", width=75, anchor="center", stretch=False)
        self.contract_tree.bind("<<TreeviewSelect>>", lambda _e: self.on_select_grid(self.contract_tree, self.hour_tree, self.night_tree))
        self.contract_tree.bind("<Double-1>", lambda _e: self.open_selected_detail_form(self.contract_tree, "contrato"))
        return panel

    def _build_night_section(self, parent):
        panel = self._panel(parent)
        header = tk.Frame(panel, bg=COLOR_PANEL)
        header.pack(fill="x", padx=12, pady=(12, 10))
        tk.Label(header, text="Tarifa nocturna", font=("Arial", 14, "bold"), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(side="left")

        self.btn_toggle_night = tk.Button(header, text="Activar / Inactivar", font=("Arial", 10, "bold"), width=16,
                                          bg=COLOR_BOTON, fg=COLOR_TEXTO, bd=0, relief="flat", cursor="hand2", state="disabled",
                                          command=lambda: self.toggle_selected_detail(self.night_tree, "nocturna"))
        self.btn_toggle_night.pack(side="right")
        self.btn_edit_night = tk.Button(header, text="Editar", font=("Arial", 10, "bold"), width=10,
                                        bg=COLOR_BOTON, fg=COLOR_TEXTO, bd=0, relief="flat", cursor="hand2", state="disabled",
                                        command=lambda: self.open_selected_detail_form(self.night_tree, "nocturna"))
        self.btn_edit_night.pack(side="right", padx=(0, 8))
        tk.Button(header, text="+ Nueva nocturna", font=("Arial", 10, "bold"), width=14,
                  bg=COLOR_BOTON, fg=COLOR_TEXTO, bd=0, relief="flat", cursor="hand2",
                  command=lambda: self.open_detail_form("nocturna")).pack(side="right", padx=(0, 8))

        table_wrap = tk.Frame(panel, bg=COLOR_PANEL)
        table_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        columns = ("Tarifa", "Horario", "Monto", "Estado")
        self.night_tree = ttk.Treeview(table_wrap, columns=columns, show="headings", style="Tarifas.Treeview")
        self.night_tree.pack(fill="both", expand=True, side="left")
        for col, text in zip(columns, columns):
            self.night_tree.heading(col, text=text)
        self.night_tree.column("Tarifa", width=210, anchor="w", stretch=True)
        self.night_tree.column("Horario", width=120, anchor="center", stretch=False)
        self.night_tree.column("Monto", width=95, anchor="e", stretch=False)
        self.night_tree.column("Estado", width=75, anchor="center", stretch=False)
        yscroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.night_tree.yview)
        yscroll.pack(side="right", fill="y")
        self.night_tree.configure(yscrollcommand=yscroll.set)
        self.night_tree.bind("<<TreeviewSelect>>", lambda _e: self.on_select_grid(self.night_tree, self.hour_tree, self.contract_tree))
        self.night_tree.bind("<Double-1>", lambda _e: self.open_selected_detail_form(self.night_tree, "nocturna"))
        return panel

    def clear_tree(self, tree):
        if tree:
            for item in tree.get_children():
                tree.delete(item)

    def refresh_vehicle_combo(self):
        tipos = obtener_tipos_vehiculo(solo_activos=True)
        self.vehicle_map = {item["nombre"]: item["id"] for item in tipos}
        valores = list(self.vehicle_map.keys())
        if self.vehicle_combo:
            self.vehicle_combo.configure(values=valores)
        if self.vehicle_var.get() not in valores:
            self.vehicle_var.set(valores[0] if valores else "Auto")

    def current_tipo_vehiculo_id(self):
        self.refresh_vehicle_combo()
        return self.vehicle_map.get(self.vehicle_var.get(), 1)

    def open_vehicle_admin(self):
        VehicleTypeAdminWindow(self).run()

    def clear_search(self):
        self.search_var.set("")
        self.load_data()

    def build_search_sql(self, params):
        texto = convertir_fecha_busqueda(self.search_var.get())
        if not texto:
            return ""
        filtro = f"%{texto}%"
        params.extend([filtro] * 14)
        return """
            AND (
                LOWER(COALESCE(T.Nombre, '')) LIKE LOWER(?)
                OR LOWER(COALESCE(T.Descripcion, '')) LIKE LOWER(?)
                OR LOWER(COALESCE(TV.Nombre, '')) LIKE LOWER(?)
                OR CAST(COALESCE(TD.MinutoInicio, '') AS TEXT) LIKE ?
                OR CAST(COALESCE(TD.MinutoFin, '') AS TEXT) LIKE ?
                OR CAST(COALESCE(TD.HorasPermitidasDia, '') AS TEXT) LIKE ?
                OR CAST(COALESCE(TD.Monto, '') AS TEXT) LIKE ?
                OR LOWER(COALESCE(TD.HoraInicio, '')) LIKE LOWER(?)
                OR LOWER(COALESCE(TD.HoraFin, '')) LIKE LOWER(?)
                OR LOWER(COALESCE(TD.Observacion, '')) LIKE LOWER(?)
                OR date(COALESCE(TD.FechaCreacion, '')) LIKE ?
                OR date(COALESCE(TD.FechaModificacion, '')) LIKE ?
                OR date(COALESCE(T.FechaCreacion, '')) LIKE ?
                OR date(COALESCE(T.FechaModificacion, '')) LIKE ?
            )
        """

    def _status_sql(self, params):
        status_filter = self.status_filter_var.get().strip()
        if status_filter == "Activas":
            params.extend([ESTADO_ACTIVO, ESTADO_ACTIVO])
            return " AND TD.Estado = ? AND T.Estado = ? "
        if status_filter == "Inactivas":
            params.append(ESTADO_INACTIVO)
            return " AND TD.Estado = ? "
        return ""

    def load_data(self):
        self.clear_tree(self.hour_tree)
        self.clear_tree(self.contract_tree)
        self.clear_tree(self.night_tree)
        tipo_vehiculo_id = self.current_tipo_vehiculo_id()

        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Tarifa por hora
            params = [tipo_vehiculo_id]
            status_sql = self._status_sql(params)
            search_sql = self.build_search_sql(params)
            cursor.execute(f"""
                SELECT TD.TarifaDetalle, T.Nombre, TD.MinutoInicio, TD.MinutoFin, TD.Monto, TD.Estado
                FROM TARIFADETALLE TD
                INNER JOIN TARIFA T ON T.Tarifa = TD.Tarifa
                INNER JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = T.TipoVehiculo
                WHERE T.TipoVehiculo = ?
                  AND T.TipoTarifa = {TIPO_TARIFA_HORA}
                  AND TD.TipoDia = {TIPO_DIA_HORA}
                  {status_sql}
                  {search_sql}
                ORDER BY TD.MinutoInicio ASC, TD.TarifaDetalle ASC
            """, params)
            for row in cursor.fetchall():
                self.hour_tree.insert("", "end", iid=str(row_get(row, "TarifaDetalle", 0)), values=(
                    row_get(row, "Nombre", 1),
                    f"{row_get(row, 'MinutoInicio', 2)} - {row_get(row, 'MinutoFin', 3)} min",
                    f"Bs {float(row_get(row, 'Monto', 4, 0) or 0):.2f}",
                    ESTADO_TEXTO.get(row_get(row, "Estado", 5), "N/D"),
                ))

            # Tarifa contrato
            params = [tipo_vehiculo_id]
            status_sql = self._status_sql(params)
            search_sql = self.build_search_sql(params)
            cursor.execute(f"""
                SELECT TD.TarifaDetalle, T.Nombre, TD.HorasPermitidasDia, TD.Monto, TD.Estado
                FROM TARIFADETALLE TD
                INNER JOIN TARIFA T ON T.Tarifa = TD.Tarifa
                INNER JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = T.TipoVehiculo
                WHERE T.TipoVehiculo = ?
                  AND T.TipoTarifa = {TIPO_TARIFA_CONTRATO}
                  AND TD.TipoDia = {TIPO_DIA_CONTRATO}
                  {status_sql}
                  {search_sql}
                ORDER BY TD.HorasPermitidasDia ASC, TD.TarifaDetalle ASC
            """, params)
            for row in cursor.fetchall():
                horas = int(row_get(row, "HorasPermitidasDia", 2, 0) or 0)
                self.contract_tree.insert("", "end", iid=str(row_get(row, "TarifaDetalle", 0)), values=(
                    row_get(row, "Nombre", 1),
                    f"{horas} h" if horas else "",
                    f"Bs {float(row_get(row, 'Monto', 3, 0) or 0):.2f}",
                    ESTADO_TEXTO.get(row_get(row, "Estado", 4), "N/D"),
                ))

            # Tarifa nocturna
            params = [tipo_vehiculo_id]
            status_sql = self._status_sql(params)
            search_sql = self.build_search_sql(params)
            cursor.execute(f"""
                SELECT TD.TarifaDetalle, T.Nombre, TD.HoraInicio, TD.HoraFin, TD.Monto, TD.Estado
                FROM TARIFADETALLE TD
                INNER JOIN TARIFA T ON T.Tarifa = TD.Tarifa
                INNER JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = T.TipoVehiculo
                WHERE T.TipoVehiculo = ?
                  AND T.TipoTarifa = {TIPO_TARIFA_NOCTURNA}
                  AND TD.TipoDia = {TIPO_DIA_NOCTURNA}
                  {status_sql}
                  {search_sql}
                ORDER BY TD.TarifaDetalle ASC
            """, params)
            for row in cursor.fetchall():
                horario = f"{row_get(row, 'HoraInicio', 2) or '20:00'} - {row_get(row, 'HoraFin', 3) or '08:00'}"
                self.night_tree.insert("", "end", iid=str(row_get(row, "TarifaDetalle", 0)), values=(
                    row_get(row, "Nombre", 1),
                    horario,
                    f"Bs {float(row_get(row, 'Monto', 4, 0) or 0):.2f}",
                    ESTADO_TEXTO.get(row_get(row, "Estado", 5), "N/D"),
                ))

            self.update_action_buttons()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar las tarifas.\n{str(e)}")
        finally:
            conn.close()

    def on_select_grid(self, active_tree, *other_trees):
        if active_tree and active_tree.selection():
            for other in other_trees:
                if other:
                    other.selection_remove(other.selection())
        self.update_action_buttons()

    def update_action_buttons(self):
        hour_state = "normal" if self.hour_tree and self.hour_tree.selection() else "disabled"
        contract_state = "normal" if self.contract_tree and self.contract_tree.selection() else "disabled"
        night_state = "normal" if self.night_tree and self.night_tree.selection() else "disabled"
        if self.btn_edit_hour: self.btn_edit_hour.config(state=hour_state)
        if self.btn_toggle_hour: self.btn_toggle_hour.config(state=hour_state)
        if self.btn_edit_contract: self.btn_edit_contract.config(state=contract_state)
        if self.btn_toggle_contract: self.btn_toggle_contract.config(state=contract_state)
        if self.btn_edit_night: self.btn_edit_night.config(state=night_state)
        if self.btn_toggle_night: self.btn_toggle_night.config(state=night_state)

    def get_selected_detail_id(self, tree):
        if not tree:
            return None
        selected = tree.selection()
        return selected[0] if selected else None

    def open_detail_form(self, section):
        RateDetailFormWindow(self, self.user_data, section=section).run()

    def open_selected_detail_form(self, tree, section):
        detail_id = self.get_selected_detail_id(tree)
        if not detail_id:
            messagebox.showwarning("Aviso", "Debe seleccionar una tarifa.")
            return
        RateDetailFormWindow(self, self.user_data, section=section, detail_id=detail_id).run()

    def toggle_selected_detail(self, tree, section):
        detail_id = self.get_selected_detail_id(tree)
        if not detail_id:
            messagebox.showwarning("Aviso", "Debe seleccionar una tarifa.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT Estado FROM TARIFADETALLE WHERE TarifaDetalle = ?", (detail_id,))
            row = cursor.fetchone()
            if not row:
                messagebox.showerror("Error", "No se encontró la tarifa seleccionada.")
                return
            current = int(row_get(row, "Estado", 0, ESTADO_ACTIVO))
            new_status = ESTADO_INACTIVO if current == ESTADO_ACTIVO else ESTADO_ACTIVO
            txt = ESTADO_TEXTO[new_status]
            if not messagebox.askyesno("Confirmar", f"¿Desea cambiar esta tarifa a '{txt}'?"):
                return
            usr = obtener_usuario_actual_id(self.user_data)
            cursor.execute("""
                UPDATE TARIFADETALLE
                SET Estado = ?, Usr = ?, UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'), FechaModificacion = datetime('now','localtime')
                WHERE TarifaDetalle = ?
            """, (new_status, usr, detail_id))
            insertar_bitacora(cursor, usr, "CAMBIAR_ESTADO_TARIFA_DETALLE", "TARIFADETALLE", detail_id,
                              f"Se cambió el estado del detalle {detail_id} a {txt} ({section})")
            conn.commit()
            messagebox.showinfo("Actualizado", "Estado actualizado correctamente.")
            self.load_data()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"No se pudo actualizar el estado.\n{str(e)}")
        finally:
            conn.close()

    def run(self):
        pass


# =========================================================
# MODAL: ADMINISTRAR TIPOS DE VEHÍCULO
# =========================================================
class VehicleTypeAdminWindow:
    def __init__(self, rates_view):
        self.rates_view = rates_view
        self.current_user = rates_view.user_data or {}
        self.window = tk.Toplevel(rates_view.parent)
        self.window.title("Tipos de vehículo")
        self.window.geometry("460x410")
        self.window.resizable(True, True)
        self.window.minsize(380, 320)
        self.window.configure(bg=COLOR_PANEL)
        self.window.grab_set()
        self.tree = None
        self.entry_name = None
        self.build_ui()
        self.load_data()

    def build_ui(self):
        tk.Label(self.window, text="Administrar tipos de vehículo", font=("Arial", 15, "bold"), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(anchor="w", padx=20, pady=(18, 12))
        input_frame = tk.Frame(self.window, bg=COLOR_PANEL)
        input_frame.pack(fill="x", padx=20, pady=(0, 12))
        tk.Label(input_frame, text="Nombre:", font=("Arial", 11, "bold"), bg=COLOR_PANEL).pack(side="left", padx=(0, 8))
        self.entry_name = tk.Entry(input_frame, font=("Arial", 11))
        self.entry_name.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(input_frame, text="Agregar", font=("Arial", 10, "bold"), bg=COLOR_BOTON, fg=COLOR_TEXTO,
                  bd=0, relief="flat", padx=12, pady=6, cursor="hand2", command=self.add_type).pack(side="left")

        table_frame = tk.Frame(self.window, bg=COLOR_PANEL)
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        columns = ("Nombre", "Estado")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="Tarifas.Treeview")
        self.tree.pack(fill="both", expand=True, side="left")
        self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("Estado", text="Estado")
        self.tree.column("Nombre", width=240, anchor="w", stretch=True)
        self.tree.column("Estado", width=90, anchor="center", stretch=False)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.fill_selected_name())

        buttons = tk.Frame(self.window, bg=COLOR_PANEL)
        buttons.pack(fill="x", padx=20, pady=(0, 18))
        tk.Button(buttons, text="Renombrar", font=("Arial", 10, "bold"), bg=COLOR_BOTON, fg=COLOR_TEXTO,
                  bd=0, relief="flat", padx=14, pady=7, cursor="hand2", command=self.rename_type).pack(side="left")
        tk.Button(buttons, text="Activar / Inactivar", font=("Arial", 10, "bold"), bg=COLOR_BOTON, fg=COLOR_TEXTO,
                  bd=0, relief="flat", padx=14, pady=7, cursor="hand2", command=self.toggle_type).pack(side="left", padx=(8, 0))
        tk.Button(buttons, text="Cerrar", font=("Arial", 10, "bold"), bg=COLOR_BOTON, fg=COLOR_TEXTO,
                  bd=0, relief="flat", padx=14, pady=7, cursor="hand2", command=self.close).pack(side="right")

    def load_data(self):
        ensure_tipo_vehiculo_table()
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT TipoVehiculo, Nombre, Estado
                FROM TIPOVEHICULO
                WHERE Nombre NOT GLOB '[0-9]*'
                ORDER BY Estado DESC, TipoVehiculo ASC
            """)
            for row in cursor.fetchall():
                self.tree.insert("", "end", iid=str(row_get(row, "TipoVehiculo", 0)), values=(
                    normalizar_nombre_vehiculo(row_get(row, "Nombre", 1)),
                    ESTADO_TEXTO.get(row_get(row, "Estado", 2), "N/D"),
                ))
        finally:
            conn.close()

    def get_selected(self):
        selected = self.tree.selection()
        if not selected:
            return None
        values = self.tree.item(selected[0], "values")
        if not values:
            return None
        return {"id": int(selected[0]), "nombre": values[0], "estado_texto": values[1]}

    def fill_selected_name(self):
        selected = self.get_selected()
        if selected:
            self.entry_name.delete(0, "end")
            self.entry_name.insert(0, selected["nombre"])

    def add_type(self):
        name = normalizar_nombre_vehiculo(self.entry_name.get())
        if not name or name.isdigit():
            messagebox.showwarning("Datos requeridos", "Debe ingresar un nombre válido.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        try:
            usr = obtener_usuario_actual_id(self.current_user)
            cursor.execute("""
                INSERT INTO TIPOVEHICULO (Nombre, Estado, Usr, UsrFecha, UsrHora, FechaCreacion, FechaModificacion)
                VALUES (?, ?, ?, date('now','localtime'), time('now','localtime'), datetime('now','localtime'), datetime('now','localtime'))
            """, (name, ESTADO_ACTIVO, usr))
            insertar_bitacora(cursor, usr, "CREAR_TIPO_VEHICULO", "TIPOVEHICULO", cursor.lastrowid, f"Se creó el tipo de vehículo {name}")
            conn.commit()
            self.entry_name.delete(0, "end")
            self.load_data()
            self.rates_view.refresh_vehicle_combo()
            self.rates_view.load_data()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"No se pudo agregar el tipo de vehículo.\n{str(e)}")
        finally:
            conn.close()

    def rename_type(self):
        selected = self.get_selected()
        if not selected:
            messagebox.showwarning("Aviso", "Debe seleccionar un tipo de vehículo.")
            return
        new_name = normalizar_nombre_vehiculo(self.entry_name.get())
        if not new_name or new_name.isdigit():
            messagebox.showwarning("Datos requeridos", "Debe ingresar un nombre válido.")
            return
        if selected["id"] in (1, 2) and new_name not in ("Auto", "Moto"):
            messagebox.showwarning("Aviso", "Auto y Moto son tipos base. No los renombres.")
            return
        if not messagebox.askyesno("Confirmar", f"¿Desea cambiar '{selected['nombre']}' por '{new_name}'?"):
            return
        conn = get_connection()
        cursor = conn.cursor()
        try:
            usr = obtener_usuario_actual_id(self.current_user)
            cursor.execute("""
                UPDATE TIPOVEHICULO
                SET Nombre = ?, Usr = ?, UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'), FechaModificacion = datetime('now','localtime')
                WHERE TipoVehiculo = ?
            """, (new_name, usr, selected["id"]))
            insertar_bitacora(cursor, usr, "RENOMBRAR_TIPO_VEHICULO", "TIPOVEHICULO", selected["id"], f"Se cambió {selected['nombre']} por {new_name}")
            conn.commit()
            self.entry_name.delete(0, "end")
            self.load_data()
            self.rates_view.refresh_vehicle_combo()
            self.rates_view.vehicle_var.set(new_name)
            self.rates_view.load_data()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"No se pudo renombrar el tipo de vehículo.\n{str(e)}")
        finally:
            conn.close()

    def toggle_type(self):
        selected = self.get_selected()
        if not selected:
            messagebox.showwarning("Aviso", "Debe seleccionar un tipo de vehículo.")
            return
        if selected["id"] in (1, 2):
            messagebox.showwarning("Aviso", "Auto y Moto son tipos base. No se pueden inactivar desde aquí.")
            return
        current = ESTADO_ACTIVO if selected["estado_texto"] == "Activa" else ESTADO_INACTIVO
        new_status = ESTADO_INACTIVO if current == ESTADO_ACTIVO else ESTADO_ACTIVO
        txt = ESTADO_TEXTO[new_status]
        if not messagebox.askyesno("Confirmar", f"¿Desea cambiar este tipo de vehículo a '{txt}'?"):
            return
        conn = get_connection()
        cursor = conn.cursor()
        try:
            usr = obtener_usuario_actual_id(self.current_user)
            cursor.execute("""
                UPDATE TIPOVEHICULO
                SET Estado = ?, Usr = ?, UsrFecha = date('now','localtime'),
                    UsrHora = time('now','localtime'), FechaModificacion = datetime('now','localtime')
                WHERE TipoVehiculo = ?
            """, (new_status, usr, selected["id"]))
            insertar_bitacora(cursor, usr, "CAMBIAR_ESTADO_TIPO_VEHICULO", "TIPOVEHICULO", selected["id"], f"Se cambió el estado a {txt}")
            conn.commit()
            self.load_data()
            self.rates_view.refresh_vehicle_combo()
            self.rates_view.load_data()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"No se pudo cambiar el estado.\n{str(e)}")
        finally:
            conn.close()

    def close(self):
        self.rates_view.refresh_vehicle_combo()
        self.rates_view.load_data()
        self.window.destroy()

    def run(self):
        pass


# =========================================================
# FORMULARIO TARIFA
# =========================================================
class RateDetailFormWindow:
    def __init__(self, rates_view, current_user, section="hora", detail_id=None):
        self.rates_view = rates_view
        self.current_user = current_user or {}
        self.section = section
        self.detail_id = detail_id
        self.form_vehicle_var = tk.StringVar(value=self.rates_view.vehicle_var.get())

        self.combo_vehicle = None
        self.entry_inicio = None
        self.entry_fin = None
        self.entry_horas = None
        self.entry_monto = None
        self.entry_hora_inicio = None
        self.entry_hora_fin = None

        self.window = tk.Toplevel(rates_view.parent)
        self.window.title("Nueva tarifa" if detail_id is None else "Editar tarifa")

        if self.section == "nocturna":
            ancho, alto = 520, 560
        elif self.section == "contrato":
            ancho, alto = 520, 430
        else:
            ancho, alto = 520, 500

        centrar_ventana(self.window, ancho, alto)
        self.window.resizable(True, True)
        self.window.minsize(450, 400)
        self.window.configure(bg=COLOR_PANEL)
        self.window.grab_set()

        self.build_ui()
        if self.detail_id is not None:
            self.load_detail_data()
        else:
            self.set_defaults()

    def get_title(self):
        if self.section == "hora":
            return "Nueva tarifa por hora" if self.detail_id is None else "Editar tarifa por hora"
        if self.section == "contrato":
            return "Nueva tarifa de contrato" if self.detail_id is None else "Editar tarifa de contrato"
        return "Nueva tarifa nocturna" if self.detail_id is None else "Editar tarifa nocturna"

    def build_ui(self):
        tk.Label(
            self.window,
            text=self.get_title(),
            font=("Arial", 16, "bold"),
            bg=COLOR_PANEL,
            fg=COLOR_TEXTO,
        ).pack(pady=(22, 18))

        form = tk.Frame(self.window, bg=COLOR_PANEL)
        form.pack(fill="x", padx=38)

        tk.Label(form, text="Tipo de vehículo *", font=("Arial", 11, "bold"), bg=COLOR_PANEL).pack(anchor="w", pady=(0, 5))
        tipos = [item["nombre"] for item in obtener_tipos_vehiculo(solo_activos=True)]
        self.combo_vehicle = ttk.Combobox(form, textvariable=self.form_vehicle_var, values=tipos, state="readonly", font=("Arial", 11))
        self.combo_vehicle.pack(fill="x", pady=(0, 12), ipady=2)
        if self.form_vehicle_var.get() not in tipos and tipos:
            self.form_vehicle_var.set(tipos[0])

        if self.section == "contrato":
            tk.Label(form, text="Horas permitidas por día *", font=("Arial", 11, "bold"), bg=COLOR_PANEL).pack(anchor="w", pady=(0, 5))
            self.entry_horas = ttk.Combobox(form, values=["3", "6", "9", "12", "24"], state="readonly", font=("Arial", 11))
            self.entry_horas.pack(fill="x", pady=(0, 12), ipady=2)
        else:
            tk.Label(form, text="Minuto inicio *", font=("Arial", 11, "bold"), bg=COLOR_PANEL).pack(anchor="w", pady=(0, 5))
            self.entry_inicio = tk.Entry(form, font=("Arial", 11), relief="solid", bd=1)
            self.entry_inicio.pack(fill="x", pady=(0, 12), ipady=4)
            tk.Label(form, text="Minuto fin *", font=("Arial", 11, "bold"), bg=COLOR_PANEL).pack(anchor="w", pady=(0, 5))
            self.entry_fin = tk.Entry(form, font=("Arial", 11), relief="solid", bd=1)
            self.entry_fin.pack(fill="x", pady=(0, 12), ipady=4)

        tk.Label(form, text="Monto (Bs) *", font=("Arial", 11, "bold"), bg=COLOR_PANEL).pack(anchor="w", pady=(0, 5))
        self.entry_monto = tk.Entry(form, font=("Arial", 11), relief="solid", bd=1)
        self.entry_monto.pack(fill="x", pady=(0, 12), ipady=4)

        if self.section == "nocturna":
            horas_disponibles = generar_horas_combo(30)

            tk.Label(form, text="Hora inicio *", font=("Arial", 11, "bold"), bg=COLOR_PANEL).pack(anchor="w", pady=(0, 5))
            self.entry_hora_inicio = ttk.Combobox(
                form,
                values=horas_disponibles,
                state="readonly",
                font=("Arial", 11),
            )
            self.entry_hora_inicio.pack(fill="x", pady=(0, 12), ipady=2)

            tk.Label(form, text="Hora fin *", font=("Arial", 11, "bold"), bg=COLOR_PANEL).pack(anchor="w", pady=(0, 5))
            self.entry_hora_fin = ttk.Combobox(
                form,
                values=horas_disponibles,
                state="readonly",
                font=("Arial", 11),
            )
            self.entry_hora_fin.pack(fill="x", pady=(0, 12), ipady=2)

        buttons = tk.Frame(self.window, bg=COLOR_PANEL)
        buttons.pack(pady=(12, 20))
        tk.Button(buttons, text="Guardar", font=("Arial", 11, "bold"), bg=COLOR_BOTON, fg=COLOR_TEXTO,
                  bd=0, relief="flat", padx=18, pady=8, cursor="hand2", command=self.confirm_save).grid(row=0, column=0, padx=10)
        tk.Button(buttons, text="Cancelar", font=("Arial", 11, "bold"), bg=COLOR_BOTON, fg=COLOR_TEXTO,
                  bd=0, relief="flat", padx=18, pady=8, cursor="hand2", command=self.window.destroy).grid(row=0, column=1, padx=10)

    def set_defaults(self):
        if self.section == "hora":
            self.entry_inicio.insert(0, "1")
            self.entry_fin.insert(0, "30")
        elif self.section == "contrato":
            self.form_vehicle_var.set("Auto")
            self.entry_horas.set("3")
        else:
            self.entry_inicio.insert(0, "1")
            self.entry_fin.insert(0, "720")
            self.entry_hora_inicio.set("20:00")
            self.entry_hora_fin.set("08:00")

    def load_detail_data(self):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT TD.TarifaDetalle, TD.Tarifa, TD.TipoDia, TD.MinutoInicio, TD.MinutoFin,
                       TD.HorasPermitidasDia, TD.Monto, TD.HoraInicio, TD.HoraFin,
                       T.TipoVehiculo, TV.Nombre AS TipoVehiculoNombre, T.TipoTarifa
                FROM TARIFADETALLE TD
                INNER JOIN TARIFA T ON T.Tarifa = TD.Tarifa
                INNER JOIN TIPOVEHICULO TV ON TV.TipoVehiculo = T.TipoVehiculo
                WHERE TD.TarifaDetalle = ?
            """, (self.detail_id,))
            row = cursor.fetchone()
            if not row:
                messagebox.showerror("Error", "No se encontró la tarifa.")
                self.window.destroy()
                return

            self.form_vehicle_var.set(normalizar_nombre_vehiculo(row_get(row, "TipoVehiculoNombre", 10)))
            tipo_tarifa = int(row_get(row, "TipoTarifa", 11, TIPO_TARIFA_HORA))
            if tipo_tarifa == TIPO_TARIFA_CONTRATO and self.entry_horas:
                self.entry_horas.set(str(row_get(row, "HorasPermitidasDia", 5, "")))
            elif self.entry_inicio and self.entry_fin:
                self.entry_inicio.delete(0, "end")
                self.entry_inicio.insert(0, str(row_get(row, "MinutoInicio", 3, "")))
                self.entry_fin.delete(0, "end")
                self.entry_fin.insert(0, str(row_get(row, "MinutoFin", 4, "")))

            self.entry_monto.delete(0, "end")
            self.entry_monto.insert(0, f"{float(row_get(row, 'Monto', 6, 0) or 0):.2f}")

            if self.section == "nocturna" and self.entry_hora_inicio and self.entry_hora_fin:
                self.entry_hora_inicio.set(row_get(row, "HoraInicio", 7, "") or "20:00")
                self.entry_hora_fin.set(row_get(row, "HoraFin", 8, "") or "08:00")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la tarifa.\n{str(e)}")
            self.window.destroy()
        finally:
            conn.close()

    def get_tarifa_tipo(self):
        if self.section == "contrato":
            return TIPO_TARIFA_CONTRATO, TIPO_DIA_CONTRATO
        if self.section == "nocturna":
            return TIPO_TARIFA_NOCTURNA, TIPO_DIA_NOCTURNA
        return TIPO_TARIFA_HORA, TIPO_DIA_HORA

    def get_or_create_tarifa(self, cursor, tipo_vehiculo_id):
        tipo_tarifa, _tipo_dia = self.get_tarifa_tipo()
        cursor.execute("""
            SELECT Tarifa
            FROM TARIFA
            WHERE TipoVehiculo = ? AND TipoTarifa = ?
            ORDER BY Estado DESC, Tarifa ASC
            LIMIT 1
        """, (tipo_vehiculo_id, tipo_tarifa))
        row = cursor.fetchone()
        if row:
            return row_get(row, "Tarifa", 0)

        usr = obtener_usuario_actual_id(self.current_user)
        nombre_vehiculo = nombre_por_tipo_id(tipo_vehiculo_id)
        if tipo_tarifa == TIPO_TARIFA_CONTRATO:
            nombre = f"Tarifa Contrato {nombre_vehiculo}"
            descripcion = f"Tarifa de contrato mensual para {nombre_vehiculo.lower()}"
        elif tipo_tarifa == TIPO_TARIFA_NOCTURNA:
            nombre = f"Tarifa Nocturna {nombre_vehiculo}"
            descripcion = f"Tarifa nocturna para {nombre_vehiculo.lower()}"
        else:
            nombre = f"Tarifa por Hora {nombre_vehiculo}"
            descripcion = f"Tarifa por hora para {nombre_vehiculo.lower()}"

        cursor.execute("""
            INSERT INTO TARIFA (Nombre, TipoVehiculo, TipoTarifa, Descripcion, Estado, Usr, UsrFecha, UsrHora, FechaCreacion, FechaModificacion)
            VALUES (?, ?, ?, ?, ?, ?, date('now','localtime'), time('now','localtime'), datetime('now','localtime'), datetime('now','localtime'))
        """, (nombre, tipo_vehiculo_id, tipo_tarifa, descripcion, ESTADO_ACTIVO, usr))
        return cursor.lastrowid

    def existe_duplicado(self, cursor, tarifa_id, tipo_dia, inicio, fin, horas):
        if tipo_dia == TIPO_DIA_CONTRATO:
            sql = """
                SELECT COUNT(*) AS Cantidad
                FROM TARIFADETALLE
                WHERE Tarifa = ? AND TipoDia = ? AND HorasPermitidasDia = ?
            """
            params = [tarifa_id, tipo_dia, horas]
        else:
            sql = """
                SELECT COUNT(*) AS Cantidad
                FROM TARIFADETALLE
                WHERE Tarifa = ? AND TipoDia = ? AND MinutoInicio = ? AND MinutoFin = ?
            """
            params = [tarifa_id, tipo_dia, inicio, fin]

        if self.detail_id is not None:
            sql += " AND TarifaDetalle <> ?"
            params.append(self.detail_id)
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return int(row_get(row, "Cantidad", 0, 0) or 0) > 0

    def confirm_save(self):
        if messagebox.askyesno("Confirmar", "¿Desea guardar esta tarifa?"):
            self.save()

    def save(self):
        tipo_vehiculo_id = tipo_id_por_nombre(self.form_vehicle_var.get())
        monto_txt = self.entry_monto.get().strip().replace(",", ".")
        if not monto_txt:
            messagebox.showwarning("Datos requeridos", "El monto es obligatorio.")
            return
        try:
            monto = float(monto_txt)
        except ValueError:
            messagebox.showwarning("Datos inválidos", "El monto debe ser numérico.")
            return
        if monto < 0:
            messagebox.showwarning("Datos inválidos", "El monto no puede ser negativo.")
            return

        inicio = None
        fin = None
        horas = None
        hora_inicio = None
        hora_fin = None

        if self.section == "contrato":
            try:
                horas = int(self.entry_horas.get().strip())
            except ValueError:
                messagebox.showwarning("Datos inválidos", "Las horas permitidas deben ser un número entero.")
                return
            if horas not in (3, 6, 9, 12, 24):
                messagebox.showwarning("Validación", "Las horas permitidas deben ser 3, 6, 9, 12 o 24.")
                return
            # Según lo definido, contrato solo aplica para Auto.
            if tipo_vehiculo_id != 1:
                messagebox.showwarning("Validación", "Las tarifas de contrato solo aplican para Auto.")
                return
        else:
            try:
                inicio = int(self.entry_inicio.get().strip())
                fin = int(self.entry_fin.get().strip())
            except ValueError:
                messagebox.showwarning("Datos inválidos", "Inicio y fin deben ser enteros.")
                return
            if inicio <= 0 or fin < inicio:
                messagebox.showwarning("Datos inválidos", "Verifica el rango ingresado.")
                return

            if self.section == "nocturna":
                hora_inicio = self.entry_hora_inicio.get().strip()
                hora_fin = self.entry_hora_fin.get().strip()
                if not validar_hora_hhmm(hora_inicio) or not validar_hora_hhmm(hora_fin):
                    messagebox.showwarning("Datos inválidos", "Las horas deben tener formato HH:MM.")
                    return
                if hora_inicio != "20:00" or hora_fin != "08:00":
                    messagebox.showwarning("Validación", "La tarifa nocturna debe ir desde 20:00 hasta 08:00.")
                    return

        tipo_tarifa, tipo_dia = self.get_tarifa_tipo()
        usr = obtener_usuario_actual_id(self.current_user)
        conn = get_connection()
        cursor = conn.cursor()
        try:
            tarifa_id = self.get_or_create_tarifa(cursor, tipo_vehiculo_id)
            if self.existe_duplicado(cursor, tarifa_id, tipo_dia, inicio, fin, horas):
                messagebox.showwarning("Validación", "Ya existe una tarifa con esos datos para este vehículo.")
                return

            if self.section == "contrato":
                obs = "Tarifa contrato"
            elif self.section == "nocturna":
                obs = "Tarifa nocturna"
            else:
                obs = "Tarifa por hora"

            if self.detail_id is None:
                cursor.execute("""
                    INSERT INTO TARIFADETALLE (
                        Tarifa, TipoDia, MinutoInicio, MinutoFin, HorasPermitidasDia, Monto,
                        HoraInicio, HoraFin, Observacion, Estado, Usr, UsrFecha, UsrHora, FechaCreacion, FechaModificacion
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, date('now','localtime'), time('now','localtime'), datetime('now','localtime'), datetime('now','localtime'))
                """, (tarifa_id, tipo_dia, inicio, fin, horas, monto, hora_inicio, hora_fin, obs, ESTADO_ACTIVO, usr))
                detail_id = cursor.lastrowid
                insertar_bitacora(cursor, usr, "CREAR_TARIFA_DETALLE", "TARIFADETALLE", detail_id, f"Se creó el detalle {detail_id}")
            else:
                cursor.execute("""
                    UPDATE TARIFADETALLE
                    SET Tarifa = ?, TipoDia = ?, MinutoInicio = ?, MinutoFin = ?, HorasPermitidasDia = ?, Monto = ?,
                        HoraInicio = ?, HoraFin = ?, Observacion = ?, Usr = ?, UsrFecha = date('now','localtime'),
                        UsrHora = time('now','localtime'), FechaModificacion = datetime('now','localtime')
                    WHERE TarifaDetalle = ?
                """, (tarifa_id, tipo_dia, inicio, fin, horas, monto, hora_inicio, hora_fin, obs, usr, self.detail_id))
                insertar_bitacora(cursor, usr, "EDITAR_TARIFA_DETALLE", "TARIFADETALLE", self.detail_id, f"Se editó el detalle {self.detail_id}")

            conn.commit()
            self.rates_view.vehicle_var.set(nombre_por_tipo_id(tipo_vehiculo_id))
            self.rates_view.refresh_vehicle_combo()
            self.rates_view.load_data()
            messagebox.showinfo("Guardado", "Tarifa guardada correctamente.")
            self.window.destroy()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"No se pudo guardar la tarifa.\n{str(e)}")
        finally:
            conn.close()

    def run(self):
        pass
