from database.db import get_connection


# =========================================================
# CATÁLOGOS / ESTADOS
# =========================================================
# Estado general:
# 0 = Inactivo
# 1 = Activo
#
# USUARIO.Rol:
# 1 = Admin
# 2 = Empleado
#
# TIPOVEHICULO:
# 1 = Auto
# 2 = Moto
#
# TARIFA.TipoTarifa:
# 1 = Por hora / escalonada
# 2 = Nocturna
# 3 = Contrato
#
# TARIFADETALLE.TipoDia:
# 1 = LunesAViernes
# 2 = Sabado
# 3 = Nocturna
# 4 = Contrato
#
# TARIFADETALLE.HorasPermitidasDia:
# Usado para contratos estándar:
# 3h, 6h, 9h, 12h, 24h.
#
# PAGO.MetodoPago:
# 1 = Efectivo
# 2 = QR
#
# CONTRATO.Estado:
# 0 = Inactivo
# 1 = Activo
# 2 = Vencido
# 3 = Suspendido
#
# CONTRATO.EstadoPago:
# 0 = Pendiente
# 1 = Pagado
#
# CONTRATO.ClaseContrato:
# 1 = Estándar
# 2 = Especial
#
# OPERACION.Estado:
# 1 = Activo
# 2 = Finalizado
# 3 = Cancelado
#
# OPERACION.TipoOperacion:
# 1 = Normal
# 2 = Contrato
#
# OPERACIONSERVICIO.Estado:
# 1 = Pendiente
# 2 = EnProceso
# 3 = Realizado
# 4 = Cancelado


# =========================================================
# CONSTANTES
# =========================================================
ESTADO_INACTIVO = 0
ESTADO_ACTIVO = 1

ROL_ADMIN = 1
ROL_EMPLEADO = 2

TIPO_VEHICULO_AUTO = 1
TIPO_VEHICULO_MOTO = 2

TIPO_TARIFA_HORA = 1
TIPO_TARIFA_NOCTURNA = 2
TIPO_TARIFA_CONTRATO = 3

TIPO_DIA_LUNES_VIERNES = 1
TIPO_DIA_SABADO = 2
TIPO_DIA_NOCTURNA = 3
TIPO_DIA_CONTRATO = 4

METODO_PAGO_EFECTIVO = 1
METODO_PAGO_QR = 2

CLASE_CONTRATO_ESTANDAR = 1
CLASE_CONTRATO_ESPECIAL = 2

ESTADO_PAGO_PENDIENTE = 0
ESTADO_PAGO_PAGADO = 1

# Configuración general
CONFIG_MULTA_TICKET_PERDIDO = "MULTA_TICKET_PERDIDO"
VALOR_DEFAULT_MULTA_TICKET_PERDIDO = 50.00


# =========================================================
# HELPERS SQL FECHA
# =========================================================
def _fecha_actual_sql():
    return "date('now', 'localtime')"


def _hora_actual_sql():
    return "time('now', 'localtime')"


def _fecha_hora_actual_sql():
    return "datetime('now', 'localtime')"


# =========================================================
# HELPERS MIGRACIÓN / VALIDACIÓN
# =========================================================
def _table_exists(cursor, table_name):
    cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone()[0] > 0


def _index_exists(cursor, index_name):
    cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name = ?",
        (index_name,),
    )
    return cursor.fetchone()[0] > 0


def _column_exists(cursor, table_name, column_name):
    if not _table_exists(cursor, table_name):
        return False

    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def _column_type(cursor, table_name, column_name):
    if not _table_exists(cursor, table_name):
        return ""

    cursor.execute(f"PRAGMA table_info({table_name})")
    for row in cursor.fetchall():
        if row[1] == column_name:
            return str(row[2] or "").upper()

    return ""


def _column_notnull(cursor, table_name, column_name):
    if not _table_exists(cursor, table_name):
        return False

    cursor.execute(f"PRAGMA table_info({table_name})")
    for row in cursor.fetchall():
        if row[1] == column_name:
            return bool(row[3])

    return False


def _add_column_if_not_exists(cursor, table_name, column_definition):
    column_name = column_definition.split()[0]

    if not _column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")


def _drop_index_if_exists(cursor, index_name):
    if _index_exists(cursor, index_name):
        cursor.execute(f"DROP INDEX IF EXISTS {index_name}")


def _needs_operational_rebuild(cursor):
    """
    Detecta esquemas antiguos incompatibles con los módulos actuales.

    Importante:
    - Si la BD ya tenía datos reales, respalda garage.db antes de ejecutar.
    - Para esta etapa del proyecto conviene reconstruir tablas operativas cuando
      hay tipos viejos TEXT, campos faltantes o checks antiguos.
    """
    if not _table_exists(cursor, "TIPOVEHICULO"):
        return True

    if _table_exists(cursor, "VEHICULO"):
        tipo_vehiculo_type = _column_type(cursor, "VEHICULO", "TipoVehiculo")
        if "INT" not in tipo_vehiculo_type:
            return True

    if _table_exists(cursor, "TARIFA"):
        tarifa_tipo_vehiculo_type = _column_type(cursor, "TARIFA", "TipoVehiculo")
        if "INT" not in tarifa_tipo_vehiculo_type:
            return True

    if _table_exists(cursor, "TARIFADETALLE"):
        if not _column_exists(cursor, "TARIFADETALLE", "HorasPermitidasDia"):
            return True

    if _table_exists(cursor, "CONTRATO"):
        if not _table_exists(cursor, "CONTRATOVEHICULO"):
            return True
        if _column_notnull(cursor, "CONTRATO", "ModalidadPago"):
            return True
        for col in ("ClaseContrato", "EstadoPago", "MetodoPago", "FechaPago", "MontoPagado", "UsuarioPago", "HorasPermitidasDia"):
            if not _column_exists(cursor, "CONTRATO", col):
                return True

    if _table_exists(cursor, "PAGO"):
        if not _column_exists(cursor, "PAGO", "Contrato"):
            return True
        if _column_notnull(cursor, "PAGO", "Operacion"):
            return True

    return False


