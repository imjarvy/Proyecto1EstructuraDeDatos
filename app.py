"""
SkyBalance AVL - Flask Web Application.

REST API layer that bridges the Python backend with the HTML/JS frontend.
Only exposes endpoints for functionality already implemented in Python modules.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from flask import Flask, render_template, send_from_directory
from flask_cors import CORS

from src.acceso_datos.DataStorage import DataStorage
from src.modelos.AVLTree import AVLTree
from src.modelos.BST import BST
from src.negocio.AVLTreeManager import AVLTreeManager
from src.negocio.TreeAnalysisManager import TreeAnalysisManager
from src.routes.flight_routes import flight_bp, init_flight_routes
from src.routes.queue_routes import queue_bp, init_queue

app = Flask(
    __name__,
    template_folder="src/presentacion/vistas",
    static_folder="src/presentacion/estilos",
    static_url_path="/estilos",
)
CORS(app)

# Register blueprints after creating the app.
app.register_blueprint(queue_bp)
app.register_blueprint(flight_bp)

# Shared application state.
avl_tree = AVLTree()
manager = AVLTreeManager(avl_tree)
bst_tree = BST()
data_storage = DataStorage()
analysis = TreeAnalysisManager()

# Presentation assets.
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "src", "presentacion", "scripts")


@app.route("/scripts/<path:filename>")
def scripts_static(filename):
    """Serve static JS files from the presentation scripts directory."""
    return send_from_directory(SCRIPTS_DIR, filename)


@app.route("/")
def index():
    """Serve the main HTML page."""
    return render_template("index.html")


# Initialize shared modules after the manager exists.
init_queue(manager)
init_flight_routes(manager, bst_tree, data_storage, analysis)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
