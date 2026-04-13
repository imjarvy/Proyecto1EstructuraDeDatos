"""
Flight routes module for SkyBalance AVL Flight Management System.

Provides Flask endpoints for tree operations including CRUD operations,
tree analysis, version management, and tree visualization.
"""

from flask import Blueprint, jsonify, request

from src.modelos.AVLTree import AVLTree

flight_bp = Blueprint("flight", __name__)

_manager = None
_bst_tree = None
_data_storage = None
_analysis = None


def init_flight_routes(manager, bst_tree, data_storage, analysis, critical_depth=5):
    """
    Initialize flight routes with required instances.
    
    Args:
        manager: AVLTreeManager instance for tree operations.
        bst_tree: BST tree instance for comparison visualization.
        data_storage: DataStorage instance for persistence.
        analysis: TreeAnalysisManager instance for analysis operations.
        critical_depth (int): Initial critical depth value for pricing penalty.
    """
    global _manager, _bst_tree, _data_storage, _analysis
    _manager = manager
    _bst_tree = bst_tree
    _data_storage = data_storage
    _analysis = analysis
    _manager.critical_depth = critical_depth


def _node_to_dict(node, depth: int = 0):
    """
    Convert AVL tree node to dictionary representation with depth info.
    
    Args:
        node: FlightNode to convert (None renders as None).
        depth (int): Current depth in tree (default: 0 at root).
    
    Returns:
        dict: Node data including flight info, depth, critical status, and children.
    """
    if node is None:
        return None
    data = node.to_dict()
    data["depth"] = depth
    data["is_critical"] = depth > _manager.critical_depth
    data["left"] = _node_to_dict(node.left, depth + 1)
    data["right"] = _node_to_dict(node.right, depth + 1)
    return data


def _bst_node_to_dict(node, depth: int = 0):
    """
    Convert BST tree node to dictionary representation with depth info.
    
    Args:
        node: FlightNode to convert (None renders as None).
        depth (int): Current depth in tree (default: 0 at root).
    
    Returns:
        dict: Node data including flight info, depth, and children.
    """
    if node is None:
        return None
    data = node.to_dict()
    data["depth"] = depth
    data["left"] = _bst_node_to_dict(node.left, depth + 1)
    data["right"] = _bst_node_to_dict(node.right, depth + 1)
    return data


def _tree_payload() -> dict:
    """
    Generate complete payload for AVL tree state.
    
    Returns:
        dict: Tree structure, metrics, metadata, and traversal orders.
    """
    tree = _manager.tree
    metadata = _data_storage.get_tree_metadata(tree.root)

    breadth_codes = []
    depth_codes = []
    if tree.root:
        try:
            breadth_codes = [node.flight_code for node in tree.breadth_first_search()]
            depth_codes = [node.flight_code for node in tree.pre_order_traversal()]
        except Exception:
            pass

    return {
        "root": _node_to_dict(tree.root),
        "height": metadata["height"],
        "node_count": metadata["node_count"],
        "leaf_count": metadata["leaf_count"],
        "can_undo": _manager.can_undo(),
        "breadth_order": breadth_codes,
        "depth_order": depth_codes,
        "metrics": {
            "LL": tree.rotation_count["LL"],
            "RR": tree.rotation_count["RR"],
            "LR": tree.rotation_count["LR"],
            "RL": tree.rotation_count["RL"],
            "total_rotations": sum(tree.rotation_count.values()),
            "mass_cancellations": tree.cascade_rebalance_count,
        },
    }


def _bst_payload() -> dict:
    """
    Generate complete payload for BST tree state.
    
    Returns:
        dict: BST structure and metadata.
    """
    if _bst_tree.root is None:
        return {"root": None, "height": 0, "node_count": 0, "leaf_count": 0}
    properties = _bst_tree.get_properties()
    return {
        "root": _bst_node_to_dict(_bst_tree.root),
        "height": properties["height"],
        "node_count": properties["node_count"],
        "leaf_count": properties["leaf_count"],
    }


@flight_bp.route("/api/tree-state", methods=["GET"])
def tree_state():
    """
    Get current AVL tree state.
    
    Returns:
        JSON: Complete tree structure and metadata.
    """
    return jsonify({
        "tree": _tree_payload(),
        "stress_mode": _manager.tree.stress_mode,
        "critical_depth": _manager.critical_depth,
    })


