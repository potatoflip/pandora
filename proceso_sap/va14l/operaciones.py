# ==========================================================
# OPERACIONES SAP DEL PROCESO VA14L
# ==========================================================

from .utilidades import (
    obtener_estado_sap,
    esperar_sap,
    capturar_diagnostico_sap,
    avanzar_hasta_documento,
    cancelar_componentes_hasta_bloqueo,
    fijar_bloqueo,
    confirmar_guardado,
    ir_a_pantalla_principal,
    es_bloqueo_credito,
    BloqueoCredito,
)
from proceso_excel.cancelacion import ProcesoCancelado, comprobar_detencion


def es_bloqueo_por_credito(estado_sap):
    """Identifica el mensaje SAP V1154 (alias conservado por compatibilidad)."""
    return es_bloqueo_credito(estado_sap)


def resultado_bloqueado_credito(etapa, estado_sap, error=""):
    """Construye un resultado específico para documentos bloqueados por crédito."""
    print("Documento bloqueado por verificación de crédito (SAP V1154).")

    return {
        "estado": "BLOQUEADO POR CRÉDITO",
        "etapa": etapa,
        "sap": estado_sap,
        "error": error,
    }


def procesar_documento(session, documento, valor_lifsk, valor_faksk):
    """Ejecuta en SAP la secuencia VA14L para un documento."""
    etapa = "Inicio"

    try:
        comprobar_detencion()
        # 1. Abrir VA14L.
        etapa = "Abrir VA14L"

        session.findById("wnd[0]/tbar[0]/okcd").text = "/nva14l"
        session.findById("wnd[0]").sendVKey(0)

        # SAP puede conservar valores de búsquedas anteriores en estos campos.
        for id_campo in (
            "wnd[0]/usr/ctxtVTWEG-LOW",
            "wnd[0]/usr/ctxtSPART-LOW",
            "wnd[0]/usr/ctxtVKBUR-LOW",
            "wnd[0]/usr/ctxtVKGRP-LOW",
        ):
            session.findById(id_campo).text = ""

        session.findById("wnd[0]/usr/ctxtVKORG").text = "3000"

        session.findById("wnd[0]/usr/radALL_VB").select()
        session.findById("wnd[0]/usr/radALL_VB").setFocus()

        # 2. Ingresar documento.
        etapa = "Ingresar documento"

        campo_documento = session.findById("wnd[0]/usr/ctxtVBELN-LOW")
        campo_documento.text = str(documento)

        # 3. Buscar documento.
        etapa = "Buscar documento"

        campo_documento.setFocus()

        # Se conservan los dos Enter del proceso original.
        session.findById("wnd[0]").sendVKey(0)
        session.findById("wnd[0]").sendVKey(0)

        # Ejecutar búsqueda con F8 y esperar a que SAP termine.
        session.findById("wnd[0]").sendVKey(8)
        esperar_sap(session)
        comprobar_detencion()

        # 4. Leer respuesta de SAP.
        estado_sap = obtener_estado_sap(session)
        mensaje_sap = estado_sap["Mensaje"]

        print(f"Respuesta de SAP: {mensaje_sap}")

        if es_bloqueo_credito(estado_sap):
            ir_a_pantalla_principal(session)
            return resultado_bloqueado_credito(etapa, estado_sap)

        if "no existe ningún documento" in mensaje_sap.casefold():
            print(f"Documento {documento} no encontrado.")
            return {
                "estado": "NO ENCONTRADO",
                "etapa": etapa,
                "sap": estado_sap,
                "error": "",
            }

        print(f"Documento {documento} encontrado.")

        # 5. Abrir detalle.
        comprobar_detencion()
        etapa = "Abrir detalle del documento"
        session.findById("wnd[1]").sendVKey(0)

        # 6. Navegar al bloqueo y aceptar con Enter todos los popups.
        etapa = "Navegar al bloqueo"
        session.findById("wnd[0]").sendVKey(5)
        session.findById("wnd[0]").sendVKey(34)
        avanzar_hasta_documento(session)

        # 7. Modificar bloqueo de entrega (LIFSK).
        etapa = "Modificar bloqueo de entrega (LIFSK)"
        fijar_bloqueo(session, "VBAK-LIFSK", valor_lifsk)

        # 8. Modificar bloqueo de factura (FAKSK).
        etapa = "Modificar bloqueo de factura (FAKSK)"
        fijar_bloqueo(session, "VBAK-FAKSK", valor_faksk)

        # 9. Guardar y verificar que SAP confirme el grabado.
        etapa = "Guardar documento"
        cancelar_componentes_hasta_bloqueo(session)
        comprobar_detencion()
        session.findById("wnd[0]").sendVKey(11)
        estado_sap = confirmar_guardado(session)

        documento_incompleto = estado_sap.get("DocumentoIncompleto", False)

        if documento_incompleto:
            print(
                f"Documento {documento} guardado aunque estaba incompleto. "
                "Queda marcado para revisión."
            )
            estado_resultado = "PROCESADO - INCOMPLETO (REVISAR)"
        else:
            print(f"Documento {documento} guardado: {estado_sap['Mensaje']}")
            estado_resultado = "PROCESADO"

        return {
            "estado": estado_resultado,
            "etapa": etapa,
            "sap": estado_sap,
            "error": "",
        }

    except ProcesoCancelado:
        # Si los campos se habían editado, /n y responder "No" deja el
        # documento sin cambios guardados antes de propagar la cancelación.
        ir_a_pantalla_principal(session)
        raise

    except BloqueoCredito as bloqueo:
        # Alerta roja en la barra de estado, sin popup: se registra,
        # se sale sin guardar y se pasa al siguiente documento.
        ir_a_pantalla_principal(session)
        return resultado_bloqueado_credito(etapa, bloqueo.estado_sap)

    except Exception as error:
        # IMPORTANTE: capturar las ventanas ANTES de cualquier recuperación.
        # El diagnóstico no envía Enter ni modifica controles SAP.
        detalle_diagnostico = capturar_diagnostico_sap(
            session=session,
            documento=documento,
            etapa=etapa,
            error=error,
        )

        estado_sap = obtener_estado_sap(session)
        mensaje_sap = estado_sap["Mensaje"]

        if es_bloqueo_credito(estado_sap):
            ir_a_pantalla_principal(session)
            return resultado_bloqueado_credito(etapa, estado_sap, str(error))

        if "no existe ningún documento" in mensaje_sap.casefold():
            print(f"Documento {documento} no encontrado.")
            # VR-490 deja SAP en la lista; no hace falta enviar más teclas.
            return {
                "estado": "NO ENCONTRADO",
                "etapa": etapa,
                "sap": estado_sap,
                "error": "",
                "diagnostico": detalle_diagnostico,
            }

        # En ocasiones SAP confirma el guardado justo después del timeout.
        # Si el diagnóstico ya muestra V1-311 para este mismo pedido,
        # no debemos registrarlo como ERROR.
        codigo_sap = str(estado_sap.get("Codigo", "")).upper()
        codigo_sap = codigo_sap.replace("-", "").replace(" ", "")
        mensaje_confirmacion = mensaje_sap.casefold()
        if (
            etapa == "Guardar documento"
            and codigo_sap == "V1311"
            and str(documento) in mensaje_sap
            and "se ha grabado" in mensaje_confirmacion
        ):
            print(
                f"SAP confirmó el guardado del documento {documento}; "
                "se registra como PROCESADO."
            )
            return {
                "estado": "PROCESADO",
                "etapa": etapa,
                "sap": estado_sap,
                "error": "",
                "diagnostico": detalle_diagnostico,
            }

        print(f"\nERROR en documento {documento}")
        print(f"Etapa: {etapa}")
        print(f"Código SAP: {estado_sap['Codigo']}")
        print(f"Mensaje SAP: {mensaje_sap}")
        print(f"Detalle: {error}")
        print("Diagnóstico SAP incluido en el registro central de errores.")

        # Salida segura: /n y "No" si SAP pregunta si grabar.
        ir_a_pantalla_principal(session)

        return {
            "estado": "ERROR",
            "etapa": etapa,
            "sap": estado_sap,
            "error": str(error),
            "diagnostico": detalle_diagnostico,
        }
