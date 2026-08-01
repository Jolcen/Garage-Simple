# =========================================================
# FUNCIONES COMUNES COMPARTIDAS
# =========================================================
# Funciones utilitarias que se usan en múltiples módulos.
# Centralizadas aquí para evitar duplicación de código.
# =========================================================

import tkinter as tk
from datetime import datetime


def centrar_ventana(window, width, height, parent=None):
    """Centra una ventana en la pantalla o相对于 su padre."""
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


def row_get(row, key, default=None):
    """Obtiene un valor de un row de SQLite de forma segura."""
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
    """Obtiene el ID del usuario desde user_data."""
    user_data = user_data or {}
    return user_data.get("Usuario") or user_data.get("id") or 0


def formatear_fecha(fecha_texto):
    """Formatea una fecha de YYYY-MM-DD HH:MM:SS a DD/MM/YYYY HH:MM."""
    if not fecha_texto:
        return ""
    try:
        return datetime.strptime(fecha_texto, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except Exception:
        return fecha_texto


def limpiar_placa_para_busqueda(placa):
    """Limpia una placa para búsquedas (sin espacios, sin guiones, mayúsculas)."""
    return (placa or "").replace(" ", "").replace("-", "").upper().strip()


def nombre_cliente_completo(nombres, apellidos):
    """Combina nombres y apellidos en un solo string."""
    nombres = (nombres or "").strip()
    apellidos = (apellidos or "").strip()
    return f"{nombres} {apellidos}".strip()


def texto_o_vacio(valor):
    """Retorna string vacío si el valor es None."""
    return valor if valor is not None else ""


def datetime_now_text():
    """Retorna la fecha y hora actual en formato YYYY-MM-DD HH:MM:SS."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
