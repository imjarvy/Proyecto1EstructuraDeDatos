"""
SkyBalance AVL - Flask Web Application.

REST API layer that bridges the Python backend with the HTML/JS frontend.
Only exposes endpoints for functionality already implemented in Python modules.
"""

import json
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

from src.acceso_datos.DataStorage import DataStorage
from src.routes.queue_routes import queue_bp, init_queue # Importar el blueprint y la función de inicialización


from src.modelos.AVLTree import AVLTree
from src.modelos.BST import BST
from src.modelos.FlightNode import FlightNode
from src.negocio.AVLTreeManager import AVLTreeManager
from src.acceso_datos.DataPersistence import DataPersistence
from src.acceso_datos.VersionManager import VersionManager
from src.acceso_datos.TreeAnalysisManager import TreeAnalysisManager

app = Flask(
    __name__,
    template_folder="src/presentacion/vistas",
    static_folder="src/presentacion/estilos",
    static_url_path="/estilos",
)
CORS(app)

# 2. Registrar el blueprint (después de crear app)
app.register_blueprint(queue_bp)

# Instancia global del árbol (será sincronizado con manager)
avl_tree = AVLTree()

# Route to serve static JS files from src/negocio/
NEGOCIO_DIR = os.path.join(os.path.dirname(__file__), "src", "negocio")

@app.route("/negocio/<path:filename>")
def negocio_static(filename):
    """Serve static JS files from the negocio directory."""
    return send_from_directory(NEGOCIO_DIR, filename)


# ===========================================================================
# GLOBAL STATE
# ===========================================================================

manager        = AVLTreeManager(avl_tree)
bst_tree       = BST()

# 3. Inicializar la cola con el árbol compartido (después de crear manager)
init_queue(manager)
persistence    = DataPersistence()
versions       = VersionManager()
analysis       = TreeAnalysisManager()
critical_depth = 5


# ===========================================================================
# HELPERS
# ===========================================================================

def _node_to_dict(node, depth: int = 0):
    """
    Recursively convert FlightNode tree into nested dict for D3.
    Includes depth and is_critical for node colour differentiation (spec §6).
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
    """Recursively convert BST FlightNode into nested dict."""
    if node is None:
        return None
    d = node.to_dict()
    d["depth"] = depth
    d["left"]  = _bst_node_to_dict(node.left,  depth + 1)
    d["right"] = _bst_node_to_dict(node.right, depth + 1)
    return d


def _tree_payload() -> dict:
    """
    Build the standardised AVL tree payload for the frontend.
    Includes nested root for D3, metadata, rotation counters,
    traversal orders, and undo availability.
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
            "mass_cancellations": t.cascade_rebalance_count,
        },
    }


def _bst_payload() -> dict:
    """Build BST comparison payload."""
    if bst_tree.root is None:
        return {"root": None, "height": 0, "node_count": 0, "leaf_count": 0}
    props = bst_tree.get_properties()
    return {
        "root":       _bst_node_to_dict(bst_tree.root),
        "height":     props["height"],
        "node_count": props["node_count"],
        "leaf_count": props["leaf_count"],
    }


def _reconstruct_from_topology(data: dict) -> bool:
    """Rebuild manager.tree from topology JSON (root_code + tree_structure)."""
    global manager
    tree_structure = data.get("tree_structure")
    root_code      = data.get("root_code")
    if not tree_structure or not root_code:
        return False

    node_map = {}
    for code, entry in tree_structure.items():
        node_map[code] = FlightNode.from_dict(entry["flight_data"])

    root_node = node_map.get(root_code)
    if root_node is None:
        return False

    for code, entry in tree_structure.items():
        current = node_map[code]
        lc = entry.get("left_child")
        rc = entry.get("right_child")
        if lc and lc in node_map:
            current.left = node_map[lc]
            node_map[lc].parent = current
        if rc and rc in node_map:
            current.right = node_map[rc]
            node_map[rc].parent = current

    new_avl       = AVLTree()
    new_avl.root  = root_node
    manager       = AVLTreeManager(new_avl)
    return True


