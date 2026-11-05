
import time

from configuracion import CARPETA_DATOS, RUTA_BLOQUEADOS
from proceso_sap.sap_login import resolver_confirmacion_sesiones
from proceso_sap.seguridad_gui import resolver_confirmaciones_exportacion


def ejecutar_vbak(session):

    print("Abriendo SE16N...")

    session.findById(
        "wnd[0]/tbar[0]/okcd"
    ).text = "/nSE16N"

    session.findById(
        "wnd[0]"
    ).sendVKey(0)

    print("Cargando VBAK...")

    campo_tabla = None
    for _ in range(60):
        resolver_confirmacion_sesiones(session)
        try:
            campo_tabla = session.findById("wnd[0]/usr/ctxtGD-TAB")
            break
        except Exception:
            time.sleep(0.5)
    if campo_tabla is None:
        try:
            mensaje = str(session.findById("wnd[0]/sbar").Text).strip()
        except Exception:
            mensaje = ""
        detalle = f" Mensaje SAP: {mensaje}" if mensaje else ""
        raise RuntimeError(
            "La transacción SE16N no terminó de abrir o SAP dejó un diálogo "
            "pendiente; no se encontraron los campos de selección de VBAK." + detalle
        )
    campo_tabla.text = "VBAK"

    session.findById(
            "wnd[0]"
        ).sendVKey(0)

    session.findById(
        "wnd[0]/usr/ctxtGD-VARIANT"
    ).text = "DOC_BLOQUEAD"

    session.findById(
        "wnd[0]/usr/txtGD-MAX_LINES"
    ).text = ""

    session.findById(
        "wnd[0]"
    ).sendVKey(0)


    print("Aplicando filtros...")

    
    session.findById(
        "wnd[0]/usr/ctxtGD_ADD_COLUMN"
        ).text = "LIFSK"

    session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN").setFocus()
    session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN").caretPosition = 5
    session.findById("wnd[0]").sendVKey (0)

    session.findById(
            "wnd[0]/usr/ctxtGD_ADD_COLUMN"
            ).text = "FAKSK"

    session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN").setFocus()
    session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN").caretPosition = 5
    session.findById("wnd[0]").sendVKey (0)

    session.findById(
                "wnd[0]/usr/ctxtGD_ADD_COLUMN"
                ).text = "NETWR"

    session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN").setFocus()
    session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN").caretPosition = 5
    session.findById("wnd[0]").sendVKey (0)

    session.findById(
                "wnd[0]/usr/ctxtGD_ADD_COLUMN"
                ).text = "VKORG"

    session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN").setFocus()
    session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN").caretPosition = 5
    session.findById("wnd[0]").sendVKey (0)


    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/ctxtGS_SELFIELDS-LOW[2,1]"
    ).text = "51"


    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/ctxtGS_SELFIELDS-LOW[2,2]"
    ).text = "51"

    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/ctxtGS_SELFIELDS-HIGH[3,1]"
    ).text = "53"

    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/ctxtGS_SELFIELDS-HIGH[3,2]"
    ).text = "53"

    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/ctxtGS_SELFIELDS-LOW[2,4]"
    ).text = "3000"

    print("Abriendo selector de condición...")

    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/btnOPTION[1,3]"
    ).setFocus()

    session.findById(
            "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/btnOPTION[1,3]"
        ).press()

    print("Ventanas:", session.Children.Count)

    session.findById("wnd[1]/usr/cntlGRID/shellcont/shell").setCurrentCell(5,"TEXT")

    session.findById(
        "wnd[1]/usr/cntlGRID/shellcont/shell"
    ).selectedRows = "5"

    session.findById(
        "wnd[1]/usr/cntlGRID/shellcont/shell"
    ).doubleClickCurrentCell()

    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/ctxtGS_SELFIELDS-LOW[2,3]"
    ).text = "0"

    print("Ejecutando F8...")

    session.findById(
        "wnd[0]"
    ).sendVKey(8)

    print("✅ Consulta ejecutada")

     # Exportar

    session.findById(
        "wnd[0]/usr/cntlRESULT_LIST/shellcont/shell"
    ).pressToolbarContextButton("&MB_EXPORT")

    session.findById(
        "wnd[0]/usr/cntlRESULT_LIST/shellcont/shell"
    ).selectContextMenuItem("&XXL")

    # Aceptar formato Excel
    session.findById(
        "wnd[1]/tbar[0]/btn[0]"
    ).press()

    # Ruta
    session.findById(
        "wnd[1]/usr/ctxtDY_PATH"
    ).text = str(CARPETA_DATOS)

    # Nombre archivo
    session.findById(
        "wnd[1]/usr/ctxtDY_FILENAME"
    ).text = RUTA_BLOQUEADOS.name

    # Guardar
    session.findById(
        "wnd[1]/tbar[0]/btn[11]"
    ).press()
    resolver_confirmaciones_exportacion()

    print("✅ bloqueados.xlsx generado")

