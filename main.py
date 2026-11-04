from proceso_sap.sap_login import maximizar_ventana, obtener_sesion
from proceso_sap.vbak import ejecutar_vbak
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


def main():
    print("===== EXTRACCIÓN Y PROCESAMIENTO SAP =====")

    session = obtener_sesion()
    maximizar_ventana(session)

    print("===== VBAK =====")
    ejecutar_vbak(session)

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
    ejecutar_liberacion(session)

    print("\n===== BLOQUEO DE PEDIDOS ESCALADOS AUTOMÁTICOS =====")
    ejecutar_bloqueo(session)

    print(
        "\nProceso automático finalizado. Cuando termines la revisión manual, "
        "ejecuta aplicar_decisiones_pandora.py y después ejecuta_liberaciones.py."
    )


if __name__ == "__main__":
    main()
