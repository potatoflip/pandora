"""Configuración central de rutas del proyecto Pandora.

Define PANDORA_DATA_DIR en cada equipo con la ruta completa de la carpeta de
datos. Esa carpeta se usa directamente, sin añadir subdirectorios.
"""

import os
from pathlib import Path


def _obtener_variable_usuario(nombre):
    """Lee una variable del proceso o del entorno persistente del usuario Windows."""
    valor = os.environ.get(nombre)
    if valor:
        return valor

    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Environment"
            ) as clave_usuario:
                valor, _ = winreg.QueryValueEx(clave_usuario, nombre)
                return valor
        except (ImportError, OSError):
            pass

    return None


_directorio_datos = _obtener_variable_usuario("PANDORA_DATA_DIR")
if not _directorio_datos:
    raise RuntimeError(
        "Debes definir PANDORA_DATA_DIR con la ruta completa de la carpeta "
        "donde están los archivos de Pandora."
    )

# PANDORA_DATA_DIR ya es la carpeta final; no se le agrega ningún subdirectorio.
CARPETA_DATOS = Path(_directorio_datos).expanduser()

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
    "revision_html": "pandora_revision.html",
    "liberar": "liberar.xlsx",
    "escalado": "escalado.xlsx",
}

RUTAS = {clave: ruta_datos(nombre) for clave, nombre in ARCHIVOS.items()}

RUTA_BLOQUEADOS = RUTAS["bloqueados"]
RUTA_DETALLE = RUTAS["detalle_bloqueado"]
RUTA_PRECIOS = RUTAS["precios"]
RUTA_PRECIOS_DISTRIBUIDOR = RUTAS["precios_distribuidor"]
RUTA_FINAL = RUTAS["resultado_final"]
RUTA_REVISION_HTML = RUTAS["revision_html"]
RUTA_LIBERAR = RUTAS["liberar"]
RUTA_ESCALADO = RUTAS["escalado"]

_ruta_decisiones_json = _obtener_variable_usuario("PANDORA_DECISIONES_JSON")
RUTA_DECISIONES_JSON = (
    Path(_ruta_decisiones_json).expanduser()
    if _ruta_decisiones_json
    else CARPETA_DATOS / "decisiones_pandora.json"
)
