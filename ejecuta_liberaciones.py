from proceso_sap.va14l.liberacion import liberar as ejecutar_liberacion
from proceso_sap.va14l.liberacion import bloqueo as ejecutar_bloqueo

print("\n===== LIBERACIÓN DE DOCUMENTOS =====")
ejecutar_liberacion()

print("\n===== BLOQUEO DE PEDIDOS ESCALADOS =====")
ejecutar_bloqueo()

print("\n===== PROCESO COMPLETO FINALIZADO =====")