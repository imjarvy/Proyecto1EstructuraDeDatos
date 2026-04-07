from flask import Blueprint, jsonify, request

from src.modelos.AVLTree import AVLTree

flight_bp = Blueprint("flight", __name__)

_manager = None
_bst_tree = None
_data_storage = None
_analysis = None
_critical_depth = 5


def init_flight_routes(manager, bst_tree, data_storage, analysis, critical_depth=5):
    global _manager, _bst_tree, _data_storage, _analysis, _critical_depth
    _manager = manager
    _bst_tree = bst_tree
    _data_storage = data_storage
    _analysis = analysis
    _critical_depth = critical_depth


def _node_to_dict(node, depth: int = 0):
    if node is None:
        return None
    data = node.to_dict()
    data["depth"] = depth
    data["is_critical"] = depth > _critical_depth
    data["left"] = _node_to_dict(node.left, depth + 1)
    data["right"] = _node_to_dict(node.right, depth + 1)
    return data


def _bst_node_to_dict(node, depth: int = 0):
    if node is None:
        return None
    data = node.to_dict()
    data["depth"] = depth
    data["left"] = _bst_node_to_dict(node.left, depth + 1)
    data["right"] = _bst_node_to_dict(node.right, depth + 1)
    return data


def _tree_payload() -> dict:
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
    return jsonify({"tree": _tree_payload()})


@flight_bp.route("/api/load-tree", methods=["POST"])
def load_tree():
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

    response = {"tree": _tree_payload()}
    if load_type == "insertion":
        response["bst_tree"] = _bst_payload()

    return jsonify(response)


@flight_bp.route("/api/export-tree", methods=["GET"])
def export_tree():
    success, error = _data_storage.export_tree(_manager.tree.root)
    if error:
        status = 400 if "vacío" in error else 500
        return jsonify({"error": error}), status

    if not success:
        return jsonify({"error": "No se pudo exportar el árbol"}), 500

    return jsonify({"message": "Arbol exportado en Descargas"})


@flight_bp.route("/api/add-flight", methods=["POST"])
def add_flight():
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
    ok = _manager.undo_last_action()
    if not ok:
        return jsonify({"error": "No hay acciones para deshacer"}), 400
    return jsonify({"tree": _tree_payload()})


@flight_bp.route("/api/toggle-stress-mode", methods=["POST"])
def toggle_stress_mode():
    body = request.get_json(silent=True) or {}
    new_state = bool(body.get("stress_mode", not _manager.tree.stress_mode))

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
    rotations = _manager.global_rebalance()
    return jsonify({"rotations_done": rotations, "tree": _tree_payload()})


@flight_bp.route("/api/audit-avl", methods=["GET"])
def audit_avl():
    report = []
    is_valid = _analysis.audit_node(_manager.tree.root, report)
    return jsonify({"valid": is_valid, "report": report})


@flight_bp.route("/api/update-critical-depth", methods=["POST"])
def update_critical_depth():
    global _critical_depth
    body = request.get_json(silent=True) or {}

    try:
        value = int(body.get("critical_depth", 5))
        if value < 1:
            return jsonify({"error": "La profundidad crítica debe ser mayor a 0"}), 400
        _critical_depth = value
    except (ValueError, TypeError):
        return jsonify({"error": "La profundidad crítica debe ser un número entero"}), 400

    _analysis.apply_depth_penalties(_manager.tree.root, 0, _critical_depth)
    return jsonify({"critical_depth": _critical_depth, "tree": _tree_payload()})


@flight_bp.route("/api/save-version", methods=["POST"])
def save_version():
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
    return jsonify({"success": ok})


@flight_bp.route("/api/restore-version", methods=["POST"])
def restore_version():
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
    return jsonify({"tree": _tree_payload()})


@flight_bp.route("/api/list-versions", methods=["GET"])
def list_versions():
    return jsonify({"versions": _data_storage.get_all_versions_info()})


@flight_bp.route("/api/delete-version", methods=["POST"])
def delete_version():
    body = request.get_json(silent=True) or {}
    version_name = body.get("version_name", "").strip()
    ok = _data_storage.delete_version(version_name)
    return jsonify({"success": ok})


@flight_bp.route("/api/delete-least-profitable", methods=["POST"])
def delete_least_profitable():
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