from proceso_sap.sap_login import maximizar_ventana, obtener_sesion
from proceso_sap.va14l.liberacion import liberar as ejecutar_liberacion
from proceso_sap.va14l.liberacion import bloqueo as ejecutar_bloqueo
from proceso_excel.historial import registrar_error_sistema
from proceso_excel.temporizador import medir_duracion
from proceso_excel.progreso import progreso_por_rango, reportar_progreso


def main():
    try:
        reportar_progreso(0, "Conectando con SAP")
        session = obtener_sesion()
        maximizar_ventana(session)

        with medir_duracion("Liberaciones y bloqueos manuales VA14L"):
            print("\n===== LIBERACIÓN DE DOCUMENTOS =====")
            ejecutar_liberacion(
                session,
                origen="MANUAL",
                progreso=progreso_por_rango(0, 50, "Liberaciones manuales"),
            )

            print("\n===== BLOQUEO DE PEDIDOS ESCALADOS =====")
            ejecutar_bloqueo(
                session,
                origen="MANUAL",
                progreso=progreso_por_rango(50, 100, "Bloqueos manuales"),
            )

        reportar_progreso(100, "Liberaciones y bloqueos manuales terminados")
        print("\n===== PROCESO COMPLETO FINALIZADO =====")
    except Exception as error:
        registrar_error_sistema("Ejecución manual VA14L", error)
        raise


if __name__ == "__main__":
    main()
