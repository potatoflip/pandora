"""Configuración central de rutas del proyecto Pandora.

Para usar otra carpeta de datos, define PANDORA_DATA_DIR en las variables
de entorno del equipo. Por defecto se usa ``Archivos_sap`` dentro del proyecto.
"""

import os
from pathlib import Path


RAIZ_PROYECTO = Path(__file__).resolve().parent
CARPETA_DATOS = Path(
    os.environ.get("PANDORA_DATA_DIR", RAIZ_PROYECTO / "Archivos_sap")
).expanduser()

SAPLOGON_PATH = Path(
    os.environ.get(
        "SAPLOGON_PATH",
        r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe",
    )
).expanduser()


def ruta_datos(nombre_archivo):
    """Devuelve la ruta completa de un archivo de intercambio de Pandora."""
    return CARPETA_DATOS / nombre_archivo


# Nombres y rutas de archivos usados por los procesos.
ARCHIVOS = {
    "bloqueados": "bloqueados.xlsx",
    "detalle_bloqueado": "detalle_bloqueado.xlsx",
    "precios": "precios.XLSX",
    "precios_distribuidor": "precios_distribuidor.xlsx",
    "resultado_final": "pandora_final.xlsx",
    "liberar": "liberar.xlsx",
    "escalado": "escalado.xlsx",
}

RUTAS = {clave: ruta_datos(nombre) for clave, nombre in ARCHIVOS.items()}

RUTA_BLOQUEADOS = RUTAS["bloqueados"]
RUTA_DETALLE = RUTAS["detalle_bloqueado"]
RUTA_PRECIOS = RUTAS["precios"]
RUTA_PRECIOS_DISTRIBUIDOR = RUTAS["precios_distribuidor"]
RUTA_FINAL = RUTAS["resultado_final"]
RUTA_LIBERAR = RUTAS["liberar"]
RUTA_ESCALADO = RUTAS["escalado"]
