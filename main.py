from proceso_sap.sap_login import obtener_sesion
from proceso_sap.vbak import ejecutar_vbak
from proceso_sap.vbap import ejecutar_vbap
from proceso_sap.zclsd0022 import ejecutar_zclsd0022
from proceso_excel.pandora_excel import ejecutar_pandora

# Procesos VA14L independientes, reutilizados desde el proceso maestro.
from proceso_sap.va14l.liberacion import liberar as ejecutar_liberacion
from proceso_sap.va14l.liberacion import bloqueo as ejecutar_bloqueo


def main():
    print("===== EXTRACCIÓN Y PROCESAMIENTO SAP =====")

    session = obtener_sesion()

    print("===== VBAK =====")
    ejecutar_vbak(session)

    print("===== VBAP =====")
    ejecutar_vbap(session)

    print("===== ZCLSD0022 =====")
    ejecutar_zclsd0022(session)

    print("===== EXCEL FINAL =====")
    ejecutar_pandora()

    print("\n===== LIBERACIÓN DE DOCUMENTOS =====")
    ejecutar_liberacion()

    print("\n===== BLOQUEO DE PEDIDOS ESCALADOS =====")
    ejecutar_bloqueo()

    print("\n===== PROCESO COMPLETO FINALIZADO =====")


if __name__ == "__main__":
    main()
