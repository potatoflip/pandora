import time
from datetime import datetime
hoy = datetime.today().strftime("%d.%m.%Y")

# ==========================================================
# EJECUTAR ZCLSD0022 LISTA
   # ==========================================================

def ejecutar_zclsd0022(session):

    print("Abriendo ZCLSD0022...")

    session.findById(
        "wnd[0]/tbar[0]/okcd"
    ).text = "/nzclsd0022"

    session.findById(
        "wnd[0]"
    ).sendVKey(0)

    time.sleep(1)

    print("Configurando selección...")

    session.findById(
        "wnd[0]/usr/radOP5"
    ).select()

    session.findById(
        "wnd[0]/usr/ctxtS_VKORG-LOW"
    ).text = "3000"

    session.findById(
        "wnd[0]/usr/ctxtP_VALID"
    ).text=hoy

    time.sleep(1)

    print("Ejecutando reporte...")

    session.findById(
        "wnd[0]/tbar[1]/btn[8]"
    ).press()

    time.sleep(3)

    print("Exportando Excel...")

    session.findById(
        "wnd[0]"
    ).sendVKey(3)

    session.findById(
        "wnd[0]/mbar/menu[0]/menu[3]/menu[1]"
    ).select()

    time.sleep(1)

    session.findById(
        "wnd[1]/tbar[0]/btn[0]"
    ).press()

    session.findById(
        "wnd[1]/usr/ctxtDY_PATH"
    ).text = r"C:\Users\MaxService\Pandora\Archivos_sap"

    session.findById(
        "wnd[1]/usr/ctxtDY_FILENAME"
    ).text = "precios.xlsx"

    session.findById(
        "wnd[1]/tbar[0]/btn[11]"
    ).press()

    print("✅ precios.xlsx generado")

   # ==========================================================
   # EJECUTAR ZCLSD0022 DISTRIBUIDOR
   # ==========================================================

def ejecutar_zclsd0022_distribuidor(session):

    print("Abriendo ZCLSD0022...")

    session.findById("wnd[0]/tbar[0]/okcd").text = "/nzclsd0022"

    session.findById("wnd[0]").sendVKey(0)

    print("Configurando selección...")

    session.findById("wnd[0]/usr/radOP4").setFocus()

    session.findById("wnd[0]/usr/radOP4").select()


    session.findById("wnd[0]/usr/ctxtS_VKORG-LOW").text = "3000"

    session.findById("wnd[0]/usr/ctxtS_VTWEG-LOW").text = "10"

    session.findById("wnd[0]/usr/ctxtP_VALID").text=hoy

    print("Ejecutando reporte...")

    session.findById(
        "wnd[0]/tbar[1]/btn[8]"
    ).press()


    print("Exportando Excel...")

    session.findById(
        "wnd[0]"
    ).sendVKey(3)

    session.findById(
        "wnd[0]/mbar/menu[0]/menu[3]/menu[1]"
    ).select()

    session.findById(
        "wnd[1]/tbar[0]/btn[0]"
    ).press()

    session.findById(
        "wnd[1]/usr/ctxtDY_PATH"
    ).text = r"C:\Users\MaxService\Pandora\Archivos_sap"

    session.findById(
        "wnd[1]/usr/ctxtDY_FILENAME"
    ).text = "precios_distribuidor.xlsx"

    session.findById(
        "wnd[1]/tbar[0]/btn[11]"
    ).press()

    print("✅ precios_distribuidor.xlsx generado")