# ==========================================================
# UTILIDADES DEL PROCESO VA14L
# ==========================================================

import time
import re
from datetime import datetime
from configuracion import CARPETA_DATOS
from pathlib import Path


class BloqueoCredito(Exception):
    """SAP devolvió V1154 (bloqueo por crédito) en la barra de estado."""

    def __init__(self, estado_sap):
        super().__init__(f"Bloqueo por crédito: {estado_sap.get('Mensaje', '')}")
        self.estado_sap = estado_sap


# ----------------------------------------------------------
# Lectura del estado de SAP
# ----------------------------------------------------------

def obtener_estado_sap(session):
    """Recupera el mensaje y los datos de la barra de estado de SAP."""
    try:
        barra = session.findById("wnd[0]/sbar")

        mensaje = barra.Text.strip()
        codigo = getattr(barra, "MessageId", "")
        numero = getattr(barra, "MessageNumber", "")
        tipo = getattr(barra, "MessageType", "")

        if codigo and numero:
            codigo_error = f"{codigo}-{numero}"
        elif codigo:
            codigo_error = str(codigo)
        else:
            codigo_error = ""

        return {
            "Mensaje": mensaje,
            "Codigo": codigo_error,
            "Tipo": str(tipo),
        }

    except Exception:
        return {
            "Mensaje": "No se pudo recuperar el estado de SAP.",
            "Codigo": "",
            "Tipo": "",
        }


def normalizar_codigo_sap(codigo):
    """Normaliza el código para comparar, por ejemplo V1-081 o V1081."""
    return str(codigo or "").upper().replace("-", "").replace(" ", "")


def es_bloqueo_credito(estado_sap):
    """True si la barra de estado muestra V1154."""
    codigo = normalizar_codigo_sap(estado_sap.get("Codigo"))
    mensaje = normalizar_codigo_sap(estado_sap.get("Mensaje"))
    return codigo == "V1154" or "V1154" in mensaje


def esperar_sap(session, timeout=10):
    """Espera a que SAP termine de procesar la última acción."""
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        try:
            if not session.Busy:
                return
        except Exception:
            return
        time.sleep(0.05)


# ----------------------------------------------------------
# Diagnóstico (solo lectura)
# ----------------------------------------------------------

def _leer_propiedad(control, propiedad):
    """Lee una propiedad SAP GUI sin interrumpir el diagnóstico."""
    try:
        valor = getattr(control, propiedad)
        return str(valor)
    except Exception:
        return "<no disponible>"


def _describir_controles(control, nivel=0, max_nivel=5):
    """
    Recorre los controles de una ventana SAP y recoge sus propiedades
    visibles/identificativas. No modifica ni acciona ningún control.
    """
    if nivel > max_nivel:
        return []

    lineas = []
    sangria = "  " * nivel

    for propiedad in ("Id", "Type", "Name", "Text", "Tooltip", "DefaultTooltip"):
        valor = _leer_propiedad(control, propiedad)
        if valor != "<no disponible>" and valor:
            lineas.append(f"{sangria}{propiedad}: {valor}")

    try:
        hijos = control.Children
        cantidad = int(hijos.Count)
    except Exception:
        return lineas

    for indice in range(cantidad):
        try:
            hijo = hijos.Item(indice)
            lineas.append(f"{sangria}Control hijo [{indice}]:")
            lineas.extend(
                _describir_controles(hijo, nivel + 1, max_nivel)
            )
        except Exception as error:
            lineas.append(
                f"{sangria}No se pudo leer el control hijo [{indice}]: {error}"
            )

    return lineas


def registrar_diagnostico_sap(session, documento, etapa, error, carpeta_logs=None):
    """
    Guarda el estado de SAP y la estructura de wnd[0]/wnd[1] al producirse
    un error. Esta función es exclusivamente de lectura: no envía teclas.
    """
    lineas = [
        "DIAGNOSTICO SAP VA14L",
        f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Documento: {documento}",
        f"Etapa: {etapa}",
        f"Error Python: {error}",
        "",
    ]

    estado = obtener_estado_sap(session)
    lineas.extend([
        "=== BARRA DE ESTADO SAP ===",
        f"Codigo: {estado['Codigo']}",
        f"Tipo: {estado['Tipo']}",
        f"Mensaje: {estado['Mensaje']}",
        "",
    ])

    for ventana_id in ("wnd[0]", "wnd[1]"):
        lineas.append(f"=== {ventana_id} ===")
        try:
            ventana = session.findById(ventana_id)
            lineas.extend(_describir_controles(ventana))
        except Exception as error_ventana:
            lineas.append(f"No disponible: {error_ventana}")
        lineas.append("")

    # El coordinador entrega la carpeta según el proceso (liberados/bloqueados).
    # La ruta alternativa conserva compatibilidad si se llama sin ese argumento.
    if carpeta_logs is None:
        carpeta_logs = CARPETA_DATOS
    else:
        carpeta_logs = Path(carpeta_logs)

    try:
        carpeta_logs.mkdir(parents=True, exist_ok=True)
        marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        nombre = f"diagnostico_va14l_{documento}_{marca_tiempo}.txt"
        ruta = carpeta_logs / nombre
        ruta.write_text("\n".join(lineas), encoding="utf-8")
        print(f"Diagnóstico SAP guardado en: {ruta}")
        return str(ruta)
    except Exception as error_guardado:
        print(f"No se pudo guardar el diagnóstico SAP: {error_guardado}")
        return None


