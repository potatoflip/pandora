"""Persistencia y vista HTML del historial operativo de Pandora."""

import base64
import html
import math
import sqlite3
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from configuracion import OFICINAS_VENTA, RUTA_HISTORIAL_DB, RUTA_HISTORIAL_HTML


def _ahora():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _texto(valor):
    if valor is None or type(valor).__name__ == "NAType":
        return ""
    try:
        if valor != valor:
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


@contextmanager
def _conectar():
    RUTA_HISTORIAL_DB.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(RUTA_HISTORIAL_DB, timeout=30)
    conexion.row_factory = sqlite3.Row
    conexion.executescript(
        """
        CREATE TABLE IF NOT EXISTS operaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            lote_id TEXT NOT NULL,
            evento TEXT NOT NULL,
            documento TEXT NOT NULL,
            solicitante TEXT NOT NULL DEFAULT '',
            nombre_solicitante TEXT NOT NULL DEFAULT '',
            canal TEXT NOT NULL DEFAULT '',
            oficina_codigo TEXT NOT NULL DEFAULT '',
            oficina TEXT NOT NULL DEFAULT '',
            vendedor_codigo TEXT NOT NULL DEFAULT '',
            vendedor TEXT NOT NULL DEFAULT '',
            origen TEXT NOT NULL DEFAULT '',
            decision TEXT NOT NULL DEFAULT '',
            estado TEXT NOT NULL DEFAULT '',
            etapa TEXT NOT NULL DEFAULT '',
            codigo_sap TEXT NOT NULL DEFAULT '',
            tipo_sap TEXT NOT NULL DEFAULT '',
            mensaje_sap TEXT NOT NULL DEFAULT '',
            detalle TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS ix_operaciones_doc
            ON operaciones(documento, id DESC);
        CREATE INDEX IF NOT EXISTS ix_operaciones_lote
            ON operaciones(lote_id, evento, decision);
        CREATE TABLE IF NOT EXISTS errores_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            componente TEXT NOT NULL,
            documento TEXT NOT NULL DEFAULT '',
            etapa TEXT NOT NULL DEFAULT '',
            codigo_sap TEXT NOT NULL DEFAULT '',
            tipo_sap TEXT NOT NULL DEFAULT '',
            mensaje_sap TEXT NOT NULL DEFAULT '',
            error TEXT NOT NULL DEFAULT '',
            detalle TEXT NOT NULL DEFAULT ''
        );
        """
    )
    try:
        with conexion:
            yield conexion
    finally:
        conexion.close()


def _contexto_fila(fila):
    oficina_codigo = _texto(fila.get("Oficina de ventas"))
    return {
        "documento": _texto(fila.get("Documento de ventas")),
        "solicitante": _texto(fila.get("Solicitante")),
        "nombre_solicitante": _texto(fila.get("Nombre solicitante")),
        "canal": _texto(fila.get("Canal distribución")),
        "oficina_codigo": oficina_codigo,
        "oficina": _texto(fila.get("Nombre oficina de ventas"))
        or OFICINAS_VENTA.get(oficina_codigo, ""),
        "vendedor_codigo": _texto(fila.get("Código vendedor")),
        "vendedor": _texto(fila.get("Vendedor")),
    }


def _insertar_operaciones(conexion, filas):
    if not filas:
        return
    columnas = (
        "fecha", "lote_id", "evento", "documento", "solicitante",
        "nombre_solicitante", "canal", "oficina_codigo", "oficina",
        "vendedor_codigo", "vendedor", "origen", "decision", "estado",
        "etapa", "codigo_sap", "tipo_sap", "mensaje_sap", "detalle",
    )
    consulta = (
        f"INSERT INTO operaciones ({','.join(columnas)}) "
        f"VALUES ({','.join('?' for _ in columnas)})"
    )
    conexion.executemany(
        consulta,
        [tuple(fila.get(columna, "") for columna in columnas) for fila in filas],
    )


