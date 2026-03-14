# AVL Flight. Processes pending queue insertions into the AVL tree.

from src.modelos.FlightNode import FlightNode
from src.modelos.FlightQueue import FlightQueue
from typing import Optional


class QueueController:
    # Handles queue processing and insertion via AVLTreeManager.

    CRITICAL_BALANCE_THRESHOLD = 2

    def __init__(self, manager, queue: FlightQueue):
        self.manager = manager        # usa manager, no avl_tree directo
        self.queue = queue

    # ================SINGLE PROCESSING=======================

    def process_one(self) -> dict:
        # Takes first flight from queue, inserts via manager, tracks result.

        if self.queue.is_empty():
            return {"status": "empty", "message": "No pending flights in queue."}

        flight = self.queue.dequeue()
        bf_before = self._max_balance_factor()

        try:
            self.manager.add_flight(      # ← manager en lugar de avl_tree.insert
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
        if bf_after >= self.CRITICAL_BALANCE_THRESHOLD:
            reason = f"Balance spiked from {bf_before} to {bf_after} after inserting {flight.flight_code}"
            self.queue.register_conflict(flight, reason)
            return {"flight": flight.flight_code, "reason": reason}
        return None

    def _max_balance_factor(self) -> int:
        if self.manager.tree.root is None:
            return 0
        nodes = self.manager.tree.breadth_first_search()
        return max(abs(n.balance_factor) for n in nodes)