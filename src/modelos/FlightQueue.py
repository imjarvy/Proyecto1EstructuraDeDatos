"AVL Flight. FIFO queue to manage pending flight insertion requests before they are processed into the AVL tree."

from src.modelos.FlightNode import FlightNode
from typing import Optional


class FlightQueue:
    "FIFO for managing pending insertion requests."

    def __init__(self):
        """Initialize empty flight queue."""
        self._queue: list[FlightNode] = [] #Internal list storing pending FlightNode objects
        self._processed: list[FlightNode] = [] #History of successfully processed flights
        self._conflicts: list[dict] = [] #List of flights that caused critical balance issues, stored as dicts with flight details and reason


    # ================ENQUEUE / DEQUEUE=======================
    def enqueue(self, flight_node: FlightNode) -> None:
        self._queue.append(flight_node)     # Add a flight to the end of the queue.

    def dequeue(self) -> Optional[FlightNode]:
        if self.is_empty(): # Next flight, or None if queue is empty.
            return None
        return self._queue.pop(0)

    def peek(self) -> Optional[FlightNode]: # Return the first flight without removing it.
        if self.is_empty():
            return None
        return self._queue[0]


    # ===================QUEUE STATUS=================

    def is_empty(self) -> bool: # has it no pending flights?
        return len(self._queue) == 0

    def size(self) -> int: # Return number of pending flights in queue.
        return len(self._queue)

    def clear(self) -> None: # Remove all pending flights from queue.
        self._queue.clear()

    # ================CONFLICT TRACKING====================
    def register_conflict(self, flight_node: FlightNode, reason: str) -> None:
        #Register a flight that caused a critical balance conflict.

        self._conflicts.append({
            "flight_code": flight_node.flight_code,
            "origin": flight_node.origin,
            "destination": flight_node.destination,
            "reason": reason
        })

    def get_conflicts(self) -> list:
        "Return list of registered conflicts."
        return self._conflicts.copy()

    def clear_conflicts(self) -> None:
        "Clear conflict history."
        self._conflicts.clear()

    # =============SERIALIZATION===============

    def queue_to_dict(self) -> dict: #Serialize queue state to dictionary.

        return {
            "pending": [f.to_dict() for f in self._queue],
            "processed": [f.to_dict() for f in self._processed],
            "conflicts": self._conflicts.copy(),
            "total_pending": len(self._queue),
            "total_processed": len(self._processed),
            "total_conflicts": len(self._conflicts)
        }