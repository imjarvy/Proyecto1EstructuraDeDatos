// =============================================================================
//  SkyBalance AVL - Frontend Coordinator
//  Responsibility: shared state, generic helpers, and module initialization.
// =============================================================================

import { registerHandlers } from "./handlers.js";
import { createTreeUi } from "./treeUi.js";
import { createQueueUi } from "./queueUi.js";

/**
 * Shared UI state used across modules.
 * @type {{selectedCode: (string|null), stressMode: boolean}}
 */
const state = {
  selectedCode: null,
  stressMode: false,
};

/**
 * Display a toast notification.
 *
 * @param {string} message - Text to show in the toast.
 * @param {"info"|"success"|"warn"|"error"} [type="info"] - Toast visual variant.
 * @returns {void}
 */
function showToast(message, type = "info") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast toast-${type} show`;
  setTimeout(() => toast.classList.remove("show"), 3500);
}

/**
 * Execute an API call and normalize backend errors for UI handling.
 *
 * @param {string} endpoint - Backend endpoint path.
 * @param {string} [method="GET"] - HTTP method.
 * @param {Object|null} [body=null] - JSON body for non-GET requests.
 * @returns {Promise<Object>} Parsed JSON response body.
 */
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

/**
 * Show a modal overlay by id.
 *
 * @param {string} id - Modal element id.
 * @returns {void}
 */
function openModal(id) {
  document.getElementById(id).style.display = "flex";
}

/**
 * Hide a modal overlay by id.
 *
 * @param {string} id - Modal element id.
 * @returns {void}
 */
function closeModal(id) {
  document.getElementById(id).style.display = "none";
}

/**
 * Register click handlers that close modals by button or overlay click.
 *
 * @returns {void}
 */
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

/**
 * Bootstrap the frontend modules and wire shared dependencies.
 *
 * @returns {void}
 */
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
  createQueueUi({ api, showToast, updatePanels: treeUi.updatePanels });
}

initializeApp();