def _reconstruct_from_insertion(data: dict) -> bool:
    """Rebuild manager.tree (AVL) and bst_tree by sequential insertion."""
    global manager, bst_tree
    flights = data.get("flights", [])
    if not flights:
        return False

    new_avl  = AVLTree()
    bst_tree = BST()

    for fd in flights:
        new_avl.insert(FlightNode.from_dict(fd))
        bst_tree.insert(FlightNode.from_dict(fd))

    manager = AVLTreeManager(new_avl)
    return True


# ===========================================================================
# ROUTES
# ===========================================================================

@app.route("/")
def index():
    """Serve the main HTML page."""
    return render_template("index.html")


@app.route("/api/tree-state", methods=["GET"])
def tree_state():
    """Return full current AVL tree state (called on page load)."""
    return jsonify({"tree": _tree_payload()})


# ---------------------------------------------------------------------------
# LOAD TREE
# ---------------------------------------------------------------------------

@app.route("/api/load-tree", methods=["POST"])
def load_tree():
    """
    Accept a JSON file upload and rebuild the in-memory tree(s).

    Topology JSON must contain: root_code + tree_structure.
    Insertion JSON must contain: flights (list of flight objects).

    Returns a descriptive error if the JSON format does not match the mode.
    """
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No se proporcionó ningún archivo"}), 400

    load_type = request.form.get("type", "topology")

    try:
        data = json.load(file)
    except json.JSONDecodeError as exc:
        return jsonify({"error": f"JSON inválido: {exc}"}), 400

    # Bug fix #2: validate format before attempting reconstruction
    if load_type == "topology":
        if "root_code" not in data or "tree_structure" not in data:
            return jsonify({
                "error": "El archivo no es de tipo Topología. "
                         "Debe contener 'root_code' y 'tree_structure'."
            }), 422
        ok = _reconstruct_from_topology(data)
    else:
        if "flights" not in data:
            return jsonify({
                "error": "El archivo no es de tipo Inserción. "
                         "Debe contener la clave 'flights' con una lista de vuelos."
            }), 422
        ok = _reconstruct_from_insertion(data)

    if not ok:
        return jsonify({"error": "No se pudo reconstruir el árbol con los datos proporcionados"}), 422

    response = {"tree": _tree_payload()}
    if load_type == "insertion":
        response["bst_tree"] = _bst_payload()

    return jsonify(response)


# ---------------------------------------------------------------------------
# EXPORT TREE
# ---------------------------------------------------------------------------

@app.route("/api/export-tree", methods=["GET"])
def export_tree():
    """Serialize the current AVL tree for JSON download."""
    if manager.tree.root is None:
        return jsonify({"error": "El árbol está vacío"}), 400
    serialized = persistence.serialize_tree_for_storage(manager.tree.root)
    return jsonify(serialized)


# ---------------------------------------------------------------------------
# FLIGHT CRUD
# ---------------------------------------------------------------------------

@app.route("/api/add-flight", methods=["POST"])
def add_flight():
    """
    Insert a new flight into the AVL tree.
    Bug fix #4: returns specific error messages for each invalid field.
    """
    data = request.get_json(silent=True) or {}

    missing = [f for f in ("flight_code", "origin", "destination", "base_price") if not data.get(f)]
    if missing:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(missing)}"}), 400

    try:
        base_price = float(data["base_price"])
        if base_price < 0:
            return jsonify({"error": "El precio base no puede ser negativo"}), 400
        passengers = int(data.get("passengers", 0))
        if passengers < 0:
            return jsonify({"error": "Los pasajeros no pueden ser negativos"}), 400
        promotion = float(data.get("promotion", 0.0))
        if not (0.0 <= promotion <= 1.0):
            return jsonify({"error": "La promoción debe estar entre 0 y 1"}), 400
        priority = int(data.get("priority", 3))
        if not (1 <= priority <= 5):
            return jsonify({"error": "La prioridad debe estar entre 1 y 5"}), 400
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"Valor numérico inválido: {exc}"}), 400

    try:
        manager.add_flight(
            flight_code = str(data["flight_code"]).strip().upper(),
            origin      = str(data["origin"]).strip(),
            destination = str(data["destination"]).strip(),
            base_price  = base_price,
            passengers  = passengers,
            promotion   = promotion,
            alert       = str(data.get("alert", "")).strip(),
            priority    = priority,
        )
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"tree": _tree_payload()})


