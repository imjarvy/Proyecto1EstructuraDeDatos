"""
AVL Tree implementation for SkyBalance Flight Management System.

This class implements a self-balancing AVL tree structure adapted from the
classroom implementation to work with FlightNode objects and integrate with
the DataStorage persistence system.
"""

from typing import Optional, List, Dict, Any
from src.modelos.FlightNode import FlightNode


class AVLTree:
    """
    Self-balancing AVL Tree for managing flight nodes.
    
    Maintains AVL property where balance factor of every node is in {-1, 0, 1}.
    Automatically rebalances after insertions and deletions.
    
    Attributes:
        root (FlightNode): Root node of the AVL tree
        rotation_count (Dict): Counter for rotation types (LL, RR, LR, RL)
        cascade_rebalance_count (int): Count of cascade rebalancing operations
        stress_mode (bool): Whether insertions defer rotations until a global rebalance
    """
    
    def __init__(self, stress_mode: bool = False):
        """
        Initialize an empty AVL tree.

        Args:
            stress_mode (bool): When True, insertions update metadata but skip
                rotations until a global rebalance is requested.
        """
        self.root: Optional[FlightNode] = None
        self.rotation_count = {"LL": 0, "RR": 0, "LR": 0, "RL": 0}
        self.cascade_rebalance_count = 0
        self.stress_mode = stress_mode
    
    # ============================================================================
    # INSERTION OPERATIONS
    # ============================================================================
    
    def insert(self, flight_node: FlightNode) -> FlightNode:
        """
        Insert a flight node into the AVL tree.

        In normal mode the tree is rebalanced immediately after the insertion.
        In stress mode only heights and balance factors are refreshed; rotations
        are deferred until ``global_rebalance`` is called.
        
        Args:
            flight_node (FlightNode): Node to insert.
            
        Returns:
            FlightNode: The inserted node.
        """
        if self.root is None:
            self.root = flight_node
            flight_node.height = 0
            flight_node.balance_factor = 0
        else:
            self._insert_recursive(self.root, flight_node)
        
        return flight_node
    
    def _insert_recursive(self, current: FlightNode, new_node: FlightNode) -> None:
        """
        Recursively insert a node while preserving BST ordering.

        Once the new node is linked, the method either performs AVL rebalancing
        immediately or only refreshes node metadata, depending on the current
        operating mode.
        
        Args:
            current (FlightNode): Current node being evaluated.
            new_node (FlightNode): Node to be inserted.
        """
        if new_node.flight_code == current.flight_code:
            print(f"Flight code {new_node.flight_code} already exists in tree.")
            return
        
        if new_node.flight_code < current.flight_code:
            if current.left is None:
                current.left = new_node
                new_node.parent = current
                if self.stress_mode:
                    self._refresh_metadata_upwards(current)
                else:
                    self._check_balance(current)
            else:
                self._insert_recursive(current.left, new_node)
        else:
            if current.right is None:
                current.right = new_node
                new_node.parent = current
                if self.stress_mode:
                    self._refresh_metadata_upwards(current)
                else:
                    self._check_balance(current)
            else:
                self._insert_recursive(current.right, new_node)

    def set_stress_mode(self, enabled: bool, rebalance_when_disabling: bool = False) -> None:
        """
        Enable or disable stress mode for future insertions.

        Args:
            enabled (bool): ``True`` to defer rotations on insert, ``False`` to
                restore immediate balancing.
            rebalance_when_disabling (bool): When ``True`` and the tree leaves
                stress mode, ``global_rebalance`` is executed before returning.
        """
        was_stress_mode = self.stress_mode
        self.stress_mode = enabled

        if was_stress_mode and not enabled and rebalance_when_disabling:
            self.global_rebalance()

    # ============================================================================
    # SEARCH OPERATIONS
    # ============================================================================
    
    def search(self, flight_code: str) -> Optional[FlightNode]:
        """
        Search for a node by flight code.
        
        Args:
            flight_code (str): Flight code to search.
            
        Returns:
            FlightNode: Found node, or None if not found.
        """
        if self.root is None:
            raise Exception("Tree is empty.")
        
        return self._search_recursive(self.root, flight_code)
    
    def _search_recursive(self, current: Optional[FlightNode], flight_code: str) -> Optional[FlightNode]:
        """
        Recursively search for a node.
        
        Args:
            current (FlightNode): Current node being evaluated.
            flight_code (str): Flight code to search.
            
        Returns:
            FlightNode: Found node, or None if not found.
        """
        if current is None:
            return None
        
        if current.flight_code == flight_code:
            return current
        elif flight_code < current.flight_code:
            return self._search_recursive(current.left, flight_code)
        else:
            return self._search_recursive(current.right, flight_code)
    
    # ============================================================================
    # TRAVERSAL OPERATIONS
    # ============================================================================
    
    def breadth_first_search(self) -> List[FlightNode]:
        """
        Breadth-first traversal (level order).
        
        Returns:
            List[FlightNode]: Nodes in breadth-first order.
        """
        if self.root is None:
            raise Exception("Tree is empty.")
        
        queue = [self.root]
        result = []
        
        while len(queue) > 0:
            current_node = queue.pop(0)
            result.append(current_node)
            
            if current_node.left is not None:
                queue.append(current_node.left)
            
            if current_node.right is not None:
                queue.append(current_node.right)
        
        return result
    
    def pre_order_traversal(self) -> List[FlightNode]:
        """
        Pre-order traversal (depth-first).
        
        Returns:
            List[FlightNode]: Nodes in pre-order sequence.
        """
        if self.root is None:
            raise Exception("Tree is empty.")
        
        result = []
        self._pre_order_traversal_recursive(self.root, result)
        return result
    
    def _pre_order_traversal_recursive(self, current: Optional[FlightNode], result: List[FlightNode]) -> None:
        """
        Recursively perform pre-order traversal.

        Args:
            current (FlightNode): Current subtree root.
            result (List[FlightNode]): Accumulator list for visited nodes.
        """
        if current is None:
            return
        
        result.append(current)
        
        if current.left is not None:
            self._pre_order_traversal_recursive(current.left, result)
        
        if current.right is not None:
            self._pre_order_traversal_recursive(current.right, result)
    
    def in_order_traversal(self) -> List[FlightNode]:
        """
        In-order traversal (depth-first).
        
        Returns:
            List[FlightNode]: Nodes in in-order sequence.
        """
        if self.root is None:
            raise Exception("Tree is empty.")
        
        result = []
        self._in_order_traversal_recursive(self.root, result)
        return result
    
    def _in_order_traversal_recursive(self, current: Optional[FlightNode], result: List[FlightNode]) -> None:
        """
        Recursively perform in-order traversal.

        Args:
            current (FlightNode): Current subtree root.
            result (List[FlightNode]): Accumulator list for visited nodes.
        """
        if current is None:
            return
        
        if current.left is not None:
            self._in_order_traversal_recursive(current.left, result)
        
        result.append(current)
        
        if current.right is not None:
            self._in_order_traversal_recursive(current.right, result)
    
    def post_order_traversal(self) -> List[FlightNode]:
        """
        Post-order traversal (depth-first).
        
        Returns:
            List[FlightNode]: Nodes in post-order sequence.
        """
        if self.root is None:
            raise Exception("Tree is empty.")
        
        result = []
        self._post_order_traversal_recursive(self.root, result)
        return result
    
    def _post_order_traversal_recursive(self, current: Optional[FlightNode], result: List[FlightNode]) -> None:
        """
        Recursively perform post-order traversal.

        Args:
            current (FlightNode): Current subtree root.
            result (List[FlightNode]): Accumulator list for visited nodes.
        """
        if current is None:
            return
        
        if current.left is not None:
            self._post_order_traversal_recursive(current.left, result)
        
        if current.right is not None:
            self._post_order_traversal_recursive(current.right, result)
        
        result.append(current)
    
    # ============================================================================
    # TREE METRICS
    # ============================================================================
    
    def get_height(self, node: Optional[FlightNode]) -> int:
        """
        Calculate height of a node.
        
        Args:
            node (FlightNode): Node to calculate height for.
            
        Returns:
            int: Height (0 if None).
        """
        if node is None:
            return -1 
        return node.height
    
    def get_node_height(self, flight_code: str) -> int:
        """
        Get height of a specific node by flight code.
        
        Args:
            flight_code (str): Flight code to search.
            
        Returns:
            int: Height of the node, or -1 if not found.
        """
        node = self.search(flight_code)
        return self._calculate_node_height(node) if node else -1
    
    def _calculate_node_height(self, node: Optional[FlightNode]) -> int:
        """
        Recursively calculate actual height of a node.
        
        Args:
            node (FlightNode): Node to calculate height for.
            
        Returns:
            int: Calculated height.
        """
        if node is None:
            return -1
        
        left_height = self._calculate_node_height(node.left)
        right_height = self._calculate_node_height(node.right)
        return max(left_height, right_height) + 1
    
    def get_tree_height(self) -> int:
        """
        Get height of entire tree.
        
        Returns:
            int: Height of the tree.
        """
        if self.root is None:
            raise Exception("Tree is empty.")
        
        return self._calculate_node_height(self.root)
    
    def get_tree_weight(self) -> int:
        """
        Get total number of nodes in tree.
        
        Returns:
            int: Node count.
        """
        return len(self.breadth_first_search()) if self.root else 0
    
    def get_leaf_count(self, node: Optional[FlightNode]) -> int:
        """
        Count leaf nodes in subtree.
        
        Args:
            node (FlightNode): Root of subtree.
            
        Returns:
            int: Number of leaf nodes.
        """
        if node is None:
            return 0
        
        if node.left is None and node.right is None:
            return 1
        
        return self.get_leaf_count(node.left) + self.get_leaf_count(node.right)
    
    def get_node_depth(self, flight_code: str) -> int:
        """
        Get depth of a specific node (distance from root).
        
        Args:
            flight_code (str): Flight code to search.
            
        Returns:
            int: Depth of the node, or -1 if not found.
        """
        node = self.search(flight_code)
        if node is None:
            return -1
        
        return self._calculate_node_depth(node, 0)
    
    def _calculate_node_depth(self, node: Optional[FlightNode], count: int) -> int:
        """
        Recursively calculate node depth.
        
        Args:
            node (FlightNode): Current node.
            count (int): Current depth counter.
            
        Returns:
            int: Calculated depth.
        """
        if node is None:
            return -1

        if node is self.root:
            return count
        
        return self._calculate_node_depth(node.parent, count + 1)
    
    def get_properties(self) -> Dict[str, Any]:
        """
        Get tree properties.
        
        Returns:
            Dict: Tree metadata (root, height, leaf count, node count, rotations).
        """
        if self.root is None:
            return {
                "tree_type": "AVL",
                "root": None,
                "height": 0,
                "leaf_count": 0,
                "node_count": 0,
                "total_rotations": sum(self.rotation_count.values()),
                "rotation_breakdown": self.rotation_count.copy(),
                "stress_mode": self.stress_mode
            }
        
        return {
            "tree_type": "AVL",
            "root": self.root.flight_code,
            "height": self.get_tree_height(),
            "leaf_count": self.get_leaf_count(self.root),
            "node_count": self.get_tree_weight(),
            "total_rotations": sum(self.rotation_count.values()),
            "rotation_breakdown": self.rotation_count.copy(),
            "stress_mode": self.stress_mode
        }
    
    # ============================================================================
    # DELETION OPERATIONS
    # ============================================================================
    
    def delete(self, flight_code: str) -> bool:
        """
        Delete a node by flight code.
        
        Args:
            flight_code (str): Flight code of node to delete.
            
        Returns:
            bool: True if deletion successful, False otherwise.
        """
        if self.root is None:
            print("Tree is empty.")
            return False
        
        node = self.search(flight_code)
        if node is None:
            print(f"Flight {flight_code} not found in tree.")
            return False
        
        self._delete_node(node)
        return True
    
    def _delete_node(self, node: FlightNode) -> None:
        """
        Delete a specific node from tree.
        
        Args:
            node (FlightNode): Node to delete.
        """
        deletion_case = self._identify_deletion_case(node)
        
        if deletion_case == 1:
            self._delete_leaf_node(node)
        elif deletion_case == 2:
            self._delete_one_child_node(node)
        elif deletion_case == 3:
            self._delete_two_child_node(node)

    def delete_subtree(self, flight_code: str) -> int:
        """
        Delete a node and its entire descendant subtree.

        This operation is used for flight cancellation rules where the selected
        flight and all dependent flights below it must be removed together.

        Args:
            flight_code (str): Root code of the subtree to remove.

        Returns:
            int: Number of removed nodes (0 when code is not found).
        """
        if self.root is None:
            print("Tree is empty.")
            return 0

        target = self.search(flight_code)
        if target is None:
            print(f"Flight {flight_code} not found in tree.")
            return 0

        removed_count = self._count_subtree_nodes(target)
        parent = target.parent

        if parent is None:
            self.root = None
        else:
            if parent.left is target:
                parent.left = None
            else:
                parent.right = None
            self._check_balance(parent)

        target.parent = None
        return removed_count

    def _count_subtree_nodes(self, node: Optional[FlightNode]) -> int:
        """
        Count total nodes in a subtree.

        Args:
            node (FlightNode): Subtree root.

        Returns:
            int: Number of nodes in the subtree.
        """
        if node is None:
            return 0

        return 1 + self._count_subtree_nodes(node.left) + self._count_subtree_nodes(node.right)
    
    def _identify_deletion_case(self, node: FlightNode) -> int:
        """
        Identify which deletion case applies to a node.
        
        Returns:
            int: Case number (1: leaf, 2: one child, 3: two children).
        """
        if node.left is None and node.right is None:
            return 1  # Leaf node
        elif node.left is not None and node.right is not None:
            return 3  # Two children
        else:
            return 2  # One child
    
    def _delete_leaf_node(self, node: FlightNode) -> None:
        """
        Delete a node that has no children.

        Args:
            node (FlightNode): Leaf node to remove.
        """
        if node.parent is None:
            self.root = None
        else:
            if node.parent.left is node:
                node.parent.left = None
            else:
                node.parent.right = None
            
            self._check_balance(node.parent)
    
    def _delete_one_child_node(self, node: FlightNode) -> None:
        """
        Delete a node that has exactly one child.

        The child takes the deleted node's place and the tree is rechecked for
        balance from the former parent.

        Args:
            node (FlightNode): Node to remove.
        """
        child_node = node.left if node.left is not None else node.right
        assert child_node is not None
        
        if node.parent is None:
            self.root = child_node
            child_node.parent = None
        else:
            if node.parent.left is node:
                node.parent.left = child_node
            else:
                node.parent.right = child_node
            
            child_node.parent = node.parent
            self._check_balance(node.parent)
    
    def _delete_two_child_node(self, node: FlightNode) -> None:
        """
        Delete a node that has two children.

        The in-order predecessor is copied into the target node and then the
        predecessor is removed as a simpler leaf/one-child case.

        Args:
            node (FlightNode): Node to remove.
        """
        # Find predecessor (rightmost in left subtree)
        predecessor = node.left
        assert predecessor is not None
        while predecessor.right is not None:
            predecessor = predecessor.right
        
        # Copy predecessor data to current node
        node.flight_code = predecessor.flight_code
        node.origin = predecessor.origin
        node.destination = predecessor.destination
        node.base_price = predecessor.base_price
        node.final_price = predecessor.final_price
        node.passengers = predecessor.passengers
        node.promotion = predecessor.promotion
        node.alert = predecessor.alert
        node.priority = predecessor.priority
        
        # Delete the predecessor
        if predecessor.left is None:
            self._delete_leaf_node(predecessor)
        else:
            self._delete_one_child_node(predecessor)
    
    # ============================================================================
    # BALANCE OPERATIONS
    # ============================================================================
    
    def _check_balance(self, node: Optional[FlightNode]) -> None:
        """
        Check and rebalance tree starting from a node.
        
        Args:
            node (FlightNode): Node to start balance check from.
        """
        if node is None: return
        self._check_balance_recursive(node) 

    def _refresh_node_metadata(self, node: FlightNode) -> None:
        """
        Recompute height and balance factor for a single node.

        Args:
            node (FlightNode): Node whose cached metadata will be updated.
        """
        left_height = self.get_height(node.left)
        right_height = self.get_height(node.right)
        node.height = max(left_height, right_height) + 1
        node.balance_factor = left_height - right_height

    def _refresh_metadata_upwards(self, node: Optional[FlightNode]) -> None:
        """
        Refresh metadata from a node up to the root without rotating.

        This is used in stress mode so the tree still reports correct heights
        and balance factors even though structural balancing is postponed.

        Args:
            node (FlightNode): Starting node for the upward refresh.
        """
        current = node
        while current is not None:
            self._refresh_node_metadata(current)
            current = current.parent

    def _check_balance_recursive(self, node: Optional[FlightNode]) -> None:
        """
        Recursively check and fix balance factors.
        
        Args:
            node (FlightNode): Current node being checked.
        """
        if node is None:
            return
        
        self._refresh_node_metadata(node)
        bf = node.balance_factor
        
        # Check if rebalancing needed
        if bf > 1 or bf < -1:
            balance_case = self._get_balance_case(node, bf)
            
            if balance_case == "LL":
                self._rotate_right(node)
            elif balance_case == "RR":
                self._rotate_left(node)
            elif balance_case == "LR":
                left_child = node.left
                assert left_child is not None
                self._rotate_left(left_child)
                self._rotate_right(node)
            elif balance_case == "RL":
                right_child = node.right
                assert right_child is not None
                self._rotate_right(right_child)
                self._rotate_left(node)
        
        # Check parent balance
        if node.parent is not None:
            self._check_balance_recursive(node.parent)
    
    def _get_balance_factor(self, node: Optional[FlightNode]) -> int:
        """
        Calculate balance factor of a node.
        
        Args:
            node (FlightNode): Node to calculate balance factor for.
            
        Returns:
            int: Balance factor (left_height - right_height).
        """
        if node is None:
            return 0
        
        left_height = self.get_height(node.left)
        right_height = self.get_height(node.right)
        return left_height - right_height
    
    def _get_balance_case(self, node: FlightNode, bf: int) -> str:
        """
        Identify balance case (LL, RR, LR, RL).
        
        Args:
            node (FlightNode): Unbalanced node.
            bf (int): Balance factor.
            
        Returns:
            str: Balance case identifier.
        """
        if bf < -1:  # Right heavy
            bf_child = self._get_balance_factor(node.right)
            if bf_child < 0:
                bf_case = "RR"
            else:
                bf_case = "RL"
        else:  # Left heavy
            bf_child = self._get_balance_factor(node.left)
            if bf_child > 0:
                bf_case = "LL"
            else:
                bf_case = "LR"
        return bf_case
    
    # ============================================================================
    # ROTATION OPERATIONS
    # ============================================================================
    
    def _rotate_right(self, top_node: FlightNode) -> None:
        """
        Perform right rotation.
        
        Args:
            top_node (FlightNode): Node to rotate right.
        """
        middle_node = top_node.left
        assert middle_node is not None
        parent_top_node = top_node.parent
        right_child_of_middle = middle_node.right
        
        # Move top node as right child of middle node
        middle_node.right = top_node
        top_node.parent = middle_node
        
        # Update parent pointer
        if parent_top_node is None:
            self.root = middle_node
            middle_node.parent = None
        else:
            if parent_top_node.left == top_node:
                parent_top_node.left = middle_node
            else:
                parent_top_node.right = middle_node
            middle_node.parent = parent_top_node
        
        # Rearrange child pointers
        top_node.left = right_child_of_middle
        if right_child_of_middle is not None:
            right_child_of_middle.parent = top_node
        
        # Update heights
        top_node.height = max(self.get_height(top_node.left), self.get_height(top_node.right)) + 1
        middle_node.height = max(self.get_height(middle_node.left), self.get_height(middle_node.right)) + 1
        
        top_node.balance_factor = self._get_balance_factor(top_node)
        middle_node.balance_factor = self._get_balance_factor(middle_node)

        self.rotation_count["LL"] += 1
    
    def _rotate_left(self, top_node: FlightNode) -> None:
        """
        Perform left rotation.
        
        Args:
            top_node (FlightNode): Node to rotate left.
        """
        middle_node = top_node.right
        assert middle_node is not None
        parent_top_node = top_node.parent
        left_child_of_middle = middle_node.left
        
        # Move top node as left child of middle node
        middle_node.left = top_node
        top_node.parent = middle_node
        
        # Update parent pointer
        if parent_top_node is None:
            self.root = middle_node
            middle_node.parent = None
        else:
            if parent_top_node.left == top_node:
                parent_top_node.left = middle_node
            else:
                parent_top_node.right = middle_node
            middle_node.parent = parent_top_node
        
        # Rearrange child pointers
        top_node.right = left_child_of_middle
        if left_child_of_middle is not None:
            left_child_of_middle.parent = top_node
        
        # Update heights
        top_node.height = max(self.get_height(top_node.left), self.get_height(top_node.right)) + 1
        middle_node.height = max(self.get_height(middle_node.left), self.get_height(middle_node.right)) + 1
        
        top_node.balance_factor = self._get_balance_factor(top_node)
        middle_node.balance_factor = self._get_balance_factor(middle_node)

        self.rotation_count["RR"] += 1
    
    # ============================================================================
    # GLOBAL REBALANCING (STRESS MODE)
    # ============================================================================
    
    def global_rebalance(self) -> int:
        """
        Perform global rebalancing on entire tree.
        
        Used when exiting stress mode to fix all imbalances.
        
        Returns:
            int: Number of rotations performed during rebalancing.
        """
        if self.root is None:
            return 0
        
        initial_rotation_count = sum(self.rotation_count.values())

        while any(abs(n.balance_factor) > 1 for n in self.breadth_first_search()):
            self.cascade_rebalance_count += 1
            self._global_rebalance_recursive(self.root)

        final_rotation_count = sum(self.rotation_count.values())
        
        return final_rotation_count - initial_rotation_count
    
    def _global_rebalance_recursive(self, node: Optional[FlightNode]) -> None:
        """
        Recursively rebalance entire subtree.
        
        Args:
            node (FlightNode): Current node being processed.
        """
        if node is None:
            return
        
        # Process left subtree
        if node.left is not None:
            self._global_rebalance_recursive(node.left)
        
        # Process right subtree
        if node.right is not None:
            self._global_rebalance_recursive(node.right)
        
        # Check and fix balance at this node
        self._refresh_node_metadata(node)
        bf = node.balance_factor
        
        if bf > 1 or bf < -1:
            balance_case = self._get_balance_case(node, bf)
            
            if balance_case == "LL":
                self._rotate_right(node)
            elif balance_case == "RR":
                self._rotate_left(node)
            elif balance_case == "LR":
                left_child = node.left
                assert left_child is not None
                self._rotate_left(left_child)
                self._rotate_right(node)
            elif balance_case == "RL":
                right_child = node.right
                assert right_child is not None
                self._rotate_right(right_child)
                self._rotate_left(node)
