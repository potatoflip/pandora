"""Genera una página local para revisar documentos pendientes de Pandora."""

import json
import numbers
from datetime import datetime
from pathlib import Path


def _normalizar_documento(valor):
    if isinstance(valor, numbers.Real) and float(valor).is_integer():
        return str(int(valor))
    return str(valor)


def _datos_revision(df):
    pendientes = df.loc[
        df["Decision Documento"] == "Documento Por Revisar"
    ]

    documentos = []
    for documento, grupo in pendientes.groupby(
        "Documento de ventas", sort=False, dropna=True
    ):
        filas = json.loads(
            grupo.to_json(
                orient="records",
                date_format="iso",
                force_ascii=False,
            )
        )
        documentos.append({
            "documento": _normalizar_documento(documento),
            "lineas": filas,
        })

    return {
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "documentos": documentos,
    }


def exportar_revision_html(df, ruta, generacion_id):
    """Escribe un HTML autónomo; las decisiones se descargan como JSON."""
    revision = _datos_revision(df)
    revision["generacion_id"] = generacion_id
    datos = json.dumps(
        revision,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    # Evita que datos de SAP puedan cerrar el elemento script del HTML.
    datos = (
        datos.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )

    html = _PLANTILLA_HTML.replace("__DATOS_REVISION__", datos)
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(html, encoding="utf-8")

    total = len(revision["documentos"])
    print(f"Página de revisión generada ({total} documento(s)): {ruta}")
    return ruta


_PLANTILLA_HTML = r'''<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Revisión de documentos Pandora</title>
  <style>
    :root { color-scheme: light; --ink:#17212b; --muted:#667085; --line:#d8dee8;
      --blue:#155eef; --surface:#fff; --canvas:#f3f5f8; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--canvas); color:var(--ink);
      font:14px/1.45 "Segoe UI", Arial, sans-serif; }
    header { background:#102a43; color:white; padding:24px max(24px, calc((100% - 1400px)/2)); }
    header h1 { margin:0 0 6px; font-size:24px; }
    header p { margin:0; color:#d9e2ec; }
    main { max-width:1400px; margin:22px auto; padding:0 20px 40px; }
    .toolbar { display:flex; flex-wrap:wrap; gap:12px; align-items:center;
      background:var(--surface); padding:14px; border:1px solid var(--line);
      border-radius:10px; position:sticky; top:0; z-index:2; }
    .toolbar input { flex:1 1 260px; min-width:200px; }
    input, select, button { font:inherit; border:1px solid #b8c2d1;
      border-radius:7px; padding:9px 11px; background:white; color:var(--ink); }
    button { border:0; background:var(--blue); color:white; font-weight:600; cursor:pointer; }
    button:hover { background:#004eeb; }
    .summary { color:var(--muted); font-size:13px; }
    #cards { display:grid; gap:16px; margin-top:16px; }
    .card { background:var(--surface); border:1px solid var(--line); border-radius:10px;
      overflow:hidden; }
    .card-head { display:flex; flex-wrap:wrap; justify-content:space-between;
      align-items:center; gap:12px; padding:14px 16px; border-bottom:1px solid var(--line); }
    .card-head h2 { margin:0; font-size:18px; }
    .card-head label { display:flex; align-items:center; gap:8px; font-weight:600; }
    .card-head select { min-width:145px; }
    .line-count { color:var(--muted); font-weight:400; font-size:13px; }
    .table-wrap { overflow:auto; max-height:480px; }
    table { border-collapse:collapse; width:max-content; min-width:100%; font-size:12px; }
    th, td { border-right:1px solid #e7ebf1; border-bottom:1px solid #e7ebf1;
      padding:8px 10px; text-align:left; vertical-align:top; max-width:360px; }
    th { background:#f7f9fc; position:sticky; top:0; z-index:1; white-space:nowrap; }
    td { white-space:pre-wrap; overflow-wrap:anywhere; }
    .empty { padding:24px; text-align:center; color:var(--muted); background:white;
      border:1px solid var(--line); border-radius:10px; }
    .notice { color:var(--muted); font-size:12px; }
    @media (max-width:650px) { header { padding:20px; } main { padding:0 12px 28px; }
      .card-head { align-items:flex-start; flex-direction:column; } }
  </style>
</head>
<body>
  <header>
    <h1>Revisión de Pandora</h1>
    <p>Una decisión por documento de ventas. La decisión se aplicará a todas sus líneas.</p>
  </header>
  <main>
    <section class="toolbar" aria-label="Controles de revisión">
      <input id="buscar" type="search" placeholder="Buscar documento o texto en sus líneas…">
      <span id="resumen" class="summary"></span>
      <button id="guardar" type="button">Guardar decisiones</button>
      <span class="notice">Descarga un JSON para procesarlo después con Python.</span>
    </section>
    <p class="notice">Al terminar, ejecuta <code>aplicar_decisiones_pandora.py</code> para actualizar las listas y, cuando estés listo, <code>ejecuta_liberaciones.py</code> para procesarlas en SAP.</p>
    <section id="cards" aria-live="polite"></section>
  </main>
  <script id="review-data" type="application/json">__DATOS_REVISION__</script>
  <script>
    const data = JSON.parse(document.getElementById("review-data").textContent);
    const cards = document.getElementById("cards");
    const search = document.getElementById("buscar");
    const summary = document.getElementById("resumen");
    const decisions = new Map();

    function text(value) {
      if (value === null || value === undefined) return "";
      if (typeof value === "object") return JSON.stringify(value);
      if (typeof value === "number" && Number.isFinite(value)) {
        const raw = String(value);
        const partes = raw.match(/^(-?\d+)(?:\.(\d+))?$/);
        if (partes) {
          const entero = partes[1].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
          return partes[2] ? `${entero},${partes[2]}` : entero;
        }
        return new Intl.NumberFormat("es-CL").format(value);
      }
      return String(value);
    }

    function render() {
      cards.replaceChildren();
      const term = search.value.trim().toLocaleLowerCase();
      const visibles = data.documentos.filter(item =>
        !term || (item.documento + " " + JSON.stringify(item.lineas))
          .toLocaleLowerCase().includes(term)
      );
      const elegidos = decisions.size;
      summary.textContent = `${visibles.length} de ${data.documentos.length} documentos · ${elegidos} con decisión · generado ${data.generado}`;

      if (!visibles.length) {
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = data.documentos.length
          ? "No hay documentos que coincidan con la búsqueda."
          : "No hay documentos pendientes de revisión.";
        cards.append(empty);
        return;
      }

      for (const item of visibles) {
        const card = document.createElement("article");
        card.className = "card";
        const head = document.createElement("div");
        head.className = "card-head";
        const title = document.createElement("h2");
        title.textContent = `Documento ${item.documento}`;
        const count = document.createElement("span");
        count.className = "line-count";
        count.textContent = ` · ${item.lineas.length} línea(s)`;
        title.append(count);

        const label = document.createElement("label");
        label.append(document.createTextNode("Decisión"));
        const select = document.createElement("select");
        select.setAttribute("aria-label", `Decisión para documento ${item.documento}`);
        for (const [value, labelText] of [["", "Pendiente"], ["LIBERADO", "Liberado"], ["BLOQUEADO", "Bloqueado"]]) {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = labelText;
          select.append(option);
        }
        select.value = decisions.get(item.documento) || "";
        select.addEventListener("change", () => {
          if (select.value) decisions.set(item.documento, select.value);
          else decisions.delete(item.documento);
          render();
        });
        label.append(select);
        head.append(title, label);
        card.append(head);

        if (item.lineas.length) {
          const wrap = document.createElement("div");
          wrap.className = "table-wrap";
          const table = document.createElement("table");
          const fields = [...new Set(item.lineas.flatMap(row => Object.keys(row)))];
          const thead = document.createElement("thead");
          const headerRow = document.createElement("tr");
          for (const field of fields) {
            const th = document.createElement("th");
            th.textContent = field;
            headerRow.append(th);
          }
          thead.append(headerRow);
          const tbody = document.createElement("tbody");
          for (const row of item.lineas) {
            const tr = document.createElement("tr");
            for (const field of fields) {
              const td = document.createElement("td");
              td.textContent = text(row[field]);
              tr.append(td);
            }
            tbody.append(tr);
          }
          table.append(thead, tbody);
          wrap.append(table);
          card.append(wrap);
        }
        cards.append(card);
      }
    }

    search.addEventListener("input", render);
    document.getElementById("guardar").addEventListener("click", () => {
      if (!decisions.size) {
        alert("Selecciona al menos una decisión antes de guardar.");
        return;
      }
      const pendientes = data.documentos.length - decisions.size;
      if (pendientes && !confirm(
        `Quedarán ${pendientes} documento(s) sin procesar. Se guardarán solo las decisiones seleccionadas. ¿Continuar?`
      )) return;
      const payload = {
        version: 1,
        generacion_id: data.generacion_id,
        generado: data.generado,
        decisiones: [...decisions].map(([documento, decision]) => ({ documento, decision }))
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "decisiones_pandora.json";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      alert(`${decisions.size} decisión(es) guardadas en decisiones_pandora.json.`);
    });

    render();
  </script>
</body>
</html>
'''
