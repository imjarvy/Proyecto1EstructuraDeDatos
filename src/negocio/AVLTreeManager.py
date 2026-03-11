"""
AVLTreeManager – Business logic layer for the SkyBalance AVL Flight Management System.

Provides high-level operations on an AVLTree:
    - add_flight      : validate and insert a new FlightNode.
    - delete_flight   : remove a flight from the tree by code.
    - update_flight   : modify one or more fields of an existing flight.
    - cancel_flight   : remove a flight and its full descendant subtree.
"""

from typing import Optional, Dict, Any, List

from src.modelos.AVLTree import AVLTree
from src.modelos.FlightNode import FlightNode
from src.acceso_datos.DataPersistence import DataPersistence


# Fields that can be updated without changing the BST key (flight_code).
_UPDATABLE_FIELDS = {
    "origin",
    "destination",
    "base_price",
    "final_price",
    "passengers",
    "promotion",
    "alert",
    "priority",
}

class AVLTreeManager:
    """
    Manages CRUD operations and flight cancellation on an AVLTree.

    Attributes:
        tree (AVLTree): The underlying AVL tree instance.
    """

    def __init__(self, tree: Optional[AVLTree] = None):
        """
        Initialise the manager.

        Args:
            tree (AVLTree, optional): Existing tree to manage. Creates a new
                                      empty tree when not provided.
        """
        self.tree: AVLTree = tree if tree is not None else AVLTree()
        self._persistence = DataPersistence()
        self._undo_stack: List[Dict[str, Any]] = []
        

    # PILA DE DESHACER (Crtl+Z)
    
    def _snapshot_state(self) -> Dict[str, Any]:
        """Capture full reversible AVL state for Ctrl+Z operations."""
        return {
            "tree_data": self._persistence.serialize_tree_for_storage(self.tree.root),
            "rotation_count": self.tree.rotation_count.copy(),
            "cascade_rebalance_count": self.tree.cascade_rebalance_count,
            "stress_mode": self.tree.stress_mode,
        }

    def _push_undo_state(self) -> None:
        """Store current state so next mutating operation can be reverted."""
        self._undo_stack.append(self._snapshot_state())

    def can_undo(self) -> bool:
        """Return True when at least one previous state is available."""
        return len(self._undo_stack) > 0

    def undo_last_action(self) -> bool:
        """
        Revert the tree to the state before the last mutating action.

        Returns:
            bool: True if an action was undone, False if history is empty.
        """
        if not self._undo_stack:
            return False

        snapshot = self._undo_stack.pop()
        tree_data = snapshot.get("tree_data")

        if tree_data is None:
            self.tree.root = None
        else:
            restored_root = self._persistence.deserialize_tree_from_dict(tree_data)
            self.tree.root = restored_root

        self.tree.rotation_count = snapshot.get("rotation_count", self.tree.rotation_count.copy())
        self.tree.cascade_rebalance_count = int(
            snapshot.get("cascade_rebalance_count", self.tree.cascade_rebalance_count)
        )
        self.tree.stress_mode = bool(snapshot.get("stress_mode", self.tree.stress_mode))
        return True

    def set_stress_mode(
        self,
        enabled: bool,
        rebalance_when_disabling: bool = False,
    ) -> None:
        """
        Configure how the managed AVL tree balances insertions.

        Args:
            enabled (bool): ``True`` to defer rotations during insertions,
                ``False`` to restore immediate balancing.
            rebalance_when_disabling (bool): When ``True``, a global rebalance
                is executed automatically when leaving stress mode.
        """
        self.tree.set_stress_mode(
            enabled,
            rebalance_when_disabling=rebalance_when_disabling,
        )

    def global_rebalance(self) -> int:
        """
        Rebalance the entire tree explicitly.

        Returns:
            int: Number of rotations executed during the operation.
        """
        return self.tree.global_rebalance()

    # -----------------------------------------------------------------------
    # ADD
    # -----------------------------------------------------------------------

    def add_flight(
        self,
        flight_code: str,
        origin: str,
        destination: str,
        base_price: float,
        passengers: int = 0,
        promotion: float = 0.0,
        alert: str = "",
        priority: int = 3,
    ) -> FlightNode:
        """
        Create a new FlightNode and insert it into the tree.

        Args:
            flight_code  (str)  : Unique flight identifier.
            origin       (str)  : Departure city.
            destination  (str)  : Arrival city.
            base_price   (float): Base ticket price (must be >= 0).
            passengers   (int)  : Initial passenger count (must be >= 0).
            promotion    (float): Discount value (0.0 – 1.0 inclusive).
            alert        (str)  : Optional alert message.
            priority     (int)  : Priority level 1–5.

        Returns:
            FlightNode: The newly inserted node.

        Raises:
            ValueError: If any argument fails validation.
            KeyError:   If the flight code already exists in the tree.
        """
        self._validate_flight_code(flight_code)
        self._validate_origin_destination(origin, destination)
        self._validate_base_price(base_price)
        self._validate_passengers(passengers)
        self._validate_promotion(promotion)
        self._validate_priority(priority)

        # Ensure code is not already present
        if self.tree.root is not None:
            existing = self.tree.search(flight_code)
            if existing is not None:
                raise KeyError(
                    f"Flight code '{flight_code}' already exists in the tree."
                )

        node = FlightNode(
            flight_code=flight_code.strip().upper(),
            origin=origin.strip(),
            destination=destination.strip(),
            base_price=base_price,
            passengers=passengers,
            promotion=promotion,
            alert=alert.strip(),
            priority=priority,
        )
        node.final_price = self._compute_final_price(base_price, promotion)

        self._push_undo_state()
        self.tree.insert(node)
        return node

    # -----------------------------------------------------------------------
    # DELETE
    # -----------------------------------------------------------------------

    def delete_flight(self, flight_code: str) -> bool:
        """
        Remove a flight from the tree.

        Args:
            flight_code (str): Code of the flight to delete.

        Returns:
            bool: True if the flight was found and deleted.

        Raises:
            ValueError: If flight_code is blank.
            KeyError:   If the flight code does not exist in the tree.
        """
        self._validate_flight_code(flight_code)
        code = flight_code.strip().upper()

        if self.tree.root is None or self.tree.search(code) is None:
            raise KeyError(f"Flight '{code}' not found in the tree.")

        self._push_undo_state()
        return self.tree.delete(code)

    # -----------------------------------------------------------------------
    # UPDATE
    # -----------------------------------------------------------------------

    def update_flight(self, flight_code: str, **fields: Any) -> FlightNode:
        """
        Modify one or more fields of an existing flight node.

        Non-key fields are updated in-place.  If ``new_flight_code`` is
        supplied the node is deleted and re-inserted under the new code so that
        BST ordering is preserved.

        Updatable fields (keyword arguments):
            new_flight_code (str)   : Rename the primary key.
            origin          (str)
            destination     (str)
            base_price      (float) : Recomputes final_price automatically.
            final_price     (float) : Override final price directly.
            passengers      (int)
            promotion       (float) : Recomputes final_price automatically.
            alert           (str)
            priority        (int)

        Args:
            flight_code (str): Code of the flight to update.
            **fields:         Keyword arguments with the new values.

        Returns:
            FlightNode: The updated node (may be a new object if code changed).

        Raises:
            ValueError: If a field value fails validation.
            KeyError:   If the flight is not found, or the new code is taken.
        """
        if not fields:
            raise ValueError("No fields provided for update.")

        self._validate_flight_code(flight_code)
        code = flight_code.strip().upper()

        node = self._require_node(code)

        unknown = set(fields) - _UPDATABLE_FIELDS - {"new_flight_code"}
        if unknown:
            raise ValueError(f"Unknown field(s): {', '.join(sorted(unknown))}")

        # ---- validate supplied values before mutating anything --------------
        if "new_flight_code" in fields:
            new_code = fields["new_flight_code"]
            self._validate_flight_code(new_code)
            new_code = new_code.strip().upper()
            if new_code != code and self.tree.root is not None:
                if self.tree.search(new_code) is not None:
                    raise KeyError(
                        f"Cannot rename: flight code '{new_code}' already exists."
                    )

        if "base_price" in fields:
            self._validate_base_price(fields["base_price"])
        if "passengers" in fields:
            self._validate_passengers(fields["passengers"])
        if "promotion" in fields:
            self._validate_promotion(fields["promotion"])
        if "priority" in fields:
            self._validate_priority(fields["priority"])
        if "origin" in fields and "destination" in fields:
            self._validate_origin_destination(fields["origin"], fields["destination"])

        # ---- apply non-key field changes -----------------------------------
        self._push_undo_state()

        if "origin" in fields:
            node.origin = fields["origin"].strip()
        if "destination" in fields:
            node.destination = fields["destination"].strip()
        if "passengers" in fields:
            node.passengers = int(fields["passengers"])
        if "promotion" in fields:
            node.promotion = float(fields["promotion"])
        if "alert" in fields:
            node.alert = str(fields["alert"]).strip()
        if "priority" in fields:
            node.priority = int(fields["priority"])

        # base_price / final_price interact – handle together
        if "base_price" in fields:
            node.base_price = float(fields["base_price"])
            node.final_price = self._compute_final_price(
                node.base_price, node.promotion
            )
        if "final_price" in fields:
            node.final_price = float(fields["final_price"])

        # ---- handle key rename (delete + re-insert) ------------------------
        if "new_flight_code" in fields:
            new_code = fields["new_flight_code"].strip().upper()
            if new_code != code:
                # Capture current data before deletion
                snapshot = node.to_dict()
                snapshot["flight_code"] = new_code

                self.tree.delete(code)

                renamed_node = FlightNode.from_dict(snapshot)
                # Reset tree-structure fields so insert sets them correctly
                renamed_node.height = 0
                renamed_node.balance_factor = 0
                renamed_node.left = None
                renamed_node.right = None
                renamed_node.parent = None

                self.tree.insert(renamed_node)
                return renamed_node

        return node

    # -----------------------------------------------------------------------
    # CANCEL
    # -----------------------------------------------------------------------

    def cancel_flight(self, flight_code: str) -> int:
        """
        Cancel a flight by removing its entire subtree.

        Cancellation differs from single-node deletion: this operation removes
        the matching node and all of its descendants, then triggers AVL
        rebalancing from the detached subtree parent.

        Args:
            flight_code (str): Code of the flight to cancel.

        Returns:
            int: Number of removed nodes.

        Raises:
            ValueError: If flight_code is blank.
            KeyError:   If the flight is not found.
        """
        self._validate_flight_code(flight_code)
        code = flight_code.strip().upper()

        self._require_node(code)
        self._push_undo_state()
        return self.tree.delete_subtree(code)

    # -----------------------------------------------------------------------
    # HELPERS
    # -----------------------------------------------------------------------

    def get_flight(self, flight_code: str) -> Optional[FlightNode]:
        """
        Return the FlightNode for *flight_code*, or None if not present.

        Args:
            flight_code (str): Flight code to look up.

        Returns:
            FlightNode | None
        """
        self._validate_flight_code(flight_code)
        if self.tree.root is None:
            return None
        return self.tree.search(flight_code.strip().upper())

    # -----------------------------------------------------------------------
    # INTERNAL VALIDATORS
    # -----------------------------------------------------------------------

    def _require_node(self, code: str) -> FlightNode:
        """Return the node or raise KeyError."""
        if self.tree.root is None:
            raise KeyError("The tree is empty.")
        node = self.tree.search(code)
        if node is None:
            raise KeyError(f"Flight '{code}' not found in the tree.")
        return node

    @staticmethod
    def _validate_flight_code(code: str) -> None:
        if not isinstance(code, str) or not code.strip():
            raise ValueError("Flight code must be a non-empty string.")

    @staticmethod
    def _validate_origin_destination(origin: str, destination: str) -> None:
        if not isinstance(origin, str) or not origin.strip():
            raise ValueError("Origin must be a non-empty string.")
        if not isinstance(destination, str) or not destination.strip():
            raise ValueError("Destination must be a non-empty string.")

    @staticmethod
    def _validate_base_price(price: float) -> None:
        if not isinstance(price, (int, float)) or price < 0:
            raise ValueError("Base price must be a non-negative number.")

    @staticmethod
    def _validate_passengers(count: int) -> None:
        if not isinstance(count, int) or count < 0:
            raise ValueError("Passengers must be a non-negative integer.")

    @staticmethod
    def _validate_promotion(promo: float) -> None:
        if not isinstance(promo, (int, float)) or not (0.0 <= float(promo) <= 1.0):
            raise ValueError("Promotion must be a float between 0.0 and 1.0.")

    @staticmethod
    def _validate_priority(priority: int) -> None:
        if not isinstance(priority, int) or not (1 <= priority <= 5):
            raise ValueError("Priority must be an integer between 1 and 5.")

    @staticmethod
    def _compute_final_price(base_price: float, promotion: float) -> float:
        """Apply promotion discount to base price."""
        return round(base_price * (1.0 - promotion), 2)
