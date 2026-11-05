"""Persistencia y vista HTML del historial operativo de Pandora."""

import html
import sqlite3
import traceback
from contextlib import contextmanager
from datetime import datetime

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
        return '<tr><td colspan="10" class="empty">Aún no hay operaciones registradas.</td></tr>'
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
        detalle = _esc(fila["detalle"] or fila["mensaje_sap"])
        evento = etiquetas_evento.get(fila["evento"], fila["evento"])
        origen = etiquetas_origen.get(fila["origen"], fila["origen"])
        decision = etiquetas_decision.get(fila["decision"], fila["decision"])
        detalle_html = (
            f"<details><summary>Ver</summary><div class=detail>{detalle}</div></details>"
            if detalle else "—"
        )
        resultado.append(
            "<tr>"
            f"<td>{_esc(fila['fecha'])}</td><td>{_esc(fila['documento'])}</td>"
            f"<td>{_esc(fila['solicitante'])}</td><td>{_esc(fila['vendedor'])}</td>"
            f"<td>{_esc(fila['oficina_codigo'])} {_esc(fila['oficina'])}</td>"
            f"<td>{_esc(evento)}</td><td>{_esc(origen)}</td>"
            f"<td>{_esc(decision)}</td><td>{_esc(fila['estado'])}</td>"
            f"<td>{detalle_html}</td></tr>"
        )
    return "".join(resultado)


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
                """SELECT oficina_codigo, oficina,
                     SUM(CASE WHEN decision='LIBERADO' THEN 1 ELSE 0 END) liberados,
                     SUM(CASE WHEN decision='BLOQUEADO' THEN 1 ELSE 0 END) bloqueados,
                     SUM(CASE WHEN decision='POR_REVISAR' THEN 1 ELSE 0 END) revisar,
                     SUM(CASE WHEN decision='ERROR' THEN 1 ELSE 0 END) errores
                   FROM operaciones
                   WHERE evento='CLASIFICACION' AND lote_id=?
                   GROUP BY oficina_codigo, oficina
                   ORDER BY oficina_codigo""",
                (lote,),
            ).fetchall()

        total_clasificado = sum(
            fila["liberados"] + fila["bloqueados"] + fila["revisar"] + fila["errores"]
            for fila in resumen
        )
        manuales_liberados = conexion.execute(
            """SELECT COUNT(*) FROM operaciones
               WHERE evento='EJECUCION_VA14L' AND origen='MANUAL'
                 AND decision='LIBERADO' AND estado LIKE 'PROCESADO%'"""
        ).fetchone()[0]
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

    html_pagina = _PLANTILLA_HTML
    sustituciones = {
        "__ULTIMA_GENERACION__": _esc(fecha_generacion),
        "__TOTAL_CLASIFICADO__": str(total_clasificado),
        "__LIBERADOS_MANUALES__": str(manuales_liberados),
        "__TOTAL_OPERACIONES__": str(total_operaciones),
        "__TOTAL_ERRORES__": str(total_errores),
        "__RESUMEN_OFICINAS__": "".join(filas_resumen),
        "__RESUMEN_VA14L__": "".join(filas_va14l),
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


_PLANTILLA_HTML = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Historial Pandora</title>
  <style>
    :root{font-family:Segoe UI,Arial,sans-serif;color:#182230;background:#f4f6fa}*{box-sizing:border-box}
    body{margin:0}header{background:#102a43;color:#fff;padding:22px max(20px,calc((100% - 1400px)/2));display:flex;align-items:center;justify-content:space-between;gap:20px}
    h1{font-size:23px;margin:0}header p{margin:5px 0 0;color:#d7e2f0}.nav a{color:#fff;text-decoration:none;border:1px solid #91a4ba;border-radius:8px;padding:9px 12px}
    main{max-width:1400px;margin:24px auto;padding:0 20px 40px}.meta{color:#667085;font-size:13px;margin-bottom:16px}.metrics{display:grid;grid-template-columns:repeat(4,minmax(140px,1fr));gap:12px;margin-bottom:22px}
    .metric,.panel{background:white;border:1px solid #e2e7ef;border-radius:12px;box-shadow:0 3px 12px #102a4308}.metric{padding:16px}.metric span{display:block;color:#667085;font-size:12px}.metric strong{display:block;font-size:25px;margin-top:5px}
    .tabs{display:flex;gap:8px;margin-bottom:14px}.tab{border:1px solid #cdd5e1;background:white;color:#344054;border-radius:8px;padding:10px 14px;cursor:pointer;font-weight:600}.tab.active{background:#155eef;border-color:#155eef;color:white}
    .panel{padding:18px;margin-bottom:18px}.tab-panel[hidden]{display:none}.panel h2{margin:0 0 5px;font-size:18px}.hint{margin:0 0 14px;color:#667085;font-size:13px}
    .table-wrap{overflow:auto;max-height:65vh;border:1px solid #e2e7ef;border-radius:8px}table{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}th,td{padding:10px 11px;text-align:left;border-bottom:1px solid #edf0f4}th{position:sticky;top:0;background:#f8fafc;z-index:1;color:#475467}td:nth-child(n+3){font-variant-numeric:tabular-nums}
    .empty{text-align:center;color:#667085;padding:20px}input[type=search]{width:min(380px,100%);padding:10px 12px;border:1px solid #cdd5e1;border-radius:8px;margin-bottom:12px}details summary{cursor:pointer;color:#155eef}pre,.detail{white-space:pre-wrap;overflow-wrap:anywhere;max-width:600px;color:#475467;font:12px/1.5 Consolas,monospace}footer{color:#667085;font-size:12px;margin-top:16px}
    @media(max-width:700px){header{align-items:flex-start;flex-direction:column}.metrics{grid-template-columns:1fr 1fr}main{padding:0 12px 28px}.panel{padding:12px}}
  </style>
</head>
<body>
  <header><div><h1>Historial Pandora</h1><p>Clasificaciones, ejecuciones y errores guardados localmente</p></div>
    <nav class="nav"><a href="pandora_revision.html">Volver a revisión</a></nav></header>
  <main>
    <div class="meta">Última generación de clasificación: <strong>__ULTIMA_GENERACION__</strong></div>
    <section class="metrics">
      <article class="metric"><span>Documentos clasificados en la última generación</span><strong>__TOTAL_CLASIFICADO__</strong></article>
      <article class="metric"><span>Liberados manualmente y procesados</span><strong>__LIBERADOS_MANUALES__</strong></article>
      <article class="metric"><span>Eventos operativos acumulados</span><strong>__TOTAL_OPERACIONES__</strong></article>
      <article class="metric"><span>Errores registrados</span><strong>__TOTAL_ERRORES__</strong></article>
    </section>
    <nav class="tabs" role="tablist"><button class="tab active" data-target="resumen" role="tab">Resumen por oficina</button>
      <button class="tab" data-target="operaciones" role="tab">Liberados y bloqueados (__OPERACIONES_CONTADOR__)</button>
      <button class="tab" data-target="errores" role="tab">Errores del sistema (__ERRORES_CONTADOR__)</button></nav>
    <section class="panel tab-panel" id="resumen" role="tabpanel"><h2>Clasificación más reciente</h2>
      <p class="hint">Conteo de documentos automáticos por oficina de ventas: liberados, bloqueados y enviados a revisión.</p>
      <div class="table-wrap"><table><thead><tr><th>VKBUR</th><th>Oficina de ventas</th><th>Liberados automáticos</th><th>Bloqueados automáticos</th><th>Por revisión</th><th>Con error</th></tr></thead><tbody>__RESUMEN_OFICINAS__</tbody></table></div>
      <h2 style="margin-top:24px">Resultados VA14L acumulados</h2><p class="hint">Solo cuenta ejecuciones terminadas correctamente; las decisiones manuales se muestran por separado.</p>
      <div class="table-wrap"><table><thead><tr><th>VKBUR</th><th>Oficina de ventas</th><th>Liberados automáticos</th><th>Bloqueados automáticos</th><th>Liberados manuales</th><th>Bloqueados manuales</th><th>Errores</th><th>No encontrados</th></tr></thead><tbody>__RESUMEN_VA14L__</tbody></table></div></section>
    <section class="panel tab-panel" id="operaciones" role="tabpanel" hidden><h2>Registro de operaciones</h2>
      <p class="hint">La tabla conserva las clasificaciones, decisiones manuales y resultados reales de VA14L. Se muestran los 2.000 eventos más recientes.</p>
      <input type="search" data-filter="tabla-operaciones" placeholder="Filtrar por documento, cliente, vendedor u oficina…"><div class="table-wrap"><table id="tabla-operaciones"><thead><tr><th>Fecha</th><th>Documento</th><th>Solicitante</th><th>Vendedor</th><th>Oficina</th><th>Evento</th><th>Origen</th><th>Decisión</th><th>Estado</th><th>Detalle</th></tr></thead><tbody>__OPERACIONES__</tbody></table></div></section>
    <section class="panel tab-panel" id="errores" role="tabpanel" hidden><h2>Errores del sistema</h2>
      <p class="hint">Se guardan las excepciones y diagnósticos SAP. Se muestran los 1.000 más recientes.</p>
      <input type="search" data-filter="tabla-errores" placeholder="Filtrar errores…"><div class="table-wrap"><table id="tabla-errores"><thead><tr><th>Fecha</th><th>Componente</th><th>Documento</th><th>Etapa</th><th>Código SAP</th><th>Tipo</th><th>Mensaje SAP</th><th>Detalle</th></tr></thead><tbody>__ERRORES__</tbody></table></div></section>
    <footer>El historial se conserva en pandora_historial.sqlite3 dentro de la carpeta PANDORA_DATA_DIR.</footer>
  </main>
  <script>
    document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(tab => tab.classList.toggle('active', tab === button));
      document.querySelectorAll('.tab-panel').forEach(panel => panel.hidden = panel.id !== button.dataset.target);
    }));
    document.querySelectorAll('[data-filter]').forEach(input => input.addEventListener('input', () => {
      const table = document.getElementById(input.dataset.filter);
      const term = input.value.toLocaleLowerCase();
      table.querySelectorAll('tbody tr').forEach(row => row.hidden = !row.textContent.toLocaleLowerCase().includes(term));
    }));
  </script>
</body>
</html>
"""
