import os
import time
import subprocess
import win32com.client
from configuracion import SAPLOGON_PATH


def maximizar_ventana(session):
    """Maximiza la ventana SAP al iniciar un flujo, si aún no lo está."""
    ventana = session.findById("wnd[0]")
    try:
        ya_maximizada = bool(ventana.IsMaximized)
    except Exception:
        # Algunas versiones de SAP GUI no exponen IsMaximized en scripting.
        ya_maximizada = False

    if not ya_maximizada:
        ventana.maximize()


def obtener_sesion():

    try:

        sap_gui = win32com.client.GetObject("SAPGUI")
        application = sap_gui.GetScriptingEngine

        if application.Children.Count > 0:

            connection = application.Children(0)

            if connection.Children.Count > 0:

                session = connection.Children(0)

                print("✅ Usando sesión SAP existente")

                return session

    except Exception:

        pass

    print("⚠️ No existe sesión SAP. Intentando abrir SAP...")

    return abrir_y_loguear()


def abrir_y_loguear():

    usuario = os.environ["SAP_USER"]
    password = os.environ["SAP_PASSWORD"]

    cliente = os.environ["SAP_CLIENT"]
    idioma = os.environ["SAP_LANGUAGE"]

    subprocess.Popen(str(SAPLOGON_PATH))

    time.sleep(8)

    sap_gui = win32com.client.GetObject("SAPGUI")

    application = sap_gui.GetScriptingEngine

    connection = application.OpenConnection(
        "1.- PRD HANA",
        True
    )

    time.sleep(3)

    session = connection.Children(0)

    try:

        session.findById(
            "wnd[0]/usr/txtRSYST-MANDT"
        ).text = cliente

        session.findById(
            "wnd[0]/usr/txtRSYST-BNAME"
        ).text = usuario

        session.findById(
            "wnd[0]/usr/pwdRSYST-BCODE"
        ).text = password

        session.findById(
            "wnd[0]/usr/txtRSYST-LANGU"
        ).text = idioma

        session.findById(
            "wnd[0]"
        ).sendVKey(0)

        print("✅ Login realizado")

    except Exception:

        print(
            "ℹ️ Probablemente ya existe una sesión autenticada."
        )

    return session
