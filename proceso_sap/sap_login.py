"""Conexión y selección segura de sesiones abiertas de SAP GUI."""

import os
import subprocess
import time

import win32com.client

from configuracion import SAPLOGON_PATH


_CAMPOS_LOGIN = (
    "wnd[0]/usr/txtRSYST-MANDT",
    "wnd[0]/usr/txtRSYST-BNAME",
    "wnd[0]/usr/pwdRSYST-BCODE",
    "wnd[0]/usr/txtRSYST-LANGU",
)


def _obtener_aplicacion():
    try:
        sap_gui = win32com.client.GetObject("SAPGUI")
        return sap_gui.GetScriptingEngine
    except Exception:
        return None


def _sesiones_abiertas(aplicacion):
    """Recorre todas las conexiones y sesiones, no solo la primera pestaña."""
    sesiones = []
    try:
        conexiones = aplicacion.Children
        for indice_conexion in range(conexiones.Count):
            try:
                conexion = conexiones(indice_conexion)
                sesiones_conexion = conexion.Children
                for indice_sesion in range(sesiones_conexion.Count):
                    try:
                        sesiones.append(sesiones_conexion(indice_sesion))
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass
    return sesiones


def _es_pantalla_login(session):
    for id_campo in _CAMPOS_LOGIN:
        try:
            session.findById(id_campo)
            return True
        except Exception:
            continue
    return False


def _sesion_utilizable(session):
    try:
        session.findById("wnd[0]")
        return not _es_pantalla_login(session)
    except Exception:
        return False


def _sesion_mas_avanzada(sesiones):
    """Prefiere una sesión autenticada; si no hay, reutiliza una pantalla de login."""
    for session in sesiones:
        if _sesion_utilizable(session):
            return session
    return sesiones[0] if sesiones else None


def resolver_confirmacion_sesiones(session):
    """Conserva las otras sesiones SAP al aceptar un inicio duplicado."""
    try:
        radio = session.findById("wnd[1]/usr/radMULTI_LOGON_OPT1")
    except Exception:
        return False

    radio.select()
    try:
        session.findById("wnd[1]/tbar[0]/btn[0]").press()
    except Exception:
        session.findById("wnd[1]").sendVKey(0)
    print("ℹ️ SAP pidió confirmar sesiones duplicadas; se conservarán las demás sesiones abiertas.")
    return True


def _esperar_inicio(session, timeout=60):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        try:
            session.Busy
        except Exception:
            pass

        if resolver_confirmacion_sesiones(session):
            time.sleep(0.5)
            continue

        if _sesion_utilizable(session):
            return session
        time.sleep(0.5)

    try:
        mensaje = str(session.findById("wnd[0]/sbar").Text).strip()
    except Exception:
        mensaje = ""
    detalle = f" Mensaje SAP: {mensaje}" if mensaje else ""
    raise RuntimeError(
        "SAP no completó el inicio de sesión dentro del tiempo esperado. "
        "Revisa si quedó un cuadro de diálogo abierto y vuelve a intentar." + detalle
    )


def _iniciar_sesion(session):
    resolver_confirmacion_sesiones(session)
    if _sesion_utilizable(session):
        print("✅ Usando sesión SAP autenticada")
        return session

    cliente = os.environ["SAP_CLIENT"]
    usuario = os.environ["SAP_USER"]
    password = os.environ["SAP_PASSWORD"]
    idioma = os.environ["SAP_LANGUAGE"]

    try:
        session.findById(_CAMPOS_LOGIN[0]).text = cliente
        session.findById(_CAMPOS_LOGIN[1]).text = usuario
        session.findById(_CAMPOS_LOGIN[2]).text = password
        session.findById(_CAMPOS_LOGIN[3]).text = idioma
        session.findById("wnd[0]").sendVKey(0)
    except Exception as error:
        raise RuntimeError(
            "Se encontró una sesión SAP, pero no se pudo completar su pantalla "
            "de inicio de sesión. No se abrirá otra conexión para evitar el "
            "aviso de sesiones duplicadas."
        ) from error

    _esperar_inicio(session)
    print("✅ Login realizado")
    return session


def obtener_sesion():
    aplicacion = _obtener_aplicacion()
    if aplicacion is not None:
        sesiones = _sesiones_abiertas(aplicacion)
        for sesion_abierta in sesiones:
            try:
                resolver_confirmacion_sesiones(sesion_abierta)
            except Exception:
                continue
        session = _sesion_mas_avanzada(sesiones)
        if session is not None:
            if _sesion_utilizable(session):
                print(f"✅ Sesión SAP existente encontrada entre {len(sesiones)} sesión(es) abiertas")
            else:
                print("⚠️ Hay una sesión SAP abierta en la pantalla de inicio; se reutilizará")
            return _iniciar_sesion(session)

    print("⚠️ No hay sesiones SAP utilizables.")
    if aplicacion is None:
        print("Abriendo SAP Logon...")
        subprocess.Popen(str(SAPLOGON_PATH))
        limite = time.monotonic() + 30
        while time.monotonic() < limite:
            aplicacion = _obtener_aplicacion()
            if aplicacion is not None:
                sesiones = _sesiones_abiertas(aplicacion)
                session = _sesion_mas_avanzada(sesiones)
                if session is not None:
                    return _iniciar_sesion(session)
                break
            time.sleep(0.5)
        if aplicacion is None:
            raise RuntimeError("SAP Logon abrió, pero no expuso el motor de scripting SAP GUI.")

    print("Abriendo conexión SAP PRD HANA...")
    connection = aplicacion.OpenConnection("1.- PRD HANA", True)
    limite = time.monotonic() + 20
    session = None
    while time.monotonic() < limite:
        session = _sesion_mas_avanzada(_sesiones_abiertas(aplicacion))
        if session is not None:
            break
        time.sleep(0.5)
    if session is None:
        try:
            session = connection.Children(0)
        except Exception as error:
            raise RuntimeError("SAP no creó una sesión de trabajo para PRD HANA.") from error
    return _iniciar_sesion(session)


def maximizar_ventana(session):
    """Maximiza la ventana SAP al iniciar un flujo, si aún no lo está."""
    ventana = session.findById("wnd[0]")
    try:
        ya_maximizada = bool(ventana.IsMaximized)
    except Exception:
        ya_maximizada = False
    if not ya_maximizada:
        ventana.maximize()
