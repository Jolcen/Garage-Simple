from database.schema import initialize_database
from database.db import get_db_path
from modules.login import LoginWindow


def main():
    try:
        print("Iniciando sistema de garaje...")
        print(f"Ruta de la base de datos: {get_db_path()}")

        initialize_database()

        print("Base de datos creada/verificada correctamente.")
        print("Abriendo ventana de inicio de sesión...")

        app = LoginWindow()
        app.run()

    except Exception as e:
        print("Ocurrió un error al iniciar el sistema:")
        print(str(e))


if __name__ == "__main__":
    main()