def _rebuild_operational_tables(cursor):
    """
    Reconstruye únicamente la parte operativa que cambió por:
    - TIPOVEHICULO
    - contratos con varios vehículos
    - pagos por operación o por contrato
    - tarifas de contrato por horas permitidas

    Se conservan USUARIO, CLIENTE, SERVICIO y BITACORA si existen.
    """
    cursor.execute("PRAGMA foreign_keys = OFF")

    tablas = [
        "PAGO",
        "OPERACIONSERVICIO",
        "OPERACION",
        "CONTRATOVEHICULO",
        "CONTRATO",
        "VEHICULO",
        "TARIFADETALLE",
        "TARIFA",
        "TIPOVEHICULO",
    ]

    for tabla in tablas:
        cursor.execute(f"DROP TABLE IF EXISTS {tabla}")

    cursor.execute("PRAGMA foreign_keys = ON")


# =========================================================
# CREATE TABLES
# =========================================================
def _create_configuracion(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS CONFIGURACION (
            Configuracion INTEGER PRIMARY KEY AUTOINCREMENT,
            Clave TEXT NOT NULL UNIQUE,
            Valor TEXT NOT NULL,
            Descripcion TEXT,
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()})
        )
    """)


def obtener_configuracion(clave, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if not _table_exists(cursor, "CONFIGURACION"):
            return default

        cursor.execute("""
            SELECT Valor
            FROM CONFIGURACION
            WHERE Clave = ?
              AND Estado = 1
            LIMIT 1
        """, (clave,))
        row = cursor.fetchone()
        if not row:
            return default
        return row[0]
    except Exception:
        return default
    finally:
        conn.close()


def obtener_configuracion_float(clave, default=0.0):
    try:
        valor = obtener_configuracion(clave, default)
        return float(str(valor).replace(",", "."))
    except Exception:
        return float(default or 0)


def obtener_multa_ticket_perdido(default=VALOR_DEFAULT_MULTA_TICKET_PERDIDO):
    return obtener_configuracion_float(CONFIG_MULTA_TICKET_PERDIDO, default)


def actualizar_configuracion(clave, valor, descripcion=None, usr=0):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        _create_configuracion(cursor)
        cursor.execute("""
            INSERT INTO CONFIGURACION (
                Clave,
                Valor,
                Descripcion,
                Estado,
                Usr,
                UsrFecha,
                UsrHora,
                FechaCreacion,
                FechaModificacion
            )
            VALUES (
                ?, ?, ?, 1, ?,
                date('now','localtime'),
                time('now','localtime'),
                datetime('now','localtime'),
                datetime('now','localtime')
            )
            ON CONFLICT(Clave) DO UPDATE SET
                Valor = excluded.Valor,
                Descripcion = COALESCE(excluded.Descripcion, CONFIGURACION.Descripcion),
                Estado = 1,
                Usr = excluded.Usr,
                UsrFecha = date('now','localtime'),
                UsrHora = time('now','localtime'),
                FechaModificacion = datetime('now','localtime')
        """, (clave, str(valor), descripcion, usr))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _create_usuario(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS USUARIO (
            Usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            Nombre TEXT NOT NULL,
            NombreUsuario TEXT NOT NULL UNIQUE,
            Password TEXT NOT NULL,
            Rol INTEGER NOT NULL CHECK (Rol IN (1, 2)),
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),
            UltimoAcceso TEXT,

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()})
        )
    """)


def _create_cliente(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS CLIENTE (
            Cliente INTEGER PRIMARY KEY AUTOINCREMENT,
            Nombres TEXT NOT NULL,
            Apellidos TEXT,
            DocumentoIdentidad TEXT,
            ComplementoDocumento TEXT,
            Telefono TEXT,
            TelefonoReferencia TEXT,
            Direccion TEXT,
            CorreoElectronico TEXT,
            Observacion TEXT,
            TipoCliente TEXT NOT NULL DEFAULT 'GENERAL' CHECK (TipoCliente IN ('GENERAL', 'ESTUDIANTE')),
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()})
        )
    """)

    _add_column_if_not_exists(cursor, "CLIENTE", "TipoCliente TEXT NOT NULL DEFAULT 'GENERAL' CHECK (TipoCliente IN ('GENERAL', 'ESTUDIANTE'))")


def _create_tipo_vehiculo(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS TIPOVEHICULO (
            TipoVehiculo INTEGER PRIMARY KEY AUTOINCREMENT,
            Nombre TEXT NOT NULL UNIQUE,
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()})
        )
    """)


