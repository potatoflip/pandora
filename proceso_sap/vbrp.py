"""Extrae el detalle histórico de las facturas encontradas por VBRK."""

import pyperclip

from configuracion import CARPETA_DATOS, RUTA_DETALLE_FACTURA, RUTA_LISTADO_FACTURA
from proceso_excel.utilidades_excel import obtener_documentos
from proceso_sap.seguridad_gui import resolver_confirmaciones_exportacion


def ejecutar_vbrp(session):
    """Consulta VBRP con los números de factura de listado_factura.xlsx."""
    facturas = obtener_documentos(RUTA_LISTADO_FACTURA, columna=0)
    if not facturas:
        raise ValueError(
            "listado_factura.xlsx no contiene facturas en su primera columna; "
            "se cancela VBRP para evitar descargar la tabla completa."
        )

    pyperclip.copy("\r\n".join(facturas))
    print(f"Facturas preparadas para VBRP: {len(facturas)}")

    session.findById("wnd[0]/tbar[0]/okcd").text = "/nse16n"
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]/usr/ctxtGD-TAB").text = "VBRP"
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]/usr/ctxtGD-VARIANT").text = "HIST_PRECIOS"
    session.findById("wnd[0]/usr/txtGD-MAX_LINES").text = ""
    session.findById("wnd[0]/usr/ctxtGD-VARIANT").setFocus()
    session.findById("wnd[0]/usr/ctxtGD-VARIANT").caretPosition = 12
    session.findById("wnd[0]").sendVKey(0)

    selector = session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/btnPUSH[4,1]"
    )
    selector.setFocus()
    selector.press()
    session.findById("wnd[1]/tbar[0]/btn[24]").press()
    session.findById("wnd[1]").sendVKey(8)
    session.findById("wnd[0]").sendVKey(8)

    tabla = session.findById("wnd[0]/usr/cntlRESULT_LIST/shellcont/shell")
    tabla.pressToolbarContextButton("&MB_EXPORT")
    tabla.selectContextMenuItem("&XXL")
    session.findById("wnd[1]/tbar[0]/btn[0]").press()
    session.findById("wnd[1]/usr/ctxtDY_PATH").text = str(CARPETA_DATOS)
    session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = RUTA_DETALLE_FACTURA.name
    session.findById("wnd[1]/tbar[0]/btn[11]").press()
    resolver_confirmaciones_exportacion()

    print(f"Detalle de facturas descargado: {RUTA_DETALLE_FACTURA}")
