"""
TreeSerializationManager for rebuilding AVL/BST trees from serialized payloads.
"""

from typing import Optional, Tuple

from src.modelos.AVLTree import AVLTree
from src.modelos.BST import BST
from src.modelos.FlightNode import FlightNode


class TreeSerializationManager:
    """Build tree instances from JSON-compatible dictionaries."""

    def reconstruct_from_topology(self, data: dict) -> Optional[AVLTree]:
        """
        Rebuild an AVL tree from topology-format JSON.

        Expected keys:
            - root_code
            - tree_structure: mapping code -> {
                flight_data, left_child, right_child
              }
        """
        tree_structure = data.get("tree_structure")
        root_code = data.get("root_code")
        if not tree_structure or not root_code:
            return None

        node_map = {}
        for code, entry in tree_structure.items():
            node_map[code] = FlightNode.from_dict(entry["flight_data"])

        root_node = node_map.get(root_code)
        if root_node is None:
            return None

        for code, entry in tree_structure.items():
            current = node_map[code]
            left_code = entry.get("left_child")
            right_code = entry.get("right_child")

            if left_code and left_code in node_map:
                current.left = node_map[left_code]
                node_map[left_code].parent = current
            if right_code and right_code in node_map:
                current.right = node_map[right_code]
                node_map[right_code].parent = current

        avl = AVLTree()
        avl.root = root_node
        return avl

    def reconstruct_from_insertion(self, data: dict) -> Optional[Tuple[AVLTree, BST]]:
        """
        Rebuild AVL and BST by inserting flights one by one.

        Expected key:
            - flights: list[dict]
        """
        flights = data.get("flights", [])
        if not flights:
            return None

        avl = AVLTree()
        bst = BST()

        for flight_data in flights:
            avl.insert(FlightNode.from_dict(flight_data))
            bst.insert(FlightNode.from_dict(flight_data))

        return avl, bst