def _create_vehiculo(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS VEHICULO (
            Vehiculo INTEGER PRIMARY KEY AUTOINCREMENT,
            Cliente INTEGER,
            Placa TEXT NOT NULL UNIQUE,
            TipoVehiculo INTEGER NOT NULL,
            Marca TEXT,
            Modelo TEXT,
            Color TEXT,
            Anio INTEGER,
            NumeroChasis TEXT,
            NumeroMotor TEXT,
            Observacion TEXT,
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),

            FOREIGN KEY (Cliente) REFERENCES CLIENTE(Cliente)
                ON UPDATE CASCADE
                ON DELETE SET NULL,

            FOREIGN KEY (TipoVehiculo) REFERENCES TIPOVEHICULO(TipoVehiculo)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
        )
    """)


def _create_tarifa(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS TARIFA (
            Tarifa INTEGER PRIMARY KEY AUTOINCREMENT,
            Nombre TEXT NOT NULL,
            TipoVehiculo INTEGER NOT NULL,
            TipoTarifa INTEGER NOT NULL CHECK (TipoTarifa IN (1, 2, 3)),
            Descripcion TEXT,
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),

            FOREIGN KEY (TipoVehiculo) REFERENCES TIPOVEHICULO(TipoVehiculo)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
        )
    """)


def _create_tarifa_detalle(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS TARIFADETALLE (
            TarifaDetalle INTEGER PRIMARY KEY AUTOINCREMENT,
            Tarifa INTEGER NOT NULL,
            TipoDia INTEGER NOT NULL CHECK (TipoDia IN (1, 2, 3, 4)),
            MinutoInicio INTEGER NOT NULL CHECK (MinutoInicio >= 0),
            MinutoFin INTEGER NOT NULL CHECK (MinutoFin >= MinutoInicio),
            Monto REAL NOT NULL CHECK (Monto >= 0),
            HorasPermitidasDia INTEGER,
            HoraInicio TEXT,
            HoraFin TEXT,
            Observacion TEXT,
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),

            FOREIGN KEY (Tarifa) REFERENCES TARIFA(Tarifa)
                ON UPDATE CASCADE
                ON DELETE CASCADE,

            CHECK (
                HorasPermitidasDia IS NULL
                OR HorasPermitidasDia IN (3, 6, 9, 12, 24)
            )
        )
    """)


def _create_servicio(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS SERVICIO (
            Servicio INTEGER PRIMARY KEY AUTOINCREMENT,
            Nombre TEXT NOT NULL UNIQUE,
            Descripcion TEXT,
            Precio REAL NOT NULL CHECK (Precio >= 0),
            DuracionEstimada INTEGER CHECK (DuracionEstimada IS NULL OR DuracionEstimada >= 0),
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()})
        )
    """)


def _create_contrato(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS CONTRATO (
            Contrato INTEGER PRIMARY KEY AUTOINCREMENT,
            Cliente INTEGER NOT NULL,
            Vehiculo INTEGER NOT NULL,
            CodigoContrato TEXT NOT NULL UNIQUE,
            FechaInicio TEXT NOT NULL,
            FechaFin TEXT NOT NULL,
            DuracionMes INTEGER CHECK (DuracionMes IS NULL OR DuracionMes > 0),
            MontoContrato REAL NOT NULL CHECK (MontoContrato >= 0),

            ModalidadPago INTEGER CHECK (
                ModalidadPago IS NULL OR ModalidadPago IN (1, 2)
            ),

            MetodoPago INTEGER CHECK (
                MetodoPago IS NULL OR MetodoPago IN (1, 2)
            ),

            EstadoPago INTEGER NOT NULL DEFAULT 0 CHECK (EstadoPago IN (0, 1)),
            FechaPago TEXT,
            MontoPagado REAL NOT NULL DEFAULT 0 CHECK (MontoPagado >= 0),
            UsuarioPago INTEGER,

            ClaseContrato INTEGER NOT NULL DEFAULT 1 CHECK (ClaseContrato IN (1, 2)),
            TarifaDetalle INTEGER,
            HorasPermitidasDia INTEGER,

            EspacioAsignado TEXT,
            Observacion TEXT,
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1, 2, 3)),

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),

            FOREIGN KEY (Cliente) REFERENCES CLIENTE(Cliente)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            FOREIGN KEY (Vehiculo) REFERENCES VEHICULO(Vehiculo)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            FOREIGN KEY (TarifaDetalle) REFERENCES TARIFADETALLE(TarifaDetalle)
                ON UPDATE CASCADE
                ON DELETE SET NULL,

            FOREIGN KEY (UsuarioPago) REFERENCES USUARIO(Usuario)
                ON UPDATE CASCADE
                ON DELETE SET NULL,

            CHECK (
                HorasPermitidasDia IS NULL
                OR HorasPermitidasDia IN (3, 6, 9, 12, 24)
            )
        )
    """)


def _create_contrato_vehiculo(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS CONTRATOVEHICULO (
            ContratoVehiculo INTEGER PRIMARY KEY AUTOINCREMENT,
            Contrato INTEGER NOT NULL,
            Vehiculo INTEGER NOT NULL,
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),

            FOREIGN KEY (Contrato) REFERENCES CONTRATO(Contrato)
                ON UPDATE CASCADE
                ON DELETE CASCADE,

            FOREIGN KEY (Vehiculo) REFERENCES VEHICULO(Vehiculo)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            UNIQUE (Contrato, Vehiculo)
        )
    """)