@flight_bp.route("/api/load-tree", methods=["POST"])
def load_tree():
    """
    Load and reconstruct tree from JSON file.
    
    Expected form fields:
        - file: Uploaded JSON file (required)
        - type: Load type "topology" or "insertion" (default: "topology")
    
    Returns:
        JSON: Reconstructed tree state or error message.
    """
    global _manager, _bst_tree

    file = request.files.get("file")
    load_type = request.form.get("type", "topology")

    avl, bst, error = _data_storage.load_and_reconstruct(file, load_type)

    if error:
        status = 400 if "No se proporcionó" in error else 422
        return jsonify({"error": error}), status

    current_stress_mode = _manager.tree.stress_mode
    avl.stress_mode = current_stress_mode
    _manager.tree = avl
    _manager._undo_stack.clear()

    if bst is not None:
        _bst_tree = bst

    response = {
        "tree": _tree_payload(),
        "stress_mode": _manager.tree.stress_mode,
        "critical_depth": _manager.critical_depth,
    }
    if load_type == "insertion":
        response["bst_tree"] = _bst_payload()

    return jsonify(response)


@flight_bp.route("/api/export-tree", methods=["GET"])
def export_tree():
    """
    Export current AVL tree to JSON file in Downloads folder.
    
    Returns:
        JSON: Success message or error.
    """
    success, error = _data_storage.export_tree(_manager.tree.root)
    if error:
        status = 400 if "vacío" in error else 500
        return jsonify({"error": error}), status

    if not success:
        return jsonify({"error": "No se pudo exportar el árbol"}), 500

    return jsonify({"message": "Arbol exportado en Descargas"})


@flight_bp.route("/api/add-flight", methods=["POST"])
def add_flight():
    """
    Add a new flight to the AVL tree.
    
    Expected JSON fields:
        - flight_code (str): Unique flight identifier (required)
        - origin (str): Departure city (required)
        - destination (str): Arrival city (required)
        - base_price (float): Base ticket price >= 0 (required)
        - passengers (int): Passenger count >= 0 (optional, default: 0)
        - promotion (float): Discount 0.0-1.0 (optional, default: 0.0)
        - alert (str): Alert message (optional, default: "")
        - priority (int): Priority 1-5 (optional, default: 3)
    
    Returns:
        JSON: Updated tree state or validation error.
    """
    data = request.get_json(silent=True) or {}

    missing = [field for field in ("flight_code", "origin", "destination", "base_price") if not data.get(field)]
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
        _manager.add_flight(
            flight_code=str(data["flight_code"]).strip().upper(),
            origin=str(data["origin"]).strip(),
            destination=str(data["destination"]).strip(),
            base_price=base_price,
            passengers=passengers,
            promotion=promotion,
            alert=str(data.get("alert", "")).strip(),
            priority=priority,
        )
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"tree": _tree_payload()})


@flight_bp.route("/api/edit-flight", methods=["POST"])
def edit_flight():
    """
    Update flight fields by code.
    
    Expected JSON fields:
        - flight_code (str): Code of flight to update (required)
        - updated_data (dict): Fields to update:
            - new_flight_code (str): Rename the flight
            - origin (str): Update origin
            - destination (str): Update destination
            - base_price (float): Update price
            - final_price (float): Override final price
            - passengers (int): Update passenger count
            - promotion (float): Update promotion
            - alert (str): Update alert message
            - priority (int): Update priority
    
    Returns:
        JSON: Updated tree state or validation error.
    """
    body = request.get_json(silent=True) or {}
    flight_code = body.get("flight_code", "").strip()
    updated_data = body.get("updated_data", {})

    if not flight_code:
        return jsonify({"error": "flight_code es requerido"}), 400
    if not updated_data:
        return jsonify({"error": "No hay campos para actualizar"}), 400

    for field, cast, label in [
        ("base_price", float, "Precio base"),
        ("passengers", int, "Pasajeros"),
        ("promotion", float, "Promoción"),
        ("priority", int, "Prioridad"),
    ]:
        if field in updated_data:
            try:
                updated_data[field] = cast(updated_data[field])
            except (ValueError, TypeError):
                return jsonify({"error": f"{label} debe ser un número válido"}), 400

    if "base_price" in updated_data and updated_data["base_price"] < 0:
        return jsonify({"error": "El precio base no puede ser negativo"}), 400
    if "passengers" in updated_data and updated_data["passengers"] < 0:
        return jsonify({"error": "Los pasajeros no pueden ser negativos"}), 400
    if "promotion" in updated_data and not (0.0 <= updated_data["promotion"] <= 1.0):
        return jsonify({"error": "La promoción debe estar entre 0 y 1"}), 400
    if "priority" in updated_data and not (1 <= updated_data["priority"] <= 5):
        return jsonify({"error": "La prioridad debe estar entre 1 y 5"}), 400

    try:
        _manager.update_flight(flight_code, **updated_data)
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"tree": _tree_payload()})


