import pandas as pd


# ============================================
# UMBRALES DE LAS REGLAS COMERCIALES
# ============================================

DESCUENTO_MAX = 0.16
MARGEN_LINEA_MIN = 0.25
MARGEN_DOC_MIN = 0.30
DESCUENTO_BLOQ = 0.25

# Excepción a nivel documento: una única línea en revisión.
DESCUENTO_EXCEPCION_MAX = 0.20
MARGEN_LINEA_EXCEPCION_MIN = 0.15


# ============================================
# EVALUAR UNA LÍNEA
# ============================================

def evaluar_linea(fila):
    """Evalúa una línea y devuelve su decisión y motivo."""

    precio_lista = fila["Precio Venta"]
    descuento = fila["Descuento %"]
    margen_linea = fila["Margen Linea %"]
    margen_documento = fila["Margen Documento %"]

    # VALIDAR PRECIO LISTA
    if pd.isna(precio_lista) or precio_lista == 0:
        return (
            "ERROR",
            "Precio lista no encontrado o igual a 0"
        )

    # VALIDAR DESCUENTO
    if pd.isna(descuento):
        return (
            "ERROR",
            "No se pudo calcular el descuento"
        )

    # REGLA 1: DESCUENTO SUPERIOR AL 25%
    if descuento > DESCUENTO_BLOQ:
        return (
            "Rechazada",
            "Descuento superior al 25%: requiere autorización de gerencia"
        )

    # REGLA 2: DESCUENTO HASTA EL 15%
    if descuento <= DESCUENTO_MAX:
        return (
            "Aprobada",
            "Descuento dentro del estándar"
        )

    # REGLA 3: DESCUENTO ENTRE 15% Y 25%
    if descuento <= DESCUENTO_BLOQ:
        if (
            pd.notna(margen_linea)
            and pd.notna(margen_documento)
            and margen_linea >= MARGEN_LINEA_MIN
            and margen_documento >= MARGEN_DOC_MIN
        ):
            return (
                "Revision",
                (
                    "Requiere autorización | "
                    "Márgenes cumplen objetivos | "
                    f"Margen Línea={margen_linea:.1%} | "
                    f"Margen Doc={margen_documento:.1%}"
                )
            )

        return (
            "Revision",
            (
                "Requiere autorización | "
                f"Desc={descuento:.1%} | "
                f"Margen Línea={margen_linea:.1%} | "
                f"Margen Doc={margen_documento:.1%}"
            )
        )

    # Protección por si aparece un valor fuera de los casos previstos.
    return (
        "ERROR",
        "No se pudo determinar la decisión de la línea"
    )


# ============================================
# EVALUAR EL DOCUMENTO COMPLETO
# ============================================

def decision_documento(grupo):
    """Determina la decisión del documento según todas sus líneas.

    Se permite liberar el documento si existe exactamente una línea en
    revisión, las demás están aprobadas, el descuento de esa línea no supera
    el 20% y su margen individual es como mínimo del 15%.
    """

    decisiones = grupo["Decision Linea"]

    # Los errores de datos siempre tienen prioridad.
    if "ERROR" in decisiones.values:
        return "Documento con Error"

    # Una línea rechazada nunca se aprueba mediante esta excepción.
    if "Rechazada" in decisiones.values:
        return "Documento Rechazado"

    revisiones = grupo.loc[decisiones == "Revision"]

    # Todas las líneas están aprobadas.
    if revisiones.empty:
        if (decisiones == "Aprobada").all():
            return "Documento Liberado"
        return "Documento Por Revisar"

    # La excepción solo cubre una única línea en revisión.
    if len(revisiones) == 1:
        otras_lineas = grupo.loc[decisiones != "Revision"]
        resto_aprobado = (otras_lineas["Decision Linea"] == "Aprobada").all()

        linea_revision = revisiones.iloc[0]
        descuento = linea_revision["Descuento %"]
        margen_linea = linea_revision["Margen Linea %"]

        cumple_excepcion = (
            resto_aprobado
            and pd.notna(descuento)
            and pd.notna(margen_linea)
            and descuento <= DESCUENTO_EXCEPCION_MAX
            and margen_linea >= MARGEN_LINEA_EXCEPCION_MIN
        )

        if cumple_excepcion:
            return "Documento Liberado"

    return "Documento Por Revisar"
