"""
DataPersistence module.

This module handles exporting tree structures to JSON, maintaining the
hierarchical structure with all node properties.
"""

import json
import os
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
        pass
    
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
            print("Error: la raíz es None. No se puede exportar un árbol vacío.")
            return False
        
        try:
            export_data = self.serialize_tree_for_storage(root)
            if export_data is None:
                print("Error: No se pudo serializar el árbol para la exportación.")
                return False
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(export_data, file, indent=2, ensure_ascii=False)
            
            print(f"Árbol exportado exitosamente a: {file_path}")
            return True
        
        except IOError as e:
            print(f"Error al escribir en el archivo: {e}")
            return False
        except Exception as e:
            print(f"Error inesperado durante la exportación: {e}")
            return False

    def export_tree_to_downloads(
        self,
        root: Optional[FlightNode],
        file_name: str = "skybalance_tree.json",
    ) -> bool:
        """
        Export tree JSON into the current user's Downloads folder.

        Args:
            root (FlightNode): Root node of the tree to export.
            file_name (str): Output filename for the exported JSON.

        Returns:
            bool: True if export successful, False otherwise.
        """
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        base, ext = os.path.splitext(file_name)  
        file_path = os.path.join(downloads_dir, file_name)

        counter = 1
        while os.path.exists(file_path):
            file_path = os.path.join(downloads_dir, f"{base}({counter}){ext}")
            counter += 1
        return self.export_tree_to_json(root, file_path)
    
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
            print("Error: formato de datos serializados inválido.")
            return None
        
        tree_structure = data["tree_structure"]
        root_code = data.get("root_code")
        
        if not root_code:
            print("Error: código de raíz no especificado.")
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

    def count_nodes(self, node: Optional[FlightNode]) -> int:
        """Count total number of nodes in a tree rooted at node."""
        if node is None:
            return 0
        return 1 + self.count_nodes(node.left) + self.count_nodes(node.right)

    def count_leaves(self, node: Optional[FlightNode]) -> int:
        """Count total number of leaf nodes in a tree rooted at node."""
        if node is None:
            return 0
        if node.left is None and node.right is None:
            return 1
        return self.count_leaves(node.left) + self.count_leaves(node.right)