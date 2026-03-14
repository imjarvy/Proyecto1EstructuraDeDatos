"""
Binary Search Tree (BST) implementation for SkyBalance Flight Management System.

This is a simplified BST used for comparison purposes with the AVL tree.
It maintains all flight nodes without automatic balancing.

Only insertion and visualization are supported (no deletion).
"""

from typing import Optional, List, Dict, Any
from src.modelos.FlightNode import FlightNode


class BST:
    """
    Basic Binary Search Tree for flight management.
    
    This BST is used to compare performance and structure with the AVL tree.
    It does NOT perform automatic balancing, allowing visual comparison with AVL.
    
    Attributes:
        root (FlightNode): Root node of the BST.
    """
    
    def __init__(self):
        """Initialize empty BST."""
        self.root: Optional[FlightNode] = None
    
    # ============================================================================
    # INSERTION OPERATIONS
    # ============================================================================
    
    def insert(self, flight_node: FlightNode) -> FlightNode:
        """
        Insert a flight node into the BST.
        
        No balancing is performed. The tree structure depends entirely on
        insertion order.
        
        Args:
            flight_node (FlightNode): Node to insert.
            
        Returns:
            FlightNode: The inserted node.
        """
        if self.root is None:
            self.root = flight_node
            flight_node.height = 0
        else:
            self._insert_recursive(self.root, flight_node)
        
        return flight_node
    
    def _insert_recursive(self, current: FlightNode, new_node: FlightNode) -> None:
        """
        Recursively insert node maintaining BST property.
        
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
                self._update_height(current)
            else:
                self._insert_recursive(current.left, new_node)
        else:
            if current.right is None:
                current.right = new_node
                new_node.parent = current
                self._update_height(current)
            else:
                self._insert_recursive(current.right, new_node)
    
    def _update_height(self, node: Optional[FlightNode]) -> None:
        """
        Update height of a node and propagate up the tree.
        
        Args:
            node (FlightNode): Node to update height for.
        """
        if node is None:
            return
        
        # Update current node height
        left_height = self._get_height(node.left)
        right_height = self._get_height(node.right)
        node.height = max(left_height, right_height) + 1
        
        # Propagate up
        if node.parent is not None:
            self._update_height(node.parent)
    
    def _get_height(self, node: Optional[FlightNode]) -> int:
        """
        Get height of a node.
        
        Args:
            node (FlightNode): Node to get height for.
            
        Returns:
            int: Height (-1 if None).
        """
        if node is None:
            return -1
        return node.height
    
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
    
    # ============================================================================
    # TREE METRICS
    # ============================================================================
    
    def get_tree_height(self) -> int:
        """
        Get height of entire tree.
        
        Returns:
            int: Height of the tree.
        """
        if self.root is None:
            return 0
        
        return self._calculate_height(self.root)
    
    def _calculate_height(self, node: Optional[FlightNode]) -> int:
        """
        Recursively calculate actual height of a node.
        
        Args:
            node (FlightNode): Node to calculate height for.
            
        Returns:
            int: Calculated height.
        """
        if node is None:
            return -1
        
        left_height = self._calculate_height(node.left)
        right_height = self._calculate_height(node.right)
        return max(left_height, right_height) + 1
    
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
    
    def get_properties(self) -> Dict[str, Any]:
        """
        Get tree properties.
        
        Returns:
            Dict: Tree metadata (root, height, leaf count, node count).
        """
        if self.root is None:
            return {
                "tree_type": "BST",
                "root": None,
                "height": 0,
                "leaf_count": 0,
                "node_count": 0
            }
        
        return {
            "tree_type": "BST",
            "root": self.root.flight_code,
            "height": self.get_tree_height(),
            "leaf_count": self.get_leaf_count(self.root),
            "node_count": self.get_tree_weight()
        }
        