from proceso_sap.sap_login import maximizar_ventana, obtener_sesion
from proceso_sap.va14l.liberacion import liberar as ejecutar_liberacion
from proceso_sap.va14l.liberacion import bloqueo as ejecutar_bloqueo
from proceso_excel.historial import registrar_error_sistema
from proceso_excel.cancelacion import ProcesoCancelado, comprobar_detencion
from proceso_excel.temporizador import medir_duracion
from proceso_excel.progreso import progreso_por_rango, reportar_progreso


def main():
    try:
        comprobar_detencion()
        reportar_progreso(0, "Conectando con SAP")
        session = obtener_sesion()
        maximizar_ventana(session)

        comprobar_detencion()
        with medir_duracion("Liberaciones y bloqueos manuales VA14L"):
            print("\n===== LIBERACIÓN DE DOCUMENTOS =====")
            comprobar_detencion()
            ejecutar_liberacion(
                session,
                origen="MANUAL",
                progreso=progreso_por_rango(0, 50, "Liberaciones manuales"),
            )

            print("\n===== BLOQUEO DE PEDIDOS ESCALADOS =====")
            comprobar_detencion()
            ejecutar_bloqueo(
                session,
                origen="MANUAL",
                progreso=progreso_por_rango(50, 100, "Bloqueos manuales"),
            )

        reportar_progreso(100, "Liberaciones y bloqueos manuales terminados")
        print("\n===== PROCESO COMPLETO FINALIZADO =====")
    except ProcesoCancelado:
        print("Ejecución manual detenida en un punto seguro.")
        raise
    except Exception as error:
        registrar_error_sistema("Ejecución manual VA14L", error)
        raise


if __name__ == "__main__":
    main()
