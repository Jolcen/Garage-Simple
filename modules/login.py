import os
import tkinter as tk
from tkinter import messagebox

from database.db import get_connection
from modules.dashboard import DashboardWindow


ROLES_USUARIO = {
    1: "admin",
    2: "empleado",
}


class LoginWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Inicio de Sesión")
        self.root.geometry("460x500")
        self.root.resizable(False, False)
        self.root.configure(bg="#facc15")

        self.entry_usuario = None
        self.entry_password = None
        self.show_password_var = tk.BooleanVar(value=False)
        self.logo_image = None

        self.build_ui()
        self.center_window()

    def get_logo_path(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "static", "logo.png")

    def center_window(self):
        self.root.update_idletasks()
        width = 460
        height = 500
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))

        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def build_ui(self):
        top_frame = tk.Frame(self.root, bg="#facc15")
        top_frame.pack(pady=(0, 0))

        logo_path = self.get_logo_path()
        if os.path.exists(logo_path):
            try:
                self.logo_image = tk.PhotoImage(file=logo_path)
                self.logo_image = self.logo_image.subsample(6, 6)

                logo_label = tk.Label(
                    top_frame,
                    image=self.logo_image,
                    bg="#facc15"
                )
                logo_label.pack(pady=(0, 2))
            except Exception:
                fallback_logo = tk.Label(
                    top_frame,
                    text="CAR PARK",
                    font=("Arial", 20, "bold"),
                    bg="#facc15",
                    fg="#1e3a8a"
                )
                fallback_logo.pack(pady=(0, 2))
        else:
            fallback_logo = tk.Label(
                top_frame,
                text="CAR PARK",
                font=("Arial", 20, "bold"),
                bg="#facc15",
                fg="#1e3a8a"
            )
            fallback_logo.pack(pady=(0, 2))

        title_label = tk.Label(
            self.root,
            text="Sistema Carpark",
            font=("Arial", 18, "bold"),
            bg="#facc15",
            fg="#111827"
        )
        title_label.pack(pady=(0, 2))

        subtitle_label = tk.Label(
            self.root,
            text="Iniciar sesión",
            font=("Arial", 11),
            bg="#facc15",
            fg="#374151"
        )
        subtitle_label.pack(pady=(0, 6))

        card = tk.Frame(
            self.root,
            bg="white",
            bd=1,
            relief="solid",
            padx=20,
            pady=20
        )
        card.pack(padx=25, fill="x")

        usuario_label = tk.Label(
            card,
            text="Usuario *",
            font=("Arial", 11, "bold"),
            bg="white",
            fg="#111827"
        )
        usuario_label.pack(anchor="w", pady=(0, 5))

        self.entry_usuario = tk.Entry(card, font=("Arial", 11))
        self.entry_usuario.pack(fill="x", pady=(0, 12))
        self.entry_usuario.focus_set()

        password_label = tk.Label(
            card,
            text="Contraseña *",
            font=("Arial", 11, "bold"),
            bg="white",
            fg="#111827"
        )
        password_label.pack(anchor="w", pady=(0, 5))

        password_frame = tk.Frame(card, bg="white")
        password_frame.pack(fill="x", pady=(0, 10))

        self.entry_password = tk.Entry(password_frame, font=("Arial", 11), show="*")
        self.entry_password.pack(side="left", fill="x", expand=True)

        toggle_button = tk.Checkbutton(
            password_frame,
            text="Mostrar",
            variable=self.show_password_var,
            onvalue=True,
            offvalue=False,
            command=self.toggle_password_visibility,
            bg="white",
            activebackground="white",
            font=("Arial", 10)
        )
        toggle_button.pack(side="left", padx=(10, 0))

        helper_label = tk.Label(
            card,
            text="Ingrese sus credenciales para acceder al sistema.",
            font=("Arial", 9),
            bg="white",
            fg="#6b7280"
        )
        helper_label.pack(anchor="w", pady=(2, 0))

        buttons_frame = tk.Frame(self.root, bg="#facc15")
        buttons_frame.pack(pady=18)

        login_button = tk.Button(
            buttons_frame,
            text="Ingresar",
            font=("Arial", 11, "bold"),
            width=15,
            bg="#1e3a8a",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            bd=0,
            relief="flat",
            cursor="hand2",
            command=self.login
        )
        login_button.grid(row=0, column=0, padx=8)

        exit_button = tk.Button(
            buttons_frame,
            text="Salir",
            font=("Arial", 11, "bold"),
            width=15,
            bg="#dc2626",
            fg="white",
            activebackground="#b91c1c",
            activeforeground="white",
            bd=0,
            relief="flat",
            cursor="hand2",
            command=self.confirm_exit
        )
        exit_button.grid(row=0, column=1, padx=8)

        self.entry_usuario.bind("<Return>", lambda event: self.login())
        self.entry_password.bind("<Return>", lambda event: self.login())

        self.root.protocol("WM_DELETE_WINDOW", self.confirm_exit)

    def toggle_password_visibility(self):
        if self.show_password_var.get():
            self.entry_password.config(show="")
        else:
            self.entry_password.config(show="*")

    def authenticate_user(self, nombre_usuario, password):
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    Usuario,
                    Nombre,
                    NombreUsuario,
                    Password,
                    Rol,
                    Estado
                FROM USUARIO
                WHERE NombreUsuario = ?
            """, (nombre_usuario,))

            user = cursor.fetchone()

            if not user:
                return None

            if user["Password"] != password:
                return None

            if user["Estado"] != 1:
                return "inactive"

            rol_texto = ROLES_USUARIO.get(user["Rol"], "empleado")

            cursor.execute("""
                UPDATE USUARIO
                SET
                    UltimoAcceso = datetime('now', 'localtime'),
                    Usr = ?,
                    UsrFecha = date('now', 'localtime'),
                    UsrHora = time('now', 'localtime'),
                    FechaModificacion = datetime('now', 'localtime')
                WHERE Usuario = ?
            """, (user["Usuario"], user["Usuario"]))

            conn.commit()

            return {
                "id": user["Usuario"],
                "Usuario": user["Usuario"],
                "nombre": user["Nombre"],
                "usuario": user["NombreUsuario"],
                "rol": rol_texto,
                "rol_id": user["Rol"],
                "estado": user["Estado"],
            }

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo validar el acceso.\n{str(e)}")
            return "db_error"

        finally:
            if conn:
                conn.close()

    def login(self):
        nombre_usuario = self.entry_usuario.get().strip()
        password = self.entry_password.get().strip()

        if not nombre_usuario or not password:
            messagebox.showwarning("Campos requeridos", "Ingrese usuario y contraseña.")
            return

        result = self.authenticate_user(nombre_usuario, password)

        if result == "db_error":
            return

        if result is None:
            self.entry_password.delete(0, tk.END)
            messagebox.showerror("Acceso denegado", "Usuario o contraseña incorrectos.")
            return

        if result == "inactive":
            self.entry_password.delete(0, tk.END)
            messagebox.showwarning("Usuario inactivo", "Este usuario está inactivo.")
            return

        messagebox.showinfo("Acceso correcto", f"Bienvenido, {result['nombre']}.")
        self.root.destroy()

        dashboard = DashboardWindow(result)
        dashboard.run()

    def confirm_exit(self):
        confirmed = messagebox.askyesno(
            "Confirmar salida",
            "¿Desea cerrar el sistema?"
        )
        if confirmed:
            self.root.destroy()

    def run(self):
        self.root.mainloop()