// =============================================================================
//  SkyBalance AVL — Frontend Script
//  File: src/negocio/script.js
//  Responsibility: Flask API communication and DOM manipulation.
// =============================================================================

// -- Global state -------------------------------------------------------------
let selectedCode = null;  // flight code of the node currently selected in the tree
let stressMode   = false;

// -- Toast notification -------------------------------------------------------
function showToast(msg, type = "info") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className   = `toast toast-${type} show`;
  setTimeout(() => t.classList.remove("show"), 3500);
}

// -- Generic Flask API helper -------------------------------------------------
async function api(endpoint, method = "GET", body = null) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  try {
    const res  = await fetch(endpoint, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Server error");
    return data;
  } catch (e) {
    showToast(e.message, "error");
    throw e;
  }
}

// -- Modal helpers ------------------------------------------------------------
function openModal(id)  { document.getElementById(id).style.display = "flex"; }
function closeModal(id) { document.getElementById(id).style.display = "none"; }

document.querySelectorAll(".close[data-close]").forEach(btn => {
  btn.addEventListener("click", () => closeModal(btn.dataset.close));
});
document.querySelectorAll(".modal").forEach(overlay => {
  overlay.addEventListener("click", e => {
    if (e.target === overlay) closeModal(overlay.id);
  });
});

// -- D3 tree renderer ---------------------------------------------------------
function renderTree(root, svgId, containerId) {
  const svg = d3.select(`#${svgId}`);
  svg.selectAll("*").remove();

  const emptyState = document.getElementById("emptyState");

  if (!root) {
    if (emptyState) emptyState.style.display = "flex";
    return;
  }
  if (emptyState) emptyState.style.display = "none";

  const container = document.getElementById(containerId);
  const W = container.clientWidth  || 900;
  const H = container.clientHeight || 500;

  const margin = { top: 50, right: 20, bottom: 20, left: 20 };
  const width  = W - margin.left - margin.right;
  const height = H - margin.top  - margin.bottom;

  const g = svg.attr("width", W).attr("height", H)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // Enable zoom and pan
  svg.call(d3.zoom().scaleExtent([0.2, 4]).on("zoom", e => {
    g.attr("transform", e.transform);
  }));

  // Build D3 hierarchy from nested node dict
  const hierarchy = d3.hierarchy(root, d => {
    const children = [];
    if (d.left)  children.push(d.left);
    if (d.right) children.push(d.right);
    return children.length ? children : null;
  });

  d3.tree().size([width, height])(hierarchy);

  // Draw edges
  g.selectAll(".link")
    .data(hierarchy.links())
    .join("path")
    .attr("class", "link")
    .attr("d", d3.linkVertical().x(d => d.x).y(d => d.y));

  // Draw nodes
  const node = g.selectAll(".node")
    .data(hierarchy.descendants())
    .join("g")
    .attr("class", d => {
      let cls = "node";
      if (!d.parent)                           cls += " node-root";
      if (d.data.is_critical)                  cls += " node-critical";
      if (!d.data.left && !d.data.right)       cls += " node-leaf";
      if (d.data.flight_code === selectedCode) cls += " node-selected";
      return cls;
    })
    .attr("transform", d => `translate(${d.x},${d.y})`)
    .style("cursor", "pointer")
    .on("click", (e, d) => selectNode(d.data));

  node.append("circle").attr("r", 28);

  // Flight code label
  node.append("text")
    .attr("class", "node-code")
    .attr("dy", "-0.25em")
    .text(d => d.data.flight_code);

  // Balance factor label
  node.append("text")
    .attr("class", "node-bf")
    .attr("dy", "1em")
    .text(d => `bf:${d.data.balance_factor}`);

  // Tooltip on hover
  node.append("title")
    .text(d =>
      `${d.data.flight_code}\n` +
      `${d.data.origin} → ${d.data.destination}\n` +
      `Price: $${(d.data.final_price || 0).toFixed(2)}\n` +
      `Passengers: ${d.data.passengers}\n` +
      `Priority: ${d.data.priority}`
    );
}

