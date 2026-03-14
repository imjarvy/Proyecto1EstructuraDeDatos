// Queue UI module — handles all /api/queue interactions

export function createQueueUi({ api, showToast, updatePanels }) {

  // ── helpers ──────────────────────────────────────────────
  function getQueueFormPayload() {
    const code  = document.getElementById("qFlightCode").value.trim().toUpperCase();
    const org   = document.getElementById("qOrigin").value.trim();
    const dst   = document.getElementById("qDestination").value.trim();
    const price = parseFloat(document.getElementById("qBasePrice").value);

    if (!code || !org || !dst || isNaN(price)) {
      showToast("Completa código, origen, destino y precio", "error");
      return null;
    }

    return {
      flight_code: code,
      origin:      org,
      destination: dst,
      base_price:  price,
      passengers:  parseInt(document.getElementById("qPassengers").value) || 0,
      promotion:   parseFloat(document.getElementById("qPromotion").value) || 0,
      alert:       document.getElementById("qAlert").value.trim(),
      priority:    parseInt(document.getElementById("qPriority").value),
    };
  }

  function clearQueueForm() {
    ["qFlightCode","qOrigin","qDestination","qBasePrice",
     "qPassengers","qPromotion","qAlert"].forEach(id => {
      document.getElementById(id).value = "";
    });
    document.getElementById("qPriority").value = "3";
  }

  function renderQueueState(data) {
    // update counters
    document.getElementById("qPending").textContent   = data.total_pending;
    document.getElementById("qProcessed").textContent = data.total_processed;
    document.getElementById("qConflicts").textContent = data.total_conflicts;

    // render pending list
    const list = document.getElementById("pendingList");
    if (!data.pending.length) {
      list.innerHTML = "<li class='empty-queue'>Cola vacía</li>";
    } else {
      list.innerHTML = data.pending.map(f => `
        <li class="queue-item">
          <strong>${f.flight_code}</strong>
          ${f.origin} → ${f.destination}
          <span class="queue-price">$${f.base_price.toLocaleString()}</span>
        </li>`).join("");
    }

    // render conflicts if any
    const log = document.getElementById("conflictLog");
    if (!data.conflicts.length) {
      log.classList.add("hidden");
    } else {
      log.classList.remove("hidden");
      document.getElementById("conflictList").innerHTML =
        data.conflicts.map(c => `
          <li class="conflict-item">
            ⚠ <strong>${c.flight_code}</strong> — ${c.reason}
          </li>`).join("");
    }
  }

  async function refreshQueue() {
    try {
      const data = await api("/api/queue");
      renderQueueState(data);
    } catch (_) {}
  }

  // ── event listeners ───────────────────────────────────────

  document.getElementById("enqueueBtn").addEventListener("click", async () => {
    const payload = getQueueFormPayload();
    if (!payload) return;

    try {
      await api("/api/queue/enqueue", "POST", payload);
      clearQueueForm();
      showToast(`Vuelo ${payload.flight_code} encolado`, "success");
      await refreshQueue();
    } catch (_) {}
  });

  document.getElementById("processOneBtn").addEventListener("click", async () => {
    try {
      const data = await api("/api/queue/process-one", "POST");
      if (data.status === "empty") {
        showToast("Cola vacía, no hay vuelos pendientes", "info");
        return;
      }
      if (data.conflict) {
        showToast(`Conflicto en ${data.conflict.flight}`, "warn");
      } else {
        showToast(`Vuelo ${data.inserted} insertado en el árbol`, "success");
      }
      updatePanels(await getTreeState());
      await refreshQueue();
    } catch (_) {}
  });

  document.getElementById("processAllBtn").addEventListener("click", async () => {
    try {
      const data = await api("/api/queue/process-all", "POST");
      showToast(`${data.total_inserted} vuelos insertados — ${data.total_conflicts} conflictos`, "success");
      updatePanels(await getTreeState());
      await refreshQueue();
    } catch (_) {}
  });

  document.getElementById("clearQueueBtn").addEventListener("click", async () => {
    if (!confirm("¿Limpiar toda la cola pendiente?")) return;
    try {
      await api("/api/queue/clear", "DELETE");
      showToast("Cola limpiada", "info");
      await refreshQueue();
    } catch (_) {}
  });

  async function getTreeState() {
    const data = await api("/api/tree-state");
    return data.tree;
  }

  // load initial state on startup
  refreshQueue();
}