def _create_operacion(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS OPERACION (
            Operacion INTEGER PRIMARY KEY AUTOINCREMENT,
            CodigoOperacion TEXT NOT NULL UNIQUE,
            Vehiculo INTEGER NOT NULL,
            Cliente INTEGER,
            Tarifa INTEGER NOT NULL,
            Contrato INTEGER,
            UsuarioIngreso INTEGER NOT NULL,
            UsuarioSalida INTEGER,

            FechaIngreso TEXT NOT NULL,
            FechaSalida TEXT,

            TipoOperacion INTEGER NOT NULL DEFAULT 1 CHECK (TipoOperacion IN (1, 2)),
            MinutosEstadia INTEGER NOT NULL DEFAULT 0 CHECK (MinutosEstadia >= 0),
            MontoParqueo REAL NOT NULL DEFAULT 0 CHECK (MontoParqueo >= 0),
            MontoServicios REAL NOT NULL DEFAULT 0 CHECK (MontoServicios >= 0),
            TicketPerdido INTEGER NOT NULL DEFAULT 0 CHECK (TicketPerdido IN (0, 1)),
            MontoMultaTicket REAL NOT NULL DEFAULT 0 CHECK (MontoMultaTicket >= 0),
            MontoTotal REAL NOT NULL DEFAULT 0 CHECK (MontoTotal >= 0),

            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (1, 2, 3)),
            CodigoRetiro TEXT,
            Observacion TEXT,
            MotivoCancelacion TEXT,

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),

            FOREIGN KEY (Vehiculo) REFERENCES VEHICULO(Vehiculo)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            FOREIGN KEY (Cliente) REFERENCES CLIENTE(Cliente)
                ON UPDATE CASCADE
                ON DELETE SET NULL,

            FOREIGN KEY (Tarifa) REFERENCES TARIFA(Tarifa)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            FOREIGN KEY (Contrato) REFERENCES CONTRATO(Contrato)
                ON UPDATE CASCADE
                ON DELETE SET NULL,

            FOREIGN KEY (UsuarioIngreso) REFERENCES USUARIO(Usuario)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            FOREIGN KEY (UsuarioSalida) REFERENCES USUARIO(Usuario)
                ON UPDATE CASCADE
                ON DELETE SET NULL
        )
    """)



    _add_column_if_not_exists(cursor, "OPERACION", "TicketPerdido INTEGER NOT NULL DEFAULT 0 CHECK (TicketPerdido IN (0, 1))")
    _add_column_if_not_exists(cursor, "OPERACION", "MontoMultaTicket REAL NOT NULL DEFAULT 0 CHECK (MontoMultaTicket >= 0)")

def _create_operacion_servicio(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS OPERACIONSERVICIO (
            OperacionServicio INTEGER PRIMARY KEY AUTOINCREMENT,
            Operacion INTEGER NOT NULL,
            Servicio INTEGER NOT NULL,
            Cantidad INTEGER NOT NULL DEFAULT 1 CHECK (Cantidad > 0),
            PrecioUnitario REAL NOT NULL CHECK (PrecioUnitario >= 0),
            Subtotal REAL NOT NULL CHECK (Subtotal >= 0),
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (1, 2, 3, 4)),
            Observacion TEXT,

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),

            FOREIGN KEY (Operacion) REFERENCES OPERACION(Operacion)
                ON UPDATE CASCADE
                ON DELETE CASCADE,

            FOREIGN KEY (Servicio) REFERENCES SERVICIO(Servicio)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
        )
    """)


def _create_pago(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS PAGO (
            Pago INTEGER PRIMARY KEY AUTOINCREMENT,
            Operacion INTEGER,
            Contrato INTEGER,
            Usuario INTEGER NOT NULL,
            FechaPago TEXT NOT NULL,
            MetodoPago INTEGER NOT NULL CHECK (MetodoPago IN (1, 2)),
            Monto REAL NOT NULL CHECK (Monto >= 0),
            Observacion TEXT,
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),

            FOREIGN KEY (Operacion) REFERENCES OPERACION(Operacion)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            FOREIGN KEY (Contrato) REFERENCES CONTRATO(Contrato)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            FOREIGN KEY (Usuario) REFERENCES USUARIO(Usuario)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            CHECK (
                Operacion IS NOT NULL
                OR Contrato IS NOT NULL
            )
        )
    """)


def _create_bitacora(cursor):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS BITACORA (
            Bitacora INTEGER PRIMARY KEY AUTOINCREMENT,
            Usuario INTEGER,
            Accion TEXT NOT NULL,
            TablaAfectada TEXT,
            RegistroAfectado INTEGER,
            Descripcion TEXT,
            FechaEvento TEXT NOT NULL,
            Estado INTEGER NOT NULL DEFAULT 1 CHECK (Estado IN (0, 1)),

            Usr INTEGER NOT NULL DEFAULT 0,
            UsrFecha TEXT NOT NULL DEFAULT ({_fecha_actual_sql()}),
            UsrHora TEXT NOT NULL DEFAULT ({_hora_actual_sql()}),
            FechaCreacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),
            FechaModificacion TEXT NOT NULL DEFAULT ({_fecha_hora_actual_sql()}),

            FOREIGN KEY (Usuario) REFERENCES USUARIO(Usuario)
                ON UPDATE CASCADE
                ON DELETE SET NULL
        )
    """)


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    if _needs_operational_rebuild(cursor):
        _rebuild_operational_tables(cursor)

    _create_configuracion(cursor)
    _create_usuario(cursor)
    _create_cliente(cursor)
    _create_tipo_vehiculo(cursor)
    _create_vehiculo(cursor)
    _create_tarifa(cursor)
    _create_tarifa_detalle(cursor)
    _create_servicio(cursor)
    _create_contrato(cursor)
    _create_contrato_vehiculo(cursor)
    _create_operacion(cursor)
    _create_operacion_servicio(cursor)
    _create_pago(cursor)
    _create_bitacora(cursor)

    _crear_indices(cursor)

    conn.commit()
    conn.close()


