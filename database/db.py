import os
import sqlite3
import sys


APP_FOLDER = "GarageData"
DB_NAME = "garage.db"


def get_base_dir():
    """
    Devuelve la carpeta base de la aplicación.

    - En desarrollo: raíz del proyecto
    - En ejecutable (.exe): carpeta donde está el ejecutable
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_app_path():
    """
    Devuelve la carpeta donde se guardarán los datos de la app.
    Si no existe, la crea.
    """
    app_path = os.path.join(get_base_dir(), APP_FOLDER)
    os.makedirs(app_path, exist_ok=True)
    return app_path


def get_db_path():
    """
    Devuelve la ruta completa del archivo de base de datos.
    """
    return os.path.join(get_app_path(), DB_NAME)


def get_connection():
    """
    Crea y devuelve una conexión a SQLite.
    Activa soporte para foreign keys y permite acceder
    a las columnas por nombre.
    """
    db_path = get_db_path()

    conn = sqlite3.connect(db_path, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row

    return conn