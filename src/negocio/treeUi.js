// =============================================================================
//  SkyBalance AVL - Tree UI Module
//  Responsibility: tree rendering, panel updates, node selection, and form sync.
// =============================================================================

export function createTreeUi({ state, showToast }) {
  const d3Api = window.d3;

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

    d3Api.tree().size([width, height])(hierarchy);

    group.selectAll(".link")
      .data(hierarchy.links())
      .join("path")
      .attr("class", "link")
      .attr("d", d3Api.linkVertical().x(data => data.x).y(data => data.y));

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
      .attr("transform", data => `translate(${data.x},${data.y})`)
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

  function updatePanels(treeData) {
    const metrics = treeData.metrics || {};

    document.getElementById("rootValue").textContent = treeData.root?.flight_code ?? "-";
    document.getElementById("heightValue").textContent = treeData.height ?? 0;
    document.getElementById("leavesValue").textContent = treeData.leaf_count ?? 0;
    document.getElementById("nodesValue").textContent = treeData.node_count ?? 0;

    document.getElementById("rotationsValue").textContent = metrics.total_rotations ?? 0;
    document.getElementById("currentHeight").textContent = treeData.height ?? 0;
    document.getElementById("llRotations").textContent = metrics.LL ?? 0;
    document.getElementById("rrRotations").textContent = metrics.RR ?? 0;
    document.getElementById("lrRotations").textContent = metrics.LR ?? 0;
    document.getElementById("rlRotations").textContent = metrics.RL ?? 0;
    document.getElementById("massCancellations").textContent = metrics.mass_cancellations ?? 0;

    document.getElementById("breadthTraversal").textContent =
      (treeData.breadth_order || []).join(" -> ") || "-";
    document.getElementById("depthTraversal").textContent =
      (treeData.depth_order || []).join(" -> ") || "-";

    document.getElementById("undoBtn").disabled = !treeData.can_undo;

    renderTree(treeData.root, "treeSvg", "treeContainer");
  }

  function updateBstPanel(bstData) {
    document.getElementById("bstSection").classList.remove("hidden");
    document.getElementById("bstRoot").textContent = bstData.root?.flight_code ?? "-";
    document.getElementById("bstHeight").textContent = bstData.height ?? 0;
    document.getElementById("bstLeaves").textContent = bstData.leaf_count ?? 0;
    document.getElementById("bstNodes").textContent = bstData.node_count ?? 0;
    renderTree(bstData.root, "bstSvg", "bstContainer");
  }

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

    document.getElementById("nodeDetail").classList.remove("hidden");
    document.getElementById("nodeDetailContent").innerHTML = `
      <p><strong>Codigo:</strong>         ${nodeData.flight_code}</p>
      <p><strong>Ruta:</strong>           ${nodeData.origin} -> ${nodeData.destination}</p>
      <p><strong>Precio base:</strong>    $${(nodeData.base_price || 0).toFixed(2)}</p>
      <p><strong>Precio final:</strong>   $${(nodeData.final_price || 0).toFixed(2)}
         ${nodeData.is_critical ? '<span class="critical-tag">+25%</span>' : ""}</p>
      <p><strong>Pasajeros:</strong>      ${nodeData.passengers}</p>
      <p><strong>Promocion:</strong>      ${((nodeData.promotion || 0) * 100).toFixed(0)}%</p>
      <p><strong>Prioridad:</strong>      ${nodeData.priority}</p>
      <p><strong>Altura nodo:</strong>    ${nodeData.height}</p>
      <p><strong>Factor balance:</strong> ${nodeData.balance_factor}</p>
      <p><strong>Profundidad:</strong>    ${nodeData.depth}</p>
      ${nodeData.alert ? `<p><strong>Alerta:</strong> ${nodeData.alert}</p>` : ""}
    `;
  }

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

  function getFormPayload() {
    const flightCode = document.getElementById("flightCode").value.trim();
    const origin = document.getElementById("origin").value.trim();
    const destination = document.getElementById("destination").value.trim();
    const basePrice = parseFloat(document.getElementById("basePrice").value);

    if (!flightCode || !origin || !destination || Number.isNaN(basePrice)) {
      showToast("Completa los campos requeridos: Codigo, Origen, Destino, Precio Base", "error");
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
    selectNode,
    clearForm,
    getFormPayload,
  };
}
