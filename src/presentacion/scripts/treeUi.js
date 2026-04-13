// =============================================================================
//  SkyBalance AVL - Tree UI Module
//  Responsibility: tree rendering, panel updates, node selection, and form sync.
// =============================================================================

/**
 * Create tree UI utilities for rendering and panel synchronization.
 *
 * @param {Object} deps - Tree UI dependencies.
 * @param {Object} deps.state - Shared frontend state.
 * @param {Function} deps.showToast - Toast notifier for validation feedback.
 * @returns {{
 *   renderTree: Function,
 *   updatePanels: Function,
 *   updateBstPanel: Function,
 *   selectNode: Function,
 *   clearForm: Function,
 *   getFormPayload: Function
 * }} Public tree UI API.
 */
export function createTreeUi({ state, showToast }) {
  const d3Api = window.d3;

  /**
   * Render a tree payload into an SVG container using D3 hierarchy layout.
   *
   * @param {Object|null} root - Root node payload from backend.
   * @param {string} svgId - Target SVG element id.
   * @param {string} containerId - Parent container id used for sizing.
   * @returns {void}
   */
  function renderTree(root, svgId, containerId) {
    const svg = d3Api.select(`#${svgId}`);
    svg.selectAll("*").remove();

    const emptyState = document.getElementById("emptyState");

    if (!root) {
      if (emptyState) emptyState.style.display = "flex";
      return;
    }
    if (emptyState) emptyState.style.display = "none";

    const container = document.getElementById(containerId);
    const widthPx = container.clientWidth || 900;
    const heightPx = container.clientHeight || 500;

    const margin = { top: 50, right: 20, bottom: 20, left: 20 };
    const width = widthPx - margin.left - margin.right;
    const height = heightPx - margin.top - margin.bottom;

    const group = svg.attr("width", widthPx).attr("height", heightPx)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    svg.call(d3Api.zoom().scaleExtent([0.2, 4]).on("zoom", event => {
      group.attr("transform", event.transform);
    }));

    const hierarchy = d3Api.hierarchy(root, data => {
      const children = [];
      if (data.left) children.push(data.left);
      if (data.right) children.push(data.right);
      return children.length ? children : null;
    });

    // nodeSize keeps spacing fixed regardless of how many nodes exist,
    // so 2 nodes won't be stretched across the full container width.
    const NODE_W = 80;   // horizontal gap between siblings
    const NODE_H = 80;   // vertical gap between levels
    d3Api.tree().nodeSize([NODE_W, NODE_H])(hierarchy);

    // After nodeSize the root sits at x=0; shift everything so it's centered.
    const nodes = hierarchy.descendants();
    const minX = Math.min(...nodes.map(d => d.x));
    const maxX = Math.max(...nodes.map(d => d.x));
    const treeWidth  = maxX - minX;
    const offsetX = (width / 2) - (treeWidth / 2) - minX;
    const offsetY = 0;

    group.selectAll(".link")
      .data(hierarchy.links())
      .join("path")
      .attr("class", "link")
      .attr("d", d3Api.linkVertical()
        .x(data => data.x + offsetX)
        .y(data => data.y + offsetY));

    const node = group.selectAll(".node")
      .data(hierarchy.descendants())
      .join("g")
      .attr("class", data => {
        let cssClass = "node";
        if (!data.parent) cssClass += " node-root";
        if (data.data.is_critical) cssClass += " node-critical";
        if (!data.data.left && !data.data.right) cssClass += " node-leaf";
        if (data.data.flight_code === state.selectedCode) cssClass += " node-selected";
        return cssClass;
      })
      .attr("transform", data => `translate(${data.x + offsetX},${data.y + offsetY})`)
      .style("cursor", "pointer")
      .on("click", (_, data) => selectNode(data.data));

    node.append("circle").attr("r", 28);

    node.append("text")
      .attr("class", "node-code")
      .attr("dy", "-0.25em")
      .text(data => data.data.flight_code);

    node.append("text")
      .attr("class", "node-bf")
      .attr("dy", "1em")
      .text(data => `bf:${data.data.balance_factor}`);

    node.append("title")
      .text(data =>
        `${data.data.flight_code}\n`
        + `${data.data.origin} -> ${data.data.destination}\n`
        + `Price: $${(data.data.final_price || 0).toFixed(2)}\n`
        + `Passengers: ${data.data.passengers}\n`
        + `Priority: ${data.data.priority}`
      );
  }

  /**
   * Update all AVL metric panels and re-render the main AVL tree.
   *
   * @param {Object} treeData - Standard tree payload returned by backend.
   * @returns {void}
   */
  function updatePanels(treeData) {
    const metrics = treeData.metrics || {};

    document.getElementById("rootValue").textContent = treeData.root?.flight_code ?? "-";
    document.getElementById("heightValue").textContent = treeData.height ?? 0;
    document.getElementById("leavesValue").textContent = treeData.leaf_count ?? 0;
    document.getElementById("nodesValue").textContent = treeData.node_count ?? 0;

    document.getElementById("rotationsValue").textContent = metrics.total_rotations ?? 0;
    document.getElementById("llRotations").textContent = metrics.LL ?? 0;
    document.getElementById("rrRotations").textContent = metrics.RR ?? 0;
    document.getElementById("lrRotations").textContent = metrics.LR ?? 0;
    document.getElementById("rlRotations").textContent = metrics.RL ?? 0;
    document.getElementById("massCancellations").textContent = metrics.mass_cancellations ?? 0;

    document.getElementById("breadthTraversal").textContent =
      (treeData.breadth_order || []).join(" → ") || "—";
    document.getElementById("depthTraversal").textContent =
      (treeData.depth_order || []).join(" → ") || "—";

    document.getElementById("undoBtn").disabled = !treeData.can_undo;

    renderTree(treeData.root, "treeSvg", "treeContainer");
  }

  /**
   * Update BST comparison panel values and render BST tree.
   *
   * @param {Object} bstData - BST payload returned by backend in insertion mode.
   * @returns {void}
   */
  function updateBstPanel(bstData) {
    document.getElementById("bstSection").classList.remove("hidden");
    document.getElementById("bstRoot").textContent = bstData.root?.flight_code ?? "-";
    document.getElementById("bstHeight").textContent = bstData.height ?? 0;
    // bstLeaves removed from new layout (compact BST header)
    const bstLeaves = document.getElementById("bstLeaves");
    if (bstLeaves) bstLeaves.textContent = bstData.leaf_count ?? 0;
    document.getElementById("bstNodes").textContent = bstData.node_count ?? 0;
    renderTree(bstData.root, "bstSvg", "bstContainer");
  }

  /**
   * Clear BST comparison panel: hide section and clear SVG.
   * Called when loading a mode that doesn't have BST data.
   *
   * @returns {void}
   */
  function clearBstPanel() {
    document.getElementById("bstSection").classList.add("hidden");
    const bstSvg = d3Api.select("#bstSvg");
    bstSvg.selectAll("*").remove();
  }

  /**
   * Handle node selection from the tree and synchronize form/detail panels.
   *
   * @param {Object} nodeData - Selected flight node payload.
   * @returns {void}
   */
  function selectNode(nodeData) {
    state.selectedCode = nodeData.flight_code;

    document.getElementById("flightCode").value = nodeData.flight_code;
    document.getElementById("origin").value = nodeData.origin;
    document.getElementById("destination").value = nodeData.destination;
    document.getElementById("basePrice").value = nodeData.base_price;
    document.getElementById("passengers").value = nodeData.passengers;
    document.getElementById("promotion").value = nodeData.promotion;
    document.getElementById("alert").value = nodeData.alert || "";
    document.getElementById("priority").value = nodeData.priority;

    document.getElementById("editFlightBtn").disabled = false;
    document.getElementById("deleteFlightBtn").disabled = false;
    document.getElementById("cancelFlightBtn").disabled = false;

    // Update detail header code label
    const detailCode = document.getElementById("nodeDetailCode");
    if (detailCode) detailCode.textContent = nodeData.flight_code;

    document.getElementById("nodeDetail").classList.remove("hidden");
    document.getElementById("nodeDetailContent").innerHTML = `
      <p><strong>Ruta</strong>           <span>${nodeData.origin} → ${nodeData.destination}</span></p>
      <p><strong>Precio base</strong>    <span>$${(nodeData.base_price || 0).toFixed(2)}</span></p>
      <p><strong>Precio final</strong>   <span>$${(nodeData.final_price || 0).toFixed(2)}${nodeData.is_critical ? '<span class="critical-tag">+25%</span>' : ""}</span></p>
      <p><strong>Pasajeros</strong>      <span>${nodeData.passengers}</span></p>
      <p><strong>Promoción</strong>      <span>${((nodeData.promotion || 0) * 100).toFixed(0)}%</span></p>
      <p><strong>Prioridad</strong>      <span>${nodeData.priority}</span></p>
      <p><strong>Altura nodo</strong>    <span>${nodeData.height}</span></p>
      <p><strong>Factor balance</strong> <span>${nodeData.balance_factor}</span></p>
      <p><strong>Profundidad</strong>    <span>${nodeData.depth}</span></p>
      ${nodeData.alert ? `<p><strong>Alerta</strong> <span>${nodeData.alert}</span></p>` : ""}
    `;
  }

  /**
   * Clear form fields and reset button/detail state after operations.
   *
   * @returns {void}
   */
  function clearForm() {
    state.selectedCode = null;
    ["flightCode", "origin", "destination", "basePrice", "passengers", "promotion", "alert"]
      .forEach(id => {
        document.getElementById(id).value = "";
      });
    document.getElementById("priority").value = "3";
    document.getElementById("editFlightBtn").disabled = true;
    document.getElementById("deleteFlightBtn").disabled = true;
    document.getElementById("cancelFlightBtn").disabled = true;
    document.getElementById("nodeDetail").classList.add("hidden");
  }

  /**
   * Build and validate payload for add/edit flight requests.
   *
   * @returns {Object|null} Form payload, or null when required fields are invalid.
   */
  function getFormPayload() {
    const flightCode = document.getElementById("flightCode").value.trim();
    const origin = document.getElementById("origin").value.trim();
    const destination = document.getElementById("destination").value.trim();
    const basePrice = parseFloat(document.getElementById("basePrice").value);

    if (!flightCode || !origin || !destination || Number.isNaN(basePrice)) {
      showToast("Completa los campos requeridos: Código, Origen, Destino, Precio Base", "error");
      return null;
    }

    return {
      flight_code: flightCode,
      origin,
      destination,
      base_price: basePrice,
      passengers: parseInt(document.getElementById("passengers").value, 10) || 0,
      promotion: parseFloat(document.getElementById("promotion").value) || 0,
      alert: document.getElementById("alert").value.trim(),
      priority: parseInt(document.getElementById("priority").value, 10),
    };
  }

  return {
    renderTree,
    updatePanels,
    updateBstPanel,
    clearBstPanel,
    selectNode,
    clearForm,
    getFormPayload,
  };
}