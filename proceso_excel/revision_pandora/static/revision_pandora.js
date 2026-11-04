const data = JSON.parse(document.getElementById("review-data").textContent);
    const cards = document.getElementById("cards");
    const search = document.getElementById("buscar");
    const filter = document.getElementById("filter");
    const decisions = new Map();
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

    function persistir() {
      try { localStorage.setItem(decisionKey, JSON.stringify(Object.fromEntries(decisions))); } catch (_) {}
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
        titleBlock.append(number, subtitle);
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
        head.append(titleWrap, decisionBox);
        card.append(head);

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
          if (row["Decision Linea"] === "Revision") {
            const motivo = String(row["Motivo"] || "").toLocaleLowerCase();
            tr.className = motivo.includes("márgenes cumplen objetivos") ? "review-normal" : "review-critical";
          }
          for (const field of fields) {
            const td = document.createElement("td");
            td.textContent = text(row[field], field);
            tr.append(td);
          }
          tbody.append(tr);
        }
        table.append(thead, tbody);
        wrap.append(table);
        card.append(wrap);
        cards.append(card);
      }
    }

    const themeSelect = document.getElementById("theme-select");
    document.addEventListener("click", event => {
      const row = event.target.closest("#cards tbody tr");
      document.querySelectorAll("#cards tbody tr.selected-line").forEach(item => item.classList.remove("selected-line"));
      if (row) row.classList.add("selected-line");
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