// -- Update all UI panels from the tree payload -------------------------------
function updatePanels(treeData) {
  const t = treeData;

  // Tree properties panel
  document.getElementById("rootValue").textContent    = t.root?.flight_code ?? "-";
  document.getElementById("heightValue").textContent  = t.height ?? 0;
  document.getElementById("leavesValue").textContent  = t.leaf_count ?? 0;
  document.getElementById("nodesValue").textContent   = t.node_count ?? 0;

  // Metrics panel
  const m = t.metrics || {};
  document.getElementById("rotationsValue").textContent    = m.total_rotations ?? 0;
  document.getElementById("currentHeight").textContent     = t.height ?? 0;
  document.getElementById("llRotations").textContent       = m.LL ?? 0;
  document.getElementById("rrRotations").textContent       = m.RR ?? 0;
  document.getElementById("lrRotations").textContent       = m.LR ?? 0;
  document.getElementById("rlRotations").textContent       = m.RL ?? 0;
  document.getElementById("massCancellations").textContent = m.mass_cancellations ?? 0;

  // Traversal order displays
  document.getElementById("breadthTraversal").textContent =
    (t.breadth_order || []).join(" → ") || "-";
  document.getElementById("depthTraversal").textContent =
    (t.depth_order   || []).join(" → ") || "-";

  // Enable undo button only when the undo stack is non-empty
  document.getElementById("undoBtn").disabled = !t.can_undo;

  // Re-render AVL tree
  renderTree(t.root, "treeSvg", "treeContainer");
}

// Update BST comparison panel (insertion mode only)
function updateBstPanel(bstData) {
  document.getElementById("bstSection").classList.remove("hidden");
  document.getElementById("bstRoot").textContent   = bstData.root?.flight_code ?? "—";
  document.getElementById("bstHeight").textContent = bstData.height ?? 0;
  document.getElementById("bstLeaves").textContent = bstData.leaf_count ?? 0;
  document.getElementById("bstNodes").textContent  = bstData.node_count ?? 0;
  renderTree(bstData.root, "bstSvg", "bstContainer");
}

// -- Node selection (click on a tree node) ------------------------------------
function selectNode(nodeData) {
  selectedCode = nodeData.flight_code;

  // Populate the flight form with the selected node's data
  document.getElementById("flightCode").value   = nodeData.flight_code;
  document.getElementById("origin").value       = nodeData.origin;
  document.getElementById("destination").value  = nodeData.destination;
  document.getElementById("basePrice").value    = nodeData.base_price;
  document.getElementById("passengers").value   = nodeData.passengers;
  document.getElementById("promotion").value    = nodeData.promotion;
  document.getElementById("alert").value        = nodeData.alert || "";
  document.getElementById("priority").value     = nodeData.priority;

  // Enable action buttons that require a selected node
  document.getElementById("editFlightBtn").disabled   = false;
  document.getElementById("deleteFlightBtn").disabled = false;
  document.getElementById("cancelFlightBtn").disabled = false;

  // Show the node detail panel
  document.getElementById("nodeDetail").classList.remove("hidden");
  document.getElementById("nodeDetailContent").innerHTML = `
    <p><strong>Código:</strong>         ${nodeData.flight_code}</p>
    <p><strong>Ruta:</strong>           ${nodeData.origin} → ${nodeData.destination}</p>
    <p><strong>Precio base:</strong>    $${(nodeData.base_price || 0).toFixed(2)}</p>
    <p><strong>Precio final:</strong>   $${(nodeData.final_price || 0).toFixed(2)}
       ${nodeData.is_critical ? '<span class="critical-tag">+25% ⚠</span>' : ""}</p>
    <p><strong>Pasajeros:</strong>      ${nodeData.passengers}</p>
    <p><strong>Promoción:</strong>      ${((nodeData.promotion || 0) * 100).toFixed(0)}%</p>
    <p><strong>Prioridad:</strong>      ${nodeData.priority}</p>
    <p><strong>Altura nodo:</strong>    ${nodeData.height}</p>
    <p><strong>Factor balance:</strong> ${nodeData.balance_factor}</p>
    <p><strong>Profundidad:</strong>    ${nodeData.depth}</p>
    ${nodeData.alert ? `<p><strong>Alerta:</strong> ${nodeData.alert}</p>` : ""}
  `;
}

