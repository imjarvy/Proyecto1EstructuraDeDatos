// =============================================================================
//  SkyBalance AVL - Handlers Module
//  Responsibility: register UI event listeners and orchestrate frontend flows.
// =============================================================================

export function registerHandlers({
  state,
  api,
  showToast,
  openModal,
  closeModal,
  updatePanels,
  updateBstPanel,
  clearForm,
  getFormPayload,
}) {
  document.getElementById("loadJsonBtn").addEventListener("click", () => openModal("jsonModal"));

  document.getElementById("jsonFile").addEventListener("change", event => {
    const name = event.target.files[0]?.name || "Seleccionar archivo .json";
    document.getElementById("fileLabel").textContent = "📂 " + name;
  });

  document.getElementById("loadJsonConfirmBtn").addEventListener("click", async () => {
    const fileInput = document.getElementById("jsonFile");
    if (!fileInput.files.length) {
      showToast("Selecciona un archivo JSON", "error");
      return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("type", document.getElementById("loadType").value);

    try {
      const response = await fetch("/api/load-tree", { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);

      updatePanels(data.tree);
      if (data.bst_tree) updateBstPanel(data.bst_tree);

      closeModal("jsonModal");
      showToast("Arbol cargado correctamente", "success");
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  document.getElementById("exportTreeBtn").addEventListener("click", async () => {
    try {
      const data = await api("/api/export-tree");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "skybalance_tree.json";
      anchor.click();
      URL.revokeObjectURL(url);
      showToast("Arbol exportado", "success");
    } catch (_) {}
  });

  document.getElementById("addFlightBtn").addEventListener("click", async () => {
    const payload = getFormPayload();
    if (!payload) return;

    try {
      const data = await api("/api/add-flight", "POST", payload);
      updatePanels(data.tree);
      clearForm();
      showToast(`Vuelo ${payload.flight_code} agregado`, "success");
    } catch (_) {}
  });

  document.getElementById("editFlightBtn").addEventListener("click", async () => {
    if (!state.selectedCode) return;

    const payload = getFormPayload();
    if (!payload) return;

    const updatedData = { ...payload };
    const editedCode = payload.flight_code.trim().toUpperCase();
    const currentCode = state.selectedCode.trim().toUpperCase();

    if (editedCode !== currentCode) {
      updatedData.new_flight_code = editedCode;
    }

    delete updatedData.flight_code;

    try {
      const data = await api("/api/edit-flight", "POST", {
        flight_code: state.selectedCode,
        updated_data: updatedData,
      });
      const updatedCode = state.selectedCode;
      updatePanels(data.tree);
      clearForm();
      showToast(`Vuelo ${updatedCode} actualizado`, "success");
    } catch (_) {}
  });

  document.getElementById("deleteFlightBtn").addEventListener("click", async () => {
    if (!state.selectedCode) return;
    if (!confirm(`¿Eliminar el vuelo ${state.selectedCode}? (solo el nodo)`)) return;

    try {
      const data = await api("/api/delete-flight", "POST", { flight_code: state.selectedCode });
      const deletedCode = state.selectedCode;
      updatePanels(data.tree);
      clearForm();
      showToast(`Vuelo ${deletedCode} eliminado`, "info");
    } catch (_) {}
  });

  document.getElementById("cancelFlightBtn").addEventListener("click", async () => {
    if (!state.selectedCode) return;
    if (!confirm(`¿Cancelar el vuelo ${state.selectedCode} y TODA su descendencia?`)) return;

    try {
      const data = await api("/api/cancel-flight", "POST", { flight_code: state.selectedCode });
      const cancelledCode = state.selectedCode;
      updatePanels(data.tree);
      clearForm();
      showToast(`Vuelo ${cancelledCode} cancelado (${data.removed_count} nodos eliminados)`, "warn");
    } catch (_) {}
  });

  document.getElementById("undoBtn").addEventListener("click", async () => {
    try {
      const data = await api("/api/undo", "POST");
      updatePanels(data.tree);
      showToast("Accion deshecha", "info");
    } catch (_) {}
  });

  document.getElementById("stressModeBtn").addEventListener("click", async () => {
    const nextState = !state.stressMode;

    try {
      const data = await api("/api/toggle-stress-mode", "POST", { stress_mode: nextState });
      state.stressMode = data.stress_mode;
      updatePanels(data.tree);

      const button = document.getElementById("stressModeBtn");
      const banner = document.getElementById("stressBanner");
      const auditButton = document.getElementById("auditAvlBtn");

      if (state.stressMode) {
        button.textContent = "Desactivar Modo Estres";
        button.classList.add("active-stress");
        banner.classList.remove("hidden");
        auditButton.style.display = "inline-block";
        showToast("Modo Estres activado", "warn");
      } else {
        button.textContent = "Activar Modo Estres";
        button.classList.remove("active-stress");
        banner.classList.add("hidden");
        auditButton.style.display = "none";
        showToast(`Modo normal restaurado - ${data.rotations_done} rotaciones aplicadas`, "success");
      }
    } catch (_) {}
  });

  document.getElementById("globalRebalanceBtn").addEventListener("click", async () => {
    try {
      const data = await api("/api/global-rebalance", "POST");
      updatePanels(data.tree);
      showToast(`Rebalanceo global completado - ${data.rotations_done} rotaciones`, "success");
    } catch (_) {}
  });

  document.getElementById("updateCriticalDepthBtn").addEventListener("click", async () => {
    const value = parseInt(document.getElementById("criticalDepth").value, 10);
    if (Number.isNaN(value) || value < 1) {
      showToast("Profundidad invalida", "error");
      return;
    }

    try {
      const data = await api("/api/update-critical-depth", "POST", { critical_depth: value });
      updatePanels(data.tree);
      showToast(`Profundidad critica actualizada a ${value}`, "success");
    } catch (_) {}
  });

  document.getElementById("deleteLeastProfitable").addEventListener("click", async () => {
    if (!confirm("¿Eliminar el vuelo de menor rentabilidad y toda su subrama?")) return;

    try {
      const data = await api("/api/delete-least-profitable", "POST");
      updatePanels(data.tree);
      showToast(`Vuelo ${data.cancelled} (menor rentabilidad) eliminado`, "warn");
    } catch (_) {}
  });

  document.getElementById("auditAvlBtn").addEventListener("click", async () => {
    try {
      const data = await api("/api/audit-avl");
      const report = document.getElementById("auditReport");

      if (data.valid) {
        report.innerHTML = "<p class='audit-ok'>El arbol cumple la propiedad AVL en todos los nodos.</p>";
      } else {
        const rows = data.report.map(item => `
          <div class="audit-node">
            <strong>${item.flight_code}</strong> <small>(profundidad ${item.depth})</small>
            <ul>${item.issues.map(issue => `<li>${issue}</li>`).join("")}</ul>
          </div>`).join("");
        report.innerHTML = `
          <p class="audit-warn">${data.report.length} nodo(s) inconsistentes:</p>
          ${rows}`;
      }

      openModal("auditModal");
    } catch (_) {}
  });

  document.getElementById("saveVersionBtn").addEventListener("click", async () => {
    const name = document.getElementById("versionName").value.trim();
    if (!name) {
      showToast("Escribe un nombre de version", "error");
      return;
    }

    try {
      await api("/api/save-version", "POST", { version_name: name });
      document.getElementById("versionName").value = "";
      showToast(`Version \"${name}\" guardada`, "success");
    } catch (_) {}
  });

  document.getElementById("showVersionsBtn").addEventListener("click", async () => {
    await refreshVersionsList();
    openModal("versionsModal");
  });

  async function refreshVersionsList() {
    try {
      const data = await api("/api/list-versions");
      const list = document.getElementById("versionsList");
      const entries = Object.entries(data.versions || {});

      if (!entries.length) {
        list.innerHTML = "<li class='no-versions'>No hay versiones guardadas</li>";
        return;
      }

      list.innerHTML = entries.map(([name, meta]) => `
        <li class="version-item">
          <div class="version-info">
            <strong>${name}</strong>
            <small>${new Date(meta.timestamp).toLocaleString("es-CO")}</small>
            <small>${meta.tree_size ?? "?"} nodos - altura ${meta.tree_height ?? "?"}</small>
          </div>
          <div class="version-actions">
            <button class="btn-restore" data-name="${name}">Restaurar</button>
            <button class="btn-del-ver" data-name="${name}">Eliminar</button>
          </div>
        </li>`).join("");

      list.querySelectorAll(".btn-restore").forEach(button => {
        button.addEventListener("click", async () => {
          const versionName = button.dataset.name;
          try {
            const data = await api("/api/restore-version", "POST", { version_name: versionName });
            updatePanels(data.tree);
            closeModal("versionsModal");
            showToast(`Version \"${versionName}\" restaurada`, "success");
          } catch (_) {}
        });
      });

      list.querySelectorAll(".btn-del-ver").forEach(button => {
        button.addEventListener("click", async () => {
          const versionName = button.dataset.name;
          if (!confirm(`¿Eliminar la version \"${versionName}\"?`)) return;

          try {
            await api("/api/delete-version", "POST", { version_name: versionName });
            showToast(`Version \"${versionName}\" eliminada`, "info");
            await refreshVersionsList();
          } catch (_) {}
        });
      });
    } catch (_) {}
  }
}