@app.route("/api/edit-flight", methods=["POST"])
def edit_flight():
    """
    Update one or more fields of an existing flight.

    Bug fix #1: updated_data arrives WITHOUT flight_code (removed by JS).
    We pass the fields directly to AVLTreeManager.update_flight instead of
    trying to reconstruct a FlightNode from scratch (which would fail without
    a flight_code). The manager handles all field validation internally.

    Body: { flight_code, updated_data: { origin, destination, ... } }
    """
    body         = request.get_json(silent=True) or {}
    flight_code  = body.get("flight_code", "").strip()
    updated_data = body.get("updated_data", {})

    if not flight_code:
        return jsonify({"error": "flight_code es requerido"}), 400
    if not updated_data:
        return jsonify({"error": "No hay campos para actualizar"}), 400

    # Coerce numeric fields coming as strings from the form
    for field, cast, label in [
        ("base_price",  float, "Precio base"),
        ("passengers",  int,   "Pasajeros"),
        ("promotion",   float, "Promoción"),
        ("priority",    int,   "Prioridad"),
    ]:
        if field in updated_data:
            try:
                updated_data[field] = cast(updated_data[field])
            except (ValueError, TypeError):
                return jsonify({"error": f"{label} debe ser un número válido"}), 400

    # Range validations
    if "base_price" in updated_data and updated_data["base_price"] < 0:
        return jsonify({"error": "El precio base no puede ser negativo"}), 400
    if "passengers" in updated_data and updated_data["passengers"] < 0:
        return jsonify({"error": "Los pasajeros no pueden ser negativos"}), 400
    if "promotion" in updated_data and not (0.0 <= updated_data["promotion"] <= 1.0):
        return jsonify({"error": "La promoción debe estar entre 0 y 1"}), 400
    if "priority" in updated_data and not (1 <= updated_data["priority"] <= 5):
        return jsonify({"error": "La prioridad debe estar entre 1 y 5"}), 400

    try:
        manager.update_flight(flight_code, **updated_data)
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"tree": _tree_payload()})


@app.route("/api/delete-flight", methods=["POST"])
def delete_flight():
    """Remove a single flight node. Body: { flight_code }"""
    body        = request.get_json(silent=True) or {}
    flight_code = body.get("flight_code", "").strip()
    if not flight_code:
        return jsonify({"error": "flight_code es requerido"}), 400

    try:
        manager.delete_flight(flight_code)
    except (ValueError, KeyError):
        return jsonify({"error": f"Vuelo '{flight_code}' no encontrado"}), 404

    return jsonify({"tree": _tree_payload()})


@app.route("/api/cancel-flight", methods=["POST"])
def cancel_flight():
    """Cancel a flight and all descendants. Body: { flight_code }"""
    body        = request.get_json(silent=True) or {}
    flight_code = body.get("flight_code", "").strip()
    if not flight_code:
        return jsonify({"error": "flight_code es requerido"}), 400

    try:
        removed = manager.cancel_flight(flight_code)
        manager.tree.cascade_rebalance_count += 1
    except (ValueError, KeyError):
        return jsonify({"error": f"Vuelo '{flight_code}' no encontrado"}), 404

    return jsonify({"removed_count": removed, "tree": _tree_payload()})


# ---------------------------------------------------------------------------
# UNDO
# ---------------------------------------------------------------------------

