# AVL Flight. Flask routes for queue management endpoints.

from flask import Blueprint, jsonify, request
from src.modelos.FlightNode import FlightNode
from src.modelos.FlightQueue import FlightQueue
from src.controllers.QueueController import QueueController

queue_bp = Blueprint("queue", __name__)  # Blueprint = mini-app Flask independiente

# Estas instancias se comparten con app.py
_queue: FlightQueue = None
_controller: QueueController = None


def init_queue(manager):   # recibe manager, no avl_tree
    global _queue, _controller
    _queue = FlightQueue()
    _controller = QueueController(manager, _queue)


# ================QUEUE STATUS============================

@queue_bp.route("/api/queue", methods=["GET"])
def get_queue():
    # Returns current queue state.
    if _queue is None:
        return jsonify({"error": "Queue not initialized."}), 500
    return jsonify(_queue.queue_to_dict()), 200


# ================ENQUEUE=================================

@queue_bp.route("/api/queue/enqueue", methods=["POST"])
def enqueue_flight():
    # Adds a flight to the pending queue without inserting into AVL.
    if _queue is None:
        return jsonify({"error": "Queue not initialized."}), 500

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Body must be JSON."}), 400

    required = ["flight_code", "origin", "destination", "base_price"]
    missing = [f for f in required if f not in body]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    node = FlightNode(
        flight_code=body["flight_code"],
        origin=body["origin"],
        destination=body["destination"],
        base_price=float(body["base_price"]),
        passengers=int(body.get("passengers", 0)),
        promotion=float(body.get("promotion", 0.0)),
        alert=body.get("alert", ""),
        priority=int(body.get("priority", 3))
    )

    _queue.enqueue(node)
    return jsonify({
        "message": f"Flight {node.flight_code} queued.",
        "pending": _queue.size()
    }), 200


# ================PROCESSING==============================

@queue_bp.route("/api/queue/process-one", methods=["POST"])
def process_one():
    # Processes next flight in queue, inserts into AVL.
    if _controller is None:
        return jsonify({"error": "Controller not initialized."}), 500
    return jsonify(_controller.process_one()), 200


@queue_bp.route("/api/queue/process-all", methods=["POST"])
def process_all():
    # Drains entire queue into AVL.
    if _controller is None:
        return jsonify({"error": "Controller not initialized."}), 500
    return jsonify(_controller.process_all()), 200


# ================CLEAR===================================

@queue_bp.route("/api/queue/clear", methods=["DELETE"])
def clear_queue():
    # Removes all pending flights without inserting them.
    if _queue is None:
        return jsonify({"error": "Queue not initialized."}), 500
    _queue.clear()
    _queue.clear_conflicts()
    return jsonify({"message": "Queue cleared.", "pending": 0}), 200