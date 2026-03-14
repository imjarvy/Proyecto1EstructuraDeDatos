"""
SkyBalance AVL - Flask Web Application.

REST API layer that bridges the Python backend with the HTML/JS frontend.
Only exposes endpoints for functionality already implemented in the Python
modules: AVLTree, AVLTreeManager, BST, DataPersistence, VersionManager.
"""

import json
import os
import sys

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.modelos.AVLTree import AVLTree
from src.modelos.BST import BST
from src.negocio.AVLTreeManager import AVLTreeManager
from src.negocio.TreeAnalysisManager import TreeAnalysisManager
from src.acceso_datos.DataPersistence import DataPersistence
from src.acceso_datos.DataStorage import DataStorage
from src.acceso_datos.VersionManager import VersionManager

app = Flask(
    __name__,
    template_folder="src/presentacion/vistas",
    static_folder="src/presentacion/estilos",
    static_url_path="/estilos",
)
CORS(app)

# Route to serve static files from src/negocio/ (script.js, etc.)
NEGOCIO_DIR = os.path.join(os.path.dirname(__file__), "src", "negocio")

@app.route("/negocio/<path:filename>")
def negocio_static(filename):
    """Serve static files from the negocio directory."""
    return send_from_directory(NEGOCIO_DIR, filename)


# ===========================================================================
# GLOBAL STATE
# ===========================================================================

manager        = AVLTreeManager()   # wraps AVLTree + undo stack
bst_tree       = BST()              # plain BST used for insertion-mode comparison
persistence    = DataPersistence()
versions       = VersionManager()
critical_depth = 5                  # default critical depth threshold
analysis       = TreeAnalysisManager()
storage        = DataStorage()


# ===========================================================================
# HELPERS
# ===========================================================================

def _node_to_dict(node, depth: int = 0):
    """
    Recursively convert a FlightNode tree into a nested dict for D3.

    Args:
        node: Current FlightNode (or None).
        depth: Current depth in the tree.

    Returns:
        dict with all node fields plus 'depth', 'is_critical', 'left', 'right'.
    """
    if node is None:
        return None
    d = node.to_dict()
    d["depth"]       = depth
    d["is_critical"] = depth > critical_depth
    d["left"]        = _node_to_dict(node.left,  depth + 1)
    d["right"]       = _node_to_dict(node.right, depth + 1)
    return d


def _bst_node_to_dict(node, depth: int = 0):
    """
    Recursively convert a BST FlightNode into a nested dict.

    Args:
        node: Current FlightNode (or None).
        depth: Current depth in the tree.

    Returns:
        dict with all node fields plus 'depth', 'left', 'right'.
    """
    if node is None:
        return None
    d = node.to_dict()
    d["depth"] = depth
    d["left"]  = _bst_node_to_dict(node.left,  depth + 1)
    d["right"] = _bst_node_to_dict(node.right, depth + 1)
    return d


def _tree_payload() -> dict:
    """
    Build the standardised AVL tree payload returned to the frontend.

    Includes the nested root hierarchy for D3, tree metadata, rotation
    counters, traversal orders, and whether an undo action is available.

    Returns:
        dict with keys: root, height, node_count, leaf_count, can_undo,
        breadth_order, depth_order, metrics.
    """
    t    = manager.tree
    meta = persistence.get_tree_metadata(t.root)

    breadth_codes = []
    depth_codes   = []
    if t.root:
        try:
            breadth_codes = [n.flight_code for n in t.breadth_first_search()]
            depth_codes   = [n.flight_code for n in t.pre_order_traversal()]
        except Exception:
            pass

    return {
        "root":          _node_to_dict(t.root),
        "height":        meta["height"],
        "node_count":    meta["node_count"],
        "leaf_count":    meta["leaf_count"],
        "can_undo":      manager.can_undo(),
        "breadth_order": breadth_codes,
        "depth_order":   depth_codes,
        "metrics": {
            "LL":                t.rotation_count["LL"],
            "RR":                t.rotation_count["RR"],
            "LR":                t.rotation_count["LR"],
            "RL":                t.rotation_count["RL"],
            "total_rotations":   sum(t.rotation_count.values()),
            "global_rebalances": t.cascade_rebalance_count,
            "mass_cancellations": t.mass_cancellation_count,
        },
    }


