"""
app.py  –  SkyBalance AVL · Servidor Flask
Coloca este archivo en la RAÍZ del proyecto.

Estructura real del proyecto:
    proyecto/
    ├── app.py
    ├── src/
    │   ├── modelos/
    │   │   ├── FlightNode.py
    │   │   └── AVLTree.py
    │   └── acceso_datos/
    │       ├── DataLoader.py
    │       ├── DataPersistence.py
    │       ├── DataStorage.py
    │       └── VersionManager.py
    └── presentacion/
        ├── vistas/
        │   └── index.html
        ├── script.js
        └── estilos/
            └── styles.css
"""

import os
import json
import tempfile

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from src.acceso_datos.DataStorage import DataStorage
from src.acceso_datos.DataPersistence import DataPersistence
from src.modelos.AVLTree import AVLTree          # ← corregido: estaba en estructuras, es en modelos

# ─────────────────────────────────────────────────────────────────────────────
# static_folder apunta a presentacion/ para servir script.js y estilos/
# El index.html se sirve manualmente desde presentacion/vistas/
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="src/presentacion", static_url_path="")
CORS(app)

storage  = DataStorage()
avl_tree = AVLTree()


# ─────────────────────────────────────────────────────────────────────────────
# Servir el frontend
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    # index.html está en src/presentacion/vistas/
    return send_from_directory(os.path.join("src", "presentacion", "vistas"), "index.html")


# ─────────────────────────────────────────────────────────────────────────────
# Helper interno
# ─────────────────────────────────────────────────────────────────────────────

