"""Genera una página HTML de demostración para revisar el diseño de Pandora."""

from pathlib import Path

import pandas as pd

from proceso_excel.revision_html import exportar_revision_html


RUTA_PREVIA = (
    Path(__file__).resolve().parent
    / "vista_previa.html"
)


def generar_vista_previa():
    """Crea una muestra autónoma con líneas normales, críticas y aprobadas."""
    filas = [
        {
            "Documento de ventas": 721761,
            "Posición": "10",
            "Material": "MAT-10001",
            "Texto breve": "Producto con margen dentro del objetivo",
            "Cantidad": 12,
            "Precio Venta": 125000,
            "Descuento %": 18.0,
            "Margen Linea %": 28.5,
            "Margen Documento %": 32.1,
            "Decision Linea": "Revision",
            "Motivo": "Requiere autorización | Márgenes cumplen objetivos | Margen Línea=28.5% | Margen Doc=32.1%",
            "Decision Documento": "Documento Por Revisar",
        },
        {
            "Documento de ventas": 721761,
            "Posición": "20",
            "Material": "MAT-10002",
            "Texto breve": "Producto con margen bajo",
            "Cantidad": 4,
            "Precio Venta": 89000,
            "Descuento %": 23.5,
            "Margen Linea %": 12.4,
            "Margen Documento %": 32.1,
            "Decision Linea": "Revision",
            "Motivo": "Requiere autorización | Desc=23.5% | Margen Línea=12.4% | Margen Doc=32.1%",
            "Decision Documento": "Documento Por Revisar",
        },
        {
            "Documento de ventas": 721761,
            "Posición": "30",
            "Material": "MAT-10003",
            "Texto breve": "Producto dentro del estándar",
            "Cantidad": 2,
            "Precio Venta": 45000,
            "Descuento %": 10.0,
            "Margen Linea %": 34.0,
            "Margen Documento %": 32.1,
            "Decision Linea": "Aprobada",
            "Motivo": "Descuento dentro del estándar",
            "Decision Documento": "Documento Por Revisar",
        },
    ]
    exportar_revision_html(
        pd.DataFrame(filas),
        RUTA_PREVIA,
        generacion_id="vista-previa",
    )


if __name__ == "__main__":
    generar_vista_previa()
