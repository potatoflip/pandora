import pandas as pd
# ============================================
# CALCULOS PANDORA
# ============================================

# ============================================
# NORMALIZAR VALORES NUMERICOS
# ============================================

def calcular_indicadores(df):

    columnas_numericas = [
        "Valor neto",
        "Costes internos",
        "Precio neto",
        "Precio Venta"
    ]

    for columna in columnas_numericas:

        df[columna] = pd.to_numeric(
            df[columna],
            errors="coerce"
        )

    # ============================================
    # MARGEN DINERO POR LINEA
    # ============================================

    df["Margen Dinero"] = (
        df["Valor neto"]
        - df["Costes internos"]
    )

    # ============================================
    # TOTALES POR DOCUMENTO
    # ============================================

    totales_documento = (
        df.groupby("Documento de ventas")
        .agg(
            **{
                "Venta Total Documento": (
                    "Valor neto",
                    "sum"
                ),
                "Costo Total Documento": (
                    "Costes internos",
                    "sum"
                )
            }
        )
    )

    # Margen dinero acumulado del documento.

    totales_documento["Margen Dinero Total Documento"] = (
        totales_documento["Venta Total Documento"]
        - totales_documento["Costo Total Documento"]
    )

    # Incorporar los totales a cada línea.

    df["Venta Total Documento"] = (
        df["Documento de ventas"].map(
            totales_documento["Venta Total Documento"]
        )
    )

    df["Costo Total Documento"] = (
        df["Documento de ventas"].map(
            totales_documento["Costo Total Documento"]
        )
    )

    df["Margen Dinero Total Documento"] = (
        df["Documento de ventas"].map(
            totales_documento["Margen Dinero Total Documento"]
        )
    )

    # ============================================
    # MARGEN LINEA %
    # ============================================

    df["Margen Linea %"] = (
        df["Margen Dinero"]
        / df["Valor neto"]
    ).where(df["Valor neto"] != 0)

    # ============================================
    # DESCUENTO %
    # ============================================

    df["Descuento %"] = (
        1 -
        (
            df["Precio neto"]
            / df["Precio Venta"]
        )
    ).where(df["Precio Venta"] != 0)

    # ============================================
    # MARGEN DOCUMENTO %
    # ============================================

    margen_documento = (
        totales_documento["Margen Dinero Total Documento"]
        / totales_documento["Venta Total Documento"]
    ).where(
        totales_documento["Venta Total Documento"] != 0
    )

    df["Margen Documento %"] = (
        df["Documento de ventas"].map(
            margen_documento
        )
    )

    return df
