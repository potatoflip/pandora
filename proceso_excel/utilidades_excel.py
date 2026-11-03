
import pandas as pd
import os
import win32com.client


# ============================================
# OBTENER DOCUMENTOS DESDE EXCEL
# ============================================

def obtener_documentos(path, columna=0):

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No se encontró el archivo: {path}"
        )

    df = pd.read_excel(
        path,
        engine="openpyxl",
        dtype=str
    )

    if isinstance(columna, int):
        documentos = df.iloc[:, columna]
    else:
        documentos = df[columna]

    documentos = (
        documentos.dropna()
        .astype(str)
        .str.strip()
    )

    documentos = documentos[documentos != ""]

    return documentos.tolist()


# ============================================
# ABRIR ARCHIVO EXCEL
# ============================================

def abrir_resultado(ruta):

    if not os.path.exists(ruta):
        raise FileNotFoundError(
            f"No se encontró el archivo: {ruta}"
        )

    print(f"Abriendo archivo: {os.path.basename(ruta)}")

    os.startfile(ruta)


# ============================================
# CERRAR ARCHIVOS EXCEL ABIERTOS
# ============================================

def cerrar_archivos_excel(rutas):

    # Normalizar las rutas para poder compararlas.

    archivos = {
        os.path.normcase(os.path.abspath(ruta))
        for ruta in rutas
    }

    try:

        excel = win32com.client.GetObject(
            Class="Excel.Application"
        )

        for libro in list(excel.Workbooks):

            ruta_libro = os.path.normcase(
                os.path.abspath(libro.FullName)
            )

            print(f"Detectado: {libro.FullName}")

            if ruta_libro in archivos:

                print(f"Cerrando: {libro.Name}")

                libro.Close(
                    SaveChanges=False
                )

    except Exception as e:

        print(f"No se pudo acceder a Excel: {e}")
