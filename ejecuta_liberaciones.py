from proceso_sap.sap_login import maximizar_ventana, obtener_sesion
from proceso_sap.va14l.liberacion import liberar as ejecutar_liberacion
from proceso_sap.va14l.liberacion import bloqueo as ejecutar_bloqueo
from proceso_excel.historial import registrar_error_sistema

try:
    session = obtener_sesion()
    maximizar_ventana(session)

    print("\n===== LIBERACIÓN DE DOCUMENTOS =====")
    ejecutar_liberacion(session, origen="MANUAL")

    print("\n===== BLOQUEO DE PEDIDOS ESCALADOS =====")
    ejecutar_bloqueo(session, origen="MANUAL")

    print("\n===== PROCESO COMPLETO FINALIZADO =====")
except Exception as error:
    registrar_error_sistema("Ejecución manual VA14L", error)
    raise