def registrar_clasificaciones(df, generacion_id):
    """Guarda una fotografía por documento de la clasificación automática."""
    if df.empty:
        generar_historial_html()
        return

    filas = []
    errores = []
    vistos = set()
    decisiones = {
        "Documento Liberado": "LIBERADO",
        "Documento Rechazado": "BLOQUEADO",
        "Documento Por Revisar": "POR_REVISAR",
        "Documento con Error": "ERROR",
    }
    for registro in df.to_dict(orient="records"):
        contexto = _contexto_fila(registro)
        documento = contexto["documento"]
        if not documento or documento in vistos:
            continue
        vistos.add(documento)
        decision_original = _texto(registro.get("Decision Documento"))
        motivo = _texto(registro.get("Motivo"))
        filas.append({
            **contexto,
            "fecha": _ahora(),
            "lote_id": str(generacion_id),
            "evento": "CLASIFICACION",
            "origen": "AUTOMATICO",
            "decision": decisiones.get(decision_original, decision_original.upper()),
            "estado": "CLASIFICADO",
            "detalle": " | ".join(
                detalle
                for detalle in (
                    motivo,
                    f"Cruce vendedor: {_texto(registro.get('Estado cruce vendedor'))}"
                    if _texto(registro.get("Estado cruce vendedor")) != "Asignado"
                    else "",
                )
                if detalle
            ),
        })
        if decision_original == "Documento con Error":
            errores.append((
                _ahora(),
                "Clasificación Pandora",
                documento,
                "Evaluación del documento",
                "",
                "",
                "",
                decision_original,
                motivo,
            ))

    with _conectar() as conexion:
        _insertar_operaciones(conexion, filas)
        if errores:
            conexion.executemany(
                """INSERT INTO errores_sistema
                   (fecha, componente, documento, etapa, codigo_sap, tipo_sap,
                    mensaje_sap, error, detalle)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                errores,
            )
    generar_historial_html()


def _buscar_contexto(conexion, documento):
    fila = conexion.execute(
        """SELECT solicitante, nombre_solicitante, canal, oficina_codigo, oficina,
                  vendedor_codigo, vendedor
           FROM operaciones
           WHERE documento = ? AND evento IN ('CLASIFICACION', 'DECISION_MANUAL')
           ORDER BY id DESC LIMIT 1""",
        (str(documento),),
    ).fetchone()
    if not fila:
        return {}
    return dict(fila)


def registrar_decisiones_manuales(decisiones, generacion_id):
    """Registra las decisiones humanas descargadas desde la revisión HTML."""
    fecha = _ahora()
    filas = []
    with _conectar() as conexion:
        for decision, documentos in decisiones.items():
            for documento in documentos:
                contexto = _buscar_contexto(conexion, documento)
                filas.append({
                    **contexto,
                    "fecha": fecha,
                    "lote_id": str(generacion_id),
                    "evento": "DECISION_MANUAL",
                    "documento": str(documento),
                    "origen": "MANUAL",
                    "decision": str(decision).upper(),
                    "estado": "DECISION_REGISTRADA",
                    "detalle": "Decisión guardada desde la revisión Pandora.",
                })
        _insertar_operaciones(conexion, filas)
    generar_historial_html()


def registrar_resultado_va14l(
    documento,
    nombre_proceso,
    origen,
    resultado,
    lote_id,
):
    """Registra el resultado por documento de una ejecución VA14L."""
    estado_sap = resultado.get("sap") or {}
    proceso = str(nombre_proceso).casefold()
    decision = "LIBERADO" if "liber" in proceso else "BLOQUEADO"
    estado = _texto(resultado.get("estado"))
    documento = _texto(documento)
    fecha = _ahora()

    with _conectar() as conexion:
        contexto = _buscar_contexto(conexion, documento)
        fila = {
            **contexto,
            "fecha": fecha,
            "lote_id": str(lote_id),
            "evento": "EJECUCION_VA14L",
            "documento": documento,
            "origen": str(origen).upper(),
            "decision": decision,
            "estado": estado,
            "etapa": _texto(resultado.get("etapa")),
            "codigo_sap": _texto(estado_sap.get("Codigo")),
            "tipo_sap": _texto(estado_sap.get("Tipo")),
            "mensaje_sap": _texto(estado_sap.get("Mensaje")),
            "detalle": _texto(resultado.get("error")),
        }
        _insertar_operaciones(conexion, [fila])
        if estado == "ERROR":
            detalle = _texto(resultado.get("diagnostico"))
            conexion.execute(
                """INSERT INTO errores_sistema
                   (fecha, componente, documento, etapa, codigo_sap, tipo_sap,
                    mensaje_sap, error, detalle)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    fecha, "VA14L", documento, fila["etapa"], fila["codigo_sap"],
                    fila["tipo_sap"], fila["mensaje_sap"], fila["detalle"], detalle,
                ),
            )


