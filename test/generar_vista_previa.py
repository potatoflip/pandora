"""Genera una página HTML de demostración para revisar el diseño de Pandora."""

from pathlib import Path
import sys

import pandas as pd

# Permite ejecutar este archivo directamente desde test/ sin perder acceso al
# paquete del proyecto ubicado en la carpeta padre.
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROYECTO))

from proceso_excel.revision_html import exportar_revision_html


RUTA_PREVIA = Path(__file__).resolve().parent / "vista_previa.html"


def generar_vista_previa():
    """Crea una muestra autónoma con líneas normales, críticas y aprobadas."""
    filas = [
        {
            "Documento de ventas": 721761,
            "Nombre solicitante": "NORTE LAB SPA",
            "Canal distribución": "10",
            "Solicitante": "20000580",
            "Posición": "10",
            "Material": "MAT-10001",
            "Texto breve": "Producto con margen dentro del objetivo",
            "Cantidad": 12,
            "Descuento %": 18.0,
            "Margen Linea %": 28.5,
            "Margen Documento %": 32.1,
            "Precio Venta Normal": 10200,
            "Precio Venta Distribuidor": 9600,
            "Precio Venta": 9600,
            "Lista de precios aplicada": "Distribuidor",
            "Decision Linea": "Revision",
            "Motivo": "Requiere autorización | Márgenes cumplen objetivos | Margen Línea=28.5% | Margen Doc=32.1%",
            "Decision Documento": "Documento Por Revisar",
            "Factura histórica": "91194395",
            "Fecha de precio histórica": "2026-06-01",
            "Precio neto histórico": 10000,
            "Precio lista histórico": 9600,
            "Costes internos históricos": 6240,
        },
        {
            "Documento de ventas": 721761,
            "Nombre solicitante": "NORTE LAB SPA",
            "Canal distribución": "10",
            "Solicitante": "20000580",
            "Posición": "20",
            "Material": "MAT-10002",
            "Texto breve": "Producto con margen bajo",
            "Cantidad": 4,
            "Precio Venta": 89000,
            "Descuento %": 23.5,
            "Margen Linea %": 12.4,
            "Margen Documento %": 32.1,
            "Precio Venta Normal": 15000,
            "Precio Venta Distribuidor": None,
            "Precio Venta": 15000,
            "Lista de precios aplicada": "Normal (respaldo sin precio distribuidor)",
            "Decision Linea": "Revision",
            "Motivo": "Requiere autorización | Desc=23.5% | Margen Línea=12.4% | Margen Doc=32.1%",
            "Decision Documento": "Documento Por Revisar",
            "Factura histórica": None,
            "Fecha de precio histórica": None,
            "Precio neto histórico": None,
            "Precio lista histórico": None,
            "Costes internos históricos": None,
        },
        {
            "Documento de ventas": 721761,
            "Nombre solicitante": "NORTE LAB SPA",
            "Canal distribución": "10",
            "Solicitante": "20000580",
            "Posición": "30",
            "Material": "MAT-10003",
            "Texto breve": "Producto dentro del estándar",
            "Cantidad": 2,
            "Precio Venta": 45000,
            "Descuento %": 10.0,
            "Margen Linea %": 34.0,
            "Margen Documento %": 32.1,
            "Precio Venta Normal": 45000,
            "Precio Venta Distribuidor": 42000,
            "Precio Venta": 42000,
            "Lista de precios aplicada": "Distribuidor",
            "Decision Linea": "Aprobada",
            "Motivo": "Descuento dentro del estándar",
            "Decision Documento": "Documento Por Revisar",
            "Factura histórica": "91200124",
            "Fecha de precio histórica": "2026-08-15",
            "Precio neto histórico": 44000,
            "Precio lista histórico": 42000,
            "Costes internos históricos": 28000,
        },
    ]
    exportar_revision_html(
        pd.DataFrame(filas),
        RUTA_PREVIA,
        generacion_id="vista-previa",
    )


if __name__ == "__main__":
    generar_vista_previa()
