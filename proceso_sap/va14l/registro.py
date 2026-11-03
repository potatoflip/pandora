# ==========================================================
# REGISTRO CSV DEL PROCESO VA14L
# ==========================================================

from datetime import datetime


COLUMNAS_LOG = [
    "Fecha",
    "Documento",
    "Estado",
    "Etapa",
    "Codigo SAP",
    "Tipo SAP",
    "Mensaje SAP",
    "Detalle del error",
]


def registrar_log(
    escritor,
    archivo,
    documento,
    estado,
    etapa,
    mensaje_sap="",
    codigo_sap="",
    tipo_sap="",
    detalle_error="",
):
    registro = {
        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Documento": str(documento),
        "Estado": estado,
        "Etapa": etapa,
        "Codigo SAP": codigo_sap,
        "Tipo SAP": tipo_sap,
        "Mensaje SAP": mensaje_sap,
        "Detalle del error": detalle_error,
    }

    escritor.writerow(registro)
    archivo.flush()
