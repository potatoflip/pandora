from configuracion import RUTA_BLOQUEADOS
from proceso_sap.sap_login import maximizar_ventana, obtener_sesion
from proceso_sap.vbak import ejecutar_vbak
from proceso_sap.knvp import ejecutar_knvp
from proceso_sap.kna1 import ejecutar_kna1
from proceso_sap.vbap import ejecutar_vbap
from proceso_sap.vbrk import ejecutar_vbrk
from proceso_sap.vbrp import ejecutar_vbrp
from proceso_sap.zclsd0022 import (
    ejecutar_zclsd0022,
    ejecutar_zclsd0022_distribuidor,
)
from proceso_excel.pandora_excel import ejecutar_pandora
from proceso_sap.va14l.liberacion import liberar as ejecutar_liberacion
from proceso_sap.va14l.liberacion import bloqueo as ejecutar_bloqueo
from proceso_excel.historial import generar_historial_html, registrar_error_sistema
from proceso_excel.temporizador import medir_duracion
from proceso_excel.progreso import progreso_por_rango, reportar_progreso
from proceso_excel.utilidades_excel import (
    leer_excel_con_reintentos,
    obtener_documentos,
)


def main():
    try:
        reportar_progreso(0, "Iniciando Pandora")
        with medir_duracion("Parte 1 · Extracción y preparación de Pandora"):
            pasos_preparacion = 11
            completados = 0

            def marcar_paso(descripcion):
                nonlocal completados
                completados += 1
                reportar_progreso(
                    round(completados / pasos_preparacion * 60),
                    descripcion,
                )

            generar_historial_html()
            marcar_paso("Historial inicial")
            session = _preparar_pandora(marcar_paso)

        with medir_duracion("Parte 2 · Liberaciones y bloqueos automáticos VA14L"):
            _ejecutar_liberaciones_automaticas(session)
        reportar_progreso(100, "Proceso automático terminado")

        print(
            "\nProceso automático finalizado. Cuando termines la revisión manual, "
            "ejecuta aplicar_decisiones_pandora.py y después ejecuta_liberaciones.py."
        )
    except Exception as error:
        registrar_error_sistema("Ejecución automática", error)
        raise


def _preparar_pandora(marcar_paso=None):
    print("===== EXTRACCIÓN Y PROCESAMIENTO SAP =====")

    session = obtener_sesion()
    maximizar_ventana(session)

    print("===== VBAK =====")
    ejecutar_vbak(session)
    if marcar_paso:
        marcar_paso("Extracción VBAK")

    # Leer bloqueados.xlsx una sola vez en memoria. Las exportaciones posteriores desde SAP
    # pueden dejar bloqueado temporalmente bloqueados.xlsx en OneDrive/Excel.
    bloqueados = leer_excel_con_reintentos(
        RUTA_BLOQUEADOS, dtype=str, engine="openpyxl"
    )
    solicitantes = list(dict.fromkeys(
        obtener_documentos(bloqueados, columna="Solicitante")
    ))
    documentos = obtener_documentos(bloqueados, columna="Documento de ventas")
    if marcar_paso:
        marcar_paso("Lectura de pedidos bloqueados")

    print("===== KNVP: CLIENTE Y VENDEDOR =====")
    try:
        ejecutar_knvp(session, solicitantes=solicitantes)
    except Exception as error:
        registrar_error_sistema("Extracción KNVP", error)
        print(
            "No se pudo actualizar el maestro cliente-vendedor. "
            "Pandora continuará y dejará el error en el historial."
        )
    finally:
        if marcar_paso:
            marcar_paso("Cruce cliente-vendedor KNVP")

    print("===== KNA1: CLIENTES SOLICITANTES =====")
    ejecutar_kna1(session, solicitantes=solicitantes)
    if marcar_paso:
        marcar_paso("Descarga de clientes KNA1")

    print("===== VBAP =====")
    ejecutar_vbap(session, documentos=documentos)
    if marcar_paso:
        marcar_paso("Extracción de pedidos VBAP")

    print("===== VBRK: LISTADO DE FACTURAS =====")
    ejecutar_vbrk(session, bloqueados=bloqueados)
    if marcar_paso:
        marcar_paso("Listado histórico de facturas VBRK")

    print("===== VBRP: HISTORIAL DE PRECIOS FACTURADOS =====")
    ejecutar_vbrp(session)
    if marcar_paso:
        marcar_paso("Detalle histórico de precios VBRP")

    print("===== ZCLSD0022 =====")
    ejecutar_zclsd0022(session)
    if marcar_paso:
        marcar_paso("Lista de precios normal")

    print("===== ZCLSD0022: PRECIOS DISTRIBUIDORES =====")
    ejecutar_zclsd0022_distribuidor(session)
    if marcar_paso:
        marcar_paso("Lista de precios de distribuidores")

    print("===== EXCEL FINAL =====")
    df_pandora = ejecutar_pandora(bloqueados=bloqueados)
    if marcar_paso:
        marcar_paso("Cálculo y generación de Pandora")
    documentos_por_revisar = df_pandora.loc[
        df_pandora["Decision Documento"] == "Documento Por Revisar",
        "Documento de ventas",
    ].nunique()

    if documentos_por_revisar:
        print(
            f"\nQuedan {documentos_por_revisar} documento(s) para revisión manual. "
            "Podrás decidirlos más tarde en pandora_final.xlsx."
        )

    return session


def _ejecutar_liberaciones_automaticas(session):
    print("\n===== LIBERACIÓN DE DOCUMENTOS AUTOMÁTICOS =====")
    ejecutar_liberacion(
        session,
        origen="AUTOMATICO",
        progreso=progreso_por_rango(60, 80, "Liberaciones automáticas"),
    )

    print("\n===== BLOQUEO DE PEDIDOS ESCALADOS AUTOMÁTICOS =====")
    ejecutar_bloqueo(
        session,
        origen="AUTOMATICO",
        progreso=progreso_por_rango(80, 100, "Bloqueos automáticos"),
    )


if __name__ == "__main__":
    main()