# ----------------------------------------------------------
# Popups
# ----------------------------------------------------------

def _texto_ventana(ventana, nivel=0, max_nivel=6):
    """Recoge texto y metadatos de wnd[1] sin accionar controles."""
    if nivel > max_nivel:
        return []
    datos = []
    for propiedad in ("Id", "Type", "Name", "Text", "Tooltip", "MessageId", "MessageNumber"):
        valor = _leer_propiedad(ventana, propiedad)
        if valor not in ("<no disponible>", ""):
            datos.append(f"{propiedad}: {valor}")
    try:
        hijos = ventana.Children
        cantidad = int(hijos.Count)
    except Exception:
        return datos
    for indice in range(cantidad):
        try:
            datos.extend(_texto_ventana(hijos.Item(indice), nivel + 1, max_nivel))
        except Exception as error:
            datos.append(f"Error leyendo hijo {indice}: {error}")
    return datos


def _buscar_ventana_secundaria(session):
    try:
        return session.findById("wnd[1]")
    except Exception:
        return None


def _codigo_popup(ventana, estado):
    datos = _texto_ventana(ventana)
    texto = " ".join(datos).upper()
    message_id = ""
    message_number = ""
    for dato in datos:
        if dato.startswith("MessageId:"):
            message_id = dato.split(":", 1)[1].strip()
        elif dato.startswith("MessageNumber:"):
            message_number = dato.split(":", 1)[1].strip()
    if message_id and message_number:
        codigo = f"{message_id}-{message_number}"
    else:
        codigo = estado.get("Codigo", "")
    codigo = normalizar_codigo_sap(codigo)
    if not codigo:
        coincidencia = re.search(r"\bV1\s*[- ]?\s*(081|423|677|154)\b", texto)
        if coincidencia:
            codigo = "V1" + coincidencia.group(1)
    return codigo, texto


# ----------------------------------------------------------
# Pantalla de bloqueos (LIFSK / FAKSK)
# ----------------------------------------------------------

def obtener_combo(session, nombre):
    """
    Busca el combo por su ruta conocida; si cambia la ruta, lo busca
    por nombre (VBAK-LIFSK / VBAK-FAKSK).
    """
    base = (
        "wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01/"
        "ssubSUBSCREEN_BODY:SAPMV45A:4400/"
        "ssubHEADER_FRAME:SAPMV45A:4440/cmb"
    )
    try:
        return session.findById(base + nombre)
    except Exception:
        return session.findByName(nombre, "GuiComboBox")


def _campos_bloqueo_disponibles(session):
    """Confirma que ambos combos estén disponibles en la pantalla actual."""
    try:
        obtener_combo(session, "VBAK-LIFSK")
        obtener_combo(session, "VBAK-FAKSK")
        return True
    except Exception:
        return False


def avanzar_hasta_documento(session, timeout=20, max_enters=15):
    """
    Pulsa Enter en TODOS los popups hasta que aparezcan los campos
    LIFSK/FAKSK. En cada vuelta revisa la barra de estado: si aparece
    V1154 lanza BloqueoCredito.
    """
    inicio = time.monotonic()
    enters = 0
    estables = 0

    while time.monotonic() - inicio < timeout:
        esperar_sap(session)

        estado = obtener_estado_sap(session)
        if es_bloqueo_credito(estado):
            raise BloqueoCredito(estado)

        ventana = _buscar_ventana_secundaria(session)
        if ventana is not None:
            estables = 0
            codigo, contenido = _codigo_popup(ventana, estado)
            if codigo == "V1154":
                raise BloqueoCredito(
                    {"Mensaje": contenido, "Codigo": "V1-154", "Tipo": "E"}
                )
            enters += 1
            if enters > max_enters:
                raise RuntimeError(
                    f"Más de {max_enters} popups seguidos. Último: {contenido}"
                )
            print(f"Popup {codigo or 'sin código'} -> Enter")
            ventana.sendVKey(0)
            time.sleep(0.15)
            continue

        if _campos_bloqueo_disponibles(session):
            estables += 1
            if estables >= 2:  # 2 comprobaciones seguidas sin popup nuevo
                print(f"Popups aceptados: {enters}")
                return enters
        else:
            estables = 0
            if estado["Tipo"] in ("E", "A"):
                raise RuntimeError(
                    "SAP mostró un error y no abrió el documento: "
                    f"{estado['Codigo']} - {estado['Mensaje']}"
                )
        time.sleep(0.15)

    raise RuntimeError("Tiempo agotado esperando los campos LIFSK/FAKSK.")