def _tree_to_response(root, label: str, rotation_count: dict = None) -> dict:
    if root is None:
        return {
            "label": label, "root": None, "root_code": None,
            "height": 0, "nodes": 0, "leaves": 0,
            "tree_structure": {},
            "rotation_count": rotation_count or {}
        }

    persistence = DataPersistence()
    meta        = persistence.get_tree_metadata(root)
    serialised  = persistence.serialize_tree_for_storage(root)

    return {
        "label":          label,
        "root":           meta.get("root"),
        "root_code":      serialised.get("root_code") if serialised else None,
        "height":         meta.get("height", 0),
        "nodes":          meta.get("node_count", 0),
        "leaves":         meta.get("leaf_count", 0),
        "tree_structure": serialised.get("tree_structure", {}) if serialised else {},
        "rotation_count": rotation_count or {}
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/load
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/load", methods=["POST"])
def load_tree():
    global avl_tree

    if "file" not in request.files:
        return jsonify({"error": "No se recibió ningún archivo."}), 400

    uploaded_file = request.files["file"]
    if uploaded_file.filename == "":
        return jsonify({"error": "El archivo está vacío."}), 400

    load_type = request.form.get("load_type", "insertion").lower()
    if load_type not in ("topology", "insertion"):
        return jsonify({"error": "load_type debe ser 'topology' o 'insertion'."}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        tmp_path = tmp.name
        uploaded_file.save(tmp_path)

    try:
        if not storage.load_data_from_path(tmp_path):
            return jsonify({"error": "No se pudo parsear el archivo JSON."}), 422

        if load_type == "topology":
            avl_root = storage.reconstruct_tree_from_topology()
            if avl_root is None:
                return jsonify({
                    "error": "Reconstrucción por topología fallida. "
                             "El JSON debe contener 'root_code' y 'tree_structure'."
                }), 422
            avl_tree      = AVLTree()
            avl_tree.root = avl_root
            storage.set_current_avl_tree(avl_root)
            storage.set_current_bst_tree(None)

        else:
            flights = storage.get_flights_for_insertion_mode()
            if not flights:
                return jsonify({"error": "No se encontraron vuelos en el JSON."}), 422

            avl_tree = AVLTree()
            for flight in flights:
                avl_tree.insert(flight)

            storage.set_current_avl_tree(avl_tree.root)
            storage.set_current_bst_tree(None)

        return jsonify({
            "load_type": load_type,
            "avl": _tree_to_response(
                storage.get_current_avl_root(), "AVL", avl_tree.rotation_count
            ),
            "bst": _tree_to_response(storage.get_current_bst_root(), "BST"),
        }), 200

    except Exception as exc:
        return jsonify({"error": f"Error en el servidor: {str(exc)}"}), 500

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/export
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/export", methods=["GET"])
def export_tree():
    tree_param = request.args.get("tree", "avl").lower()
    root = (storage.get_current_avl_root()
            if tree_param == "avl"
            else storage.get_current_bst_root())

    if root is None:
        return jsonify({"error": f"No hay árbol {tree_param.upper()} cargado."}), 404

    serialised = DataPersistence().serialize_tree_for_storage(root)
    if serialised is None:
        return jsonify({"error": "Error al serializar el árbol."}), 500

    filename = f"skybalance_{tree_param}_export.json"
    response = app.response_class(
        response=json.dumps(serialised, indent=2, ensure_ascii=False),
        status=200,
        mimetype="application/json"
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/insert
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/insert", methods=["POST"])
def insert_flight():
    """
    Inserta un vuelo nuevo en el árbol AVL.

    Request body (JSON):
    {
        "flight_code": "SK010",
        "origin":      "Bogotá",
        "destination": "Cali",
        "base_price":  180000,
        "passengers":  0,
        "promotion":   0,
        "alert":       "",
        "priority":    3
    }
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "El cuerpo debe ser JSON."}), 400

    required = ["flight_code", "origin", "destination", "base_price"]
    missing  = [f for f in required if f not in body]
    if missing:
        return jsonify({"error": f"Faltan campos: {', '.join(missing)}"}), 400

    # Verificar que el vuelo no exista ya
    try:
        existing = avl_tree.search(body["flight_code"])
        if existing:
            return jsonify({"error": f"El vuelo '{body['flight_code']}' ya existe en el árbol."}), 409
    except Exception:
        pass  # search lanza excepción si el árbol está vacío, lo cual es válido

    try:
        from src.modelos.FlightNode import FlightNode
        new_node = FlightNode.from_dict({
            "flight_code": body["flight_code"],
            "origin":      body["origin"],
            "destination": body["destination"],
            "base_price":  float(body["base_price"]),
            "passengers":  int(body.get("passengers", 0)),
            "promotion":   float(body.get("promotion", 0.0)),
            "alert":       body.get("alert", ""),
            "priority":    int(body.get("priority", 3)),
        })

        avl_tree.insert(new_node)
        storage.set_current_avl_tree(avl_tree.root)

        return jsonify({
            "message": f"Vuelo '{body['flight_code']}' insertado correctamente.",
            "avl": _tree_to_response(avl_tree.root, "AVL", avl_tree.rotation_count),
        }), 200

    except Exception as exc:
        return jsonify({"error": f"Error al insertar: {str(exc)}"}), 500


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/delete/<flight_code>
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/delete/<flight_code>", methods=["DELETE"])
def delete_flight(flight_code):
    """
    Elimina un vuelo del árbol AVL por su código.

    URL: DELETE /api/delete/SK010
    """
    if avl_tree.root is None:
        return jsonify({"error": "El árbol está vacío."}), 404

    success = avl_tree.delete(flight_code)
    if not success:
        return jsonify({"error": f"Vuelo '{flight_code}' no encontrado en el árbol."}), 404

    storage.set_current_avl_tree(avl_tree.root)

    return jsonify({
        "message": f"Vuelo '{flight_code}' eliminado correctamente.",
        "avl": _tree_to_response(avl_tree.root, "AVL", avl_tree.rotation_count),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/status
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({
        "status": "ok",
        "avl": _tree_to_response(
            storage.get_current_avl_root(), "AVL", avl_tree.rotation_count
        ),
        "bst": _tree_to_response(storage.get_current_bst_root(), "BST"),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)