# =========================================================
# ÍNDICES
# =========================================================
def _crear_indices(cursor):
    cursor.executescript("""
    CREATE INDEX IF NOT EXISTS IDX_CONFIGURACION_Clave
        ON CONFIGURACION(Clave);

    CREATE INDEX IF NOT EXISTS IDX_CONFIGURACION_Estado
        ON CONFIGURACION(Estado);

    CREATE INDEX IF NOT EXISTS IDX_USUARIO_NombreUsuario
        ON USUARIO(NombreUsuario);

    CREATE INDEX IF NOT EXISTS IDX_CLIENTE_DocumentoIdentidad
        ON CLIENTE(DocumentoIdentidad);

    CREATE INDEX IF NOT EXISTS IDX_CLIENTE_TipoCliente
        ON CLIENTE(TipoCliente);

    CREATE INDEX IF NOT EXISTS IDX_TIPOVEHICULO_Nombre
        ON TIPOVEHICULO(Nombre);

    CREATE INDEX IF NOT EXISTS IDX_VEHICULO_Placa
        ON VEHICULO(Placa);

    CREATE INDEX IF NOT EXISTS IDX_VEHICULO_Cliente
        ON VEHICULO(Cliente);

    CREATE INDEX IF NOT EXISTS IDX_VEHICULO_TipoVehiculo
        ON VEHICULO(TipoVehiculo);

    CREATE INDEX IF NOT EXISTS IDX_TARIFA_TipoVehiculo
        ON TARIFA(TipoVehiculo);

    CREATE INDEX IF NOT EXISTS IDX_TARIFA_TipoTarifa
        ON TARIFA(TipoTarifa);

    CREATE INDEX IF NOT EXISTS IDX_TARIFADETALLE_Tarifa
        ON TARIFADETALLE(Tarifa);

    CREATE INDEX IF NOT EXISTS IDX_TARIFADETALLE_TipoDia
        ON TARIFADETALLE(TipoDia);

    CREATE INDEX IF NOT EXISTS IDX_TARIFADETALLE_HorasPermitidasDia
        ON TARIFADETALLE(HorasPermitidasDia);

    CREATE INDEX IF NOT EXISTS IDX_CONTRATO_Cliente
        ON CONTRATO(Cliente);

    CREATE INDEX IF NOT EXISTS IDX_CONTRATO_Vehiculo
        ON CONTRATO(Vehiculo);

    CREATE INDEX IF NOT EXISTS IDX_CONTRATO_FechaInicio
        ON CONTRATO(FechaInicio);

    CREATE INDEX IF NOT EXISTS IDX_CONTRATO_FechaFin
        ON CONTRATO(FechaFin);

    CREATE INDEX IF NOT EXISTS IDX_CONTRATO_EstadoPago
        ON CONTRATO(EstadoPago);

    CREATE INDEX IF NOT EXISTS IDX_CONTRATO_ClaseContrato
        ON CONTRATO(ClaseContrato);

    CREATE INDEX IF NOT EXISTS IDX_CONTRATOVEHICULO_Contrato
        ON CONTRATOVEHICULO(Contrato);

    CREATE INDEX IF NOT EXISTS IDX_CONTRATOVEHICULO_Vehiculo
        ON CONTRATOVEHICULO(Vehiculo);

    CREATE UNIQUE INDEX IF NOT EXISTS IDX_CONTRATOVEHICULO_Contrato_Vehiculo
        ON CONTRATOVEHICULO(Contrato, Vehiculo);

    CREATE UNIQUE INDEX IF NOT EXISTS IDX_CONTRATOVEHICULO_Vehiculo_Activo
        ON CONTRATOVEHICULO(Vehiculo)
        WHERE Estado = 1;

    CREATE INDEX IF NOT EXISTS IDX_OPERACION_Estado
        ON OPERACION(Estado);

    CREATE INDEX IF NOT EXISTS IDX_OPERACION_FechaIngreso
        ON OPERACION(FechaIngreso);

    CREATE INDEX IF NOT EXISTS IDX_OPERACION_FechaSalida
        ON OPERACION(FechaSalida);

    CREATE INDEX IF NOT EXISTS IDX_OPERACION_CodigoRetiro
        ON OPERACION(CodigoRetiro);

    CREATE INDEX IF NOT EXISTS IDX_OPERACION_Vehiculo
        ON OPERACION(Vehiculo);

    CREATE INDEX IF NOT EXISTS IDX_OPERACION_Cliente
        ON OPERACION(Cliente);

    CREATE INDEX IF NOT EXISTS IDX_OPERACION_Contrato
        ON OPERACION(Contrato);

    CREATE INDEX IF NOT EXISTS IDX_OPERACION_TicketPerdido
        ON OPERACION(TicketPerdido);

    CREATE INDEX IF NOT EXISTS IDX_OPERACIONSERVICIO_Operacion
        ON OPERACIONSERVICIO(Operacion);

    CREATE INDEX IF NOT EXISTS IDX_OPERACIONSERVICIO_Servicio
        ON OPERACIONSERVICIO(Servicio);

    CREATE INDEX IF NOT EXISTS IDX_PAGO_Operacion
        ON PAGO(Operacion);

    CREATE INDEX IF NOT EXISTS IDX_PAGO_Contrato
        ON PAGO(Contrato);

    CREATE INDEX IF NOT EXISTS IDX_PAGO_Usuario
        ON PAGO(Usuario);

    CREATE INDEX IF NOT EXISTS IDX_PAGO_FechaPago
        ON PAGO(FechaPago);

    CREATE INDEX IF NOT EXISTS IDX_BITACORA_Usuario
        ON BITACORA(Usuario);

    CREATE UNIQUE INDEX IF NOT EXISTS IDX_TARIFADETALLE_Rango
        ON TARIFADETALLE(Tarifa, TipoDia, MinutoInicio, MinutoFin);
    """)


