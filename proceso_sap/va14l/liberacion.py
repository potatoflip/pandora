
# ==========================================================
# PROCESOS INDEPENDIENTES: LIBERACIÓN Y BLOQUEO
# ==========================================================

from proceso_sap.sap_login import obtener_sesion
from proceso_sap.va14l.va14l import ejecutar_va14l
from configuracion import RUTA_ESCALADO, RUTA_LIBERAR


# ==========================================================
# LIBERACIÓN DE DOCUMENTOS
# ==========================================================

def liberar(session=None):
    print("========== LIBERACIÓN DE DOCUMENTOS ==========")

    if session is None:
        session = obtener_sesion()

    ejecutar_va14l(
        session=session,
        ruta_excel=RUTA_LIBERAR,
        valor_lifsk=" ",
        valor_faksk=" ",
        nombre_proceso="Liberacion",
    )

    print("Proceso de liberación finalizado.")


# ==========================================================
# BLOQUEO DE PEDIDOS ESCALADOS
# ==========================================================

def bloqueo(session=None):
    print("========== BLOQUEO DE PEDIDOS ESCALADOS ==========")

    if session is None:
        session = obtener_sesion()

    ejecutar_va14l(
        session=session,
        ruta_excel=RUTA_ESCALADO,
        valor_lifsk="54",
        valor_faksk="54",
        nombre_proceso="Bloqueo_Escalados",
    )

    print("Proceso de bloqueo finalizado.")


if __name__ == "__main__":
    liberar()
