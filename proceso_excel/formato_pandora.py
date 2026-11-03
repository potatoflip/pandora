import os

import pandas as pd

from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.filters import AutoFilter


# ============================================
# GENERAR ARCHIVOS POR DECISION DOCUMENTO
# ============================================

def generar_archivo_documentos(df, decision, ruta):

    # Filtrar por decisión y copiar únicamente
    # la primera columna del Pandora final.

    documentos = df.loc[
        df["Decision Documento"] == decision,
        [df.columns[0]]
    ].copy()

    # Eliminar valores vacíos y duplicados.

    documentos = documentos.dropna()
    documentos = documentos.drop_duplicates()

    # Si no hay documentos, crear igualmente un Excel nuevo.
    # El mensaje se coloca en una segunda columna para que
    # obtener_documentos() no lo interprete como un documento SAP.

    # Preparar el contenido que se escribirá en el Excel.
    # Si no hay documentos, la primera columna queda vacía y el
    # mensaje se escribe en una segunda columna.

    if documentos.empty:
        archivo_salida = pd.DataFrame({
            documentos.columns[0]: [None],
            "Estado": ["No hay datos"]
        })
    else:
        archivo_salida = documentos

    # Guardar el archivo. to_excel sobrescribe el archivo
    # existente si ya se encuentra en la ruta indicada.

    archivo_salida.to_excel(
        ruta,
        index=False
    )

    print(f"\nArchivo generado: {os.path.basename(ruta)}")

    if documentos.empty:
        print("No hay datos para esta categoría.")
    else:
        print(f"Documentos únicos: {len(documentos)}")

    return documentos


# ============================================
# EXPORTAR Y FORMATEAR PANDORA FINAL
# ============================================

def exportar_pandora(df, ruta_final, ruta_liberar, ruta_escalado):

    # ============================================
    # EXPORTAR PANDORA FINAL
    # ============================================

    df.to_excel(
        ruta_final,
        index=False
    )

    # ============================================
    # FORMATO EXCEL
    # ============================================

    wb = load_workbook(ruta_final)
    ws = wb.active

    ultima_fila = ws.max_row
    ultima_columna = ws.max_column

    # ============================================
    # CREAR TABLA
    # ============================================

    tabla = Table(
        displayName="TablaPandora",
        ref=f"A1:{ws.cell(ultima_fila, ultima_columna).coordinate}"
    )

    estilo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False
    )

    tabla.tableStyleInfo = estilo

    # ============================================
    # COLORES
    # ============================================

    verde = PatternFill(
        "solid",
        fgColor="C6EFCE"
    )

    naranja = PatternFill(
        "solid",
        fgColor="FCE4D6"
    )

    rojo = PatternFill(
        "solid",
        fgColor="FFC7CE"
    )

    amarillo = PatternFill(
        "solid",
        fgColor="FFF099"
    )

    col_decision = None
    col_decision_documento = None

    for celda in ws[1]:

        if celda.value == "Decision Linea":
            col_decision = celda.column

        elif celda.value == "Decision Documento":
            col_decision_documento = celda.column

    if col_decision is None or col_decision_documento is None:

        raise ValueError(
            "No se encontraron las columnas de decisión en Pandora."
        )

    for fila in range(2, ultima_fila + 1):

        valor = ws.cell(
            fila,
            col_decision
        ).value

        color = None

        if valor == "Aprobada":
            color = verde

        elif valor == "Rechazada":
            color = naranja

        elif valor == "ERROR":
            color = rojo

        elif valor == "Revision":
            color = amarillo

        if color:

            for col in range(1, ultima_columna + 1):

                ws.cell(
                    fila,
                    col
                ).fill = color

    # ============================================
    # FORMATO MONEDA
    # ============================================

    columnas_monedas = [
        "Precio neto",
        "Precio Venta",
        "Valor neto",
        "Costes internos",
        "Margen Dinero Linea",
        "Margen Dinero",
        "Venta Total Documento",
        "Costo Total Documento"
    ]

    for encabezado in ws[1]:

        if encabezado.value in columnas_monedas:

            for fila in range(2, ultima_fila + 1):

                ws.cell(
                    fila,
                    encabezado.column
                ).number_format = '#,##0'

    # ============================================
    # FORMATO PORCENTAJE
    # ============================================

    columnas_porcentaje = [
        "Descuento %",
        "Margen Linea %",
        "Margen Documento %"
    ]

    for encabezado in ws[1]:

        if encabezado.value in columnas_porcentaje:

            for fila in range(2, ultima_fila + 1):

                ws.cell(
                    fila,
                    encabezado.column
                ).number_format = '0.0"%"'

    # ============================================
    # FILTRO PANDORA FINAL
    # ============================================

    tabla.autoFilter = AutoFilter(
        ref=tabla.ref
    )

    tabla.autoFilter.add_filter_column(
        col_decision_documento - 1,
        [
            "Documento Por Revisar",
            "Documento con Error"
        ]
    )

    ws.add_table(tabla)

    wb.save(ruta_final)

    print("\nPandora final generado correctamente.")

    # ============================================
    # GENERAR LIBERAR Y ESCALADO
    # ============================================

    documentos_liberados = generar_archivo_documentos(
        df,
        "Documento Liberado",
        ruta_liberar
    )

    documentos_rechazados = generar_archivo_documentos(
        df,
        "Documento Rechazado",
        ruta_escalado
    )

    return documentos_liberados, documentos_rechazados
