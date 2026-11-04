"""Extrae las facturas de los solicitantes presentes en los pedidos detallados."""

from datetime import date, datetime

import pandas as pd
import pyperclip

from configuracion import (
    CARPETA_DATOS,
    RUTA_BLOQUEADOS,
    RUTA_DETALLE,
    RUTA_LISTADO_FACTURA,
    VBRK_FECHA_DESDE,
    VBRK_FECHA_HASTA,
)


def _rango_fechas():
    inicio = datetime.strptime(VBRK_FECHA_DESDE, "%d.%m.%Y").date()
    fin = (
        datetime.strptime(VBRK_FECHA_HASTA, "%d.%m.%Y").date()
        if VBRK_FECHA_HASTA.strip()
        else date.today()
    )
    if fin < inicio:
        raise ValueError("La fecha final de VBRK no puede ser anterior a la inicial.")
    return inicio.strftime("%d.%m.%Y"), fin.strftime("%d.%m.%Y")


def _solicitantes_con_detalle():
    bloqueados = pd.read_excel(RUTA_BLOQUEADOS, dtype=str, engine="openpyxl")
    detalle = pd.read_excel(RUTA_DETALLE, dtype=str, engine="openpyxl")
    columnas = {"Documento de ventas", "Solicitante"}
    if not columnas.issubset(bloqueados.columns):
        raise ValueError(
            "bloqueados.xlsx debe incluir Documento de ventas y Solicitante."
        )
    if "Documento de ventas" not in detalle.columns:
        raise ValueError("detalle_bloqueado.xlsx no incluye Documento de ventas.")

    def normalizar(serie):
        return (
            serie.astype("string")
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )

    docs_detalle = set(normalizar(detalle["Documento de ventas"]).dropna())
    solicitantes = normalizar(bloqueados["Solicitante"])
    documentos = normalizar(bloqueados["Documento de ventas"])
    resultado = solicitantes[documentos.isin(docs_detalle)].dropna().unique().tolist()
    return [valor for valor in resultado if valor]


def ejecutar_vbrk(session):
    """Busca facturas desde KUNAG usando los solicitantes de pedidos activos."""
    solicitantes = _solicitantes_con_detalle()
    if not solicitantes:
        raise ValueError(
            "No hay solicitantes asociados a los pedidos de detalle_bloqueado.xlsx; "
            "se cancela VBRK para evitar descargar facturas sin filtro."
        )

    pyperclip.copy("\r\n".join(solicitantes))
    print(f"Solicitantes preparados para VBRK: {len(solicitantes)}")
    fecha_desde, fecha_hasta = _rango_fechas()
    print(f"Rango de facturas VBRK: {fecha_desde} a {fecha_hasta}")

    session.findById("wnd[0]/tbar[0]/okcd").text = "/nse16n"
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]/usr/ctxtGD-VARIANT").text = "Facturas"
    session.findById("wnd[0]/usr/txtGD-MAX_LINES").text = ""
    session.findById("wnd[0]/usr/ctxtGD-VARIANT").setFocus()
    session.findById("wnd[0]/usr/ctxtGD-VARIANT").caretPosition = 8
    session.findById("wnd[0]").sendVKey(0)

    for campo in ("KUNAG", "FKDAT"):
        entrada = session.findById("wnd[0]/usr/ctxtGD_ADD_COLUMN")
        entrada.text = campo
        entrada.setFocus()
        entrada.caretPosition = len(campo)
        session.findById("wnd[0]").sendVKey(0)

    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/ctxtGS_SELFIELDS-LOW[2,2]"
    ).text = fecha_desde
    session.findById(
        "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC/ctxtGS_SELFIELDS-HIGH[3,2]"
    ).text = fecha_hasta

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
    session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = RUTA_LISTADO_FACTURA.name
    session.findById("wnd[1]/tbar[0]/btn[11]").press()

    print(f"Listado de facturas descargado: {RUTA_LISTADO_FACTURA}")
