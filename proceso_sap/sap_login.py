import os
import time
import subprocess
import win32com.client


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

    saplogon_path = (
        r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe"
    )

    subprocess.Popen(saplogon_path)

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