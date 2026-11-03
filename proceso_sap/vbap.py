from proceso_excel.utilidades_excel import obtener_documentos
import pyperclip
ruta = r"C:\Users\MaxService\Pandora\Archivos_sap\bloqueados.xlsx"
from datetime import datetime
año_vigente = datetime.now().year

def ejecutar_vbap(session):

    print("Leyendo bloqueados.xlsx...")

    documentos = obtener_documentos(ruta)

    texto = "\r\n".join(documentos)

    pyperclip.copy(texto)

    print(
        f"✅ {len(documentos)} documentos copiados al portapapeles"
    )

    session.findById(
            "wnd[0]/tbar[0]/okcd"
        ).text = "/nSE16N"
    
    session.findById("wnd[0]"   ).sendVKey(0) 
        
    print("Abriendo VBAP...")

    session.findById(
        "wnd[0]/usr/ctxtGD-TAB"
    ).text = "VBAP"

    session.findById(
                "wnd[0]"
            ).sendVKey(0)

    session.findById(
        "wnd[0]/usr/ctxtGD-VARIANT"
    ).text = "DOC_RES_BLOQ"

    session.findById(
        "wnd[0]/usr/txtGD-MAX_LINES"
    ).text = ""

    session.findById(
        "wnd[0]/usr/ctxtGD-VARIANT"
    ).setFocus()

    session.findById(
        "wnd[0]/usr/ctxtGD-VARIANT"
    ).caretPosition = 12

    session.findById(
        "wnd[0]"
    ).sendVKey(0)

    print("Aplicando filtros...")

    #FILTRO PARA DESCARTAR LOS PEDIDOS ANULADOS. 

    session.findById(
    "wnd[0]/usr/ctxtGD_ADD_COLUMN"
    ).text = "ABGRU"

    session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN").setFocus()
    session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN").caretPosition = 5
    session.findById("wnd[0]").sendVKey (0)

    print("Abriendo selector de condición...")

    session.findById("wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/btnOPTION[1,1]").setFocus()
    session.findById("wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/btnOPTION[1,1]").press()
    session.findById("wnd[1]/usr/cntlGRID/shellcont/shell").setCurrentCell(3,"TEXT")
    session.findById("wnd[1]/usr/cntlGRID/shellcont/shell").selectedRows = "3"
    session.findById("wnd[1]/usr/cntlGRID/shellcont/shell").doubleClickCurrentCell()

    #FILTRO PARA PEDIDOS DEL AÑO VIGENTE. 

    session.findById(
    "wnd[0]/usr/ctxtGD_ADD_COLUMN"
    ).text = "ERDAT"

    session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN").setFocus()
    session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN").caretPosition = 5
    session.findById("wnd[0]").sendVKey (0)   
    session.findById("wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/btnOPTION[1,2]").setFocus()
    session.findById("wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/btnOPTION[1,2]").press()    
    session.findById("wnd[1]/usr/cntlGRID/shellcont/shell").setCurrentCell(8,"TEXT")
    session.findById("wnd[1]/usr/cntlGRID/shellcont/shell").selectedRows = "8"
    session.findById("wnd[1]/usr/cntlGRID/shellcont/shell").doubleClickCurrentCell()


    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/ctxtGS_SELFIELDS-LOW[2,2]"
    ).text = f"01.10.{año_vigente}"


    print("Cargando documentos desde portapapeles...")

    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/btnPUSH[4,3]"
    ).setFocus()

    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/btnPUSH[4,3]"
    ).press()

    session.findById(
        "wnd[1]/tbar[0]/btn[24]"
    ).press()

    session.findById(
        "wnd[1]"
    ).sendVKey(8)

    print("Ejecutando consulta VBAP...")

    session.findById(
        "wnd[0]"
    ).sendVKey(8)

    print("✅ Consulta VBAP ejecutada")

    print("Exportando Excel...")

    session.findById(
        "wnd[0]/usr/cntlRESULT_LIST/shellcont/shell"
    ).pressToolbarContextButton("&MB_EXPORT")

    session.findById(
        "wnd[0]/usr/cntlRESULT_LIST/shellcont/shell"
    ).selectContextMenuItem("&XXL")

    session.findById(
        "wnd[1]/tbar[0]/btn[0]"
    ).press()

    session.findById(
        "wnd[1]/usr/ctxtDY_PATH"
    ).text = r"C:\Users\MaxService\Pandora\Archivos_sap"

    session.findById(
        "wnd[1]/usr/ctxtDY_FILENAME"
    ).text = "detalle_bloqueado.xlsx"

    session.findById(
          "wnd[1]/tbar[0]/btn[11]"
      ).press()

    print(
        "✅ detalle_bloqueado.xlsx generado"
    )