def fijar_bloqueo(session, nombre, valor):
    """Cambia un combo de bloqueo y verifica que haya quedado el valor."""
    combo = obtener_combo(session, nombre)

    if not combo.Changeable:
        estado = obtener_estado_sap(session)
        raise RuntimeError(
            f"El campo {nombre} no es editable (¿pedido en uso por otro usuario?). "
            f"Barra: {estado['Codigo']} - {estado['Mensaje']}"
        )

    combo.key = valor
    esperar_sap(session)

    estado = obtener_estado_sap(session)
    if es_bloqueo_credito(estado):
        raise BloqueoCredito(estado)

    if str(combo.key).strip() != str(valor).strip():
        raise RuntimeError(
            f"{nombre} no quedó en {valor!r}; quedó en {combo.key!r}"
        )

    print(f"{nombre} = {valor!r}")


def _es_popup_documento_incompleto(ventana):
    """Identifica el popup de SAP que pregunta si se graba un documento incompleto."""
    datos = _texto_ventana(ventana)
    contenido = " ".join(datos).casefold()

    frases = (
        "grabar documento incompleto",
        "el documento aún está incompleto",
        "el documento aun esta incompleto",
    )
    return any(frase in contenido for frase in frases)


def _grabar_documento_incompleto(session, ventana):
    """
    Selecciona explícitamente el botón 'Grabar' del popup de documento
    incompleto. No usa Enter porque podría elegir una opción distinta.
    """
    try:
        boton = session.findById("wnd[1]/usr/btnSPOP-VAROPTION1")
    except Exception:
        try:
            boton = ventana.findByName("SPOP-VAROPTION1", "GuiButton")
        except Exception as error:
            raise RuntimeError(
                "SAP mostró el popup de documento incompleto, pero no se "
                "encontró el botón específico 'Grabar'."
            ) from error

    boton.press()
    esperar_sap(session)


def confirmar_guardado(session, timeout=15):
    """
    Espera la confirmación de SAP. Si aparece 'Grabar documento incompleto',
    selecciona explícitamente 'Grabar' y marca el resultado para revisión.
    """
    inicio = time.monotonic()
    documento_incompleto = False

    while time.monotonic() - inicio < timeout:
        esperar_sap(session)
        estado = obtener_estado_sap(session)

        if es_bloqueo_credito(estado):
            raise BloqueoCredito(estado)

        ventana = _buscar_ventana_secundaria(session)
        if ventana is not None:
            if _es_popup_documento_incompleto(ventana):
                if not documento_incompleto:
                    print(
                        "SAP solicita grabar un documento incompleto. "
                        "Seleccionando explícitamente 'Grabar'."
                    )
                _grabar_documento_incompleto(session, ventana)
                documento_incompleto = True
                time.sleep(0.15)
                continue

            # Se conserva el comportamiento previo para otros avisos
            # que SAP presente durante la confirmación del guardado.
            ventana.sendVKey(0)
            time.sleep(0.15)
            continue

        if estado["Tipo"] == "S":
            estado["DocumentoIncompleto"] = documento_incompleto
            return estado

        if estado["Tipo"] in ("E", "A"):
            raise RuntimeError(
                f"No se guardó: {estado['Codigo']} - {estado['Mensaje']}"
            )

        time.sleep(0.15)

    raise RuntimeError("No se recibió confirmación de grabado de SAP.")


# ----------------------------------------------------------
# Salida a la pantalla principal
# ----------------------------------------------------------

def ir_a_pantalla_principal(session):
    """
    Envía /n sin guardar. Si SAP pregunta si desea grabar los datos,
    responde NO (nunca guarda a ciegas con Enter).
    """
    try:
        session.findById("wnd[0]/tbar[0]/okcd").text = "/n"
        session.findById("wnd[0]").sendVKey(0)
        esperar_sap(session)

        for _ in range(3):
            ventana = _buscar_ventana_secundaria(session)
            if ventana is None:
                break
            try:
                ventana.findByName("SPOP-OPTION2", "GuiButton").press()  # "No"
            except Exception:
                try:
                    session.findById("wnd[1]/usr/btnSPOP-OPTION2").press()
                except Exception:
                    ventana.sendVKey(0)
            esperar_sap(session)

    except Exception as error:
        print(f"No se pudo volver a la pantalla principal: {error}")