@flight_bp.route("/api/delete-flight", methods=["POST"])
def delete_flight():
    """
    Delete a single flight from the tree by code.
    
    Expected JSON fields:
        - flight_code (str): Code of flight to delete
    
    Returns:
        JSON: Updated tree state or error.
    """
    body = request.get_json(silent=True) or {}
    flight_code = body.get("flight_code", "").strip()
    if not flight_code:
        return jsonify({"error": "flight_code es requerido"}), 400

    try:
        _manager.delete_flight(flight_code)
    except (ValueError, KeyError):
        return jsonify({"error": f"Vuelo '{flight_code}' no encontrado"}), 404

    return jsonify({"tree": _tree_payload()})


@flight_bp.route("/api/cancel-flight", methods=["POST"])
def cancel_flight():
    """
    Cancel a flight and remove its entire subtree.
    
    Expected JSON fields:
        - flight_code (str): Code of flight to cancel
    
    Returns:
        JSON: Removed count and updated tree state or error.
    """
    body = request.get_json(silent=True) or {}
    flight_code = body.get("flight_code", "").strip()
    if not flight_code:
        return jsonify({"error": "flight_code es requerido"}), 400

    try:
        removed = _manager.cancel_flight(flight_code)
        _manager.tree.cascade_rebalance_count += 1
    except (ValueError, KeyError):
        return jsonify({"error": f"Vuelo '{flight_code}' no encontrado"}), 404

    return jsonify({"removed_count": removed, "tree": _tree_payload()})


@flight_bp.route("/api/undo", methods=["POST"])
def undo():
    """
    Undo the last mutating operation (Ctrl+Z).
    
    Returns:
        JSON: Restored tree state or error if no undo history.
    """
    ok = _manager.undo_last_action()
    if not ok:
        return jsonify({"error": "No hay acciones para deshacer"}), 400
    return jsonify({
        "tree": _tree_payload(),
        "stress_mode": _manager.tree.stress_mode,
        "critical_depth": _manager.critical_depth,
    })


@flight_bp.route("/api/toggle-stress-mode", methods=["POST"])
def toggle_stress_mode():
    """
    Toggle stress mode for the AVL tree.
    
    In stress mode, rotations are deferred until global_rebalance is called.
    
    Expected JSON fields:
        - stress_mode (bool): Target stress mode state
    
    Returns:
        JSON: New stress mode state, rotations executed, and tree state.
    """
    body = request.get_json(silent=True) or {}
    new_state = bool(body.get("stress_mode", not _manager.tree.stress_mode))

    if new_state != _manager.tree.stress_mode:
        _manager.record_undo_state()

    rotations_done = 0
    if not new_state:
        rotations_done = _manager.global_rebalance()
        _manager.set_stress_mode(False)
    else:
        _manager.set_stress_mode(True)

    return jsonify({
        "stress_mode": _manager.tree.stress_mode,
        "rotations_done": rotations_done,
        "tree": _tree_payload(),
    })


@flight_bp.route("/api/global-rebalance", methods=["POST"])
def global_rebalance():
    """
    Perform a complete tree rebalance.
    
    Returns:
        JSON: Number of rotations performed and updated tree state.
    """
    _manager.record_undo_state()
    rotations = _manager.global_rebalance()
    return jsonify({"rotations_done": rotations, "tree": _tree_payload()})


@flight_bp.route("/api/audit-avl", methods=["GET"])
def audit_avl():
    """
    Audit the AVL tree for structural integrity.
    
    Verifies balance factors and height consistency.
    
    Returns:
        JSON: Audit result (valid yes/no) and detailed issue report.
    """
    report = []
    is_valid = _analysis.audit_node(_manager.tree.root, report)
    return jsonify({"valid": is_valid, "report": report})