# =========================================================
# INSERTS SEGUROS
# =========================================================
def _ensure_configuracion(cursor, clave, valor, descripcion=None, usr=0):
    cursor.execute("""
        INSERT INTO CONFIGURACION (
            Clave,
            Valor,
            Descripcion,
            Estado,
            Usr,
            UsrFecha,
            UsrHora,
            FechaCreacion,
            FechaModificacion
        )
        VALUES (
            ?, ?, ?, 1, ?,
            date('now','localtime'),
            time('now','localtime'),
            datetime('now','localtime'),
            datetime('now','localtime')
        )
        ON CONFLICT(Clave) DO UPDATE SET
            Descripcion = COALESCE(CONFIGURACION.Descripcion, excluded.Descripcion),
            Estado = 1,
            FechaModificacion = datetime('now','localtime')
    """, (clave, str(valor), descripcion, usr))


def _ensure_tipo_vehiculo(cursor, tipo_id, nombre):
    cursor.execute("""
        INSERT OR IGNORE INTO TIPOVEHICULO (
            TipoVehiculo,
            Nombre,
            Estado,
            Usr,
            UsrFecha,
            UsrHora,
            FechaCreacion,
            FechaModificacion
        )
        VALUES (
            ?, ?, 1, 0,
            date('now','localtime'),
            time('now','localtime'),
            datetime('now','localtime'),
            datetime('now','localtime')
        )
    """, (tipo_id, nombre))