@app.route("/api/undo", methods=["POST"])
def undo():
    """Revert the last mutating action via the undo stack."""
    ok = manager.undo_last_action()
    if not ok:
        return jsonify({"error": "No hay acciones para deshacer"}), 400
    return jsonify({"tree": _tree_payload()})


# ---------------------------------------------------------------------------
# STRESS MODE
# ---------------------------------------------------------------------------

@app.route("/api/toggle-stress-mode", methods=["POST"])
def toggle_stress_mode():
    """
    Toggle stress mode. Turning OFF automatically triggers global rebalance.
    Body: { stress_mode: bool }
    """
    body      = request.get_json(silent=True) or {}
    new_state = bool(body.get("stress_mode", not manager.tree.stress_mode))

    rotations_done = 0
    if not new_state:
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
    """Trigger an explicit global rebalance."""
    rotations = manager.global_rebalance()
    return jsonify({"rotations_done": rotations, "tree": _tree_payload()})


# ---------------------------------------------------------------------------
# AVL AUDIT  — spec §7
# ---------------------------------------------------------------------------

@app.route("/api/audit-avl", methods=["GET"])
def audit_avl():
    """Verify AVL balance property across the whole tree."""
    report   = []
    is_valid = analysis.audit_node(manager.tree.root, report)
    return jsonify({"valid": is_valid, "report": report})


# ---------------------------------------------------------------------------
# CRITICAL DEPTH  — spec §6
# ---------------------------------------------------------------------------

@app.route("/api/update-critical-depth", methods=["POST"])
def update_critical_depth():
    """
    Change critical depth and recompute all final prices (+25% surcharge rule).
    Body: { critical_depth: int }
    """
    global critical_depth
    body = request.get_json(silent=True) or {}

    try:
        val = int(body.get("critical_depth", 5))
        if val < 1:
            return jsonify({"error": "La profundidad crítica debe ser mayor a 0"}), 400
        critical_depth = val
    except (ValueError, TypeError):
        return jsonify({"error": "La profundidad crítica debe ser un número entero"}), 400

    analysis.apply_depth_penalties(manager.tree.root, 0, critical_depth)
    return jsonify({"critical_depth": critical_depth, "tree": _tree_payload()})


# ---------------------------------------------------------------------------
# VERSIONS
# ---------------------------------------------------------------------------

@app.route("/api/save-version", methods=["POST"])
def save_version():
    """Save current tree as named version. Body: { version_name }"""
    body         = request.get_json(silent=True) or {}
    version_name = body.get("version_name", "").strip()
    if not version_name:
        return jsonify({"error": "version_name es requerido"}), 400
    ok = versions.save_version(manager.tree.root, version_name)
    return jsonify({"success": ok})


@app.route("/api/restore-version", methods=["POST"])
def restore_version():
    """Restore a saved version. Body: { version_name }"""
    global manager
    body         = request.get_json(silent=True) or {}
    version_name = body.get("version_name", "").strip()
    if not version_name:
        return jsonify({"error": "version_name es requerido"}), 400

    version_file = versions._find_file_by_version_name(version_name)
    if version_file is None:
        return jsonify({"error": f"Version '{version_name}' not found"}), 404
    
    payload = versions._read_version_file(version_file)
    root = versions.restore_version(version_name)
    if root is None:
        return jsonify({"error": f"Version '{version_name}' not found"}), 404
    root = versions.restore_version(version_name)
    if root is None:
        return jsonify({"error": f"Versión '{version_name}' no encontrada"}), 404

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
    """Delete a saved version. Body: { version_name }"""
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
    Find and cancel the least-profitable flight and its entire subtree.
    Profitability = passengers × final_price − promotion.
    Tie-breaking: deepest node, then largest flight_code.
    """
    if manager.tree.root is None:
        return jsonify({"error": "El árbol está vacío"}), 400

    target = analysis.find_least_profitable(manager.tree.root)
    if target is None:
        return jsonify({"error": "No se encontraron nodos"}), 500

    try:
        removed = manager.cancel_flight(target.flight_code)
        manager.tree.cascade_rebalance_count += 1
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