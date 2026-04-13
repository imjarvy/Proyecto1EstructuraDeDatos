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
        self._queue_undo_stack = []

    def _clone_node(self, node: FlightNode) -> FlightNode:
        """Create an independent copy of a flight node for queue snapshots."""
        return FlightNode.from_dict(node.to_dict())

    def _snapshot_queue_state(self) -> dict:
        """Capture queue/processed/conflicts state before queue processing."""
        return {
            "pending": [self._clone_node(node) for node in self.queue._queue],
            "processed": [self._clone_node(node) for node in self.queue._processed],
            "conflicts": [conflict.copy() for conflict in self.queue._conflicts],
        }

    def record_undo_snapshot(self) -> None:
        """Store queue state so the next queue mutation can be reverted."""
        self._queue_undo_stack.append(self._snapshot_queue_state())

    def undo_last_queue_change(self) -> bool:
        """Restore queue state before the last successful queue mutation."""
        if not self._queue_undo_stack:
            return False

        snapshot = self._queue_undo_stack.pop()
        self.queue._queue = [self._clone_node(node) for node in snapshot["pending"]]
        self.queue._processed = [self._clone_node(node) for node in snapshot["processed"]]
        self.queue._conflicts = [conflict.copy() for conflict in snapshot["conflicts"]]
        return True

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

        queue_snapshot = self._snapshot_queue_state()
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
                priority=flight.priority,
                undo_source="queue_process",
            )
            self.queue._processed.append(flight)

            bf_after = self._max_balance_factor()
            conflict = self._detect_conflict(flight, bf_before, bf_after)
            self._queue_undo_stack.append(queue_snapshot)

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