def registrar_error_sistema(
    componente,
    error,
    documento="",
    etapa="",
    codigo_sap="",
    tipo_sap="",
    mensaje_sap="",
    detalle="",
):
    """Agrega una excepción al único registro persistente de errores."""
    traza = traceback.format_exc()
    if not detalle:
        detalle = traza
    elif traza.strip() != "NoneType: None":
        detalle = f"{detalle}\n\n{traza}"
    with _conectar() as conexion:
        conexion.execute(
            """INSERT INTO errores_sistema
               (fecha, componente, documento, etapa, codigo_sap, tipo_sap,
                mensaje_sap, error, detalle)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                _ahora(), str(componente), _texto(documento), _texto(etapa),
                _texto(codigo_sap), _texto(tipo_sap), _texto(mensaje_sap),
                str(error), str(detalle),
            ),
        )
    generar_historial_html()


def _esc(valor):
    return html.escape(_texto(valor), quote=True).replace("\n", "<br>")


def _render_operaciones(filas):
    if not filas:
        return '<tr><td colspan="8" class="empty">Aún no hay operaciones registradas.</td></tr>'
    resultado = []
    etiquetas_evento = {
        "CLASIFICACION": "Clasificación automática",
        "DECISION_MANUAL": "Decisión manual",
        "EJECUCION_VA14L": "Ejecución VA14L",
    }
    etiquetas_origen = {"AUTOMATICO": "Automático", "MANUAL": "Manual"}
    etiquetas_decision = {
        "LIBERADO": "Liberado",
        "BLOQUEADO": "Bloqueado",
        "POR_REVISAR": "Por revisar",
        "ERROR": "Error",
    }
    for fila in filas:
        evento = etiquetas_evento.get(fila["evento"], fila["evento"])
        origen = etiquetas_origen.get(fila["origen"], fila["origen"])
        decision = etiquetas_decision.get(fila["decision"], fila["decision"])
        resultado.append(
            "<tr>"
            f"<td>{_esc(fila['fecha'])}</td><td>{_esc(fila['documento'])}</td>"
            f"<td>{_esc(fila['vendedor'])}</td>"
            f"<td>{_esc(fila['oficina_codigo'])} {_esc(fila['oficina'])}</td>"
            f"<td>{_esc(evento)}</td><td>{_esc(origen)}</td>"
            f"<td>{_esc(decision)}</td><td>{_esc(fila['estado'])}</td></tr>"
        )
    return "".join(resultado)


def _render_resumen_vendedores(filas):
    if not filas:
        return '<tr><td colspan="5" class="empty">Aún no hay vendedores clasificados.</td></tr>'
    resultado = []
    for fila in filas:
        codigo = _esc(fila["vendedor_codigo"])
        nombre = _esc(fila["vendedor"] or "Sin asignación")
        vendedor = f"{codigo} · {nombre}" if codigo else nombre
        total = fila["liberados"] + fila["bloqueados"] + fila["revisar"]
        resultado.append(
            "<tr>"
            f"<td>{vendedor}</td><td>{fila['liberados']}</td>"
            f"<td>{fila['bloqueados']}</td><td>{fila['revisar']}</td>"
            f"<td><strong>{total}</strong></td></tr>"
        )
    return "".join(resultado)


def _render_grafico_oficinas(filas):
    if not filas:
        return '<div class="empty chart-empty">Aún no hay datos para graficar.</div>'

    categorias = (
        ("liberados", "var(--ok)", "Liberados"),
        ("bloqueados", "var(--urgent)", "Bloqueados"),
        ("revisar", "var(--warn)", "Por revisar"),
    )
    maximo = max(
        (fila[categoria] for fila in filas for categoria, _, _ in categorias),
        default=0,
    )
    paso = max(1, math.ceil(maximo / 4))
    tope = paso * 4
    ancho_grupo = 58
    margen_izquierdo = 44
    margen_derecho = 16
    alto = 320
    margen_superior = 20
    margen_inferior = 64
    alto_grafico = alto - margen_superior - margen_inferior
    ancho = margen_izquierdo + len(filas) * ancho_grupo + margen_derecho
    partes = [
        f'<svg class="history-chart-svg" viewBox="0 0 {ancho} {alto}" '
        f'width="{ancho}" height="{alto}" role="img" '
        'aria-label="Clasificación por oficina de ventas">',
    ]

    for indice in range(5):
        valor = tope - indice * paso
        y = margen_superior + alto_grafico * indice / 4
        partes.append(
            f'<line x1="{margen_izquierdo}" y1="{y:.1f}" '
            f'x2="{ancho - margen_derecho}" y2="{y:.1f}" '
            'stroke="var(--border)" stroke-dasharray="3 4"/>'
            f'<text x="{margen_izquierdo - 8}" y="{y + 4:.1f}" '
            'text-anchor="end" fill="var(--textDim)" font-size="10">'
            f"{valor}</text>"
        )

    for indice, fila in enumerate(filas):
        x_grupo = margen_izquierdo + indice * ancho_grupo + 8
        nombre_oficina = _esc(fila["oficina"] or "Sin oficina")
        codigo = _esc(fila["oficina_codigo"] or "—")
        for indice_categoria, (columna, color, etiqueta) in enumerate(categorias):
            valor = fila[columna]
            altura = alto_grafico * valor / tope if tope else 0
            x = x_grupo + indice_categoria * 12
            y = margen_superior + alto_grafico - altura
            partes.append(
                f'<g><title>{nombre_oficina} · {etiqueta}: {valor}</title>'
                f'<rect x="{x}" y="{y:.1f}" width="9" height="{altura:.1f}" '
                f'rx="2" fill="{color}"/></g>'
            )
        partes.append(
            f'<text x="{x_grupo + 15}" y="{alto - 36}" text-anchor="middle" '
            'fill="var(--text)" font-size="10">'
            f"{codigo}</text>"
        )
    partes.append("</svg>")
    return "".join(partes)


def _render_errores(filas):
    if not filas:
        return '<tr><td colspan="8" class="empty">No hay errores registrados.</td></tr>'
    resultado = []
    for fila in filas:
        detalle = "\n".join(
            parte for parte in (_texto(fila["error"]), _texto(fila["detalle"])) if parte
        )
        detalle_html = (
            f"<details><summary>Ver detalle</summary><pre>{html.escape(detalle)}</pre></details>"
            if detalle else "—"
        )
        resultado.append(
            "<tr>"
            f"<td>{_esc(fila['fecha'])}</td><td>{_esc(fila['componente'])}</td>"
            f"<td>{_esc(fila['documento'])}</td><td>{_esc(fila['etapa'])}</td>"
            f"<td>{_esc(fila['codigo_sap'])}</td><td>{_esc(fila['tipo_sap'])}</td>"
            f"<td>{_esc(fila['mensaje_sap'])}</td><td>{detalle_html}</td></tr>"
        )
    return "".join(resultado)


def generar_historial_html():
    """Regenera el HTML a partir de los dos registros SQLite persistentes."""
    with _conectar() as conexion:
        ultima_clasificacion = conexion.execute(
            "SELECT lote_id, fecha FROM operaciones WHERE evento='CLASIFICACION' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        lote = ultima_clasificacion["lote_id"] if ultima_clasificacion else ""
        fecha_generacion = ultima_clasificacion["fecha"] if ultima_clasificacion else "Sin ejecuciones"
        resumen = []
        resumen_vendedores = []
        resumen_va14l = conexion.execute(
            """SELECT oficina_codigo, oficina,
                 SUM(CASE WHEN origen='AUTOMATICO' AND decision='LIBERADO'
                               AND estado LIKE 'PROCESADO%' THEN 1 ELSE 0 END) auto_liberados,
                 SUM(CASE WHEN origen='AUTOMATICO' AND decision='BLOQUEADO'
                               AND estado LIKE 'PROCESADO%' THEN 1 ELSE 0 END) auto_bloqueados,
                 SUM(CASE WHEN origen='MANUAL' AND decision='LIBERADO'
                               AND estado LIKE 'PROCESADO%' THEN 1 ELSE 0 END) manual_liberados,
                 SUM(CASE WHEN origen='MANUAL' AND decision='BLOQUEADO'
                               AND estado LIKE 'PROCESADO%' THEN 1 ELSE 0 END) manual_bloqueados,
                 SUM(CASE WHEN estado='ERROR' THEN 1 ELSE 0 END) errores,
                 SUM(CASE WHEN estado='NO ENCONTRADO' THEN 1 ELSE 0 END) no_encontrados
               FROM operaciones WHERE evento='EJECUCION_VA14L'
               GROUP BY oficina_codigo, oficina ORDER BY oficina_codigo"""
        ).fetchall()
        if lote:
            resumen = conexion.execute(
                """SELECT c.oficina_codigo, c.oficina,
                     SUM(CASE WHEN c.decision='LIBERADO' THEN 1 ELSE 0 END) liberados,
                     SUM(CASE WHEN c.decision='BLOQUEADO' THEN 1 ELSE 0 END) bloqueados,
                     SUM(CASE WHEN c.decision='POR_REVISAR' AND NOT EXISTS (
                           SELECT 1 FROM operaciones dm
                           WHERE dm.evento='DECISION_MANUAL'
                             AND dm.lote_id=c.lote_id
                             AND dm.documento=c.documento
                         ) THEN 1 ELSE 0 END) revisar,
                     SUM(CASE WHEN c.decision='ERROR' THEN 1 ELSE 0 END) errores
                   FROM operaciones c
                   WHERE c.evento='CLASIFICACION' AND c.lote_id=?
                   GROUP BY c.oficina_codigo, c.oficina
                   ORDER BY c.oficina_codigo""",
                (lote,),
            ).fetchall()
            resumen_vendedores = conexion.execute(
                """SELECT c.vendedor_codigo, c.vendedor,
                     SUM(CASE WHEN c.decision='LIBERADO' THEN 1 ELSE 0 END) liberados,
                     SUM(CASE WHEN c.decision='BLOQUEADO' THEN 1 ELSE 0 END) bloqueados,
                     SUM(CASE WHEN c.decision='POR_REVISAR' AND NOT EXISTS (
                           SELECT 1 FROM operaciones dm
                           WHERE dm.evento='DECISION_MANUAL'
                             AND dm.lote_id=c.lote_id
                             AND dm.documento=c.documento
                         ) THEN 1 ELSE 0 END) revisar
                   FROM operaciones c
                   WHERE c.evento='CLASIFICACION' AND c.lote_id=?
                   GROUP BY c.vendedor_codigo, c.vendedor
                   ORDER BY COUNT(*) DESC, c.vendedor""",
                (lote,),
            ).fetchall()

            total_clasificado = conexion.execute(
                "SELECT COUNT(*) FROM operaciones WHERE evento='CLASIFICACION' AND lote_id=?",
                (lote,),
            ).fetchone()[0]
        else:
            total_clasificado = 0
        total_operaciones = conexion.execute(
            "SELECT COUNT(*) FROM operaciones"
        ).fetchone()[0]
        total_errores = conexion.execute(
            "SELECT COUNT(*) FROM errores_sistema"
        ).fetchone()[0]
        operaciones = conexion.execute(
            "SELECT * FROM operaciones ORDER BY id DESC LIMIT 2000"
        ).fetchall()
        errores = conexion.execute(
            "SELECT * FROM errores_sistema ORDER BY id DESC LIMIT 1000"
        ).fetchall()

    filas_resumen = []
    for fila in resumen:
        filas_resumen.append(
            "<tr>"
            f"<td>{_esc(fila['oficina_codigo'])}</td><td>{_esc(fila['oficina'])}</td>"
            f"<td>{fila['liberados']}</td><td>{fila['bloqueados']}</td>"
            f"<td>{fila['revisar']}</td><td>{fila['errores']}</td></tr>"
        )
    if not filas_resumen:
        filas_resumen.append('<tr><td colspan="6" class="empty">Aún no hay una clasificación registrada.</td></tr>')

    filas_vendedores = _render_resumen_vendedores(resumen_vendedores)
    grafico_oficinas = _render_grafico_oficinas(resumen)

    filas_va14l = []
    for fila in resumen_va14l:
        filas_va14l.append(
            "<tr>"
            f"<td>{_esc(fila['oficina_codigo'])}</td><td>{_esc(fila['oficina'])}</td>"
            f"<td>{fila['auto_liberados']}</td><td>{fila['auto_bloqueados']}</td>"
            f"<td>{fila['manual_liberados']}</td><td>{fila['manual_bloqueados']}</td>"
            f"<td>{fila['errores']}</td><td>{fila['no_encontrados']}</td></tr>"
        )
    if not filas_va14l:
        filas_va14l.append('<tr><td colspan="8" class="empty">Aún no hay ejecuciones VA14L.</td></tr>')

    directorio_ui = Path(__file__).resolve().parent / "revision_pandora"
    directorio_assets = Path(__file__).resolve().parent.parent / "assets"
    logo_light = base64.b64encode(
        (directorio_assets / "maxservice-logo.png").read_bytes()
    ).decode("ascii")
    logo_dark = base64.b64encode(
        (directorio_assets / "maxservice-logo-oscuro.png").read_bytes()
    ).decode("ascii")
    icono = base64.b64encode(
        (directorio_assets / "maxservice-icono.png").read_bytes()
    ).decode("ascii")
    html_pagina = _PLANTILLA_HTML.read_text(encoding="utf-8")
    html_pagina = html_pagina.replace(
        "__CSS_INLINE__",
        (directorio_ui / "static" / "revision_pandora.css").read_text(encoding="utf-8"),
    )
    sustituciones = {
        "__LOGO_LIGHT_DATA__": f"data:image/png;base64,{logo_light}",
        "__LOGO_DARK_DATA__": f"data:image/png;base64,{logo_dark}",
        "__ICON_DATA__": f"data:image/png;base64,{icono}",
        "__ULTIMA_GENERACION__": _esc(fecha_generacion),
        "__TOTAL_CLASIFICADO__": str(total_clasificado),
        "__TOTAL_LIBERADOS__": str(sum(fila["liberados"] for fila in resumen)),
        "__TOTAL_BLOQUEADOS__": str(sum(fila["bloqueados"] for fila in resumen)),
        "__TOTAL_REVISION__": str(sum(fila["revisar"] for fila in resumen)),
        "__TOTAL_OPERACIONES__": str(total_operaciones),
        "__TOTAL_ERRORES__": str(total_errores),
        "__RESUMEN_OFICINAS__": "".join(filas_resumen),
        "__RESUMEN_VA14L__": "".join(filas_va14l),
        "__RESUMEN_VENDEDORES__": filas_vendedores,
        "__GRAFICO_OFICINAS__": grafico_oficinas,
        "__OPERACIONES__": _render_operaciones(operaciones),
        "__ERRORES__": _render_errores(errores),
        "__OPERACIONES_CONTADOR__": str(total_operaciones),
        "__ERRORES_CONTADOR__": str(total_errores),
    }
    for marcador, valor in sustituciones.items():
        html_pagina = html_pagina.replace(marcador, valor)

    RUTA_HISTORIAL_HTML.parent.mkdir(parents=True, exist_ok=True)
    RUTA_HISTORIAL_HTML.write_text(html_pagina, encoding="utf-8")
    return RUTA_HISTORIAL_HTML


_PLANTILLA_HTML = (
    Path(__file__).resolve().parent
    / "revision_pandora"
    / "templates"
    / "historial_pandora.html"
)