@flight_bp.route("/api/update-critical-depth", methods=["POST"])
def update_critical_depth():
    """
    Update the critical depth threshold and apply pricing penalties.
    
    Expected JSON fields:
        - critical_depth (int): New depth threshold (must be >= 1)
    
    Returns:
        JSON: New critical depth value and updated tree state or error.
    """
    body = request.get_json(silent=True) or {}

    try:
        value = int(body.get("critical_depth", 5))
        if value < 1:
            return jsonify({"error": "La profundidad crítica debe ser mayor a 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "La profundidad crítica debe ser un número entero"}), 400

    if value != _manager.critical_depth:
        _manager.record_undo_state()

    _manager.critical_depth = value
    _analysis.apply_depth_penalties(_manager.tree.root, 0, _manager.critical_depth)
    return jsonify({"critical_depth": _manager.critical_depth, "tree": _tree_payload()})


@flight_bp.route("/api/save-version", methods=["POST"])
def save_version():
    """
    Save current tree state as a named version.
    
    Expected JSON fields:
        - version_name (str): Descriptive name for this version (required)
    
    Returns:
        JSON: Success flag.
    """
    body = request.get_json(silent=True) or {}
    version_name = body.get("version_name", "").strip()
    if not version_name:
        return jsonify({"error": "version_name es requerido"}), 400

    ok = _data_storage.save_avl_version(
        version_name,
        _manager.tree.root,
        rotation_count=_manager.tree.rotation_count,
        cascade_rebalance_count=_manager.tree.cascade_rebalance_count,
        mass_cancellation_count=_manager.tree.mass_cancellation_count,
    )
    if not ok:
        return jsonify({"error": "No se pudo guardar la versión. Verifica que el árbol no esté vacío."}), 400

    return jsonify({"success": True})


@flight_bp.route("/api/restore-version", methods=["POST"])
def restore_version():
    """
    Restore tree state from a saved version.
    
    Expected JSON fields:
        - version_name (str): Name of version to restore (required)
    
    Returns:
        JSON: Updated tree state or error if version not found.
    """
    global _manager
    body = request.get_json(silent=True) or {}
    version_name = body.get("version_name", "").strip()
    if not version_name:
        return jsonify({"error": "version_name es requerido"}), 400

    root = _data_storage.restore_avl_version(version_name)
    if root is None:
        return jsonify({"error": f"Versión '{version_name}' no encontrada"}), 404

    metadata = _data_storage.get_version_info(version_name) or {}
    current_stress_mode = _manager.tree.stress_mode
    new_avl = AVLTree(stress_mode=current_stress_mode)
    new_avl.root = root

    saved_rotations = metadata.get("rotation_count")
    if isinstance(saved_rotations, dict):
        new_avl.rotation_count = saved_rotations
    new_avl.cascade_rebalance_count = int(metadata.get("cascade_rebalance_count", 0))
    new_avl.mass_cancellation_count = int(metadata.get("mass_cancellation_count", 0))

    _manager.tree = new_avl
    _manager._undo_stack.clear()
    return jsonify({
        "tree": _tree_payload(),
        "stress_mode": _manager.tree.stress_mode,
        "critical_depth": _manager.critical_depth,
    })


@flight_bp.route("/api/list-versions", methods=["GET"])
def list_versions():
    """
    Get information about all saved versions.
    
    Returns:
        JSON: Dictionary mapping version names to their metadata.
    """
    return jsonify({"versions": _data_storage.get_all_versions_info()})


@flight_bp.route("/api/delete-version", methods=["POST"])
def delete_version():
    """
    Delete a saved version.
    
    Expected JSON fields:
        - version_name (str): Name of version to delete
    
    Returns:
        JSON: Success flag.
    """
    body = request.get_json(silent=True) or {}
    version_name = body.get("version_name", "").strip()
    ok = _data_storage.delete_version(version_name)
    return jsonify({"success": ok})


@flight_bp.route("/api/delete-least-profitable", methods=["POST"])
def delete_least_profitable():
    """
    Find and cancel the least profitable flight in the tree.
    
    Applies profitability tiebreaker rules to identify the target flight,
    then cancels it and removes its entire subtree.
    
    Returns:
        JSON: Cancelled flight code, removed count, and updated tree state.
    """
    if _manager.tree.root is None:
        return jsonify({"error": "El árbol está vacío"}), 400

    target = _analysis.find_least_profitable(_manager.tree.root)
    if target is None:
        return jsonify({"error": "No se encontraron nodos"}), 500

    try:
        removed = _manager.cancel_flight(target.flight_code)
        _manager.tree.cascade_rebalance_count += 1
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({
        "cancelled": target.flight_code,
        "removed_count": removed,
        "tree": _tree_payload(),
    })