// Clear the flight form and reset node-dependent button states
function clearForm() {
  selectedCode = null;
  ["flightCode", "origin", "destination", "basePrice", "passengers", "promotion", "alert"]
    .forEach(id => { document.getElementById(id).value = ""; });
  document.getElementById("priority").value = "3";
  document.getElementById("editFlightBtn").disabled   = true;
  document.getElementById("deleteFlightBtn").disabled = true;
  document.getElementById("cancelFlightBtn").disabled = true;
  document.getElementById("nodeDetail").classList.add("hidden");
}

// Read and validate the flight form; return a payload object or null
function getFormPayload() {
  const fc = document.getElementById("flightCode").value.trim();
  const or = document.getElementById("origin").value.trim();
  const de = document.getElementById("destination").value.trim();
  const bp = parseFloat(document.getElementById("basePrice").value);

  if (!fc || !or || !de || isNaN(bp)) {
    showToast("Completa los campos requeridos: Código, Origen, Destino, Precio Base", "error");
    return null;
  }
  return {
    flight_code:  fc,
    origin:       or,
    destination:  de,
    base_price:   bp,
    passengers:   parseInt(document.getElementById("passengers").value, 10) || 0,
    promotion:    parseFloat(document.getElementById("promotion").value) || 0,
    alert:        document.getElementById("alert").value.trim(),
    priority:     parseInt(document.getElementById("priority").value, 10),
  };
}

// -- Load JSON ----------------------------------------------------------------
document.getElementById("loadJsonBtn").addEventListener("click", () => openModal("jsonModal"));

document.getElementById("jsonFile").addEventListener("change", e => {
  const name = e.target.files[0]?.name || "Seleccionar archivo .json";
  document.getElementById("fileLabel").textContent = "📂 " + name;
});