def _bst_payload() -> dict:
    """
    Build the BST comparison payload.

    Returns:
        dict with keys: root, height, node_count, leaf_count.
    """
    if bst_tree.root is None:
        return {"root": None, "height": 0, "node_count": 0, "leaf_count": 0}
    props = bst_tree.get_properties()
    return {
        "root":       _bst_node_to_dict(bst_tree.root),
        "height":     props["height"],
        "node_count": props["node_count"],
        "leaf_count": props["leaf_count"],
    }


# ===========================================================================
# ROUTES
# ===========================================================================

@app.route("/")
def index():
    """Serve the main HTML page."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# TREE STATE
# ---------------------------------------------------------------------------

@app.route("/api/tree-state", methods=["GET"])
def tree_state():
    """Return the full current AVL tree state (called on page load)."""
    return jsonify({"tree": _tree_payload()})


# ---------------------------------------------------------------------------
# LOAD TREE
# ---------------------------------------------------------------------------

@app.route("/api/load-tree", methods=["POST"])
def load_tree():
    """
    Accept a JSON file upload and rebuild the in-memory tree(s).

    Form fields:
        file : the JSON file
        type : 'topology' | 'insertion'

    Returns the AVL tree payload; insertion mode also includes bst_tree.
    """
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    load_type = request.form.get("type", "topology")

    try:
        data = json.load(file)
    except json.JSONDecodeError as exc:
        return jsonify({"error": f"Invalid JSON: {exc}"}), 400

    global manager, bst_tree
    if load_type == "topology":
        rebuilt_avl = storage.reconstruct_avl_from_dict(data)
        if rebuilt_avl is None:
            return jsonify({"error": "Could not reconstruct the tree from the provided data"}), 422
        manager = AVLTreeManager(rebuilt_avl)
    else:
        rebuilt = storage.reconstruct_both_from_flights(data)
        if rebuilt is None:
            return jsonify({"error": "Could not reconstruct the tree from the provided data"}), 422
        rebuilt_avl, rebuilt_bst = rebuilt
        manager = AVLTreeManager(rebuilt_avl)
        bst_tree = rebuilt_bst

    if manager.tree.root is None:
        return jsonify({"error": "Could not reconstruct the tree from the provided data"}), 422

    response = {"tree": _tree_payload()}
    if load_type == "insertion":
        response["bst_tree"] = _bst_payload()

    return jsonify(response)


# ---------------------------------------------------------------------------
# EXPORT TREE  — DataPersistence.serialize_tree_for_storage
# ---------------------------------------------------------------------------

@app.route("/api/export-tree", methods=["GET"])
def export_tree():
    """Serialize the current AVL tree structure for JSON download."""
    if manager.tree.root is None:
        return jsonify({"error": "Tree is empty"}), 400
    serialized = persistence.serialize_tree_for_storage(manager.tree.root)
    return jsonify(serialized)


# ---------------------------------------------------------------------------
# FLIGHT CRUD  — AVLTreeManager (undo push happens automatically inside)
# ---------------------------------------------------------------------------

@app.route("/api/add-flight", methods=["POST"])
def add_flight():
    """
    Insert a new flight into the AVL tree.

    Body JSON: flight_code, origin, destination, base_price,
               passengers (opt), promotion (opt), alert (opt), priority (opt).
    """
    data = request.get_json(silent=True) or {}
    required = ("flight_code", "origin", "destination", "base_price")
    if not all(data.get(f) for f in required):
        return jsonify({"error": "Missing required fields: flight_code, origin, destination, base_price"}), 400

    try:
        manager.add_flight(
            flight_code = str(data["flight_code"]),
            origin      = str(data["origin"]),
            destination = str(data["destination"]),
            base_price  = float(data["base_price"]),
            passengers  = int(data.get("passengers", 0)),
            promotion   = float(data.get("promotion", 0.0)),
            alert       = str(data.get("alert", "")),
            priority    = int(data.get("priority", 3)),
        )
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"tree": _tree_payload()})


@app.route("/api/edit-flight", methods=["POST"])
def edit_flight():
    """
    Update one or more fields of an existing flight.

    Body JSON: flight_code, updated_data (dict of fields to change).
    """
    body         = request.get_json(silent=True) or {}
    flight_code  = body.get("flight_code", "").strip()
    updated_data = body.get("updated_data", {})

    if not flight_code or not updated_data:
        return jsonify({"error": "flight_code and updated_data are required"}), 400

    try:
        manager.update_flight(flight_code, **updated_data)
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"tree": _tree_payload()})


@app.route("/api/delete-flight", methods=["POST"])
def delete_flight():
    """
    Remove a single flight node (standard AVL delete + rebalance).

    Body JSON: flight_code.
    """
    body        = request.get_json(silent=True) or {}
    flight_code = body.get("flight_code", "").strip()
    if not flight_code:
        return jsonify({"error": "flight_code is required"}), 400

    try:
        manager.delete_flight(flight_code)
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify({"tree": _tree_payload()})


@app.route("/api/cancel-flight", methods=["POST"])
def cancel_flight():
    """
    Cancel a flight: remove the node AND all its descendants, then rebalance.

    Body JSON: flight_code.
    """
    body        = request.get_json(silent=True) or {}
    flight_code = body.get("flight_code", "").strip()
    if not flight_code:
        return jsonify({"error": "flight_code is required"}), 400

    try:
        removed = manager.cancel_flight(flight_code)
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify({"removed_count": removed, "tree": _tree_payload()})


# ---------------------------------------------------------------------------
# UNDO  — AVLTreeManager.undo_last_action
# ---------------------------------------------------------------------------

@app.route("/api/undo", methods=["POST"])
def undo():
    """Revert the last mutating action using the undo stack."""
    ok = manager.undo_last_action()
    if not ok:
        return jsonify({"error": "No actions available to undo"}), 400
    return jsonify({"tree": _tree_payload()})


# ---------------------------------------------------------------------------
# STRESS MODE  — AVLTree.set_stress_mode / global_rebalance
# ---------------------------------------------------------------------------

@app.route("/api/toggle-stress-mode", methods=["POST"])
def toggle_stress_mode():
    """
    Toggle stress mode (deferred rebalancing).

    Turning stress mode OFF automatically triggers a global rebalance.

    Body JSON: stress_mode (bool).
    """
    body      = request.get_json(silent=True) or {}
    new_state = bool(body.get("stress_mode", not manager.tree.stress_mode))

    rotations_done = 0
    if not new_state:
        # Leaving stress mode: rebalance first, then disable
        rotations_done = manager.global_rebalance()
        manager.set_stress_mode(False)
    else:
        manager.set_stress_mode(True)

    return jsonify({
        "stress_mode":    manager.tree.stress_mode,
        "rotations_done": rotations_done,
        "tree":           _tree_payload(),
    })


@app.route("/api/global-rebalance", methods=["POST"])
def global_rebalance():
    """Trigger an explicit global rebalance on the entire tree."""
    rotations = manager.global_rebalance()
    return jsonify({"rotations_done": rotations, "tree": _tree_payload()})


# ---------------------------------------------------------------------------
# AVL AUDIT
# ---------------------------------------------------------------------------

@app.route("/api/audit-avl", methods=["GET"])
def audit_avl():
    """
    Verify the AVL balance property across the whole tree.

    Returns a per-node report listing any balance or height inconsistencies.
    Intended for use during stress mode (spec §7).
    """
    report   = []
    is_valid = analysis.audit_node(manager.tree.root, report)
    return jsonify({"valid": is_valid, "report": report})


# ---------------------------------------------------------------------------
# CRITICAL DEPTH / PENALISATION  — spec §6
# ---------------------------------------------------------------------------

@app.route("/api/update-critical-depth", methods=["POST"])
def update_critical_depth():
    """
    Change the critical depth threshold and recompute final prices.

    Nodes deeper than the threshold have their final_price set to
    base_price × 1.25 (25% surcharge). Nodes at or above the threshold
    are reset to base_price.

    Body JSON: critical_depth (int).
    """
    global critical_depth
    body           = request.get_json(silent=True) or {}
    critical_depth = int(body.get("critical_depth", 5))
    analysis.apply_depth_penalties(manager.tree.root, 0, critical_depth)
    return jsonify({"critical_depth": critical_depth, "tree": _tree_payload()})


# ---------------------------------------------------------------------------
# VERSIONS  — VersionManager
# ---------------------------------------------------------------------------

@app.route("/api/save-version", methods=["POST"])
def save_version():
    """
    Save the current AVL tree as a named version.

    Body JSON: version_name (str).
    """
    body         = request.get_json(silent=True) or {}
    version_name = body.get("version_name", "").strip()
    if not version_name:
        return jsonify({"error": "version_name is required"}), 400
    t = manager.tree
    ok = versions.save_version(
        manager.tree.root,
        version_name,
        rotation_count=t.rotation_count.copy(),
        cascade_rebalance_count=t.cascade_rebalance_count,
        mass_cancellation_count=t.mass_cancellation_count,
    )
    return jsonify({"success": ok})


@app.route("/api/restore-version", methods=["POST"])
def restore_version():
    """
    Restore a previously saved version into the active AVL tree.

    Body JSON: version_name (str).
    """
    global manager
    body         = request.get_json(silent=True) or {}
    version_name = body.get("version_name", "").strip()
    if not version_name:
        return jsonify({"error": "version_name is required"}), 400

    version_file = versions._find_file_by_version_name(version_name)
    if version_file is None:
        return jsonify({"error": f"Version '{version_name}' not found"}), 404
    
    payload = versions._read_version_file(version_file)
    root = versions.restore_version(version_name)
    if root is None:
        return jsonify({"error": f"Version '{version_name}' not found"}), 404
    root = versions.restore_version(version_name)
    if root is None:
        return jsonify({"error": f"Version '{version_name}' not found"}), 404

    new_avl       = AVLTree()
    new_avl.root  = root
    
    meta = payload.get("metadata", {})
    saved_rotations = meta.get("rotation_count")
    if isinstance(saved_rotations, dict):
        new_avl.rotation_count = saved_rotations
    new_avl.cascade_rebalance_count = int(meta.get("cascade_rebalance_count", 0))
    new_avl.mass_cancellation_count = int(meta.get("mass_cancellation_count", 0))

    manager = AVLTreeManager(new_avl)
    return jsonify({"tree": _tree_payload()})


@app.route("/api/list-versions", methods=["GET"])
def list_versions():
    """Return metadata for all saved versions."""
    return jsonify({"versions": versions.get_all_versions_info()})


@app.route("/api/delete-version", methods=["POST"])
def delete_version():
    """
    Delete a saved version by name.

    Body JSON: version_name (str).
    """
    body         = request.get_json(silent=True) or {}
    version_name = body.get("version_name", "").strip()
    ok           = versions.delete_version(version_name)
    return jsonify({"success": ok})


# ---------------------------------------------------------------------------
# ECONOMIC ELIMINATION  — spec §8
# ---------------------------------------------------------------------------

@app.route("/api/delete-least-profitable", methods=["POST"])
def delete_least_profitable():
    """
    Find and cancel the least-profitable flight (and its entire subtree).

    Profitability = passengers × final_price.
    Tie-breaking: deepest node wins; then largest flight_code wins.
    """
    if manager.tree.root is None:
        return jsonify({"error": "Tree is empty"}), 400

    target = analysis.find_least_profitable(manager.tree.root, depth=0)
    if target is None:
        return jsonify({"error": "No nodes found"}), 500

    try:
        removed = manager.cancel_flight(target.flight_code)
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({
        "cancelled":     target.flight_code,
        "removed_count": removed,
        "tree":          _tree_payload(),
    })


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)