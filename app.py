"""
SkyBalance AVL - Flask Web Application.

REST API layer that bridges the Python backend (AVLTree, DataStorage,
VersionManager) with the HTML/JS frontend.  Every endpoint returns JSON
so the StorageManager class on the client side can persist the data in
LocalStorage and render it with D3.

All data kept in memory for the lifetime of the process; the client is
responsible for persisting snapshots in LocalStorage between sessions.
"""

import json
import os
import sys

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.modelos.AVLTree import AVLTree
from src.modelos.FlightNode import FlightNode
from src.acceso_datos.DataPersistence import DataPersistence
from src.acceso_datos.VersionManager import VersionManager

app = Flask(
    __name__,
    template_folder="src/presentacion/vistas",
    static_folder="src/presentacion/estilos",
)
CORS(app)

# ---------------------------------------------------------------------------
# Global state (single-user in-process session)
# ---------------------------------------------------------------------------
avl_tree    = AVLTree()
bst_tree    = AVLTree()            # plain BST: insert without rebalancing
stress_mode = False
persistence = DataPersistence()
versions    = VersionManager()


# ===========================================================================
# HELPERS
# ===========================================================================

def _node_to_dict(node: FlightNode | None, depth: int = 0) -> dict | None:
    """Recursively convert a FlightNode tree into a nested dict for D3."""
    if node is None:
        return None
    return {
        **node.to_dict(),
        "depth": depth,
        "left":  _node_to_dict(node.left,  depth + 1),
        "right": _node_to_dict(node.right, depth + 1),
    }


def _tree_payload(tree: AVLTree, label: str = "avl") -> dict:
    """
    Build the standardised tree payload returned to the frontend.

    Contains the nested root hierarchy (for D3), flat metadata, and
    rotation counters so StorageManager can persist everything in one go.
    """
    meta = persistence.get_tree_metadata(tree.root)
    return {
        "root":       _node_to_dict(tree.root),
        "height":     meta["height"],
        "node_count": meta["node_count"],
        "leaf_count": meta["leaf_count"],
        "metrics": {
            "LL": tree.rotation_count["LL"],
            "RR": tree.rotation_count["RR"],
            "LR": tree.rotation_count["LR"],
            "RL": tree.rotation_count["RL"],
            "total_rotations": sum(tree.rotation_count.values()),
            "mass_cancellations": tree.cascade_rebalance_count,
        },
    }


def _build_bst_insert(node: FlightNode, new_node: FlightNode) -> None:
    """Insert into a plain BST without rebalancing (for insertion-mode comparison)."""
    if new_node.flight_code < node.flight_code:
        if node.left is None:
            node.left = new_node
            new_node.parent = node
        else:
            _build_bst_insert(node.left, new_node)
    elif new_node.flight_code > node.flight_code:
        if node.right is None:
            node.right = new_node
            new_node.parent = node
        else:
            _build_bst_insert(node.right, new_node)


def _reconstruct_from_topology(data: dict) -> bool:
    """
    Rebuild avl_tree from a topology JSON (preserves parent-child structure).
    Returns True on success.
    """
    global avl_tree
    tree_structure = data.get("tree_structure")
    root_code      = data.get("root_code")
    if not tree_structure or not root_code:
        return False

    node_map: dict[str, FlightNode] = {}
    for code, entry in tree_structure.items():
        node_map[code] = FlightNode.from_dict(entry["flight_data"])

    root_node = node_map.get(root_code)
    if root_node is None:
        return False

    for code, entry in tree_structure.items():
        current = node_map[code]
        left_code  = entry.get("left_child")
        right_code = entry.get("right_child")
        if left_code and left_code in node_map:
            current.left = node_map[left_code]
            node_map[left_code].parent = current
        if right_code and right_code in node_map:
            current.right = node_map[right_code]
            node_map[right_code].parent = current

    avl_tree      = AVLTree()
    avl_tree.root = root_node
    return True


def _reconstruct_from_insertion(data: dict) -> bool:
    """
    Rebuild avl_tree and bst_tree by inserting flights one by one.
    Returns True on success.
    """
    global avl_tree, bst_tree
    flights = data.get("flights", [])
    if not flights:
        return False

    avl_tree = AVLTree()
    bst_tree = AVLTree()

    for flight_data in flights:
        avl_node = FlightNode.from_dict(flight_data)
        bst_node = FlightNode.from_dict(flight_data)

        avl_tree.insert(avl_node)

        if bst_tree.root is None:
            bst_tree.root = bst_node
        else:
            _build_bst_insert(bst_tree.root, bst_node)

    return True


