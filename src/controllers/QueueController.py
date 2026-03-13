# AVL Flight. Processes pending queue insertions into the AVL tree.

from src.modelos.FlightNode import FlightNode
from src.modelos.AVLTree import AVLTree
from src.modelos.FlightQueue import FlightQueue
from typing import Optional


class QueueController:
    # Handles queue processing and insertion into the AVL tree.

    CRITICAL_BALANCE_THRESHOLD = 2  # bf beyond this triggers a conflict

    def __init__(self, avl_tree: AVLTree, queue: FlightQueue):
        self.avl_tree = avl_tree
        self.queue = queue

    # ================SINGLE PROCESSING=======================

    def process_one(self) -> dict:
        # Takes first flight from queue, inserts into AVL, tracks result.

        if self.queue.is_empty():
            return {"status": "empty", "message": "No pending flights in queue."}

        flight = self.queue.dequeue()
        bf_before = self._max_balance_factor()

        try:
            self.avl_tree.insert(flight)
            self.queue._processed.append(flight)

            bf_after = self._max_balance_factor()
            conflict = self._detect_conflict(flight, bf_before, bf_after)

            return {
                "status": "ok",
                "inserted": flight.flight_code,
                "conflict": conflict,
                "tree_height": self.avl_tree.get_tree_height(),
                "pending": self.queue.size()
            }

        except Exception as e:
            self.queue.register_conflict(flight, str(e))
            return {"status": "error", "flight": flight.flight_code, "reason": str(e)}

    # ================FULL PROCESSING=========================

    def process_all(self) -> dict:
        # Drains entire queue, returns summary of all insertions.

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
        # Checks if insertion caused a critical balance spike.

        if bf_after >= self.CRITICAL_BALANCE_THRESHOLD:
            reason = f"Balance spiked from {bf_before} to {bf_after} after inserting {flight.flight_code}"
            self.queue.register_conflict(flight, reason)
            return {"flight": flight.flight_code, "reason": reason}
        return None

    def _max_balance_factor(self) -> int:
        # Walks the tree and returns the highest absolute balance factor found.

        if self.avl_tree.root is None:
            return 0
        nodes = self.avl_tree.breadth_first_search()
        return max(abs(n.balance_factor) for n in nodes)