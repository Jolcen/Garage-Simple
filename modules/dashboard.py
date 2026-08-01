import tkinter as tk
from tkinter import messagebox

from modules.operations import OperationsView
from modules.vehicles_customers import VehiclesCustomersView
from modules.rates import RatesView
from modules.services import ServicesView
from modules.reports import ReportsView
from modules.users import UsersView
from modules.audit_log import AuditLogView
from modules.contracts import ContractsView
from modules.configuration import ConfigurationView


class DashboardWindow:
    def __init__(self, user_data):
        self.user_data = user_data or {}

        self.root = tk.Tk()
        self.root.title("Sistema de Garaje")
        self.root.geometry("1366x768")
        self.root.minsize(1200, 700)
        self.root.configure(bg="#f3f4f6")

        try:
            self.root.state("zoomed")
        except Exception:
            pass

        self.content_frame = None
        self.title_label = None
        self.sidebar_buttons = {}

        self.build_ui()
        self.show_module("Operaciones")

        self.root.protocol("WM_DELETE_WINDOW", self.confirm_exit)

    # =====================================================
    # USUARIO / ROL
    # =====================================================
    def get_user_name(self):
        return (
            self.user_data.get("nombre")
            or self.user_data.get("Nombre")
            or self.user_data.get("NombreUsuario")
            or self.user_data.get("usuario")
            or "Usuario"
        )

    def get_user_role_text(self):
        rol = (
            self.user_data.get("rol")
            or self.user_data.get("Rol")
            or self.user_data.get("role")
            or self.user_data.get("Role")
            or "empleado"
        )

        if isinstance(rol, int):
            return "admin" if rol == 1 else "empleado"

        rol_texto = str(rol).strip().lower()
        if rol_texto in ("1", "admin", "administrador"):
            return "admin"
        return "empleado"

    def is_admin(self):
        return self.get_user_role_text() == "admin"

    # =====================================================
    # UI PRINCIPAL
    # =====================================================
    def build_ui(self):
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self.build_topbar()
        self.build_sidebar()
        self.build_content_area()

    def build_topbar(self):
        topbar = tk.Frame(self.root, bg="#1f2937", height=55)
        topbar.grid(row=0, column=0, columnspan=2, sticky="nsew")
        topbar.grid_propagate(False)

        title = tk.Label(
            topbar,
            text="Sistema de Garaje",
            bg="#1f2937",
            fg="white",
            font=("Arial", 16, "bold")
        )
        title.pack(side="left", padx=20)

        user_info = tk.Label(
            topbar,
            text=f"{self.get_user_name()} | Rol: {self.get_user_role_text()}",
            bg="#1f2937",
            fg="white",
            font=("Arial", 11)
        )
        user_info.pack(side="right", padx=20)

    def build_sidebar(self):
        sidebar = tk.Frame(self.root, bg="#111827", width=220)
        sidebar.grid(row=1, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        menu_title = tk.Label(
            sidebar,
            text="MENÚ",
            bg="#111827",
            fg="white",
            font=("Arial", 13, "bold")
        )
        menu_title.pack(pady=(20, 15))

        # Módulos visibles para empleado y admin.
        buttons = [
            ("Operaciones", lambda: self.show_module("Operaciones")),
            ("Vehículos / Clientes", lambda: self.show_module("Vehículos / Clientes")),
            ("Contratos", lambda: self.show_module("Contratos")),
        ]

        # Módulos solo para administrador.
        if self.is_admin():
            buttons.extend([
                ("Reportes", lambda: self.show_module("Reportes")),
                ("Tarifas", lambda: self.show_module("Tarifas")),
                ("Servicios", lambda: self.show_module("Servicios")),
                ("Configuración", lambda: self.show_module("Configuración")),
                ("Usuarios", lambda: self.show_module("Usuarios")),
                ("Bitácora", lambda: self.show_module("Bitácora")),
            ])

        for text, command in buttons:
            btn = tk.Button(
                sidebar,
                text=text,
                command=command,
                bg="#1f2937",
                fg="white",
                activebackground="#2563eb",
                activeforeground="white",
                font=("Arial", 11),
                bd=0,
                relief="flat",
                width=22,
                height=2,
                cursor="hand2"
            )
            btn.pack(pady=5)
            self.sidebar_buttons[text] = btn

        logout_btn = tk.Button(
            sidebar,
            text="Cerrar sesión",
            command=self.logout,
            bg="#b91c1c",
            fg="white",
            activebackground="#991b1b",
            activeforeground="white",
            font=("Arial", 11, "bold"),
            bd=0,
            relief="flat",
            width=22,
            height=2,
            cursor="hand2"
        )
        logout_btn.pack(side="bottom", pady=20)

    def build_content_area(self):
        container = tk.Frame(self.root, bg="#f3f4f6")
        container.grid(row=1, column=1, sticky="nsew")
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)

        header = tk.Frame(container, bg="#e5e7eb", height=50)
        header.grid(row=0, column=0, sticky="nsew")
        header.grid_propagate(False)

        self.title_label = tk.Label(
            header,
            text="",
            bg="#e5e7eb",
            fg="#111827",
            font=("Arial", 14, "bold")
        )
        self.title_label.pack(side="left", padx=20, pady=10)

        self.content_frame = tk.Frame(container, bg="white")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)

        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

    # =====================================================
    # NAVEGACIÓN
    # =====================================================
    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def update_active_button(self, module_name):
        for name, button in self.sidebar_buttons.items():
            if name == module_name:
                button.configure(bg="#2563eb")
            else:
                button.configure(bg="#1f2937")

    def show_module(self, module_name):
        # Seguridad: empleado no puede abrir módulos administrativos aunque se llame manualmente.
        admin_modules = {
            "Reportes",
            "Tarifas",
            "Servicios",
            "Configuración",
            "Usuarios",
            "Bitácora",
        }

        if module_name in admin_modules and not self.is_admin():
            messagebox.showwarning(
                "Acceso denegado",
                "Este módulo solo está disponible para el administrador."
            )
            return

        self.clear_content()
        self.title_label.config(text=module_name)
        self.update_active_button(module_name)

        if module_name == "Operaciones":
            view = OperationsView(self.content_frame, self.user_data)
        elif module_name == "Vehículos / Clientes":
            view = VehiclesCustomersView(self.content_frame, self.user_data)
        elif module_name == "Contratos":
            view = ContractsView(self.content_frame, self.user_data)
        elif module_name == "Tarifas":
            view = RatesView(self.content_frame, self.user_data)
        elif module_name == "Servicios":
            view = ServicesView(self.content_frame, self.user_data)
        elif module_name == "Reportes":
            view = ReportsView(self.content_frame)
        elif module_name == "Configuración":
            view = ConfigurationView(self.content_frame, self.user_data)
        elif module_name == "Usuarios":
            view = UsersView(self.content_frame, self.user_data)
        elif module_name == "Bitácora":
            view = AuditLogView(self.content_frame, self.user_data)
        else:
            return

        if hasattr(view, "build"):
            view.build()
        else:
            view.pack(fill="both", expand=True)

    # =====================================================
    # SESIÓN / SALIDA
    # =====================================================
    def logout(self):
        confirm = messagebox.askyesno("Cerrar sesión", "¿Desea cerrar sesión?")
        if not confirm:
            return

        self.root.destroy()

        from modules.login import LoginWindow
        login = LoginWindow()
        login.run()

    def confirm_exit(self):
        confirm = messagebox.askyesno("Salir", "¿Desea cerrar el sistema?")
        if confirm:
            self.root.destroy()

    def run(self):
        self.root.mainloop()