document.getElementById("loadJsonConfirmBtn").addEventListener("click", async () => {
  const fileInput = document.getElementById("jsonFile");
  if (!fileInput.files.length) { showToast("Selecciona un archivo JSON", "error"); return; }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("type", document.getElementById("loadType").value);

  try {
    const res  = await fetch("/api/load-tree", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    updatePanels(data.tree);
    if (data.bst_tree) updateBstPanel(data.bst_tree);

    closeModal("jsonModal");
    showToast("Árbol cargado correctamente ✅", "success");
  } catch (e) {
    showToast(e.message, "error");
  }
});

// -- Export JSON --------------------------------------------------------------
document.getElementById("exportTreeBtn").addEventListener("click", async () => {
  try {
    const data = await api("/api/export-tree");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = "skybalance_tree.json";
    a.click();
    URL.revokeObjectURL(url);
    showToast("Árbol exportado 💾", "success");
  } catch (_) {}
});

// -- Add flight ---------------------------------------------------------------
document.getElementById("addFlightBtn").addEventListener("click", async () => {
  const payload = getFormPayload();
  if (!payload) return;
  try {
    const data = await api("/api/add-flight", "POST", payload);
    updatePanels(data.tree);
    clearForm();
    showToast(`Vuelo ${payload.flight_code} agregado ✅`, "success");
  } catch (_) {}
});

// -- Edit flight --------------------------------------------------------------
document.getElementById("editFlightBtn").addEventListener("click", async () => {
  if (!selectedCode) return;
  const payload = getFormPayload();
  if (!payload) return;

  // Remove flight_code from the update payload (it is sent separately)
  const updated_data = { ...payload };
  const editedCode = payload.flight_code.trim().toUpperCase();
  const currentCode = selectedCode.trim().toUpperCase();

  if (editedCode !== currentCode) {
    updated_data.new_flight_code = editedCode;
  }

  delete updated_data.flight_code;

  try {
    const data = await api("/api/edit-flight", "POST", {
      flight_code: selectedCode,
      updated_data,
    });
    updatePanels(data.tree);
    clearForm();
    showToast(`Vuelo ${selectedCode} actualizado ✅`, "success");
  } catch (_) {}
});

// -- Delete flight (single node) ----------------------------------------------
document.getElementById("deleteFlightBtn").addEventListener("click", async () => {
  if (!selectedCode) return;
  if (!confirm(`¿Eliminar el vuelo ${selectedCode}? (solo el nodo)`)) return;
  try {
    const data = await api("/api/delete-flight", "POST", { flight_code: selectedCode });
    updatePanels(data.tree);
    clearForm();
    showToast(`Vuelo ${selectedCode} eliminado`, "info");
  } catch (_) {}
});

// -- Cancel flight (node + entire subtree) ------------------------------------
document.getElementById("cancelFlightBtn").addEventListener("click", async () => {
  if (!selectedCode) return;
  if (!confirm(`¿Cancelar el vuelo ${selectedCode} y TODA su descendencia?`)) return;
  try {
    const data = await api("/api/cancel-flight", "POST", { flight_code: selectedCode });
    updatePanels(data.tree);
    clearForm();
    showToast(`Vuelo ${selectedCode} cancelado (${data.removed_count} nodos eliminados)`, "warn");
  } catch (_) {}
});

// -- Undo ---------------------------------------------------------------------
document.getElementById("undoBtn").addEventListener("click", async () => {
  try {
    const data = await api("/api/undo", "POST");
    updatePanels(data.tree);
    showToast("Acción deshecha ↩", "info");
  } catch (_) {}
});

// -- Stress mode --------------------------------------------------------------
document.getElementById("stressModeBtn").addEventListener("click", async () => {
  const nextState = !stressMode;
  try {
    const data = await api("/api/toggle-stress-mode", "POST", { stress_mode: nextState });
    stressMode = data.stress_mode;
    updatePanels(data.tree);

    const btn    = document.getElementById("stressModeBtn");
    const banner = document.getElementById("stressBanner");
    const audit  = document.getElementById("auditAvlBtn");

    if (stressMode) {
      btn.textContent = "Desactivar Modo Estrés";
      btn.classList.add("active-stress");
      banner.classList.remove("hidden");
      audit.style.display = "inline-block";  // spec §7: only visible during stress mode
      showToast("Modo Estrés activado — balanceo diferido ⚡", "warn");
    } else {
      btn.textContent = "Activar Modo Estrés";
      btn.classList.remove("active-stress");
      banner.classList.add("hidden");
      audit.style.display = "none";
      showToast(`Modo normal restaurado — ${data.rotations_done} rotaciones aplicadas`, "success");
    }
  } catch (_) {}
});

// -- Global rebalance ---------------------------------------------------------
document.getElementById("globalRebalanceBtn").addEventListener("click", async () => {
  try {
    const data = await api("/api/global-rebalance", "POST");
    updatePanels(data.tree);
    showToast(`Rebalanceo global completado — ${data.rotations_done} rotaciones`, "success");
  } catch (_) {}
});

// -- Critical depth -----------------------------------------------------------
document.getElementById("updateCriticalDepthBtn").addEventListener("click", async () => {
  const val = parseInt(document.getElementById("criticalDepth").value, 10);
  if (isNaN(val) || val < 1) { showToast("Profundidad inválida", "error"); return; }
  try {
    const data = await api("/api/update-critical-depth", "POST", { critical_depth: val });
    updatePanels(data.tree);
    showToast(`Profundidad crítica actualizada a ${val}`, "success");
  } catch (_) {}
});

// -- Delete least profitable --------------------------------------------------
document.getElementById("deleteLeastProfitable").addEventListener("click", async () => {
  if (!confirm("¿Eliminar el vuelo de menor rentabilidad y toda su subrama?")) return;
  try {
    const data = await api("/api/delete-least-profitable", "POST");
    updatePanels(data.tree);
    showToast(`Vuelo ${data.cancelled} (menor rentabilidad) eliminado`, "warn");
  } catch (_) {}
});

// -- AVL Audit (button visible only during stress mode — spec §7) -------------
document.getElementById("auditAvlBtn").addEventListener("click", async () => {
  try {
    const data   = await api("/api/audit-avl");
    const report = document.getElementById("auditReport");

    if (data.valid) {
      report.innerHTML = `<p class="audit-ok">✅ El árbol cumple la propiedad AVL en todos los nodos.</p>`;
    } else {
      const rows = data.report.map(r => `
        <div class="audit-node">
          <strong>${r.flight_code}</strong> <small>(profundidad ${r.depth})</small>
          <ul>${r.issues.map(i => `<li>${i}</li>`).join("")}</ul>
        </div>`).join("");
      report.innerHTML = `
        <p class="audit-warn">⚠ ${data.report.length} nodo(s) inconsistentes:</p>
        ${rows}`;
    }
    openModal("auditModal");
  } catch (_) {}
});

// -- Versions -----------------------------------------------------------------
document.getElementById("saveVersionBtn").addEventListener("click", async () => {
  const name = document.getElementById("versionName").value.trim();
  if (!name) { showToast("Escribe un nombre de versión", "error"); return; }
  try {
    await api("/api/save-version", "POST", { version_name: name });
    document.getElementById("versionName").value = "";
    showToast(`Versión "${name}" guardada 💾`, "success");
  } catch (_) {}
});

document.getElementById("showVersionsBtn").addEventListener("click", async () => {
  await refreshVersionsList();
  openModal("versionsModal");
});

async function refreshVersionsList() {
  try {
    const data    = await api("/api/list-versions");
    const ul      = document.getElementById("versionsList");
    const entries = Object.entries(data.versions || {});

    if (!entries.length) {
      ul.innerHTML = "<li class='no-versions'>No hay versiones guardadas</li>";
      return;
    }

    ul.innerHTML = entries.map(([name, meta]) => `
      <li class="version-item">
        <div class="version-info">
          <strong>${name}</strong>
          <small>${new Date(meta.timestamp).toLocaleString("es-CO")}</small>
          <small>${meta.tree_size ?? "?"} nodos · altura ${meta.tree_height ?? "?"}</small>
        </div>
        <div class="version-actions">
          <button class="btn-restore" data-name="${name}">Restaurar</button>
          <button class="btn-del-ver" data-name="${name}">Eliminar</button>
        </div>
      </li>`).join("");

    // Restore version
    ul.querySelectorAll(".btn-restore").forEach(btn => {
      btn.addEventListener("click", async () => {
        const n = btn.dataset.name;
        try {
          const d = await api("/api/restore-version", "POST", { version_name: n });
          updatePanels(d.tree);
          closeModal("versionsModal");
          showToast(`Versión "${n}" restaurada ✅`, "success");
        } catch (_) {}
      });
    });

    // Delete version
    ul.querySelectorAll(".btn-del-ver").forEach(btn => {
      btn.addEventListener("click", async () => {
        const n = btn.dataset.name;
        if (!confirm(`¿Eliminar la versión "${n}"?`)) return;
        try {
          await api("/api/delete-version", "POST", { version_name: n });
          showToast(`Versión "${n}" eliminada`, "info");
          await refreshVersionsList();
        } catch (_) {}
      });
    });
  } catch (_) {}
}

// -- Initial load: sync tree state when the page opens -----------------------
(async () => {
  try {
    const data = await api("/api/tree-state");
    if (data.tree) updatePanels(data.tree);
  } catch (_) {}
})();