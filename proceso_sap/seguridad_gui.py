"""Atiende confirmaciones de seguridad SAP GUI para exportar Excel."""

import os
import time
import unicodedata

import win32con
import win32gui

from configuracion import CARPETA_DATOS


_TITULOS_SEGURIDAD = ("seguridad sap gui", "sap gui security")
_TEXTOS_RECORDAR = ("retener mi decision", "remember my decision")
_TEXTOS_PERMITIR = ("permitir", "allow")


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.replace("&", "").strip().casefold()


def _ventanas_seguridad():
    ventanas = []

    def visitar(hwnd, _):
        try:
            titulo = _normalizar(win32gui.GetWindowText(hwnd))
            if (
                win32gui.IsWindowVisible(hwnd)
                and any(texto in titulo for texto in _TITULOS_SEGURIDAD)
            ):
                ventanas.append(hwnd)
        except Exception:
            pass
        return True

    win32gui.EnumWindows(visitar, None)
    return ventanas


def _controles_ventana(hwnd_ventana):
    controles = []

    def visitar(hwnd, _):
        controles.append(hwnd)
        return True

    win32gui.EnumChildWindows(hwnd_ventana, visitar, None)
    return controles


def _ruta_excel_en_carpeta_datos(texto):
    texto_normalizado = os.path.normcase(str(texto).replace("/", "\\"))
    carpeta = os.path.normcase(os.path.abspath(str(CARPETA_DATOS))).rstrip("\\")
    inicio = texto_normalizado.find(carpeta + "\\")
    if inicio < 0:
        return None

    for extension in (".xlsx", ".xlsm", ".xls"):
        fin = texto_normalizado.find(extension, inicio)
        if fin < 0:
            continue
        ruta = texto_normalizado[inicio : fin + len(extension)].rstrip(" '\".,;)")
        try:
            if os.path.commonpath((carpeta, ruta)) == carpeta:
                return ruta
        except ValueError:
            continue
    return None


def _resolver_ventana(hwnd_ventana):
    controles = _controles_ventana(hwnd_ventana)
    textos = []
    checkbox = None
    boton_permitir = None

    for hwnd in controles:
        try:
            clase = win32gui.GetClassName(hwnd)
            texto = win32gui.GetWindowText(hwnd)
        except Exception:
            continue
        normalizado = _normalizar(texto)
        textos.append(texto)
        if clase.casefold() != "button":
            continue
        if any(etiqueta in normalizado for etiqueta in _TEXTOS_RECORDAR):
            checkbox = hwnd
        elif any(
            normalizado == etiqueta or normalizado.startswith(etiqueta + " ")
            for etiqueta in _TEXTOS_PERMITIR
        ):
            boton_permitir = hwnd

    contenido = " ".join(textos)
    ruta = _ruta_excel_en_carpeta_datos(contenido)
    if ruta is None:
        raise RuntimeError(
            "Se detectó Seguridad SAP GUI, pero el diálogo no identifica un "
            "Excel dentro de PANDORA_DATA_DIR. No se permitió automáticamente. "
            f"Contenido detectado: {contenido}"
        )
    if checkbox is None or boton_permitir is None:
        raise RuntimeError(
            "El diálogo de Seguridad SAP GUI coincide con un Excel de Pandora, "
            "pero no se encontraron la casilla 'Retener mi decisión' y el botón "
            f"'Permitir'. Contenido detectado: {contenido}"
        )

    estado = win32gui.SendMessage(checkbox, win32con.BM_GETCHECK, 0, 0)
    if estado != win32con.BST_CHECKED:
        win32gui.SendMessage(checkbox, win32con.BM_CLICK, 0, 0)
        estado = win32gui.SendMessage(checkbox, win32con.BM_GETCHECK, 0, 0)
    if estado != win32con.BST_CHECKED:
        raise RuntimeError(
            "No se pudo marcar 'Retener mi decisión' en Seguridad SAP GUI. "
            f"Archivo: {ruta}"
        )

    try:
        win32gui.SetForegroundWindow(hwnd_ventana)
    except Exception:
        pass
    win32gui.SendMessage(boton_permitir, win32con.BM_CLICK, 0, 0)

    limite = time.monotonic() + 2
    while time.monotonic() < limite:
        if not win32gui.IsWindow(hwnd_ventana) or not win32gui.IsWindowVisible(
            hwnd_ventana
        ):
            return ruta
        time.sleep(0.05)
    raise RuntimeError(
        "Se pulsó 'Permitir', pero el diálogo de Seguridad SAP GUI no se cerró. "
        f"Archivo: {ruta}"
    )


def resolver_confirmaciones_exportacion(timeout=20, espera_sin_dialogo=1.2):
    """Permite las confirmaciones SAP GUI de Excel y cuenta cuántas aparecieron.

    La rutina solo permite diálogos con el título de seguridad SAP GUI y una
    ruta .xls/.xlsx/.xlsm dentro de CARPETA_DATOS. Si no hay confirmación,
    devuelve cero. Si aparecen varias, las resuelve una por una.
    """
    inicio = time.monotonic()
    ultima_confirmacion = None
    cantidad = 0

    while time.monotonic() - inicio < timeout:
        ventanas = _ventanas_seguridad()
        if ventanas:
            ruta = _resolver_ventana(ventanas[0])
            cantidad += 1
            ultima_confirmacion = time.monotonic()
            print(
                f"Seguridad SAP GUI: decisión recordada y permiso concedido "
                f"para {ruta} (ventana {cantidad})."
            )
            continue

        ahora = time.monotonic()
        if cantidad and ultima_confirmacion is not None:
            if ahora - ultima_confirmacion >= 0.6:
                break
        elif ahora - inicio >= espera_sin_dialogo:
            break
        time.sleep(0.1)
    else:
        raise TimeoutError(
            "Se agotó el tiempo esperando las confirmaciones de Seguridad SAP GUI."
        )

    print(f"Confirmaciones de seguridad SAP GUI atendidas: {cantidad}.")
    return cantidad