def _ensure_tarifa(cursor, nombre, tipo_vehiculo, tipo_tarifa, descripcion, usr=0):
    cursor.execute(
        """
        SELECT Tarifa
        FROM TARIFA
        WHERE TipoVehiculo = ?
          AND TipoTarifa = ?
        ORDER BY Tarifa ASC
        LIMIT 1
        """,
        (tipo_vehiculo, tipo_tarifa),
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(f"""
        INSERT INTO TARIFA (
            Nombre,
            TipoVehiculo,
            TipoTarifa,
            Descripcion,
            Estado,
            Usr,
            UsrFecha,
            UsrHora,
            FechaCreacion,
            FechaModificacion
        )
        VALUES (
            ?, ?, ?, ?, ?, ?,
            {_fecha_actual_sql()}, {_hora_actual_sql()},
            {_fecha_hora_actual_sql()}, {_fecha_hora_actual_sql()}
        )
    """, (
        nombre,
        tipo_vehiculo,
        tipo_tarifa,
        descripcion,
        ESTADO_ACTIVO,
        usr,
    ))
    return cursor.lastrowid


def _ensure_tarifa_detalle(
    cursor,
    tarifa,
    tipo_dia,
    minuto_inicio,
    minuto_fin,
    monto,
    horas_permitidas_dia=None,
    hora_inicio=None,
    hora_fin=None,
    observacion=None,
    usr=0,
):
    cursor.execute(
        """
        SELECT TarifaDetalle
        FROM TARIFADETALLE
        WHERE Tarifa = ?
          AND TipoDia = ?
          AND MinutoInicio = ?
          AND MinutoFin = ?
        LIMIT 1
        """,
        (tarifa, tipo_dia, minuto_inicio, minuto_fin),
    )
    row = cursor.fetchone()

    if row:
        cursor.execute(f"""
            UPDATE TARIFADETALLE
            SET
                Monto = ?,
                HorasPermitidasDia = ?,
                HoraInicio = ?,
                HoraFin = ?,
                Observacion = ?,
                Estado = ?,
                Usr = ?,
                UsrFecha = {_fecha_actual_sql()},
                UsrHora = {_hora_actual_sql()},
                FechaModificacion = {_fecha_hora_actual_sql()}
            WHERE TarifaDetalle = ?
        """, (
            monto,
            horas_permitidas_dia,
            hora_inicio,
            hora_fin,
            observacion,
            ESTADO_ACTIVO,
            usr,
            row[0],
        ))
        return row[0]

    cursor.execute(f"""
        INSERT INTO TARIFADETALLE (
            Tarifa,
            TipoDia,
            MinutoInicio,
            MinutoFin,
            Monto,
            HorasPermitidasDia,
            HoraInicio,
            HoraFin,
            Observacion,
            Estado,
            Usr,
            UsrFecha,
            UsrHora,
            FechaCreacion,
            FechaModificacion
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            {_fecha_actual_sql()}, {_hora_actual_sql()},
            {_fecha_hora_actual_sql()}, {_fecha_hora_actual_sql()}
        )
    """, (
        tarifa,
        tipo_dia,
        minuto_inicio,
        minuto_fin,
        monto,
        horas_permitidas_dia,
        hora_inicio,
        hora_fin,
        observacion,
        ESTADO_ACTIVO,
        usr,
    ))
    return cursor.lastrowid


def _normalizar_tarifa_nocturna(cursor, tarifa, monto, observacion, usr=0):
    """
    Garantiza una sola tarifa nocturna por cabecera:
    TipoDia = 3, MinutoInicio = 1, MinutoFin = 720, HoraInicio = 20:00, HoraFin = 08:00.
    """
    cursor.execute(
        """
        SELECT TarifaDetalle
        FROM TARIFADETALLE
        WHERE Tarifa = ?
          AND TipoDia = ?
          AND MinutoInicio = 1
          AND MinutoFin = 720
        ORDER BY TarifaDetalle ASC
        LIMIT 1
        """,
        (tarifa, TIPO_DIA_NOCTURNA),
    )
    target = cursor.fetchone()

    if target:
        target_id = target[0]

        cursor.execute(f"""
            UPDATE TARIFADETALLE
            SET
                Monto = ?,
                HorasPermitidasDia = NULL,
                HoraInicio = '20:00',
                HoraFin = '08:00',
                Observacion = ?,
                Estado = ?,
                Usr = ?,
                UsrFecha = {_fecha_actual_sql()},
                UsrHora = {_hora_actual_sql()},
                FechaModificacion = {_fecha_hora_actual_sql()}
            WHERE TarifaDetalle = ?
        """, (
            monto,
            observacion,
            ESTADO_ACTIVO,
            usr,
            target_id,
        ))

        cursor.execute(
            """
            DELETE FROM TARIFADETALLE
            WHERE Tarifa = ?
              AND TipoDia = ?
              AND TarifaDetalle <> ?
            """,
            (tarifa, TIPO_DIA_NOCTURNA, target_id),
        )

        return target_id

    cursor.execute(
        """
        SELECT TarifaDetalle
        FROM TARIFADETALLE
        WHERE Tarifa = ?
          AND TipoDia = ?
        ORDER BY TarifaDetalle ASC
        LIMIT 1
        """,
        (tarifa, TIPO_DIA_NOCTURNA),
    )
    old = cursor.fetchone()

    if old:
        old_id = old[0]

        cursor.execute(
            """
            DELETE FROM TARIFADETALLE
            WHERE Tarifa = ?
              AND TipoDia = ?
              AND TarifaDetalle <> ?
            """,
            (tarifa, TIPO_DIA_NOCTURNA, old_id),
        )

        cursor.execute(f"""
            UPDATE TARIFADETALLE
            SET
                MinutoInicio = 1,
                MinutoFin = 720,
                Monto = ?,
                HorasPermitidasDia = NULL,
                HoraInicio = '20:00',
                HoraFin = '08:00',
                Observacion = ?,
                Estado = ?,
                Usr = ?,
                UsrFecha = {_fecha_actual_sql()},
                UsrHora = {_hora_actual_sql()},
                FechaModificacion = {_fecha_hora_actual_sql()}
            WHERE TarifaDetalle = ?
        """, (
            monto,
            observacion,
            ESTADO_ACTIVO,
            usr,
            old_id,
        ))

        return old_id

    return _ensure_tarifa_detalle(
        cursor,
        tarifa,
        TIPO_DIA_NOCTURNA,
        1,
        720,
        monto,
        None,
        "20:00",
        "08:00",
        observacion,
        usr,
    )


# =========================================================
# DATA INICIAL
# =========================================================
def insert_initial_data():
    """
    Inserta datos iniciales sin duplicar.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    # -----------------------------------------------------
    # Configuración general
    # -----------------------------------------------------
    _ensure_configuracion(
        cursor,
        CONFIG_MULTA_TICKET_PERDIDO,
        f"{VALOR_DEFAULT_MULTA_TICKET_PERDIDO:.2f}",
        "Monto de multa por pérdida de ticket. Este valor se usa en el ticket y en el cobro."
    )

    # -----------------------------------------------------
    # Tipos de vehículo
    # -----------------------------------------------------
    _ensure_tipo_vehiculo(cursor, TIPO_VEHICULO_AUTO, "Auto")
    _ensure_tipo_vehiculo(cursor, TIPO_VEHICULO_MOTO, "Moto")

    # -----------------------------------------------------
    # Usuario admin inicial
    # -----------------------------------------------------
    cursor.execute(
        "SELECT COUNT(*) FROM USUARIO WHERE NombreUsuario = ?",
        ("admin",),
    )
    admin_exists = cursor.fetchone()[0]

    if admin_exists == 0:
        cursor.execute(f"""
            INSERT INTO USUARIO (
                Nombre,
                NombreUsuario,
                Password,
                Rol,
                Estado,
                UltimoAcceso,
                Usr,
                UsrFecha,
                UsrHora,
                FechaCreacion,
                FechaModificacion
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, {_fecha_actual_sql()}, {_hora_actual_sql()},
                {_fecha_hora_actual_sql()}, {_fecha_hora_actual_sql()}
            )
        """, (
            "Administrador",
            "admin",
            "1234",
            ROL_ADMIN,
            ESTADO_ACTIVO,
            None,
            0,
        ))

    # -----------------------------------------------------
    # Tarifas por vehículo
    # -----------------------------------------------------
    tarifa_hora_auto = _ensure_tarifa(
        cursor,
        "Tarifa por Hora Auto",
        TIPO_VEHICULO_AUTO,
        TIPO_TARIFA_HORA,
        "Tarifa por hora para auto",
    )
    tarifa_nocturna_auto = _ensure_tarifa(
        cursor,
        "Tarifa Nocturna Auto",
        TIPO_VEHICULO_AUTO,
        TIPO_TARIFA_NOCTURNA,
        "Tarifa nocturna de 20:00 a 08:00 para auto",
    )
    tarifa_contrato_auto = _ensure_tarifa(
        cursor,
        "Tarifa Contrato Auto",
        TIPO_VEHICULO_AUTO,
        TIPO_TARIFA_CONTRATO,
        "Tarifa para contratos de auto por horas permitidas al día",
    )

    tarifa_hora_moto = _ensure_tarifa(
        cursor,
        "Tarifa por Hora Moto",
        TIPO_VEHICULO_MOTO,
        TIPO_TARIFA_HORA,
        "Tarifa por hora para moto",
    )
    tarifa_nocturna_moto = _ensure_tarifa(
        cursor,
        "Tarifa Nocturna Moto",
        TIPO_VEHICULO_MOTO,
        TIPO_TARIFA_NOCTURNA,
        "Tarifa nocturna de 20:00 a 08:00 para moto",
    )

    # -----------------------------------------------------
    # Detalles hora auto
    # -----------------------------------------------------
    detalle_lunes_viernes_auto = [
        (1, 30, 4.0, "1 a 30 min"),
        (31, 60, 6.0, "1 hora"),
        (61, 120, 10.0, "2 horas"),
        (121, 180, 14.0, "3 horas"),
        (181, 240, 18.0, "4 horas"),
        (241, 300, 22.0, "5 horas"),
        (301, 360, 26.0, "6 horas"),
        (361, 420, 30.0, "7 horas"),
        (421, 480, 35.0, "8 horas"),
    ]

    for inicio, fin, monto, obs in detalle_lunes_viernes_auto:
        _ensure_tarifa_detalle(
            cursor,
            tarifa_hora_auto,
            TIPO_DIA_LUNES_VIERNES,
            inicio,
            fin,
            monto,
            None,
            None,
            None,
            obs,
        )

    # -----------------------------------------------------
    # Detalles hora moto
    # -----------------------------------------------------
    detalle_lunes_viernes_moto = [
        (1, 30, 2.0, "1 a 30 min moto"),
        (31, 60, 3.0, "1 hora moto"),
        (61, 120, 5.0, "2 horas moto"),
        (121, 180, 7.0, "3 horas moto"),
        (181, 240, 9.0, "4 horas moto"),
        (241, 300, 11.0, "5 horas moto"),
        (301, 360, 13.0, "6 horas moto"),
        (361, 420, 15.0, "7 horas moto"),
        (421, 480, 18.0, "8 horas moto"),
    ]

    for inicio, fin, monto, obs in detalle_lunes_viernes_moto:
        _ensure_tarifa_detalle(
            cursor,
            tarifa_hora_moto,
            TIPO_DIA_LUNES_VIERNES,
            inicio,
            fin,
            monto,
            None,
            None,
            None,
            obs,
        )

    # -----------------------------------------------------
    # Detalles nocturnos
    # -----------------------------------------------------
    _normalizar_tarifa_nocturna(
        cursor,
        tarifa_nocturna_auto,
        25.0,
        "Tarifa nocturna auto de 20:00 a 08:00",
    )

    _normalizar_tarifa_nocturna(
        cursor,
        tarifa_nocturna_moto,
        15.0,
        "Tarifa nocturna moto de 20:00 a 08:00",
    )

    # -----------------------------------------------------
    # Detalles de contrato estándar para auto
    # Regla del dueño:
    # 3h = 250
    # 6h = 300
    # 9h = 350
    # 12h = 400
    # 24h = 500
    # El monto NO se multiplica si el contrato incluye varios vehículos.
    # -----------------------------------------------------
    detalles_contrato_auto = [
        (3, 250.0),
        (6, 300.0),
        (9, 350.0),
        (12, 400.0),
        (24, 500.0),
    ]

    for horas, monto in detalles_contrato_auto:
        _ensure_tarifa_detalle(
            cursor,
            tarifa_contrato_auto,
            TIPO_DIA_CONTRATO,
            horas,
            horas,
            monto,
            horas,
            None,
            None,
            f"Contrato estándar auto {horas}h por día",
        )

    # -----------------------------------------------------
    # Servicios iniciales
    # -----------------------------------------------------
    cursor.execute("SELECT COUNT(*) FROM SERVICIO")
    servicios_count = cursor.fetchone()[0]

    if servicios_count == 0:
        servicios = [
            ("Lavado", "Lavado básico del vehículo", 15.00, 30, ESTADO_ACTIVO, 0),
            ("Pulido", "Pulido exterior", 25.00, 60, ESTADO_ACTIVO, 0),
            ("Detailing", "Limpieza y detallado del vehículo", 40.00, 90, ESTADO_ACTIVO, 0),
            ("Mantenimiento", "Servicio general de mantenimiento", 50.00, 120, ESTADO_ACTIVO, 0),
        ]

        cursor.executemany(f"""
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
                {_fecha_actual_sql()}, {_hora_actual_sql()},
                {_fecha_hora_actual_sql()}, {_fecha_hora_actual_sql()}
            )
        """, servicios)

    conn.commit()
    conn.close()


# =========================================================
# INICIALIZACIÓN
# =========================================================
def initialize_database():
    """
    Inicializa completamente la base de datos.
    """
    create_tables()
    insert_initial_data()
