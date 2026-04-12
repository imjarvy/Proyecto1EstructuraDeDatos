// =============================================================================
//  SkyBalance AVL - Frontend Coordinator
// =============================================================================

import { registerHandlers } from "./handlers.js";
import { createTreeUi } from "./treeUi.js";
import { createQueueUi } from "./queueUi.js";

const state = {
  selectedCode: null,
  stressMode: false,
};

function showToast(message, type = "info") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast toast-${type} show`;
  setTimeout(() => toast.classList.remove("show"), 3500);
}

async function api(endpoint, method = "GET", body = null) {
  const options = { method, headers: {} };
  if (body) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(endpoint, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Server error");
    return data;
  } catch (error) {
    showToast(error.message, "error");
    throw error;
  }
}

function openModal(id) {
  document.getElementById(id).style.display = "flex";
}

function closeModal(id) {
  document.getElementById(id).style.display = "none";
}

function registerModalCloseHandlers() {
  // New layout uses class "modal-close" with data-close attribute
  document.querySelectorAll(".modal-close[data-close]").forEach(button => {
    button.addEventListener("click", () => closeModal(button.dataset.close));
  });

  // Fallback: old .close[data-close] pattern
  document.querySelectorAll(".close[data-close]").forEach(button => {
    button.addEventListener("click", () => closeModal(button.dataset.close));
  });

  // Click overlay to close
  document.querySelectorAll(".modal").forEach(overlay => {
    overlay.addEventListener("click", event => {
      if (event.target === overlay) closeModal(overlay.id);
    });
  });
}

function syncStressModeUi(enabled) {
  const button = document.getElementById("stressModeBtn");
  const banner = document.getElementById("stressBanner");
  const auditButton = document.getElementById("auditAvlBtn");

  state.stressMode = enabled;

  if (enabled) {
    button.textContent = "Desactivar Estrés";
    button.classList.add("active-stress");
    banner.classList.remove("hidden");
    auditButton.style.display = "inline-block";
    document.body.classList.add("stress-active");
    return;
  }

  button.textContent = "Modo Estrés";
  button.classList.remove("active-stress");
  banner.classList.add("hidden");
  auditButton.style.display = "none";
  document.body.classList.remove("stress-active");
}

async function hydrateInitialState(treeUi) {
  try {
    const data = await api("/api/tree-state");
    treeUi.updatePanels(data.tree);

    if (typeof data.stress_mode === "boolean") {
      syncStressModeUi(data.stress_mode);
    }

    if (typeof data.critical_depth === "number") {
      document.getElementById("criticalDepth").value = data.critical_depth;
    }

    if (!data.tree?.root) {
      treeUi.clearBstPanel();
    }
  } catch (_) {}
}

function initializeApp() {
  const treeUi = createTreeUi({ state, showToast });

  registerModalCloseHandlers();
  registerHandlers({
    state,
    api,
    showToast,
    openModal,
    closeModal,
    updatePanels: treeUi.updatePanels,
    updateBstPanel: treeUi.updateBstPanel,
    clearBstPanel: treeUi.clearBstPanel,
    clearForm: treeUi.clearForm,
    getFormPayload: treeUi.getFormPayload,
    syncStressModeUi,
  });
  createQueueUi({ api, showToast, updatePanels: treeUi.updatePanels });

  hydrateInitialState(treeUi);
}

initializeApp();