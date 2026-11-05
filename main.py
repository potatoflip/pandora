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


def main():
    try:
        generar_historial_html()
        _ejecutar_proceso()
    except Exception as error:
        registrar_error_sistema("Ejecución automática", error)
        raise


def _ejecutar_proceso():
    print("===== EXTRACCIÓN Y PROCESAMIENTO SAP =====")

    session = obtener_sesion()
    maximizar_ventana(session)

    print("===== VBAK =====")
    ejecutar_vbak(session)

    print("===== KNVP: CLIENTE Y VENDEDOR =====")
    try:
        ejecutar_knvp(session)
    except Exception as error:
        registrar_error_sistema("Extracción KNVP", error)
        print(
            "No se pudo actualizar el maestro cliente-vendedor. "
            "Pandora continuará y dejará el error en el historial."
        )

    print("===== KNA1: CLIENTES SOLICITANTES =====")
    ejecutar_kna1(session)

    print("===== VBAP =====")
    ejecutar_vbap(session)

    print("===== VBRK: LISTADO DE FACTURAS =====")
    ejecutar_vbrk(session)

    print("===== VBRP: HISTORIAL DE PRECIOS FACTURADOS =====")
    ejecutar_vbrp(session)

    print("===== ZCLSD0022 =====")
    ejecutar_zclsd0022(session)

    print("===== ZCLSD0022: PRECIOS DISTRIBUIDORES =====")
    ejecutar_zclsd0022_distribuidor(session)

    print("===== EXCEL FINAL =====")
    df_pandora = ejecutar_pandora()
    documentos_por_revisar = df_pandora.loc[
        df_pandora["Decision Documento"] == "Documento Por Revisar",
        "Documento de ventas",
    ].nunique()

    if documentos_por_revisar:
        print(
            f"\nQuedan {documentos_por_revisar} documento(s) para revisión manual. "
            "Podrás decidirlos más tarde en pandora_final.xlsx."
        )

    print("\n===== LIBERACIÓN DE DOCUMENTOS AUTOMÁTICOS =====")
    ejecutar_liberacion(session, origen="AUTOMATICO")

    print("\n===== BLOQUEO DE PEDIDOS ESCALADOS AUTOMÁTICOS =====")
    ejecutar_bloqueo(session, origen="AUTOMATICO")

    print(
        "\nProceso automático finalizado. Cuando termines la revisión manual, "
        "ejecuta aplicar_decisiones_pandora.py y después ejecuta_liberaciones.py."
    )


if __name__ == "__main__":
    main()
