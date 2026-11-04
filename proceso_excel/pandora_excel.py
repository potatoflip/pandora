import uuid

import pandas as pd

from configuracion import (
    RUTA_BLOQUEADOS,
    RUTA_DETALLE,
    RUTA_ESCALADO,
    RUTA_FINAL,
    RUTA_LIBERAR,
    RUTA_PRECIOS,
    RUTA_REVISION_HTML,
)

from proceso_excel.utilidades_excel import (
    abrir_resultado,
    cerrar_archivos_excel,
)
from proceso_excel.reglas_pandora import (
    evaluar_linea,
    decision_documento,
)
from proceso_excel.calculos_pandora import calcular_indicadores
from proceso_excel.formato_pandora import exportar_pandora
from proceso_excel.revision_html import exportar_revision_html


# ============================================
# RUTAS
# ============================================

# ============================================
# EJECUTAR PANDORA
# ============================================

def ejecutar_pandora():

    # ============================================
    # CERRAR ARCHIVOS EXCEL ABIERTOS
    # ============================================

    cerrar_archivos_excel([
        RUTA_DETALLE,
        RUTA_PRECIOS,
        RUTA_BLOQUEADOS,
        RUTA_FINAL,
        RUTA_LIBERAR,
        RUTA_ESCALADO
    ])

    # ============================================
    # CARGAR ARCHIVOS EXCEL
    # ============================================

    df_vbap = pd.read_excel(
        RUTA_DETALLE,
        engine="openpyxl"
    )

    df_precios = pd.read_excel(
        RUTA_PRECIOS,
        engine="openpyxl"
    )

    # ============================================
    # NORMALIZAR MATERIAL
    # ============================================

    df_vbap["Material"] = (
        df_vbap["Material"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )

    df_precios["Material"] = (
        df_precios["Material"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )

    # ============================================
    # CRUZAR DETALLE VBAP CON PRECIOS
    # ============================================

    df = df_vbap.merge(
        df_precios[
            [
                "Material",
                "Precio Venta"
            ]
        ],
        on="Material",
        how="left"
    )

    # ============================================
    # CALCULAR INDICADORES
    # ============================================

    df = calcular_indicadores(df)

    # ============================================
    # EVALUAR REGLAS POR LINEA
    # ============================================

    resultado = df.apply(
        evaluar_linea,
        axis=1
    )

    df["Decision Linea"] = [
        x[0] for x in resultado
    ]

    df["Motivo"] = [
        x[1] for x in resultado
    ]

    # ============================================
    # DETERMINAR DECISION POR DOCUMENTO
    # ============================================

    decision_documentos = pd.Series({
        documento: decision_documento(grupo)
        for documento, grupo in df.groupby("Documento de ventas")
    })

    df["Decision Documento"] = (
        df["Documento de ventas"].map(decision_documentos)
    )

    # ============================================
    # CONVERTIR PORCENTAJES A 1 DECIMAL
    # ============================================

    # Se realiza después de evaluar las reglas porque
    # las reglas trabajan con valores decimales (0.156 = 15.6%).

    df["Descuento %"] = (
        df["Descuento %"] * 100
    ).round(1)

    df["Margen Linea %"] = (
        df["Margen Linea %"] * 100
    ).round(1)

    df["Margen Documento %"] = (
        df["Margen Documento %"] * 100
    ).round(1)

    # ============================================
    # EXPORTAR Y FORMATEAR ARCHIVOS
    # ============================================

    generacion_id = uuid.uuid4().hex
    documentos_liberados, documentos_rechazados = exportar_pandora(
        df,
        RUTA_FINAL,
        RUTA_LIBERAR,
        RUTA_ESCALADO,
        generacion_id,
    )

    exportar_revision_html(df, RUTA_REVISION_HTML, generacion_id)

    # ============================================
    # RESUMEN
    # ============================================

    print("\n========== RESUMEN PANDORA ==========")

    print(
    f"Documentos totales: {df['Documento de ventas'].nunique()}"
)

    print(
        f"Documentos liberados: {len(documentos_liberados)}"
    )

    print(
        f"Documentos rechazados: {len(documentos_rechazados)}"
    )

    print(
        "Documentos por revisar:",
        df.loc[
            df["Decision Documento"] == "Documento Por Revisar",
            "Documento de ventas"
        ].nunique()
    )

    print(
        "Documentos con error:",
        df.loc[
            df["Decision Documento"] == "Documento con Error",
            "Documento de ventas"
        ].nunique()
    )

    print("\nArchivos generados:")
    print(RUTA_FINAL)
    print(RUTA_REVISION_HTML)
    print(RUTA_LIBERAR)
    print(RUTA_ESCALADO)

    # ============================================
    # ABRIR PANDORA FINAL
    # ============================================

    print("\nAbriendo la página de revisión Pandora...")

    abrir_resultado(RUTA_REVISION_HTML)

    return df
