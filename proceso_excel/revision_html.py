"""Genera el HTML autónomo para revisar documentos pendientes de Pandora."""

import base64
import json
import numbers
from datetime import datetime
from pathlib import Path


_DIRECTORIO_VISTA = Path(__file__).resolve().parent / "revision_pandora"
_PLANTILLA = _DIRECTORIO_VISTA / "templates" / "revision_pandora.html"
_ESTILOS = _DIRECTORIO_VISTA / "static" / "revision_pandora.css"
_SCRIPT = _DIRECTORIO_VISTA / "static" / "revision_pandora.js"
_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_LOGO_LIGHT = _ASSETS / "maxservice-logo.png"
_LOGO_DARK = _ASSETS / "maxservice-logo-oscuro.png"
_ICON = _ASSETS / "maxservice-icono.png"


def _normalizar_documento(valor):
    if isinstance(valor, numbers.Real) and float(valor).is_integer():
        return str(int(valor))
    return str(valor)


def _datos_revision(df):
    pendientes = df.loc[
        df["Decision Documento"] == "Documento Por Revisar"
    ]

    documentos = []
    for documento, grupo in pendientes.groupby(
        "Documento de ventas", sort=False, dropna=True
    ):
        filas = json.loads(
            grupo.to_json(
                orient="records",
                date_format="iso",
                force_ascii=False,
            )
        )
        documentos.append({
            "documento": _normalizar_documento(documento),
            "lineas": filas,
        })

    return {
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "documentos": documentos,
    }


def exportar_revision_html(df, ruta, generacion_id, ruta_historial=None):
    """Combina las fuentes separadas en una página HTML autónoma."""
    revision = _datos_revision(df)
    revision["generacion_id"] = generacion_id
    datos = json.dumps(
        revision,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    # Evita que el contenido del Excel pueda cerrar el bloque JSON del HTML.
    datos = (
        datos.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )

    logo_light = base64.b64encode(_LOGO_LIGHT.read_bytes()).decode("ascii")
    logo_dark = base64.b64encode(_LOGO_DARK.read_bytes()).decode("ascii")
    icon = base64.b64encode(_ICON.read_bytes()).decode("ascii")
    html = _PLANTILLA.read_text(encoding="utf-8")
    html = html.replace("__CSS_INLINE__", _ESTILOS.read_text(encoding="utf-8"))
    html = html.replace("__APP_JS__", _SCRIPT.read_text(encoding="utf-8"))
    html = html.replace("__DATOS_REVISION__", datos)
    ruta_historial = Path(ruta_historial or "pandora_historial.html")
    html = html.replace("__HISTORIAL_HREF__", ruta_historial.name)
    html = html.replace("__LOGO_LIGHT_DATA__", f"data:image/png;base64,{logo_light}")
    html = html.replace("__LOGO_DARK_DATA__", f"data:image/png;base64,{logo_dark}")
    html = html.replace("__ICON_DATA__", f"data:image/png;base64,{icon}")

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(html, encoding="utf-8")

    total = len(revision["documentos"])
    print(f"Página de revisión generada ({total} documento(s)): {ruta}")
    return ruta
