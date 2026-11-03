# ==========================================================
# COORDINADOR DEL PROCESO VA14L
# ==========================================================

import csv
import os
from datetime import datetime

from proceso_excel.utilidades_excel import obtener_documentos

from .operaciones import procesar_documento
from .registro import COLUMNAS_LOG, registrar_log
from .utilidades import ir_a_pantalla_principal


def ejecutar_va14l(
    session,
    ruta_excel,
    valor_lifsk,
    valor_faksk,
    nombre_proceso,
):
    """Procesa documentos desde un Excel con los bloqueos indicados."""

    carpeta_base = os.path.dirname(ruta_excel)
    proceso_normalizado = nombre_proceso.casefold()

    if "liber" in proceso_normalizado:
        carpeta_logs = os.path.join(carpeta_base, "log_liberados")
    else:
        carpeta_logs = os.path.join(carpeta_base, "log_bloqueados")

    os.makedirs(carpeta_logs, exist_ok=True)
    fecha_ejecucion = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_log = os.path.join(
        carpeta_logs,
        f"{nombre_proceso}_log_{fecha_ejecucion}.csv",
    )

    print(f"Leyendo ruta: {ruta_excel}")

    documentos = obtener_documentos(ruta_excel)
    total = len(documentos)

    errores = []
    no_encontrados = []
    bloqueados_credito = []
    procesados = 0

    print(f"Se encontraron {total} documentos.")
    print(f"Valores objetivo: LIFSK={valor_lifsk!r}, FAKSK={valor_faksk!r}")

    if total == 0:
        print("No hay documentos para procesar.")
        return session, errores

    with open(
        ruta_log,
        mode="w",
        newline="",
        encoding="utf-8-sig",
    ) as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=COLUMNAS_LOG,
            delimiter=";",
        )

        escritor.writeheader()
        archivo.flush()

        print(f"Registro de ejecución: {ruta_log}")

        for contador, documento in enumerate(documentos, start=1):
            print(
                f"\n[{contador}/{total}] Documento {documento} | "
                f"Correctos: {procesados} | "
                f"No encontrados: {len(no_encontrados)} | "
                f"Bloqueados por crédito: {len(bloqueados_credito)} | "
                f"Errores: {len(errores)}"
            )

            resultado = procesar_documento(
                session,
                documento,
                valor_lifsk,
                valor_faksk,
                carpeta_logs=carpeta_logs,
            )

            estado_sap = resultado["sap"]
            estado = resultado["estado"]

            registrar_log(
                escritor,
                archivo,
                documento,
                estado,
                resultado["etapa"],
                estado_sap["Mensaje"],
                estado_sap["Codigo"],
                estado_sap["Tipo"],
                resultado["error"],
            )

            # Fuerza la escritura a disco para no perder registros
            # si el proceso se interrumpe.
            try:
                os.fsync(archivo.fileno())
            except OSError:
                pass

            if estado == "PROCESADO":
                procesados += 1
            elif estado == "NO ENCONTRADO":
                no_encontrados.append(documento)
            elif estado == "BLOQUEADO POR CRÉDITO":
                bloqueados_credito.append(documento)
                print(f"Documento {documento}: bloqueado por crédito.")
            else:
                errores.append({
                    "Documento": documento,
                    "Etapa": resultado["etapa"],
                    "Codigo SAP": estado_sap["Codigo"],
                    "Mensaje SAP": estado_sap["Mensaje"],
                    "Error": resultado["error"],
                })
                print("Error registrado; se continuará con el siguiente documento.")

        pendientes = (
            total
            - procesados
            - len(no_encontrados)
            - len(bloqueados_credito)
            - len(errores)
        )

        print(f"\n========== RESUMEN {nombre_proceso.upper()} ==========")
        print(f"Total documentos: {total}")
        print(f"Procesados correctamente: {procesados}")
        print(f"No encontrados: {len(no_encontrados)}")
        print(f"Bloqueados por crédito: {len(bloqueados_credito)}")
        print(f"Errores: {len(errores)}")
        print(f"Pendientes: {pendientes}")
        print("\nArchivo de registro:")
        print(ruta_log)

        if bloqueados_credito:
            print("\nDOCUMENTOS BLOQUEADOS POR CRÉDITO (V1154):")
            for documento in bloqueados_credito:
                print(documento)

        if no_encontrados:
            print("\nDOCUMENTOS NO ENCONTRADOS:")
            for documento in no_encontrados:
                print(documento)

        if errores:
            print("\nDOCUMENTOS CON ERRORES:")
            for error in errores:
                print(
                    f"Documento: {error['Documento']} | "
                    f"Etapa: {error['Etapa']} | "
                    f"Código SAP: {error['Codigo SAP']} | "
                    f"Mensaje: {error['Mensaje SAP']}"
                )

    # Al terminar, volver a la pantalla principal de SAP con /n.
    ir_a_pantalla_principal(session)

    return session, errores
