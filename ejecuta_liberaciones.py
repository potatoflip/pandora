from proceso_sap.sap_login import maximizar_ventana, obtener_sesion
from proceso_sap.va14l.liberacion import liberar as ejecutar_liberacion
from proceso_sap.va14l.liberacion import bloqueo as ejecutar_bloqueo

session = obtener_sesion()
maximizar_ventana(session)

print("\n===== LIBERACIÓN DE DOCUMENTOS =====")
ejecutar_liberacion(session)

print("\n===== BLOQUEO DE PEDIDOS ESCALADOS =====")
ejecutar_bloqueo(session)

print("\n===== PROCESO COMPLETO FINALIZADO =====")
