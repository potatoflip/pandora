"""Cruza las facturas históricas por cliente y material para comparar precios."""

import pandas as pd

from configuracion import RUTA_DETALLE_FACTURA, RUTA_LISTADO_FACTURA


def _normalizar_clave(serie):
    return (
        serie.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def _columna(df, candidatas, descripcion):
    for nombre in candidatas:
        if nombre in df.columns:
            return nombre
    raise ValueError(
        f"La exportación VBRK debe incluir {descripcion} como columna de salida "
        f"(se buscó: {', '.join(candidatas)})."
    )


def agregar_historial_precios(df, ruta_vbrk):
    """Agrega a cada pedido la última factura histórica de su cliente/material.

    Los campos actuales del pedido se conservan. Los importes de VBRP se llevan
    a valor unitario multiplicando los montos SAP por 100 y dividiendo por la
    cantidad facturada.
    """
    vbrk = pd.read_excel(ruta_vbrk, engine="openpyxl")
    vbrp = pd.read_excel(RUTA_DETALLE_FACTURA, engine="openpyxl")

    campo_factura = _columna(vbrk, ["Factura", "Documento de factura"], "la factura")
    campo_cliente = _columna(
        vbrk,
        ["Solicitante", "Cliente", "KUNAG"],
        "el cliente solicitante KUNAG",
    )
    requeridas_vbrp = {
        "Factura",
        "Material",
        "Cantidad facturada",
        "Fecha de precio",
        "Valor neto",
        "Costes internos",
        "Subtotal 1",
    }
    faltantes = requeridas_vbrp.difference(vbrp.columns)
    if faltantes:
        raise ValueError(
            f"detalle_factura.xlsx no contiene las columnas requeridas: "
            f"{sorted(faltantes)}"
        )

    cabecera = vbrk[[campo_factura, campo_cliente]].copy()
    cabecera.columns = ["Factura", "Solicitante"]
    cabecera["Factura"] = _normalizar_clave(cabecera["Factura"])
    cabecera["Solicitante"] = _normalizar_clave(cabecera["Solicitante"])
    if cabecera["Factura"].duplicated().any():
        cabecera = cabecera.drop_duplicates("Factura", keep="last")

    detalle = vbrp[
        [
            "Factura",
            "Material",
            "Cantidad facturada",
            "Fecha de precio",
            "Valor neto",
            "Costes internos",
            "Subtotal 1",
        ]
    ].copy()
    detalle["Factura"] = _normalizar_clave(detalle["Factura"])
    detalle["Material"] = _normalizar_clave(detalle["Material"])
    detalle["Fecha de precio"] = pd.to_datetime(
        detalle["Fecha de precio"], dayfirst=True, errors="coerce"
    )
    detalle = detalle.rename(columns={"Fecha de precio": "Fecha de precio histórica"})
    detalle = detalle.merge(
        cabecera,
        on="Factura",
        how="inner",
        validate="many_to_one",
    )

    columnas_monto = ["Cantidad facturada", "Valor neto", "Costes internos", "Subtotal 1"]
    for columna in columnas_monto:
        detalle[columna] = pd.to_numeric(detalle[columna], errors="coerce")
    detalle = detalle.loc[
        detalle["Cantidad facturada"].notna()
        & detalle["Cantidad facturada"].ne(0)
        & detalle["Fecha de precio histórica"].notna()
    ].copy()

    historico = (
        detalle.groupby(
            ["Solicitante", "Material", "Factura", "Fecha de precio histórica"],
            as_index=False,
            dropna=True,
        )[["Cantidad facturada", "Valor neto", "Costes internos", "Subtotal 1"]]
        .sum()
    )
    cantidad = historico["Cantidad facturada"]
    historico["Precio neto histórico"] = historico["Subtotal 1"] * 100 / cantidad
    historico["Precio lista histórico"] = historico["Valor neto"] * 100 / cantidad
    historico["Costes internos históricos"] = historico["Costes internos"] * 100 / cantidad
    historico = historico.sort_values(
        ["Fecha de precio histórica", "Factura"], kind="stable"
    ).drop_duplicates(["Solicitante", "Material"], keep="last")
    historico = historico[
        [
            "Solicitante",
            "Material",
            "Factura",
            "Fecha de precio histórica",
            "Precio neto histórico",
            "Precio lista histórico",
            "Costes internos históricos",
        ]
    ].rename(columns={"Factura": "Factura histórica"})

    resultado = df.copy()
    resultado["Solicitante"] = _normalizar_clave(resultado["Solicitante"])
    resultado["Material"] = _normalizar_clave(resultado["Material"])
    resultado = resultado.merge(
        historico,
        on=["Solicitante", "Material"],
        how="left",
        validate="many_to_one",
    )
    sin_historial = resultado["Factura histórica"].isna().sum()
    if sin_historial:
        print(
            f"Aviso: {sin_historial} línea(s) no tienen una factura histórica "
            "coincidente por solicitante y material."
        )
    return resultado
