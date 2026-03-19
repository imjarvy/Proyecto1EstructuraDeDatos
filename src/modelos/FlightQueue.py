"""
FlightQueue class definition for the SkyBalance AVL Flight Management System.

This module provides a FIFO queue used to temporarily store flight insertion requests before they are processed into the AVL tree. 
It also tracks processed flights and conflict records generated during queue processing.
"""

from src.modelos.FlightNode import FlightNode
from typing import Optional


class FlightQueue:
    """
    FIFO queue for managing pending flight insertion requests.

    Attributes:
        _queue (list[FlightNode]): Pending flights waiting to be processed.
        _processed (list[FlightNode]): History of successfully processed flights.
        _conflicts (list[dict]): Logged conflicts detected during processing.
    """

    def __init__(self):
        """
        Initialize an empty flight queue.

        Creates separate internal lists for pending items, processed history,
        and conflict tracking.
        """
        self._queue: list[FlightNode] = []
        self._processed: list[FlightNode] = []
        self._conflicts: list[dict] = []


    # ================ENQUEUE / DEQUEUE=======================
    def enqueue(self, flight_node: FlightNode) -> None:
        """
        Add a flight to the end of the queue.

        Args:
            flight_node (FlightNode): Flight to enqueue.
        """
        self._queue.append(flight_node)

    def dequeue(self) -> Optional[FlightNode]:
        """
        Remove and return the next pending flight.

        Returns:
            Optional[FlightNode]: First queued flight, or None when empty.
        """
        if self.is_empty():
            return None
        return self._queue.pop(0)

    def peek(self) -> Optional[FlightNode]:
        """
        Return the next pending flight without removing it.

        Returns:
            Optional[FlightNode]: First queued flight, or None when empty.
        """
        if self.is_empty():
            return None
        return self._queue[0]


    # ===================QUEUE STATUS=================

    def is_empty(self) -> bool:
        """
        Check whether there are pending flights in the queue.

        Returns:
            bool: True when queue is empty, False otherwise.
        """
        return len(self._queue) == 0

    def size(self) -> int:
        """
        Get the number of pending flights in the queue.

        Returns:
            int: Count of pending queue items.
        """
        return len(self._queue)

    def clear(self) -> None:
        """
        Remove all pending flights from the queue.
        """
        self._queue.clear()

    # ================CONFLICT TRACKING====================
    def register_conflict(self, flight_node: FlightNode, reason: str) -> None:
        """
        Register a flight that caused a processing conflict.

        Args:
            flight_node (FlightNode): Flight related to the conflict.
            reason (str): Human-readable reason for the conflict.
        """

        self._conflicts.append({
            "flight_code": flight_node.flight_code,
            "origin": flight_node.origin,
            "destination": flight_node.destination,
            "reason": reason
        })

    def get_conflicts(self) -> list:
        """
        Return a copy of all registered conflicts.

        Returns:
            list: Conflict records as dictionaries.
        """
        return self._conflicts.copy()

    def clear_conflicts(self) -> None:
        """
        Clear all stored conflict records.
        """
        self._conflicts.clear()

    # =============SERIALIZATION===============

    def queue_to_dict(self) -> dict:
        """
        Serialize current queue state to a dictionary payload.

        Returns:
            dict: Pending flights, processed history, conflicts, and totals.
        """

        return {
            "pending": [f.to_dict() for f in self._queue],
            "processed": [f.to_dict() for f in self._processed],
            "conflicts": self._conflicts.copy(),
            "total_pending": len(self._queue),
            "total_processed": len(self._processed),
            "total_conflicts": len(self._conflicts)
        }