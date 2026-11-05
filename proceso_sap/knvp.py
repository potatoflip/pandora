"""Extrae desde KNVP la relación entre solicitante y vendedor ZV."""

import pyperclip

from configuracion import CARPETA_DATOS, RUTA_BLOQUEADOS, RUTA_CLIENTE_VENDEDOR
from proceso_excel.utilidades_excel import cerrar_archivos_excel, obtener_documentos
from proceso_sap.va14l.utilidades import esperar_sap


def ejecutar_knvp(session):
    solicitantes = list(dict.fromkeys(
        obtener_documentos(RUTA_BLOQUEADOS, columna="Solicitante")
    ))
    if not solicitantes:
        raise ValueError(
            "bloqueados.xlsx no contiene solicitantes; se cancela KNVP para "
            "evitar descargar relaciones de todos los clientes."
        )

    pyperclip.copy("\r\n".join(solicitantes))
    print(f"Consultando KNVP para {len(solicitantes)} solicitante(s) con función ZV...")

    session.findById("wnd[0]/tbar[0]/okcd").text = "/nse16n"
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]/usr/ctxtGD-TAB").text = "KNVP"
    session.findById("wnd[0]/usr/txtGD-MAX_LINES").text = ""
    session.findById("wnd[0]").sendVKey(0)

    campo_columna = session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN")
    campo_columna.text = "PARVW"
    campo_columna.setFocus()
    campo_columna.caretPosition = 5
    session.findById("wnd[0]").sendVKey(0)
    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/ctxtGS_SELFIELDS-LOW[2,1]"
    ).text = "ZV"

    boton_clientes = session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/btnPUSH[4,2]"
    )
    boton_clientes.setFocus()
    boton_clientes.press()
    session.findById("wnd[1]").sendVKey(24)
    session.findById("wnd[1]").sendVKey(8)
    esperar_sap(session)
    session.findById("wnd[0]").sendVKey(8)
    esperar_sap(session)

    tabla = session.findById("wnd[0]/usr/cntlRESULT_LIST/shellcont/shell")
    tabla.pressToolbarContextButton("&MB_EXPORT")
    tabla.selectContextMenuItem("&XXL")
    session.findById("wnd[1]/tbar[0]/btn[0]").press()
    cerrar_archivos_excel([RUTA_CLIENTE_VENDEDOR])
    session.findById("wnd[1]/usr/ctxtDY_PATH").text = str(CARPETA_DATOS)
    session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = RUTA_CLIENTE_VENDEDOR.name
    session.findById("wnd[1]/tbar[0]/btn[11]").press()
    esperar_sap(session)

    print(f"Relación cliente-vendedor exportada: {RUTA_CLIENTE_VENDEDOR}")
