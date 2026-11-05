"""Reemplaza las listas VA14L con las decisiones manuales descargadas del HTML."""

import json
import numbers
from pathlib import Path

from openpyxl import Workbook, load_workbook

from configuracion import (
    RUTA_DECISIONES_JSON,
    RUTA_ESCALADO,
    RUTA_FINAL,
    RUTA_LIBERAR,
)
from proceso_excel.historial import registrar_decisiones_manuales, registrar_error_sistema


DECISIONES_VALIDAS = {"LIBERADO", "BLOQUEADO"}


def _normalizar_documento(valor):
    if valor is None:
        return ""
    if isinstance(valor, numbers.Real) and float(valor).is_integer():
        return str(int(valor))
    return str(valor).strip()


def _buscar_archivo_decisiones():
    carpeta = RUTA_DECISIONES_JSON.parent
    patron = f"{RUTA_DECISIONES_JSON.stem}*.json"
    candidatos = [ruta for ruta in carpeta.glob(patron) if ruta.is_file()]
    if not candidatos:
        raise FileNotFoundError(
            "No se encontró el JSON descargado. Se buscó el archivo más reciente "
            f"{patron} en {carpeta}. Configura el navegador para descargar allí "
            "o define PANDORA_DECISIONES_JSON con la ruta deseada."
        )
    return max(candidatos, key=lambda ruta: ruta.stat().st_mtime)


def _leer_documentos_pendientes():
    libro = load_workbook(RUTA_FINAL, read_only=True, data_only=True)
    hoja = libro.active
    encabezados = {
        str(celda.value).strip(): celda.column - 1
        for celda in hoja[1]
        if celda.value is not None
    }
    necesarias = {"Documento de ventas", "Decision Documento"}
    faltantes = necesarias - encabezados.keys()
    if faltantes:
        libro.close()
        raise ValueError(
            "pandora_final.xlsx no tiene las columnas: "
            + ", ".join(sorted(faltantes))
        )

    if "_control" not in libro.sheetnames:
        libro.close()
        raise ValueError(
            "pandora_final.xlsx no tiene el identificador de generación. "
            "Vuelve a generarlo con la versión actual."
        )
    generacion_id = libro["_control"].cell(1, 2).value

    pendientes = set()
    indice_documento = encabezados["Documento de ventas"]
    indice_decision = encabezados["Decision Documento"]
    for fila in hoja.iter_rows(min_row=2, values_only=True):
        if fila[indice_decision] == "Documento Por Revisar":
            documento = _normalizar_documento(fila[indice_documento])
            if documento:
                pendientes.add(documento)
    libro.close()
    return pendientes, generacion_id


def _leer_decisiones(ruta_json, pendientes, generacion_id):
    with Path(ruta_json).open("r", encoding="utf-8") as archivo:
        contenido = json.load(archivo)

    if contenido.get("version") != 1 or not isinstance(contenido.get("decisiones"), list):
        raise ValueError("El JSON no tiene el formato de decisiones Pandora esperado.")
    if contenido.get("generacion_id") != generacion_id:
        raise ValueError(
            "Este JSON pertenece a otra generación de Pandora. "
            "Abre la página de revisión actual y guarda las decisiones de nuevo."
        )

    decisiones = {"LIBERADO": [], "BLOQUEADO": []}
    vistas = {}
    for item in contenido["decisiones"]:
        documento = _normalizar_documento(item.get("documento"))
        decision = str(item.get("decision", "")).strip().upper()
        if not documento:
            continue
        if decision not in DECISIONES_VALIDAS:
            raise ValueError(
                f"Decisión no válida para {documento}: {decision}. "
                "Usa Liberado o Bloqueado."
            )
        if documento not in pendientes:
            raise ValueError(
                f"El documento {documento} no está pendiente en el pandora_final.xlsx actual."
            )
        if documento in vistas and vistas[documento] != decision:
            raise ValueError(f"El documento {documento} tiene decisiones contradictorias.")
        vistas[documento] = decision
        decisiones[decision].append(documento)

    return {
        decision: list(dict.fromkeys(documentos))
        for decision, documentos in decisiones.items()
    }


def _guardar_lista(ruta, documentos):
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Sheet1"
    hoja.cell(1, 1, "Documento de ventas")

    if documentos:
        for fila, documento in enumerate(documentos, start=2):
            hoja.cell(fila, 1, documento)
    else:
        hoja.cell(1, 2, "Estado")
        hoja.cell(2, 2, "No hay datos")

    libro.save(ruta)


def aplicar_decisiones():
    ruta_json = _buscar_archivo_decisiones()
    if not ruta_json.exists():
        raise FileNotFoundError(f"No se encontró el archivo de decisiones: {ruta_json}")
    if not Path(RUTA_FINAL).exists():
        raise FileNotFoundError(f"No se encontró el archivo de referencia: {RUTA_FINAL}")

    pendientes, generacion_id = _leer_documentos_pendientes()
    decisiones = _leer_decisiones(ruta_json, pendientes, generacion_id)
    if not decisiones["LIBERADO"] and not decisiones["BLOQUEADO"]:
        raise ValueError("El archivo no contiene decisiones seleccionadas; no se modificaron las listas.")

    # Sobrescribe las listas: solo incluye las decisiones manuales de este JSON.
    _guardar_lista(RUTA_LIBERAR, decisiones["LIBERADO"])
    _guardar_lista(RUTA_ESCALADO, decisiones["BLOQUEADO"])
    registrar_decisiones_manuales(decisiones, generacion_id)

    print(f"Decisiones leídas desde: {ruta_json}")
    print("Listas manuales actualizadas:")
    print(f"  Liberar: {len(decisiones['LIBERADO'])} -> {RUTA_LIBERAR}")
    print(f"  Bloquear: {len(decisiones['BLOQUEADO'])} -> {RUTA_ESCALADO}")
    print(
        "Cuando quieras ejecutarlas en SAP, cierra los Excel y ejecuta "
        "ejecuta_liberaciones.py."
    )


if __name__ == "__main__":
    try:
        aplicar_decisiones()
    except Exception as error:
        registrar_error_sistema("aplicar_decisiones_pandora.py", error)
        raise
