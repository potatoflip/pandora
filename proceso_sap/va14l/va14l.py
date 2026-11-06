# ==========================================================
# COORDINADOR DEL PROCESO VA14L
# ==========================================================

import uuid

from proceso_excel.historial import generar_historial_html, registrar_resultado_va14l
from proceso_excel.cancelacion import ProcesoCancelado, comprobar_detencion
from proceso_excel.utilidades_excel import obtener_documentos

from .operaciones import procesar_documento
from .utilidades import ir_a_pantalla_principal


def ejecutar_va14l(
    session,
    ruta_excel,
    valor_lifsk,
    valor_faksk,
    nombre_proceso,
    origen="AUTOMATICO",
    progreso=None,
):
    """Procesa documentos y guarda sus resultados en el historial persistente."""
    print(f"Leyendo ruta: {ruta_excel}")
    documentos = obtener_documentos(ruta_excel)
    total = len(documentos)
    lote_id = uuid.uuid4().hex

    errores = []
    no_encontrados = []
    bloqueados_credito = []
    procesados = 0

    print(f"Se encontraron {total} documentos.")
    print(f"Valores objetivo: LIFSK={valor_lifsk!r}, FAKSK={valor_faksk!r}")
    if progreso:
        progreso(0, total, nombre_proceso)

    if total == 0:
        print("No hay documentos para procesar.")
        if progreso:
            progreso(1, 1, nombre_proceso)
        generar_historial_html()
        return session, errores

    try:
        for contador, documento in enumerate(documentos, start=1):
            comprobar_detencion()
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
            )
            estado_sap = resultado.get("sap") or {}
            estado = resultado.get("estado", "ERROR")

            registrar_resultado_va14l(
                documento=documento,
                nombre_proceso=nombre_proceso,
                origen=origen,
                resultado=resultado,
                lote_id=lote_id,
            )
            if progreso:
                progreso(contador, total, nombre_proceso)

            if estado.startswith("PROCESADO"):
                procesados += 1
            elif estado == "NO ENCONTRADO":
                no_encontrados.append(documento)
            elif estado == "BLOQUEADO POR CRÉDITO":
                bloqueados_credito.append(documento)
                print(f"Documento {documento}: bloqueado por crédito.")
            else:
                errores.append({
                    "Documento": documento,
                    "Etapa": resultado.get("etapa", ""),
                    "Codigo SAP": estado_sap.get("Codigo", ""),
                    "Mensaje SAP": estado_sap.get("Mensaje", ""),
                    "Error": resultado.get("error", ""),
                })
                print("Error registrado; se continuará con el siguiente documento.")

            # El resultado del documento ya quedó registrado. No se empieza
            # el siguiente si se solicitó detener durante este documento.
            comprobar_detencion()
    except ProcesoCancelado:
        print(
            f"\nDetención solicitada. Se completaron {procesados} documento(s) "
            "antes de parar; no se procesarán los siguientes."
        )
        generar_historial_html()
        ir_a_pantalla_principal(session)
        raise

    pendientes = total - procesados - len(no_encontrados) - len(bloqueados_credito) - len(errores)
    print(f"\n========== RESUMEN {nombre_proceso.upper()} ==========")
    print(f"Total documentos: {total}")
    print(f"Procesados correctamente: {procesados}")
    print(f"No encontrados: {len(no_encontrados)}")
    print(f"Bloqueados por crédito: {len(bloqueados_credito)}")
    print(f"Errores: {len(errores)}")
    print(f"Pendientes: {pendientes}")

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
                f"Documento: {error['Documento']} | Etapa: {error['Etapa']} | "
                f"Código SAP: {error['Codigo SAP']} | Mensaje: {error['Mensaje SAP']}"
            )

    generar_historial_html()
    ir_a_pantalla_principal(session)
    return session, errores
