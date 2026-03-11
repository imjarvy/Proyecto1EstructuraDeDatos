/**
 * script.js  –  SkyBalance AVL · Frontend completo
 * Coloca este archivo en:  presentacion/script.js
 *
 * El index.html ya lo importa con:
 *   <script type="module" src="script.js"></script>
 */

const API = "http://127.0.0.1:5000";

// ─────────────────────────────────────────────────────────────────────────────
// Estado local
// ─────────────────────────────────────────────────────────────────────────────
let currentAVL = null;
let currentBST = null;


// ═════════════════════════════════════════════════════════════════════════════
// FETCH HELPERS
// ═════════════════════════════════════════════════════════════════════════════

async function checkResponse(response) {
  if (!response.ok) {
    let msg = `HTTP ${response.status}`;
    try { const b = await response.json(); if (b.error) msg += ` – ${b.error}`; }
    catch (_) {}
    throw new Error(msg);
  }
  return response;
}

async function apiLoad(file, loadType) {
  const form = new FormData();
  form.append("file",      file);
  form.append("load_type", loadType);
  const res = await checkResponse(
    await fetch(`${API}/api/load`, { method: "POST", body: form })
  );
  return res.json();
}

async function apiExport(treeType = "avl") {
  const res = await checkResponse(await fetch(`${API}/api/export?tree=${treeType}`));

  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match       = disposition.match(/filename="?([^"]+)"?/);
  const filename    = match ? match[1] : `skybalance_${treeType}_export.json`;

  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  const a    = Object.assign(document.createElement("a"), { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function apiStatus() {
  const res = await checkResponse(await fetch(`${API}/api/status`));
  return res.json();
}


// ═════════════════════════════════════════════════════════════════════════════
// ACTUALIZAR PANELES HTML
// ═════════════════════════════════════════════════════════════════════════════

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = (value != null) ? value : "-";
}

function updatePanels(avl, bst) {
  setText("rootValue",   avl.root);
  setText("heightValue", avl.height);
  setText("leavesValue", avl.leaves);
  setText("nodesValue",  avl.nodes);

  const rc    = avl.rotation_count || {};
  const total = (rc.LL || 0) + (rc.RR || 0) + (rc.LR || 0) + (rc.RL || 0);
  setText("rotationsValue", total);

  setText("currentHeight", avl.height);
  setText("llRotations",   rc.LL ?? 0);
  setText("rrRotations",   rc.RR ?? 0);
  setText("lrRotations",   rc.LR ?? 0);
  setText("rlRotations",   rc.RL ?? 0);

  const bfs = getBFSOrder(avl.tree_structure, avl.root_code);
  setText("breadthTraversal", bfs.join(" → ") || "-");

  const pre = getPreOrder(avl.tree_structure, avl.root_code);
  setText("depthTraversal", pre.join(" → ") || "-");
}

function getBFSOrder(treeStructure, rootCode) {
  if (!rootCode || !treeStructure) return [];
  const result = [], queue = [rootCode];
  while (queue.length) {
    const code = queue.shift();
    result.push(code);
    const node = treeStructure[code];
    if (!node) continue;
    if (node.left_child)  queue.push(node.left_child);
    if (node.right_child) queue.push(node.right_child);
  }
  return result;
}

function getPreOrder(treeStructure, code) {
  if (!code || !treeStructure[code]) return [];
  const node = treeStructure[code];
  return [
    code,
    ...getPreOrder(treeStructure, node.left_child),
    ...getPreOrder(treeStructure, node.right_child),
  ];
}


// ═════════════════════════════════════════════════════════════════════════════
// VISUALIZACIÓN D3
// ═════════════════════════════════════════════════════════════════════════════

function renderTree(treeStructure, rootCode) {
  const svg = d3.select("#treeSvg");
  svg.selectAll("*").remove();

  if (!rootCode || !treeStructure || !treeStructure[rootCode]) {
    svg.append("text")
       .attr("x", "50%").attr("y", "50%")
       .attr("text-anchor", "middle").attr("dominant-baseline", "middle")
       .style("fill", "#999").style("font-size", "16px")
       .text("No hay árbol cargado");
    return;
  }

  function toHierarchy(code) {
    if (!code || !treeStructure[code]) return null;
    const n  = treeStructure[code];
    const fd = n.flight_data || {};
    const node = {
      id:             code,
      origin:         fd.origin         || "",
      destination:    fd.destination    || "",
      balance_factor: fd.balance_factor ?? 0,
      height:         fd.height         ?? 0,
      children: []
    };
    const left  = toHierarchy(n.left_child);
    const right = toHierarchy(n.right_child);
    if (left)  node.children.push(left);
    if (right) node.children.push(right);
    if (!node.children.length) delete node.children;
    return node;
  }

  const hierarchyData = d3.hierarchy(toHierarchy(rootCode));

  const container  = document.getElementById("treeContainer");
  const W          = container.clientWidth  || 900;
  const H          = container.clientHeight || 500;
  const nodeRadius = 28;

  const treeLayout = d3.tree().size([W - 80, H - 100]);
  treeLayout(hierarchyData);

  const g = svg
    .attr("width",  W)
    .attr("height", H)
    .append("g")
    .attr("transform", "translate(40,50)");

  g.selectAll(".link")
   .data(hierarchyData.links())
   .join("line")
   .attr("class", "link")
   .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
   .attr("x2", d => d.target.x).attr("y2", d => d.target.y);

  const node = g.selectAll(".node")
    .data(hierarchyData.descendants())
    .join("g")
    .attr("class", d => {
      const bf = d.data.balance_factor;
      return `node${(bf > 1 || bf < -1) ? " critical" : ""}`;
    })
    .attr("transform", d => `translate(${d.x},${d.y})`)
    .on("click", (event, d) => showNodeDetails(d.data));

  node.append("circle").attr("r", nodeRadius);

  node.append("text")
    .attr("dy", "-0.3em")
    .style("font-size", "10px")
    .style("font-weight", "bold")
    .text(d => d.data.id);

  node.append("text")
    .attr("dy", "1em")
    .style("font-size", "9px")
    .style("fill", "#555")
    .text(d => `BF:${d.data.balance_factor} H:${d.data.height}`);
}

function showNodeDetails(nodeData) {
  const modal  = document.getElementById("auditModal");
  const report = document.getElementById("auditReport");
  if (!modal || !report) return;

  const fd = currentAVL?.tree_structure?.[nodeData.id]?.flight_data || {};

  report.innerHTML = `
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <tr style="background:#f0f0f0"><td colspan="2"><b>Detalles del vuelo</b></td></tr>
      <tr><td><b>Código</b></td>      <td>${fd.flight_code  ?? nodeData.id}</td></tr>
      <tr><td><b>Origen</b></td>      <td>${fd.origin       ?? "-"}</td></tr>
      <tr><td><b>Destino</b></td>     <td>${fd.destination  ?? "-"}</td></tr>
      <tr><td><b>Precio base</b></td> <td>${fd.base_price   ?? "-"}</td></tr>
      <tr><td><b>Precio final</b></td><td>${fd.final_price  ?? "-"}</td></tr>
      <tr><td><b>Pasajeros</b></td>   <td>${fd.passengers   ?? 0}</td></tr>
      <tr><td><b>Promoción</b></td>   <td>${fd.promotion    ?? 0}</td></tr>
      <tr><td><b>Prioridad</b></td>   <td>${fd.priority     ?? "-"}</td></tr>
      <tr><td><b>Altura (H)</b></td>  <td>${fd.height       ?? nodeData.height}</td></tr>
      <tr><td><b>Factor Bal.</b></td> <td>${fd.balance_factor ?? nodeData.balance_factor}</td></tr>
    </table>`;

  modal.style.display = "block";

  // También rellena el formulario para poder eliminar desde ahí
  if (window._fillFormFromNode) window._fillFormFromNode(nodeData);
}


// ═════════════════════════════════════════════════════════════════════════════
// WIRING DE BOTONES
// ═════════════════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {

  // Modales
  function openModal(id)  { document.getElementById(id).style.display = "block"; }
  function closeModal(id) { document.getElementById(id).style.display = "none";  }

  document.querySelectorAll(".close").forEach(btn => {
    btn.addEventListener("click", () => btn.closest(".modal").style.display = "none");
  });
  window.addEventListener("click", e => {
    document.querySelectorAll(".modal").forEach(m => { if (e.target === m) m.style.display = "none"; });
  });

  // ── Cargar JSON ───────────────────────────────────────────────────────
  document.getElementById("loadJsonBtn")?.addEventListener("click", () => {
    openModal("jsonModal");
  });

  document.getElementById("loadJsonConfirmBtn")?.addEventListener("click", async () => {
    const file     = document.getElementById("jsonFile")?.files?.[0];
    const loadType = document.getElementById("loadType")?.value ?? "insertion";

    if (!file) { alert("Selecciona un archivo JSON primero."); return; }

    try {
      const data = await apiLoad(file, loadType);
      currentAVL = data.avl;
      currentBST = data.bst;
      updatePanels(data.avl, data.bst);
      renderTree(data.avl.tree_structure, data.avl.root_code);
      closeModal("jsonModal");
    } catch (err) {
      console.error(err);
      alert(`Error al cargar: ${err.message}`);
    }
  });

  // ── Exportar JSON ─────────────────────────────────────────────────────
  document.getElementById("exportTreeBtn")?.addEventListener("click", async () => {
    try {
      await apiExport("avl");
    } catch (err) {
      console.error(err);
      alert(`Error al exportar: ${err.message}`);
    }
  });

  // ── Modo Estrés ───────────────────────────────────────────────────────
  document.getElementById("stressModeBtn")?.addEventListener("click", () => {
    document.body.classList.toggle("stress-mode");
    const active = document.body.classList.contains("stress-mode");
    document.getElementById("stressModeBtn").textContent =
      active ? "Desactivar Modo Estrés" : "Activar Modo Estrés";
    const auditBtn = document.getElementById("auditAvlBtn");
    if (auditBtn) auditBtn.style.display = active ? "inline-block" : "none";
  });

  // ── Rebalanceo Global ─────────────────────────────────────────────────
  document.getElementById("globalRebalanceBtn")?.addEventListener("click", async () => {
    try {
      const data = await apiStatus();
      currentAVL = data.avl;
      currentBST = data.bst;
      updatePanels(data.avl, data.bst);
      renderTree(data.avl.tree_structure, data.avl.root_code);
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  });

  // ── Profundidad Crítica ───────────────────────────────────────────────
  document.getElementById("updateCriticalDepthBtn")?.addEventListener("click", () => {
    const depth = parseInt(document.getElementById("criticalDepth")?.value ?? "5", 10);
    alert(`Profundidad crítica actualizada a: ${depth}`);
  });

  // ── Verificar AVL (solo en modo estrés) ───────────────────────────────
  document.getElementById("auditAvlBtn")?.addEventListener("click", () => {
    openModal("auditModal");
    const report = document.getElementById("auditReport");
    if (!currentAVL) { report.textContent = "No hay árbol cargado."; return; }

    const issues = [];
    for (const [code, node] of Object.entries(currentAVL.tree_structure || {})) {
      const bf = node.flight_data?.balance_factor ?? 0;
      if (bf > 1 || bf < -1) issues.push(`${code} (BF: ${bf})`);
    }
    report.innerHTML = issues.length
      ? `<p style="color:red">⚠ Nodos fuera de rango:</p><ul>${issues.map(i => `<li>${i}</li>`).join("")}</ul>`
      : `<p style="color:green">✔ Propiedad AVL verificada correctamente.</p>`;
  });

  // ── Helpers internos del formulario ──────────────────────────────────

  // Lee los campos del formulario y devuelve un objeto con los datos
  function readForm() {
    return {
      flight_code:  document.getElementById("flightCode")?.value.trim(),
      origin:       document.getElementById("origin")?.value.trim(),
      destination:  document.getElementById("destination")?.value.trim(),
      base_price:   parseFloat(document.getElementById("basePrice")?.value),
      passengers:   parseInt(document.getElementById("passengers")?.value ?? "0", 10),
      promotion:    parseFloat(document.getElementById("promotion")?.value ?? "0"),
      alert:        document.getElementById("alert")?.value.trim() ?? "",
      priority:     parseInt(document.getElementById("priority")?.value ?? "3", 10),
    };
  }

  // Limpia todos los campos del formulario y desactiva botones de edición
  function clearForm() {
    ["flightCode","origin","destination","basePrice","passengers","promotion","alert"]
      .forEach(id => { const el = document.getElementById(id); if (el) el.value = ""; });
    const prio = document.getElementById("priority");
    if (prio) prio.value = "3";
    document.getElementById("editFlightBtn")?.setAttribute("disabled", true);
    document.getElementById("deleteFlightBtn")?.setAttribute("disabled", true);
    document.getElementById("cancelFlightBtn")?.setAttribute("disabled", true);
    selectedFlightCode = null;
  }

  // Actualiza árbol local y redibuja tras cualquier operación exitosa
  function applyTreeResponse(data) {
    currentAVL = data.avl;
    updatePanels(data.avl, currentBST || { root: null, height: 0, nodes: 0, leaves: 0, rotation_count: {} });
    renderTree(data.avl.tree_structure, data.avl.root_code);
  }

  // ── Selección de nodo al hacer click en el árbol ──────────────────────
  // Cuando el usuario hace click en un nodo, además de mostrar el modal
  // de detalles, rellena el formulario para poder editar o eliminar.
  let selectedFlightCode = null;

  // Sobreescribimos showNodeDetails para que también rellene el formulario
  const _originalShowNodeDetails = showNodeDetails;
  window._fillFormFromNode = function(nodeData) {
    const fd = currentAVL?.tree_structure?.[nodeData.id]?.flight_data || {};
    selectedFlightCode = nodeData.id;

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val ?? ""; };
    set("flightCode",   fd.flight_code  ?? nodeData.id);
    set("origin",       fd.origin       ?? "");
    set("destination",  fd.destination  ?? "");
    set("basePrice",    fd.base_price   ?? "");
    set("passengers",   fd.passengers   ?? 0);
    set("promotion",    fd.promotion    ?? 0);
    set("alert",        fd.alert        ?? "");
    const prio = document.getElementById("priority");
    if (prio) prio.value = fd.priority ?? 3;

    // Habilitar botones de edición/eliminación
    document.getElementById("editFlightBtn")?.removeAttribute("disabled");
    document.getElementById("deleteFlightBtn")?.removeAttribute("disabled");
    document.getElementById("cancelFlightBtn")?.removeAttribute("disabled");
  };

  // ── Agregar vuelo ─────────────────────────────────────────────────────
  document.getElementById("addFlightBtn")?.addEventListener("click", async () => {
    const data = readForm();

    if (!data.flight_code || !data.origin || !data.destination || isNaN(data.base_price)) {
      alert("Completa los campos obligatorios: Código, Origen, Destino y Precio Base.");
      return;
    }

    try {
      const res = await fetch(`${API}/api/insert`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(data),
      });
      const json = await res.json();
      if (!res.ok) { alert(`Error: ${json.error}`); return; }

      applyTreeResponse(json);
      clearForm();
    } catch (err) {
      console.error(err);
      alert(`Error al agregar: ${err.message}`);
    }
  });

  // ── Eliminar vuelo ────────────────────────────────────────────────────
  // El código del vuelo a eliminar viene del campo flightCode del formulario
  // (que se rellena al hacer click en un nodo del árbol).
  document.getElementById("deleteFlightBtn")?.addEventListener("click", async () => {
    const code = document.getElementById("flightCode")?.value.trim();
    if (!code) { alert("Selecciona un vuelo del árbol primero (haz click en un nodo)."); return; }

    if (!confirm(`¿Eliminar el vuelo ${code}?`)) return;

    try {
      const res = await fetch(`${API}/api/delete/${encodeURIComponent(code)}`, {
        method: "DELETE",
      });
      const json = await res.json();
      if (!res.ok) { alert(`Error: ${json.error}`); return; }

      applyTreeResponse(json);
      clearForm();
    } catch (err) {
      console.error(err);
      alert(`Error al eliminar: ${err.message}`);
    }
  });

  // ── Cancelar / limpiar formulario ─────────────────────────────────────
  document.getElementById("cancelFlightBtn")?.addEventListener("click", () => {
    clearForm();
  });

});
   