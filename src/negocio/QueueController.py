"""
QueueController module for SkyBalance AVL Flight Management System.

This module processes pending queue insertions into the AVL tree.
It handles single and batch processing with conflict detection.
"""

from src.modelos.FlightNode import FlightNode
from src.modelos.FlightQueue import FlightQueue
from typing import Optional

class QueueController:
    """
    Manages flight queue processing and insertion via AVLTreeManager.
    
    Handles dequeueing flights and inserting them into the tree with
    conflict detection based on balance factor changes.
    
    Attributes:
        manager: AVLTreeManager instance for tree operations.
        queue (FlightQueue): Queue instance containing pending flights.
        CRITICAL_BALANCE_THRESHOLD (int): Maximum acceptable balance factor spike.
    """

    CRITICAL_BALANCE_THRESHOLD = 2

    def __init__(self, manager, queue: FlightQueue):
        """
        Initialize the queue controller.
        
        Args:
            manager: AVLTreeManager instance for tree operations.
            queue (FlightQueue): Queue to process flights from.
        """
        self.manager = manager
        self.queue = queue

    # ================SINGLE PROCESSING=======================

    def process_one(self) -> dict:
        """
        Process next flight from queue and insert into tree.
        
        Takes the first flight from the queue, validates it, and inserts
        via the manager. Detects conflicts based on balance factor changes.
        
        Returns:
            dict: Status information including:
                - status: "empty", "ok", or "error"
                - inserted: Flight code if successful
                - conflict: Conflict details if detected
                - tree_height: Current tree height
                - pending: Remaining queue size
        """

        if self.queue.is_empty():
            return {"status": "empty", "message": "No pending flights in queue."}

        flight = self.queue.dequeue()
        bf_before = self._max_balance_factor()

        try:
            self.manager.add_flight(
                flight_code=flight.flight_code,
                origin=flight.origin,
                destination=flight.destination,
                base_price=flight.base_price,
                passengers=flight.passengers,
                promotion=flight.promotion,
                alert=flight.alert,
                priority=flight.priority
            )
            self.queue._processed.append(flight)

            bf_after = self._max_balance_factor()
            conflict = self._detect_conflict(flight, bf_before, bf_after)

            return {
                "status": "ok",
                "inserted": flight.flight_code,
                "conflict": conflict,
                "tree_height": self.manager.tree.get_tree_height(),
                "pending": self.queue.size()
            }

        except Exception as e:
            self.queue.register_conflict(flight, str(e))
            return {"status": "error", "flight": flight.flight_code, "reason": str(e)}

    # ================FULL PROCESSING=========================

    def process_all(self) -> dict:
        """
        Process all flights in queue and insert into tree.
        
        Drains the entire queue, returns summary of all insertions
        including processed counts and detected conflicts.
        
        Returns:
            dict: Summary including:
                - status: "done"
                - total_inserted: Number of successfully inserted flights
                - total_conflicts: Number of conflicts detected
                - conflicts: List of conflict details
                - results: List of results from each process_one call
        """

        results = []
        while not self.queue.is_empty():
            results.append(self.process_one())

        return {
            "status": "done",
            "total_inserted": len(self.queue._processed),
            "total_conflicts": len(self.queue.get_conflicts()),
            "conflicts": self.queue.get_conflicts(),
            "results": results
        }

    # ================CONFLICT DETECTION======================

    def _detect_conflict(self, flight: FlightNode, bf_before: int, bf_after: int) -> Optional[dict]:
        """
        Detect conflicts based on balance factor changes.
        
        A conflict is registered when the balance factor spike after
        insertion exceeds CRITICAL_BALANCE_THRESHOLD.
        
        Args:
            flight (FlightNode): Flight being inserted.
            bf_before (int): Maximum balance factor before insertion.
            bf_after (int): Maximum balance factor after insertion.
        
        Returns:
            dict: Conflict details if detected, None otherwise.
        """
        if bf_after >= self.CRITICAL_BALANCE_THRESHOLD:
            reason = f"Balance spiked from {bf_before} to {bf_after} after inserting {flight.flight_code}"
            self.queue.register_conflict(flight, reason)
            return {"flight": flight.flight_code, "reason": reason}
        return None

    def _max_balance_factor(self) -> int:
        """
        Get the maximum absolute balance factor in the tree.
        
        Returns:
            int: Maximum balance factor value, or 0 if tree is empty.
        """
        if self.manager.tree.root is None:
            return 0
        nodes = self.manager.tree.breadth_first_search()
        return max(abs(n.balance_factor) for n in nodes)