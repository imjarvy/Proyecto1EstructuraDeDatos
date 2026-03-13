// =============================================================================
//  SkyBalance AVL - Frontend Coordinator
//  Responsibility: shared state, generic helpers, and module initialization.
// =============================================================================

import { registerHandlers } from "./handlers.js";
import { createTreeUi } from "./treeUi.js";

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
  document.querySelectorAll(".close[data-close]").forEach(button => {
    button.addEventListener("click", () => closeModal(button.dataset.close));
  });

  document.querySelectorAll(".modal").forEach(overlay => {
    overlay.addEventListener("click", event => {
      if (event.target === overlay) closeModal(overlay.id);
    });
  });
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
    clearForm: treeUi.clearForm,
    getFormPayload: treeUi.getFormPayload,
  });
}

initializeApp();
