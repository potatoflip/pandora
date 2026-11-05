"""Agrega oficina y vendedor a las filas de Pandora."""

import unicodedata

import pandas as pd

from configuracion import (
    OFICINAS_VENTA,
    RUTA_CLIENTE_VENDEDOR,
    RUTA_VENDEDORES,
)


def _normalizar_clave(valor):
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto


def _normalizar_nombre_columna(valor):
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return texto.casefold().replace(" ", "").replace("_", "")


def _buscar_columna(columnas, fragmento):
    buscado = _normalizar_nombre_columna(fragmento)
    for columna in columnas:
        nombre = _normalizar_nombre_columna(columna)
        if buscado in nombre:
            return columna
    return None


def _leer_relaciones_cliente_vendedor():
    relaciones = pd.read_excel(RUTA_CLIENTE_VENDEDOR, dtype=str, engine="openpyxl")
    columnas_cliente = [
        columna
        for columna in relaciones.columns
        if _normalizar_nombre_columna(columna).startswith("cliente")
    ]

    if len(columnas_cliente) >= 2:
        columna_cliente, columna_vendedor = columnas_cliente[:2]
    elif len(relaciones.columns) == 2:
        columna_cliente, columna_vendedor = relaciones.columns
    elif len(relaciones.columns) >= 7:
        # KNVP: KUNNR está en la columna 1 y KUNN2 (interlocutor ZV) en la 7.
        columna_cliente, columna_vendedor = relaciones.columns[0], relaciones.columns[6]
    else:
        raise ValueError(
            "cliente_vendedor.xlsx debe tener dos columnas Cliente o la estructura KNVP."
        )

    columna_funcion = _buscar_columna(relaciones.columns, "funcion interlocutor")
    if columna_funcion:
        relaciones = relaciones.loc[
            relaciones[columna_funcion].astype("string").str.strip().str.upper() == "ZV"
        ]

    columna_organizacion = _buscar_columna(relaciones.columns, "organizacion ventas")
    if columna_organizacion:
        relaciones = relaciones.loc[
            relaciones[columna_organizacion].map(_normalizar_clave) == "3000"
        ]

    columna_canal = _buscar_columna(relaciones.columns, "canal distribucion")
    columnas = [columna_cliente, columna_vendedor]
    if columna_canal:
        columnas.append(columna_canal)

    resultado = relaciones[columnas].copy()
    nombres = ["_cliente", "_codigo_vendedor"]
    if columna_canal:
        nombres.append("_canal")
    resultado.columns = nombres
    resultado["_cliente"] = resultado["_cliente"].map(_normalizar_clave)
    resultado["_codigo_vendedor"] = resultado["_codigo_vendedor"].map(_normalizar_clave)
    if "_canal" not in resultado.columns:
        resultado["_canal"] = ""
    else:
        resultado["_canal"] = resultado["_canal"].map(_normalizar_clave)

    return resultado.loc[
        resultado["_cliente"].ne("") & resultado["_codigo_vendedor"].ne("")
    ].drop_duplicates()


def enriquecer_contexto_comercial(df):
    """Añade nombre de oficina y vendedor sin detener el análisis si falta el maestro."""
    resultado = df.copy()
    if "Oficina de ventas" not in resultado.columns:
        raise ValueError(
            "bloqueados.xlsx debe incluir la columna 'Oficina de ventas' (VKBUR)."
        )

    resultado["Oficina de ventas"] = resultado["Oficina de ventas"].map(_normalizar_clave)
    resultado["Nombre oficina de ventas"] = resultado["Oficina de ventas"].map(
        lambda codigo: OFICINAS_VENTA.get(codigo, "")
    )
    resultado["Código vendedor"] = ""
    resultado["Vendedor"] = ""
    resultado["Estado cruce vendedor"] = "Sin asignación"

    try:
        relaciones = _leer_relaciones_cliente_vendedor()
        if relaciones.empty:
            raise ValueError(
                "cliente_vendedor.xlsx no contiene relaciones ZV para la organización 3000."
            )
        vendedores = pd.read_excel(RUTA_VENDEDORES, dtype=str, engine="openpyxl")
        columnas_requeridas = {"Cliente", "Nombre 1"}
        if not columnas_requeridas.issubset(vendedores.columns):
            raise ValueError("vendedores.xlsx debe incluir las columnas Cliente y Nombre 1.")

        vendedores = vendedores[["Cliente", "Nombre 1"]].copy()
        vendedores["Cliente"] = vendedores["Cliente"].map(_normalizar_clave)
        vendedores["Nombre 1"] = vendedores["Nombre 1"].fillna("").astype(str).str.strip()
        nombres_vendedor = (
            vendedores.loc[vendedores["Cliente"].ne("")]
            .drop_duplicates("Cliente", keep="last")
            .set_index("Cliente")["Nombre 1"]
            .to_dict()
        )

        por_cliente_canal = {}
        por_cliente = {}
        for fila in relaciones.itertuples(index=False, name=None):
            cliente, codigo_vendedor, canal = fila
            por_cliente_canal.setdefault((cliente, canal), set()).add(codigo_vendedor)
            por_cliente.setdefault(cliente, set()).add(codigo_vendedor)

        solicitante = resultado["Solicitante"].map(_normalizar_clave)
        canal = resultado["Canal distribución"].map(_normalizar_clave)

        def resolver_vendedor(cliente, canal_cliente):
            codigos = por_cliente_canal.get((cliente, canal_cliente), set())
            if not codigos:
                codigos = por_cliente.get(cliente, set())
            if len(codigos) == 1:
                return next(iter(codigos)), "Asignado"
            if len(codigos) > 1:
                return "", "Asignación ambigua"
            return "", "Sin asignación"

        asignaciones = [
            resolver_vendedor(cliente, canal_cliente)
            for cliente, canal_cliente in zip(solicitante, canal)
        ]
        resultado["Código vendedor"] = [codigo for codigo, _ in asignaciones]
        resultado["Estado cruce vendedor"] = [estado for _, estado in asignaciones]
        resultado["Vendedor"] = resultado["Código vendedor"].map(nombres_vendedor).fillna("")
        resultado.loc[
            resultado["Código vendedor"].ne("") & resultado["Vendedor"].eq(""),
            "Estado cruce vendedor",
        ] = "Código sin nombre en vendedores.xlsx"
    except Exception as error:
        from proceso_excel.historial import registrar_error_sistema

        registrar_error_sistema(
            "Cruce cliente-vendedor",
            error,
            detalle="Se continuará el análisis con oficina de ventas, pero sin asignar vendedor.",
        )

    return resultado
