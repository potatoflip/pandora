from datetime import date, datetime
import unicodedata

import pyperclip

from configuracion import (
    CARPETA_DATOS,
    RUTA_BLOQUEADOS,
    RUTA_DETALLE,
    VBAP_FECHA_DESDE,
)
from proceso_excel.utilidades_excel import obtener_documentos


def _fecha_desde():
    return datetime.strptime(VBAP_FECHA_DESDE, "%d.%m.%Y").strftime("%d.%m.%Y")


def _seleccionar_mayor_que(session):
    tabla_opciones = session.findById("wnd[1]/usr/cntlGRID/shellcont/shell")
    for fila in range(tabla_opciones.RowCount):
        texto = str(tabla_opciones.GetCellValue(fila, "TEXT")).strip()
        normalizado = (
            unicodedata.normalize("NFKD", texto)
            .encode("ascii", "ignore")
            .decode("ascii")
            .casefold()
        )
        es_mayor_que = (
            normalizado in {">", "gt"}
            or (
                ("mayor" in normalizado or "greater than" in normalizado)
                and "igual" not in normalizado
                and "equal" not in normalizado
            )
        )
        if es_mayor_que:
            tabla_opciones.setCurrentCell(fila, "TEXT")
            tabla_opciones.selectedRows = str(fila)
            tabla_opciones.doubleClickCurrentCell()
            print(f"Condición ERDAT seleccionada: {texto}")
            return
    raise RuntimeError(
        "SAP no mostró la condición 'mayor que' para el filtro ERDAT."
    )

def ejecutar_vbap(session):

    fecha_desde = _fecha_desde()
    print(f"Filtro de fecha de pedidos VBAP: mayor que {fecha_desde}")

    print("Leyendo bloqueados.xlsx...")

    documentos = obtener_documentos(RUTA_BLOQUEADOS)

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
    _seleccionar_mayor_que(session)


    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/ctxtGS_SELFIELDS-LOW[2,2]"
    ).text = fecha_desde

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
    ).text = str(CARPETA_DATOS)

    session.findById(
        "wnd[1]/usr/ctxtDY_FILENAME"
    ).text = RUTA_DETALLE.name

    session.findById(
          "wnd[1]/tbar[0]/btn[11]"
      ).press()

    print(
        "✅ detalle_bloqueado.xlsx generado"
    )
