import uuid

import pandas as pd

from configuracion import (
    RUTA_BLOQUEADOS,
    RUTA_CLIENTES,
    RUTA_LISTADO_FACTURA,
    RUTA_DETALLE_FACTURA,
    RUTA_DETALLE,
    RUTA_ESCALADO,
    RUTA_FINAL,
    RUTA_HISTORIAL_HTML,
    RUTA_LIBERAR,
    RUTA_PRECIOS,
    RUTA_PRECIOS_DISTRIBUIDOR,
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
from proceso_excel.historial_precios import agregar_historial_precios
from proceso_excel.formato_pandora import exportar_pandora
from proceso_excel.revision_html import exportar_revision_html
from proceso_excel.contexto_comercial import enriquecer_contexto_comercial
from proceso_excel.historial import registrar_clasificaciones


def _normalizar_clave(serie):
    return (
        serie.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def _precios_por_material(df_precios, nombre):
    requeridas = {"Material", "Precio Venta", "F. Validez Desde"}
    faltantes = requeridas.difference(df_precios.columns)
    if faltantes:
        raise ValueError(
            f"{nombre} no contiene las columnas requeridas: {sorted(faltantes)}"
        )

    precios = df_precios[["Material", "Precio Venta", "F. Validez Desde"]].copy()
    precios["Material"] = _normalizar_clave(precios["Material"])
    precios["Precio Venta"] = pd.to_numeric(precios["Precio Venta"], errors="coerce")
    precios["_VigenciaDesde"] = pd.to_datetime(
        precios["F. Validez Desde"], dayfirst=True, errors="coerce"
    )

    conflictos = (
        precios.groupby(["Material", "_VigenciaDesde"], dropna=False)["Precio Venta"]
        .nunique(dropna=True)
        .gt(1)
    )
    if conflictos.any():
        raise ValueError(
            f"{nombre} contiene materiales con precios distintos para la misma "
            "fecha de vigencia; no es seguro elegir uno automáticamente."
        )

    return (
        precios.sort_values(
            ["Material", "_VigenciaDesde"],
            kind="stable",
            na_position="first",
        )
        .drop_duplicates("Material", keep="last")
        .drop(columns=["F. Validez Desde", "_VigenciaDesde"])
    )


def _agregar_solicitante_y_canal(df_vbap):
    bloqueados = pd.read_excel(RUTA_BLOQUEADOS, engine="openpyxl")
    clientes = pd.read_excel(RUTA_CLIENTES, engine="openpyxl")
    columnas_bloqueados = {
        "Documento de ventas",
        "Solicitante",
        "Canal distribución",
        "Oficina de ventas",
    }
    faltantes = columnas_bloqueados.difference(bloqueados.columns)
    if faltantes:
        raise ValueError(
            f"bloqueados.xlsx no contiene las columnas requeridas: {sorted(faltantes)}"
        )
    if not {"Cliente", "Nombre 1"}.issubset(clientes.columns):
        raise ValueError("clientes.xlsx debe incluir Cliente y Nombre 1.")

    bloqueados = bloqueados[
        ["Documento de ventas", "Solicitante", "Canal distribución", "Oficina de ventas"]
    ].copy()
    bloqueados["Documento de ventas"] = _normalizar_clave(
        bloqueados["Documento de ventas"]
    )
    bloqueados["Solicitante"] = _normalizar_clave(bloqueados["Solicitante"])
    bloqueados["Canal distribución"] = _normalizar_clave(
        bloqueados["Canal distribución"]
    )
    if bloqueados["Documento de ventas"].duplicated().any():
        repetidos = bloqueados[
            bloqueados["Documento de ventas"].duplicated(keep=False)
        ]
        inconsistentes = repetidos.groupby("Documento de ventas")[
            ["Solicitante", "Canal distribución", "Oficina de ventas"]
        ].nunique(dropna=False).gt(1).any(axis=1)
        if inconsistentes.any():
            raise ValueError(
                "bloqueados.xlsx tiene documentos con más de un solicitante, canal "
                "u oficina de ventas."
            )
        bloqueados = bloqueados.drop_duplicates("Documento de ventas")

    df = df_vbap.copy()
    df["Documento de ventas"] = _normalizar_clave(df["Documento de ventas"])
    df = df.merge(
        bloqueados,
        on="Documento de ventas",
        how="left",
        validate="many_to_one",
    )

    clientes = clientes[["Cliente", "Nombre 1"]].copy()
    clientes["Cliente"] = _normalizar_clave(clientes["Cliente"])
    clientes = clientes.rename(
        columns={"Cliente": "Solicitante", "Nombre 1": "Nombre solicitante"}
    )
    if clientes["Solicitante"].duplicated().any():
        clientes = clientes.drop_duplicates("Solicitante")
    df = df.merge(
        clientes,
        on="Solicitante",
        how="left",
        validate="many_to_one",
    )
    return enriquecer_contexto_comercial(df)

# ============================================
# EJECUTAR PANDORA
# ============================================

def ejecutar_pandora():

    # ============================================
    # CERRAR ARCHIVOS EXCEL ABIERTOS
    # ============================================

    cerrar_archivos_excel([
        RUTA_DETALLE,
        RUTA_CLIENTES,
        RUTA_LISTADO_FACTURA,
        RUTA_DETALLE_FACTURA,
        RUTA_PRECIOS,
        RUTA_PRECIOS_DISTRIBUIDOR,
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
    df_precios_distribuidor = pd.read_excel(
        RUTA_PRECIOS_DISTRIBUIDOR,
        engine="openpyxl",
    )

    # ============================================
    # NORMALIZAR MATERIAL
    # ============================================

    df_vbap["Material"] = (
        _normalizar_clave(df_vbap["Material"])
    )

    df = _agregar_solicitante_y_canal(df_vbap)
    precios_normales = _precios_por_material(df_precios, "precios.XLSX")
    precios_normales = precios_normales.rename(
        columns={"Precio Venta": "Precio Venta Normal"}
    )
    df_precios_distribuidor["Canal"] = _normalizar_clave(
        df_precios_distribuidor["Canal"]
    )
    precios_distribuidor = _precios_por_material(
        df_precios_distribuidor.loc[
            df_precios_distribuidor["Canal"] == "10"
        ],
        "precios_distribuidor.xlsx",
    ).rename(columns={"Precio Venta": "Precio Venta Distribuidor"})

    # ============================================
    # CRUZAR DETALLE VBAP CON PRECIOS
    # ============================================

    df = df.merge(
        precios_normales,
        on="Material",
        how="left",
        validate="many_to_one",
    )
    df = df.merge(
        precios_distribuidor,
        on="Material",
        how="left",
        validate="many_to_one",
    )
    canal_distribuidor = df["Canal distribución"] == "10"
    hay_precio_distribuidor = df["Precio Venta Distribuidor"].notna()
    usa_precio_distribuidor = canal_distribuidor & hay_precio_distribuidor
    df.loc[~canal_distribuidor, "Precio Venta Distribuidor"] = pd.NA
    df["Precio Venta"] = df["Precio Venta Normal"]
    df.loc[usa_precio_distribuidor, "Precio Venta"] = df.loc[
        usa_precio_distribuidor, "Precio Venta Distribuidor"
    ]
    df["Lista de precios aplicada"] = "Normal"
    df.loc[
        canal_distribuidor & ~hay_precio_distribuidor,
        "Lista de precios aplicada",
    ] = "Normal (respaldo sin precio distribuidor)"
    df.loc[usa_precio_distribuidor, "Lista de precios aplicada"] = "Distribuidor"

    df = agregar_historial_precios(df, RUTA_LISTADO_FACTURA)

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

    # Mantener todos los datos actuales (incluidas reglas y márgenes) primero;
    # las referencias históricas quedan agrupadas al final.
    columnas_historicas = [
        "Factura histórica",
        "Fecha de precio histórica",
        "Precio neto histórico",
        "Precio lista histórico",
        "Costes internos históricos",
    ]
    columnas_contexto = [
        "Documento de ventas",
        "Nombre solicitante",
        "Canal distribución",
        "Solicitante",
    ]
    columnas_primero = [
        columna for columna in columnas_contexto if columna in df.columns
    ]
    columnas_historicas = [
        columna for columna in columnas_historicas if columna in df.columns
    ]
    columnas_actuales = [
        columna
        for columna in df.columns
        if columna not in columnas_primero and columna not in columnas_historicas
    ]
    df = df[columnas_primero + columnas_actuales + columnas_historicas]

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

    exportar_revision_html(
        df,
        RUTA_REVISION_HTML,
        generacion_id,
        ruta_historial=RUTA_HISTORIAL_HTML,
    )
    registrar_clasificaciones(df, generacion_id)

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
