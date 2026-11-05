"""Extrae los datos de solicitantes usados por los pedidos bloqueados."""

import pyperclip

from configuracion import CARPETA_DATOS, RUTA_BLOQUEADOS, RUTA_CLIENTES
from proceso_excel.utilidades_excel import obtener_documentos
from proceso_sap.seguridad_gui import resolver_confirmaciones_exportacion


def ejecutar_kna1(session, solicitantes=None):
    """Consulta KNA1 con los solicitantes de la segunda columna de bloqueados."""
    if solicitantes is None:
        solicitantes = obtener_documentos(RUTA_BLOQUEADOS, columna=1)
    if not solicitantes:
        raise ValueError(
            "bloqueados.xlsx no contiene solicitantes en la segunda columna; "
            "se cancela KNA1 para evitar descargar la tabla completa."
        )

    pyperclip.copy("\r\n".join(solicitantes))
    print(f"Solicitantes preparados para KNA1: {len(solicitantes)}")

    session.findById("wnd[0]/tbar[0]/okcd").text = "/nse16n"
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]/usr/ctxtGD-TAB").text = "KNA1"
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]/usr/ctxtGD-VARIANT").text = "NOMBRECLIENT"
    session.findById("wnd[0]/usr/txtGD-MAX_LINES").text = ""
    session.findById("wnd[0]/usr/ctxtGD-VARIANT").setFocus()
    session.findById("wnd[0]/usr/ctxtGD-VARIANT").caretPosition = 12
    session.findById("wnd[0]").sendVKey(0)

    filtro = session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/btnPUSH[4,1]"
    )
    filtro.setFocus()
    filtro.press()
    session.findById("wnd[1]").sendVKey(24)
    session.findById("wnd[1]").sendVKey(8)
    session.findById("wnd[0]").sendVKey(8)

    tabla = session.findById("wnd[0]/usr/cntlRESULT_LIST/shellcont/shell")
    tabla.pressToolbarContextButton("&MB_VARIANT")
    tabla.pressToolbarContextButton("&MB_EXPORT")
    tabla.selectContextMenuItem("&XXL")
    session.findById("wnd[1]/tbar[0]/btn[0]").press()
    session.findById("wnd[1]/usr/ctxtDY_PATH").text = str(CARPETA_DATOS)
    session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = RUTA_CLIENTES.name
    session.findById("wnd[1]/tbar[0]/btn[11]").press()
    resolver_confirmaciones_exportacion()

    print(f"Clientes descargados desde KNA1: {RUTA_CLIENTES}")
