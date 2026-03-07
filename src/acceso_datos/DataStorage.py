"""
DataStorage module for the SkyBalance AVL Flight Management System.

Main integration module that coordinates loading, persisting, and versioning
of flight data and tree structures. This is the primary interface for all
data management operations.
"""

from typing import Optional, List, Dict, Tuple
from src.modelos.FlightNode import FlightNode
from src.acceso_datos.DataLoader import DataLoader
from src.acceso_datos.DataPersistence import DataPersistence
from src.acceso_datos.VersionManager import VersionManager


class DataStorage:
    """
    Central data management system for SkyBalance AVL.
    
    Coordinates loading flight data, persisting tree states, and managing
    version control across the entire application.
    """
    
    def __init__(self):
        """Initialize DataStorage with all component modules."""
        self.loader = DataLoader()
        self.persistence = DataPersistence()
        self.version_manager = VersionManager()
        self.current_avl_root = None
        self.current_bst_root = None
    
    # ============================================================================
    # DATA LOADING OPERATIONS
    # ============================================================================
    
    def load_data_from_user_selection(self) -> bool:
        """
        Prompt user to select JSON file and load it.
        
        Returns:
            bool: True if loading successful, False otherwise.
        """
        return self.loader.select_and_load_file()
    
    def load_data_from_path(self, file_path: str) -> bool:
        """
        Load JSON file from specified path.
        
        Args:
            file_path (str): Path to JSON file.
            
        Returns:
            bool: True if loading successful, False otherwise.
        """
        return self.loader.load_from_path(file_path)
    
    def reconstruct_tree_from_topology(self) -> Optional[FlightNode]:
        """
        Reconstruct tree respecting parent-child topology from loaded JSON.
        
        This mode preserves the exact hierarchical structure defined in the JSON.
        The returned root can be used for both AVL and BST visualization.
        
        Returns:
            FlightNode: Root node of reconstructed tree, or None if failed.
        """
        root = self.loader.reconstruct_topology_mode()
        if root:
            self.current_avl_root = root
        return root
    
    def get_flights_for_insertion_mode(self) -> List[FlightNode]:
        """
        Get list of flights for sequential insertion.
        
        In insertion mode, these flights will be inserted one by one into
        both an AVL tree and a BST for comparison purposes.
        
        Returns:
            List[FlightNode]: List of flight nodes ready for insertion.
        """
        flights = self.loader.get_flights_for_insertion()
        return [FlightNode.from_dict(flight.to_dict()) for flight in flights]
    
    def set_current_avl_tree(self, root: Optional[FlightNode]):
        """
        Set the current AVL tree root.
        
        Args:
            root (FlightNode): Root node of the AVL tree.
        """
        self.current_avl_root = root
    
    def set_current_bst_tree(self, root: Optional[FlightNode]):
        """
        Set the current BST root.
        
        Args:
            root (FlightNode): Root node of the BST.
        """
        self.current_bst_root = root
    
    # ============================================================================
    # PERSISTENCE OPERATIONS
    # ============================================================================
    
    def save_avl_tree_to_file(self, file_path: str) -> bool:
        """
        Export current AVL tree to JSON file.
        
        Args:
            file_path (str): Path where JSON will be saved.
            
        Returns:
            bool: True if save successful, False otherwise.
        """
        return self.persistence.export_tree_to_json(self.current_avl_root, file_path)
    
    def save_bst_tree_to_file(self, file_path: str) -> bool:
        """
        Export current BST to JSON file.
        
        Args:
            file_path (str): Path where JSON will be saved.
            
        Returns:
            bool: True if save successful, False otherwise.
        """
        return self.persistence.export_tree_to_json(self.current_bst_root, file_path)
    
    def save_both_trees_to_files(self, avl_path: str, bst_path: str) -> bool:
        """
        Export both AVL and BST trees to separate JSON files.
        
        Args:
            avl_path (str): Path for AVL tree export.
            bst_path (str): Path for BST tree export.
            
        Returns:
            bool: True if both saves successful, False otherwise.
        """
        avl_success = self.persistence.export_tree_to_json(self.current_avl_root, avl_path)
        bst_success = self.persistence.export_tree_to_json(self.current_bst_root, bst_path)
        
        return avl_success and bst_success
    
    def serialize_avl_tree(self) -> Optional[Dict]:
        """
        Serialize AVL tree to dictionary for in-memory storage.
        
        Returns:
            dict: Serialized tree structure, or None if tree is empty.
        """
        return self.persistence.serialize_tree_for_storage(self.current_avl_root)
    
    def serialize_bst_tree(self) -> Optional[Dict]:
        """
        Serialize BST to dictionary for in-memory storage.
        
        Returns:
            dict: Serialized tree structure, or None if tree is empty.
        """
        return self.persistence.serialize_tree_for_storage(self.current_bst_root)
    
    def deserialize_and_load_avl_tree(self, data: Dict) -> Optional[FlightNode]:
        """
        Reconstruct AVL tree from serialized data.
        
        Args:
            data (Dict): Serialized tree data.
            
        Returns:
            FlightNode: Root node of reconstructed tree, or None if failed.
        """
        root = self.persistence.deserialize_tree_from_dict(data)
        if root:
            self.current_avl_root = root
        return root
    
    def deserialize_and_load_bst_tree(self, data: Dict) -> Optional[FlightNode]:
        """
        Reconstruct BST from serialized data.
        
        Args:
            data (Dict): Serialized tree data.
            
        Returns:
            FlightNode: Root node of reconstructed tree, or None if failed.
        """
        root = self.persistence.deserialize_tree_from_dict(data)
        if root:
            self.current_bst_root = root
        return root
    
    # ============================================================================
    # METADATA OPERATIONS
    # ============================================================================
    
    def get_avl_tree_metadata(self) -> Dict:
        """
        Get metadata about current AVL tree.
        
        Returns:
            dict: Tree statistics (root, height, node count, leaf count).
        """
        return self.persistence.get_tree_metadata(self.current_avl_root)
    
    def get_bst_tree_metadata(self) -> Dict:
        """
        Get metadata about current BST.
        
        Returns:
            dict: Tree statistics (root, height, node count, leaf count).
        """
        return self.persistence.get_tree_metadata(self.current_bst_root)
    
    def get_comparison_metadata(self) -> Dict:
        """
        Get side-by-side comparison of AVL vs BST metadata.
        
        Returns:
            dict: Dictionary containing metadata for both trees.
        """
        return {
            "avl": self.get_avl_tree_metadata(),
            "bst": self.get_bst_tree_metadata()
        }
    
    # ============================================================================
    # VERSION MANAGEMENT OPERATIONS
    # ============================================================================
    
    def save_avl_version(self, version_name: str) -> bool:
        """
        Save current AVL tree state as a named version.
        
        Args:
            version_name (str): Descriptive name for this version.
            
        Returns:
            bool: True if save successful, False otherwise.
        """
        return self.version_manager.save_version(self.current_avl_root, version_name)
    
    def restore_avl_version(self, version_name: str) -> Optional[FlightNode]:
        """
        Restore AVL tree from a saved version.
        
        Args:
            version_name (str): Name of version to restore.
            
        Returns:
            FlightNode: Root node of restored tree, or None if failed.
        """
        root = self.version_manager.restore_version(version_name)
        if root:
            self.current_avl_root = root
        return root
    
    def list_avl_versions(self) -> List[str]:
        """
        List all saved AVL tree versions.
        
        Returns:
            List[str]: List of version names.
        """
        return self.version_manager.list_versions()
    
    def get_version_info(self, version_name: str) -> Optional[Dict]:
        """
        Get detailed information about a specific version.
        
        Args:
            version_name (str): Name of version.
            
        Returns:
            dict: Version metadata (timestamp, size, height, etc.).
        """
        return self.version_manager.get_version_info(version_name)
    
    def delete_version(self, version_name: str) -> bool:
        """
        Delete a saved version.
        
        Args:
            version_name (str): Name of version to delete.
            
        Returns:
            bool: True if deletion successful, False otherwise.
        """
        return self.version_manager.delete_version(version_name)
    
    def export_version_to_file(self, version_name: str, file_path: str) -> bool:
        """
        Export a specific version to a JSON file.
        
        Args:
            version_name (str): Name of version to export.
            file_path (str): Path where file will be saved.
            
        Returns:
            bool: True if export successful, False otherwise.
        """
        return self.version_manager.export_version_to_file(version_name, file_path)
    
    def import_version_from_file(self, file_path: str, version_name: str) -> bool:
        """
        Import a previously exported version from file.
        
        Args:
            file_path (str): Path to JSON file.
            version_name (str): Name to assign to imported version.
            
        Returns:
            bool: True if import successful, False otherwise.
        """
        return self.version_manager.import_version_from_file(file_path, version_name)
    
    def get_all_versions_info(self) -> Dict:
        """
        Get information about all saved versions.
        
        Returns:
            dict: Dictionary mapping version names to metadata.
        """
        return self.version_manager.get_all_versions_info()
    
    def clear_all_versions(self) -> bool:
        """
        Clear all saved versions.
        
        Returns:
            bool: True if operation successful.
        """
        return self.version_manager.clear_all_versions()
    
    # ============================================================================
    # UTILITY OPERATIONS
    # ============================================================================
    
    def get_loaded_json_data(self) -> Optional[Dict]:
        """
        Get raw JSON data that was loaded.
        
        Returns:
            dict: Raw JSON data, or None if no data loaded.
        """
        return self.loader.get_raw_data()
    
    def get_current_avl_root(self) -> Optional[FlightNode]:
        """
        Get current AVL tree root.
        
        Returns:
            FlightNode: Current AVL root, or None if not set.
        """
        return self.current_avl_root
    
    def get_current_bst_root(self) -> Optional[FlightNode]:
        """
        Get current BST root.
        
        Returns:
            FlightNode: Current BST root, or None if not set.
        """
        return self.current_bst_root
    
    def clear_all_data(self):
        """
        Clear all loaded data and tree structures.
        """
        self.loader = DataLoader()
        self.current_avl_root = None
        self.current_bst_root = None
        print("All data cleared.")