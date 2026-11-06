"""Descarga de VBAK filtrada para los pedidos bloqueados activos."""

import time
from datetime import datetime

from configuracion import CARPETA_DATOS, RUTA_BLOQUEADOS, VBAP_FECHA_DESDE
from proceso_excel.cancelacion import comprobar_detencion
from proceso_sap.sap_login import resolver_confirmacion_sesiones
from proceso_sap.seguridad_gui import resolver_confirmaciones_exportacion


_CAMPO_COLUMNA = "wnd[0]/usr/ctxtGD_ADD_COLUMN"
_TABLA_CONDICIONES = "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC"
_TABLA_OPCIONES = "wnd[1]/usr/cntlGRID/shellcont/shell"


def _fecha_desde():
    """Valida y normaliza la fecha de inicio usada por la variante VBAK."""
    return datetime.strptime(VBAP_FECHA_DESDE, "%d.%m.%Y").strftime("%d.%m.%Y")


def _agregar_columna(session, nombre):
    campo = session.findById(_CAMPO_COLUMNA)
    campo.text = nombre
    campo.setFocus()
    campo.caretPosition = len(nombre)
    session.findById("wnd[0]").sendVKey(0)


def _seleccionar_condicion(session, numero_opcion, fila):
    comprobar_detencion()
    boton = session.findById(
        f"{_TABLA_CONDICIONES}/btnOPTION[1,{numero_opcion}]"
    )
    boton.setFocus()
    boton.press()

    tabla = session.findById(_TABLA_OPCIONES)
    tabla.setCurrentCell(fila, "TEXT")
    tabla.selectedRows = str(fila)
    tabla.doubleClickCurrentCell()


def ejecutar_vbak(session):
    """Consulta VBAK usando la variante actual y los filtros de Pandora."""
    comprobar_detencion()
    print("Abriendo SE16N...")
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nSE16N"
    session.findById("wnd[0]").sendVKey(0)

    print("Cargando VBAK...")
    campo_tabla = None
    for _ in range(60):
        comprobar_detencion()
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
            "pendiente; no se encontraron los campos de selección de VBAK."
            + detalle
        )

    campo_tabla.text = "VBAK"
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]/usr/ctxtGD-VARIANT").text = "DOC_BLOQUEAD"
    session.findById("wnd[0]/usr/txtGD-MAX_LINES").text = ""
    session.findById("wnd[0]").sendVKey(0)

    print("Aplicando filtros...")
    for nombre in ("LIFSK", "FAKSK", "NETWR", "VKORG"):
        comprobar_detencion()
        _agregar_columna(session, nombre)

    session.findById(
        f"{_TABLA_CONDICIONES}/ctxtGS_SELFIELDS-LOW[2,1]"
    ).text = "51"
    session.findById(
        f"{_TABLA_CONDICIONES}/ctxtGS_SELFIELDS-LOW[2,2]"
    ).text = "51"
    session.findById(
        f"{_TABLA_CONDICIONES}/ctxtGS_SELFIELDS-HIGH[3,1]"
    ).text = "53"
    session.findById(
        f"{_TABLA_CONDICIONES}/ctxtGS_SELFIELDS-HIGH[3,2]"
    ).text = "53"
    session.findById(
        f"{_TABLA_CONDICIONES}/ctxtGS_SELFIELDS-LOW[2,4]"
    ).text = "3000"

    print("Seleccionando condición de valor neto...")
    _seleccionar_condicion(session, numero_opcion=3, fila=5)
    session.findById(
        f"{_TABLA_CONDICIONES}/ctxtGS_SELFIELDS-LOW[2,3]"
    ).text = "0"

    print("Seleccionando filtro de fecha...")
    _seleccionar_condicion(session, numero_opcion=6, fila=6)
    fecha_desde = _fecha_desde()
    session.findById(
        f"{_TABLA_CONDICIONES}/ctxtGS_SELFIELDS-LOW[2,6]"
    ).text = fecha_desde
    print(f"Fecha VBAK desde: {fecha_desde}")

    comprobar_detencion()
    print("Ejecutando F8...")
    session.findById("wnd[0]").sendVKey(8)
    print("✅ Consulta ejecutada")

    # Si se pidió detener mientras SAP ejecutaba la consulta, evita exportar
    # y evita que main.py continúe con las demás extracciones.
    comprobar_detencion()
    print("Exportando Excel...")
    tabla = session.findById("wnd[0]/usr/cntlRESULT_LIST/shellcont/shell")
    tabla.pressToolbarContextButton("&MB_EXPORT")
    tabla.selectContextMenuItem("&XXL")
    session.findById("wnd[1]/tbar[0]/btn[0]").press()
    session.findById("wnd[1]/usr/ctxtDY_PATH").text = str(CARPETA_DATOS)
    session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = RUTA_BLOQUEADOS.name
    session.findById("wnd[1]/tbar[0]/btn[11]").press()
    resolver_confirmaciones_exportacion()

    comprobar_detencion()
    print("✅ bloqueados.xlsx generado")
