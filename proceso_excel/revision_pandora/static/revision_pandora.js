const data = JSON.parse(document.getElementById("review-data").textContent);
    const cards = document.getElementById("cards");
    const search = document.getElementById("buscar");
    const filter = document.getElementById("filter");
    const decisions = new Map();
    const sortByDocument = new Map();
    let freezeIndex = 0;
    const decisionKey = `ms_pandora_decisions_${data.generacion_id}`;
    const validThemes = ["light", "dark", "lino", "greda", "cordillera", "telar"];

    try {
      const saved = JSON.parse(localStorage.getItem(decisionKey) || "{}");
      for (const item of data.documentos) {
        if (["LIBERADO", "BLOQUEADO"].includes(saved[item.documento])) decisions.set(item.documento, saved[item.documento]);
      }
    } catch (_) {}

    function text(value, field) {
      if (value === null || value === undefined) return "";
      if (field === "Documento de ventas") return String(value);
      if (typeof value === "object") return JSON.stringify(value);
      if (typeof value === "number" && Number.isFinite(value)) {
        const raw = String(value);
        const parts = raw.match(/^(-?\d+)(?:\.(\d+))?$/);
        if (parts) {
          const integer = parts[1].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
          return parts[2] ? `${integer},${parts[2]}` : integer;
        }
        return new Intl.NumberFormat("es-CL").format(value);
      }
      return String(value);
    }

    function precioIgualAlHistorico(precioVenta, precioHistorico) {
      const convertir = value => {
        if (typeof value === "number") return value;
        if (value === null || value === undefined || value === "") return Number.NaN;
        const raw = String(value).trim();
        const normalizado = raw.includes(",")
          ? raw.replace(/\./g, "").replace(",", ".")
          : raw;
        return Number(normalizado);
      };
      const actual = convertir(precioVenta);
      const historico = convertir(precioHistorico);
      return Number.isFinite(actual)
        && Number.isFinite(historico)
        && Math.round(actual * 100) === Math.round(historico * 100);
    }

    function persistir() {
      try { localStorage.setItem(decisionKey, JSON.stringify(Object.fromEntries(decisions))); } catch (_) {}
    }

    function actualizarColumnasFijas(table) {
      const widths = [...table.querySelectorAll("col")].map(col =>
        Number.parseFloat(col.style.width) || col.getBoundingClientRect().width
      );
      table.querySelectorAll("thead tr, tbody tr").forEach(row => {
        let left = 0;
        [...row.children].forEach((cell, index) => {
          const fijada = freezeIndex >= 0 && index <= freezeIndex;
          cell.classList.toggle("frozen-column", fijada);
          cell.classList.toggle("frozen-last", fijada && index === freezeIndex);
          cell.style.left = fijada ? `${left}px` : "";
          if (fijada) left += widths[index] || cell.getBoundingClientRect().width;
        });
      });
    }

    function actualizarResumen(visibles) {
      const liberar = [...decisions.values()].filter(value => value === "LIBERADO").length;
      const bloquear = [...decisions.values()].filter(value => value === "BLOQUEADO").length;
      document.getElementById("metric-total").textContent = text(data.documentos.length);
      document.getElementById("metric-liberar").textContent = text(liberar);
      document.getElementById("metric-bloquear").textContent = text(bloquear);
      document.getElementById("pending-badge").textContent = `${data.documentos.length - decisions.size} pendientes`;
      document.getElementById("sidebar-status").textContent = decisions.size ? `${decisions.size} decidido(s)` : "Pendiente de revisar";
      document.getElementById("generated-at").textContent = data.generado;
      document.title = decisions.size ? `Revisión Pandora (${decisions.size}/${data.documentos.length}) | Max Service` : "Revisión Pandora | Max Service";
      return { liberar, bloquear, visibles };
    }

    function render() {
      cards.replaceChildren();
      const term = search.value.trim().toLocaleLowerCase();
      const status = filter.value;
      const visibles = data.documentos.filter(item => {
        const decision = decisions.get(item.documento) || "";
        const matchesStatus = status === "todos" || (status === "pendiente" ? !decision : decision === status);
        const matchesText = !term || (item.documento + " " + JSON.stringify(item.lineas)).toLocaleLowerCase().includes(term);
        return matchesStatus && matchesText;
      });
      actualizarResumen(visibles.length);

      if (!visibles.length) {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        const icon = document.createElement("span");
        icon.className = "empty-icon";
        icon.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>';
        const title = document.createElement("strong");
        const message = document.createElement("p");
        if (!data.documentos.length) {
          title.textContent = "No hay documentos pendientes";
          message.textContent = "Las reglas automáticas no dejaron documentos para revisión manual.";
        } else if (term || status !== "todos") {
          title.textContent = "No encontramos documentos";
          message.textContent = "Prueba con otra búsqueda o cambia el filtro.";
        } else {
          title.textContent = "Revisión completada";
          message.textContent = "Guarda las decisiones para descargarlas y procesarlas después.";
        }
        empty.append(icon, title, message);
        cards.append(empty);
        return;
      }

      for (const item of visibles) {
        const decision = decisions.get(item.documento) || "";
        const card = document.createElement("article");
        card.className = `doc-card${decision ? ` decision-${decision.toLowerCase()}` : ""}`;
        const head = document.createElement("div");
        head.className = "doc-head";
        const titleWrap = document.createElement("div");
        titleWrap.className = "doc-title-wrap";
        const titleBlock = document.createElement("div");
        const number = document.createElement("div");
        number.className = "doc-number";
        number.textContent = `Documento ${item.documento}`;
        const subtitle = document.createElement("div");
        subtitle.className = "doc-subtitle";
        subtitle.textContent = "Decisión a nivel de nota de venta";
        const primeraLinea = item.lineas[0] || {};
        const contexto = document.createElement("div");
        contexto.className = "doc-context";
        const nombreSolicitante = document.createElement("strong");
        nombreSolicitante.className = "doc-requester";
        nombreSolicitante.textContent = primeraLinea["Nombre solicitante"] || "Solicitante sin nombre";
        const canal = document.createElement("span");
        canal.className = "channel-badge";
        canal.textContent = `Canal ${primeraLinea["Canal distribución"] || "—"}`;
        contexto.append(nombreSolicitante, canal);
        titleBlock.append(number, contexto, subtitle);
        const count = document.createElement("span");
        count.className = "line-pill";
        count.textContent = `${item.lineas.length} línea(s)`;
        titleWrap.append(titleBlock, count);

        const decisionBox = document.createElement("label");
        decisionBox.className = "decision-box";
        const labelText = document.createElement("span");
        labelText.className = "decision-label";
        labelText.textContent = "Decisión";
        const select = document.createElement("select");
        select.className = `decision-select${decision ? ` selected-${decision.toLowerCase()}` : ""}`;
        select.setAttribute("aria-label", `Decisión para documento ${item.documento}`);
        for (const [value, caption] of [["", "Pendiente"], ["LIBERADO", "Liberado"], ["BLOQUEADO", "Bloqueado"]]) {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = caption;
          select.append(option);
        }
        select.value = decision;
        select.addEventListener("change", () => {
          if (select.value) decisions.set(item.documento, select.value);
          else decisions.delete(item.documento);
          persistir();
          render();
        });
        decisionBox.append(labelText, select);
        const lineasConHistorial = item.lineas.filter(row => row["Factura histórica"]).length;
        if (lineasConHistorial) {
          const historyBadge = document.createElement("span");
          historyBadge.className = "history-badge";
          historyBadge.title = `Historial de precios disponible en ${lineasConHistorial} línea(s)`;
          historyBadge.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5h16v4a3 3 0 0 0 0 6v4H4v-4a3 3 0 0 0 0-6V5Z"/><path d="M13 6v2m0 2v2m0 2v2m0 2v1"/></svg>';
          const label = document.createElement("span");
          label.textContent = `Historial · ${lineasConHistorial}`;
          historyBadge.append(label);
          head.append(titleWrap, historyBadge, decisionBox);
        } else {
          head.append(titleWrap, decisionBox);
        }
        card.append(head);

        const wrap = document.createElement("div");
        wrap.className = "table-wrap";
        const table = document.createElement("table");
        const camposDeEncabezado = new Set([
          "Nombre solicitante",
          "Canal distribución",
          "Solicitante",
        ]);
        const fields = [...new Set(item.lineas.flatMap(row => Object.keys(row)))].filter(
          field => !camposDeEncabezado.has(field)
        );
        const colgroup = document.createElement("colgroup");
        for (const field of fields) {
          const col = document.createElement("col");
          const longestCell = Math.max(0, ...item.lineas.map(row =>
            text(row[field], field).split("\n").reduce((longest, part) => Math.max(longest, part.length), 0)
          ));
          const tieneTicketHistorial = field === "Documento de ventas"
            && item.lineas.some(row => row["Factura histórica"]);
          const tieneCoincidenciaPrecio = field === "Precio Venta"
            && item.lineas.some(row => row["Factura histórica"]
              && precioIgualAlHistorico(row["Precio Venta"], row["Precio lista histórico"]));
          const espacioHistorial = tieneTicketHistorial || tieneCoincidenciaPrecio
            ? 36
            : 24;
          col.style.width = `${Math.max(96, Math.min(420, longestCell * 7 + espacioHistorial))}px`;
          colgroup.append(col);
        }
        table.append(colgroup);
        const thead = document.createElement("thead");
        const headerRow = document.createElement("tr");
        const sortState = sortByDocument.get(item.documento);
        fields.forEach((field, fieldIndex) => {
          const th = document.createElement("th");
          const headerActions = document.createElement("div");
          headerActions.className = "header-actions";
          const sortButton = document.createElement("button");
          sortButton.type = "button";
          sortButton.className = "sort-button";
          sortButton.dataset.sortField = field;
          sortButton.setAttribute("aria-label", `Ordenar por ${field}`);
          sortButton.title = `Ordenar por ${field}`;
          const label = document.createElement("span");
          label.className = "sort-label";
          label.textContent = field;
          const indicator = document.createElement("span");
          indicator.className = "sort-indicator";
          indicator.textContent = sortState?.field === field ? (sortState.desc ? "▼" : "▲") : "↕";
          sortButton.append(label, indicator);
          const freezeButton = document.createElement("button");
          freezeButton.type = "button";
          freezeButton.className = `freeze-button${freezeIndex === fieldIndex ? " active" : ""}`;
          freezeButton.dataset.freezeIndex = String(fieldIndex);
          freezeButton.setAttribute("aria-pressed", String(freezeIndex === fieldIndex));
          freezeButton.setAttribute("aria-label", `Inmovilizar columnas hasta ${field}`);
          freezeButton.title = freezeIndex === fieldIndex
            ? `Liberar columnas hasta ${field}`
            : `Inmovilizar columnas hasta ${field}`;
          freezeButton.textContent = "📌";
          headerActions.append(sortButton, freezeButton);
          const resizeHandle = document.createElement("span");
          resizeHandle.className = "column-resize-handle";
          resizeHandle.dataset.resizeIndex = String(fieldIndex);
          resizeHandle.setAttribute("aria-hidden", "true");
          th.append(headerActions, resizeHandle);
          headerRow.append(th);
        });
        thead.append(headerRow);
        const tbody = document.createElement("tbody");
        const lineas = [...item.lineas];
        if (sortState) {
          const collator = new Intl.Collator("es", { numeric: true, sensitivity: "base" });
          lineas.sort((left, right) => {
            const a = left[sortState.field];
            const b = right[sortState.field];
            const comparison = typeof a === "number" && typeof b === "number"
              ? a - b
              : collator.compare(String(a ?? ""), String(b ?? ""));
            return sortState.desc ? -comparison : comparison;
          });
        }
        for (const row of lineas) {
          const tr = document.createElement("tr");
          if (row["Decision Linea"] === "Revision") {
            const motivo = String(row["Motivo"] || "").toLocaleLowerCase();
            tr.className = motivo.includes("márgenes cumplen objetivos") ? "review-normal" : "review-critical";
          }
          if (row["Factura histórica"]) {
            tr.classList.add("has-price-history");
            tr.title = "Esta línea tiene historial de precios";
          }
          fields.forEach((field, fieldIndex) => {
            const td = document.createElement("td");
            const valor = text(row[field], field);
            if (row["Factura histórica"] && fieldIndex === 0) {
              td.classList.add("history-cell");
              const value = document.createElement("span");
              value.className = "history-value";
              value.textContent = valor;
              const marker = document.createElement("span");
              marker.className = "history-line-marker";
              marker.textContent = "✓";
              marker.title = `Factura histórica ${row["Factura histórica"]}`;
              marker.setAttribute("aria-label", "Tiene precio histórico");
              td.append(value, marker);
            } else if (
              field === "Precio Venta"
              && row["Factura histórica"]
              && precioIgualAlHistorico(row["Precio Venta"], row["Precio lista histórico"])
            ) {
              td.classList.add("history-cell", "price-match-cell");
              const value = document.createElement("span");
              value.className = "history-value";
              value.textContent = valor;
              const marker = document.createElement("span");
              marker.className = "price-match-marker";
              marker.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 9h12M6 15h12"/></svg>';
              marker.title = `Precio de venta igual al precio de lista histórico (${text(row["Precio lista histórico"], "Precio lista histórico")})`;
              marker.setAttribute("aria-label", "Precio de venta igual al precio de lista histórico");
              td.append(value, marker);
            } else {
              td.textContent = valor;
            }
            if (freezeIndex >= 0 && fieldIndex <= freezeIndex) {
              td.classList.add("frozen-column");
              if (fieldIndex === freezeIndex) td.classList.add("frozen-last");
            }
            tr.append(td);
          });
          tbody.append(tr);
        }
        table.append(thead, tbody);
        wrap.append(table);
        card.append(wrap);
        cards.append(card);
        actualizarColumnasFijas(table);
      }
    }

    const themeSelect = document.getElementById("theme-select");
    document.addEventListener("click", event => {
      const freezeButton = event.target.closest("#cards .freeze-button");
      if (freezeButton) {
        const selectedIndex = Number(freezeButton.dataset.freezeIndex);
        freezeIndex = freezeIndex === selectedIndex ? -1 : selectedIndex;
        render();
        return;
      }
      const sortButton = event.target.closest("#cards .sort-button");
      if (sortButton) {
        const card = sortButton.closest(".doc-card");
        const documentNumber = card?.querySelector(".doc-number")?.textContent.replace(/^Documento\s+/, "");
        if (documentNumber) {
          const previous = sortByDocument.get(documentNumber);
          sortByDocument.set(documentNumber, {
            field: sortButton.dataset.sortField,
            desc: previous?.field === sortButton.dataset.sortField ? !previous.desc : false,
          });
          render();
        }
        return;
      }
      const row = event.target.closest("#cards tbody tr");
      document.querySelectorAll("#cards tbody tr.selected-line").forEach(item => item.classList.remove("selected-line"));
      if (row) row.classList.add("selected-line");
    });
    document.addEventListener("mousedown", event => {
      const handle = event.target.closest("#cards .column-resize-handle");
      if (!handle) return;
      event.preventDefault();
      const table = handle.closest("table");
      const column = table.querySelectorAll("col")[Number(handle.dataset.resizeIndex)];
      const startX = event.clientX;
      const startWidth = column.getBoundingClientRect().width;
      handle.classList.add("resizing");
      document.body.classList.add("resizing-column");
      const resize = moveEvent => {
        column.style.width = `${Math.max(72, startWidth + moveEvent.clientX - startX)}px`;
        actualizarColumnasFijas(table);
      };
      const finish = () => {
        handle.classList.remove("resizing");
        document.body.classList.remove("resizing-column");
        document.removeEventListener("mousemove", resize);
        document.removeEventListener("mouseup", finish);
      };
      document.addEventListener("mousemove", resize);
      document.addEventListener("mouseup", finish);
    });
    const currentTheme = document.documentElement.dataset.theme || "light";
    themeSelect.value = validThemes.includes(currentTheme) ? currentTheme : "light";
    themeSelect.addEventListener("change", () => {
      document.documentElement.dataset.theme = themeSelect.value;
      try { localStorage.setItem("ms_theme", themeSelect.value); } catch (_) {}
    });
    search.addEventListener("input", render);
    filter.addEventListener("change", render);
    document.getElementById("guardar").addEventListener("click", () => {
      if (!decisions.size) {
        alert("Selecciona al menos una decisión antes de guardar.");
        return;
      }
      const pending = data.documentos.length - decisions.size;
      if (pending && !confirm(`Quedarán ${pending} documento(s) sin procesar. Se guardarán solo las decisiones seleccionadas. ¿Continuar?`)) return;
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
