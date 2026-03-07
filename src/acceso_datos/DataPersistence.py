"""
DataPersistence module for the SkyBalance AVL Flight Management System.

This module handles exporting tree structures to JSON, maintaining the
hierarchical structure with all node properties.
"""

import json
from typing import Optional, Dict, Any
from src.modelos.FlightNode import FlightNode


class DataPersistence:
    """
    Handles serialization and persistence of tree structures to JSON format.
    
    Ensures complete hierarchy preservation including heights, balance factors,
    and all flight attributes.
    """
    
    def __init__(self):
        """Initialize the DataPersistence module."""
        self.last_export_path = None
    
    def export_tree_to_json(self, root: Optional[FlightNode], file_path: str) -> bool:
        """
        Export complete tree structure to JSON file.
        
        The exported JSON maintains the hierarchical structure with parent-child
        relationships and all node properties.
        
        Args:
            root (FlightNode): Root node of the tree to export.
            file_path (str): Path where JSON will be saved.
            
        Returns:
            bool: True if export successful, False otherwise.
        """
        if not root:
            print("Error: Root node is None. Cannot export empty tree.")
            return False
        
        try:
            export_data = {
                "root_code": root.flight_code,
                "tree_structure": {}
            }
            
            # Traverse tree and collect all nodes with their relationships
            self._traverse_and_collect(root, export_data["tree_structure"])
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(export_data, file, indent=2, ensure_ascii=False)
            
            self.last_export_path = file_path
            print(f"Successfully exported tree to: {file_path}")
            return True
        
        except IOError as e:
            print(f"Error writing to file: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error during export: {e}")
            return False
    
    def export_tree_topology_only(self, root: Optional[FlightNode], file_path: str) -> bool:
        """
        Export tree structure with minimal data (for topology reconstruction).
        
        Args:
            root (FlightNode): Root node of the tree.
            file_path (str): Path where JSON will be saved.
            
        Returns:
            bool: True if export successful, False otherwise.
        """
        if not root:
            print("Error: Root node is None.")
            return False
        
        try:
            export_data = {
                "root_code": root.flight_code,
                "tree_structure": {}
            }
            
            self._traverse_topology_only(root, export_data["tree_structure"])
            
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(export_data, file, indent=2, ensure_ascii=False)
            
            print(f"Successfully exported topology to: {file_path}")
            return True
        
        except (IOError, Exception) as e:
            print(f"Error exporting topology: {e}")
            return False
    
    def _traverse_and_collect(self, node: FlightNode, tree_dict: Dict[str, Any]):
        """
        Recursively traverse tree and collect node data with relationships.
        
        Args:
            node (FlightNode): Current node being processed.
            tree_dict (Dict): Dictionary to store node data.
        """
        if not node:
            return
        
        # Create node entry with all flight data
        node_entry = {
            "flight_data": node.to_dict(),
            "left_child": node.left.flight_code if node.left else None,
            "right_child": node.right.flight_code if node.right else None
        }
        
        tree_dict[node.flight_code] = node_entry
        
        # Recursively process children
        if node.left:
            self._traverse_and_collect(node.left, tree_dict)
        
        if node.right:
            self._traverse_and_collect(node.right, tree_dict)
    
    def _traverse_topology_only(self, node: FlightNode, tree_dict: Dict[str, Any]):
        """
        Traverse tree collecting only structure and flight codes.
        
        Args:
            node (FlightNode): Current node being processed.
            tree_dict (Dict): Dictionary to store topology data.
        """
        if not node:
            return
        
        node_entry = {
            "flight_code": node.flight_code,
            "height": node.height,
            "balance_factor": node.balance_factor,
            "left_child": node.left.flight_code if node.left else None,
            "right_child": node.right.flight_code if node.right else None
        }
        
        tree_dict[node.flight_code] = node_entry
        
        if node.left:
            self._traverse_topology_only(node.left, tree_dict)
        
        if node.right:
            self._traverse_topology_only(node.right, tree_dict)
    
    def serialize_tree_for_storage(self, root: Optional[FlightNode]) -> Optional[Dict]:
        """
        Serialize tree structure to dictionary (for in-memory storage).
        
        Args:
            root (FlightNode): Root node of the tree.
            
        Returns:
            dict: Serialized tree structure, or None if tree is empty.
        """
        if not root:
            return None
        
        tree_dict = {}
        self._traverse_and_collect(root, tree_dict)
        
        return {
            "root_code": root.flight_code,
            "tree_structure": tree_dict
        }
    
    def deserialize_tree_from_dict(self, data: Dict) -> Optional[FlightNode]:
        """
        Reconstruct tree from serialized dictionary.
        
        Args:
            data (Dict): Serialized tree data.
            
        Returns:
            FlightNode: Root node of reconstructed tree, or None if failed.
        """
        if not data or "tree_structure" not in data:
            print("Error: Invalid serialized data format.")
            return None
        
        tree_structure = data["tree_structure"]
        root_code = data.get("root_code")
        
        if not root_code:
            print("Error: No root code specified.")
            return None
        
        # Rebuild nodes
        node_map = {}
        for flight_code, node_data in tree_structure.items():
            flight_info = node_data.get("flight_data", {})
            node = FlightNode.from_dict(flight_info)
            node_map[flight_code] = node
        
        # Establish relationships
        root = node_map.get(root_code)
        if not root:
            print(f"Error: Root node '{root_code}' not found in deserialized data.")
            return None
        
        for flight_code, node_data in tree_structure.items():
            current_node = node_map[flight_code]
            
            left_child_code = node_data.get("left_child")
            if left_child_code and left_child_code in node_map:
                current_node.left = node_map[left_child_code]
                current_node.left.parent = current_node
            
            right_child_code = node_data.get("right_child")
            if right_child_code and right_child_code in node_map:
                current_node.right = node_map[right_child_code]
                current_node.right.parent = current_node
        
        return root
    
    def get_tree_metadata(self, root: Optional[FlightNode]) -> Dict[str, Any]:
        """
        Calculate and return tree metadata.
        
        Args:
            root (FlightNode): Root node of the tree.
            
        Returns:
            dict: Dictionary containing tree statistics.
        """
        if not root:
            return {
                "root": None,
                "height": 0,
                "node_count": 0,
                "leaf_count": 0
            }
        
        metadata = {
            "root": root.flight_code,
            "height": root.height,
            "node_count": self._count_nodes(root),
            "leaf_count": self._count_leaves(root)
        }
        
        return metadata
    
    def _count_nodes(self, node: Optional[FlightNode]) -> int:
        """
        Count total number of nodes in tree.
        
        Args:
            node (FlightNode): Current node.
            
        Returns:
            int: Total node count.
        """
        if not node:
            return 0
        
        return 1 + self._count_nodes(node.left) + self._count_nodes(node.right)
    
    def _count_leaves(self, node: Optional[FlightNode]) -> int:
        """
        Count leaf nodes in tree.
        
        Args:
            node (FlightNode): Current node.
            
        Returns:
            int: Total leaf count.
        """
        if not node:
            return 0
        
        if not node.left and not node.right:
            return 1
        
        return self._count_leaves(node.left) + self._count_leaves(node.right)