# ===========================================================================
# ROUTES
# ===========================================================================

@app.route("/")
def index():
    """Serve the main HTML page."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# 1. LOAD TREE
# ---------------------------------------------------------------------------

@app.route("/api/load-tree", methods=["POST"])
def load_tree():
    """
    Accept a JSON file upload from the browser and rebuild the in-memory tree(s).

    Form fields:
        file  : the JSON file
        type  : "topology" | "insertion"

    Returns the AVL tree payload; insertion mode also returns bst_tree.
    """
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    load_type = request.form.get("type", "topology")

    try:
        data = json.load(file)
    except json.JSONDecodeError as exc:
        return jsonify({"error": f"Invalid JSON: {exc}"}), 400

    if load_type == "topology":
        ok = _reconstruct_from_topology(data)
    else:
        ok = _reconstruct_from_insertion(data)

    if not ok:
        return jsonify({"error": "Failed to reconstruct tree from provided data"}), 422

    response = {"tree": _tree_payload(avl_tree)}
    if load_type == "insertion":
        response["bst_tree"] = _tree_payload(bst_tree, label="bst")

    return jsonify(response)


# ---------------------------------------------------------------------------
# 2. SAVE TREE  (LocalStorage → Python → JSON download via frontend)
# ---------------------------------------------------------------------------

@app.route("/api/save-tree", methods=["POST"])
def save_tree():
    """
    Receive a tree structure from the frontend (from LocalStorage),
    restore it into Python memory, and confirm persistence.

    The actual file download is handled client-side via StorageManager.exportJSON.
    This endpoint keeps the Python state in sync.

    Body JSON:
        tree_type : "avl" | "bst"
        tree_data : the tree object stored in LocalStorage
    """
    global avl_tree, bst_tree
    body      = request.get_json(silent=True) or {}
    tree_type = body.get("tree_type", "avl")
    tree_data = body.get("tree_data")

    if not tree_data:
        return jsonify({"error": "No tree_data provided"}), 400

    # Rebuild the Python object from the serialised data
    root_dict = tree_data.get("root")
    if root_dict:
        root_node = _dict_to_node(root_dict)
        if tree_type == "bst":
            bst_tree      = AVLTree()
            bst_tree.root = root_node
        else:
            avl_tree      = AVLTree()
            avl_tree.root = root_node

    return jsonify({"success": True})


def _dict_to_node(d: dict | None) -> FlightNode | None:
    """Recursively rebuild a FlightNode tree from a nested dict."""
    if d is None:
        return None
    node       = FlightNode.from_dict(d)
    node.left  = _dict_to_node(d.get("left"))
    node.right = _dict_to_node(d.get("right"))
    if node.left:
        node.left.parent  = node
    if node.right:
        node.right.parent = node
    return node


# ---------------------------------------------------------------------------
# 3. FLIGHT CRUD
# ---------------------------------------------------------------------------

@app.route("/api/add-flight", methods=["POST"])
def add_flight():
    """Insert a new flight node into the AVL tree."""
    data = request.get_json(silent=True) or {}
    if not _validate_flight_fields(data):
        return jsonify({"error": "Missing required flight fields"}), 400

    node = FlightNode.from_dict(data)
    avl_tree.insert(node)
    return jsonify({"tree": _tree_payload(avl_tree)})


@app.route("/api/edit-flight", methods=["POST"])
def edit_flight():
    """
    Update an existing flight (delete then re-insert with updated data).
    Body: { flight_code, updated_data: {...} }
    """
    body         = request.get_json(silent=True) or {}
    flight_code  = body.get("flight_code")
    updated_data = body.get("updated_data")

    if not flight_code or not updated_data:
        return jsonify({"error": "flight_code and updated_data are required"}), 400

    deleted = avl_tree.delete(flight_code)
    if not deleted:
        return jsonify({"error": f"Flight '{flight_code}' not found"}), 404

    avl_tree.insert(FlightNode.from_dict(updated_data))
    return jsonify({"tree": _tree_payload(avl_tree)})


@app.route("/api/delete-flight", methods=["POST"])
def delete_flight():
    """
    Remove a single flight node (standard BST delete + rebalance).
    Body: { flight_code }
    """
    body        = request.get_json(silent=True) or {}
    flight_code = body.get("flight_code")
    if not flight_code:
        return jsonify({"error": "flight_code is required"}), 400

    deleted = avl_tree.delete(flight_code)
    if not deleted:
        return jsonify({"error": f"Flight '{flight_code}' not found"}), 404

    return jsonify({"tree": _tree_payload(avl_tree)})


@app.route("/api/cancel-flight", methods=["POST"])
def cancel_flight():
    """
    Cancel a flight: remove the node AND all its descendants, then rebalance.
    Body: { flight_code }
    """
    body        = request.get_json(silent=True) or {}
    flight_code = body.get("flight_code")
    if not flight_code:
        return jsonify({"error": "flight_code is required"}), 400

    node = avl_tree.search(flight_code) if avl_tree.root else None
    if node is None:
        return jsonify({"error": f"Flight '{flight_code}' not found"}), 404

    _detach_subtree(node)
    avl_tree.cascade_rebalance_count += 1
    return jsonify({"tree": _tree_payload(avl_tree)})


def _detach_subtree(node: FlightNode) -> None:
    """
    Unlink a node from its parent, removing it and all descendants.
    If the node is the root, the tree becomes empty.
    """
    parent = node.parent
    if parent is None:
        avl_tree.root = None
        return

    if parent.left is node:
        parent.left = None
    else:
        parent.right = None

    node.parent = None

    # Rebalance upward from the parent
    avl_tree._check_balance(parent)   # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 4. STRESS MODE
# ---------------------------------------------------------------------------

@app.route("/api/toggle-stress-mode", methods=["POST"])
def toggle_stress_mode():
    """
    Enable or disable stress mode (deferred rebalancing).
    Body: { stress_mode: bool }
    When turning OFF, triggers a full global rebalance.
    """
    global stress_mode
    body       = request.get_json(silent=True) or {}
    stress_mode = bool(body.get("stress_mode", not stress_mode))
    avl_tree.stress_mode = stress_mode   # AVLTree must respect this flag

    rotations_done = 0
    if not stress_mode:
        rotations_done = avl_tree.global_rebalance()

    return jsonify({
        "stress_mode":    stress_mode,
        "rotations_done": rotations_done,
        "tree":           _tree_payload(avl_tree),
    })


@app.route("/api/audit-avl", methods=["GET"])
def audit_avl():
    """
    Verify AVL property across the entire tree.
    Returns a per-node report listing any inconsistencies found.
    Only meaningful in stress mode.
    """
    report   = []
    is_valid = _audit_node(avl_tree.root, report)
    return jsonify({"valid": is_valid, "report": report})


def _audit_node(node: FlightNode | None, report: list, depth: int = 0) -> bool:
    """Recursively audit AVL property and populate the report list."""
    if node is None:
        return True

    issues = []
    if node.balance_factor not in (-1, 0, 1):
        issues.append(f"balance_factor={node.balance_factor} ∉ {{-1,0,1}}")

    expected_height = max(
        _get_height(node.left), _get_height(node.right)
    ) + 1 if (node.left or node.right) else 0

    if node.height != expected_height:
        issues.append(f"height={node.height} but expected {expected_height}")

    if issues:
        report.append({"flight_code": node.flight_code, "depth": depth, "issues": issues})

    left_ok  = _audit_node(node.left,  report, depth + 1)
    right_ok = _audit_node(node.right, report, depth + 1)
    return len(issues) == 0 and left_ok and right_ok


def _get_height(node: FlightNode | None) -> int:
    return node.height if node else -1


# ---------------------------------------------------------------------------
# 5. CRITICAL DEPTH / PENALISATION
# ---------------------------------------------------------------------------

@app.route("/api/update-critical-depth", methods=["POST"])
def update_critical_depth():
    """
    Change the critical-depth threshold and recalculate final prices for
    all nodes (±25 % rule from spec section 6).

    Body: { critical_depth: int }
    """
    body           = request.get_json(silent=True) or {}
    critical_depth = int(body.get("critical_depth", 5))

    _apply_depth_penalties(avl_tree.root, 0, critical_depth)
    return jsonify({"critical_depth": critical_depth, "tree": _tree_payload(avl_tree)})


def _apply_depth_penalties(node: FlightNode | None, depth: int, limit: int) -> None:
    """Walk the tree and adjust final_price based on depth vs critical limit."""
    if node is None:
        return
    if depth > limit:
        node.final_price = node.base_price * 1.25
    else:
        node.final_price = node.base_price
    _apply_depth_penalties(node.left,  depth + 1, limit)
    _apply_depth_penalties(node.right, depth + 1, limit)


# ---------------------------------------------------------------------------
# 6. VERSION MANAGEMENT
# ---------------------------------------------------------------------------

@app.route("/api/save-version", methods=["POST"])
def save_version():
    """
    Save the current AVL tree as a named version in the Python VersionManager.
    Body: { version_name, tree_data (optional, ignored – Python state is used) }
    """
    body         = request.get_json(silent=True) or {}
    version_name = body.get("version_name", "").strip()
    if not version_name:
        return jsonify({"error": "version_name is required"}), 400

    ok = versions.save_version(avl_tree.root, version_name)
    return jsonify({"success": ok})


@app.route("/api/restore-version", methods=["POST"])
def restore_version():
    """
    Restore a saved version back into the AVL tree.
    Body: { version_name }
    """
    global avl_tree
    body         = request.get_json(silent=True) or {}
    version_name = body.get("version_name", "").strip()
    if not version_name:
        return jsonify({"error": "version_name is required"}), 400

    root = versions.restore_version(version_name)
    if root is None:
        return jsonify({"error": f"Version '{version_name}' not found"}), 404

    avl_tree.root = root
    return jsonify({"tree": _tree_payload(avl_tree)})


@app.route("/api/list-versions", methods=["GET"])
def list_versions():
    """Return all saved version names with metadata."""
    return jsonify({"versions": versions.get_all_versions_info()})


@app.route("/api/delete-version", methods=["POST"])
def delete_version():
    """Delete a named version. Body: { version_name }"""
    body         = request.get_json(silent=True) or {}
    version_name = body.get("version_name", "").strip()
    ok           = versions.delete_version(version_name)
    return jsonify({"success": ok})


# ---------------------------------------------------------------------------
# 7. ECONOMIC ELIMINATION (spec section 8)
# ---------------------------------------------------------------------------

@app.route("/api/delete-least-profitable", methods=["POST"])
def delete_least_profitable():
    """
    Find and cancel the least-profitable flight (and its subtree).
    profitability = passengers × final_price − promotion
    Tie-breaking: deepest node → largest flight_code.
    """
    if avl_tree.root is None:
        return jsonify({"error": "Tree is empty"}), 400

    target = _find_least_profitable(avl_tree.root, depth=0)
    if target is None:
        return jsonify({"error": "No nodes found"}), 500

    _detach_subtree(target)
    avl_tree.cascade_rebalance_count += 1
    return jsonify({"cancelled": target.flight_code, "tree": _tree_payload(avl_tree)})


def _profitability(node: FlightNode) -> float:
    return node.passengers * node.final_price - node.promotion


def _find_least_profitable(node: FlightNode | None, depth: int) -> FlightNode | None:
    """
    Traverse the tree and return the node with the lowest profitability.
    Tie-breaking: prefer deeper node; then larger flight_code.
    """
    if node is None:
        return None

    best   = node
    best_p = _profitability(node)
    best_d = depth

    for child, d in [(node.left, depth + 1), (node.right, depth + 1)]:
        candidate = _find_least_profitable(child, d)
        if candidate is None:
            continue
        cand_p = _profitability(candidate)
        cand_d = d

        if (cand_p < best_p
                or (cand_p == best_p and cand_d > best_d)
                or (cand_p == best_p and cand_d == best_d
                    and candidate.flight_code > best.flight_code)):
            best, best_p, best_d = candidate, cand_p, cand_d

    return best


# ---------------------------------------------------------------------------
# 8. TREE STATE  (generic getter for the frontend to refresh UI)
# ---------------------------------------------------------------------------

@app.route("/api/tree-state", methods=["GET"])
def tree_state():
    """Return the full current AVL tree state (called on page load)."""
    return jsonify({"tree": _tree_payload(avl_tree)})


# ---------------------------------------------------------------------------
# UTILITY
# ---------------------------------------------------------------------------

def _validate_flight_fields(data: dict) -> bool:
    """Check that the minimum required flight fields are present."""
    required = ("flight_code", "origin", "destination", "base_price")
    return all(data.get(f) for f in required)


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
