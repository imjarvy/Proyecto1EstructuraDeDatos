"""
VersionManager module for the SkyBalance AVL Flight Management System.

This module manages versioning of tree states, allowing users to save and
restore specific snapshots of the system at different points in time.
"""

import json
from typing import Dict, Optional, List
from datetime import datetime
from src.modelos.FlightNode import FlightNode
from src.acceso_datos.DataPersistence import DataPersistence


class VersionManager:
    """
    Manages version snapshots of tree states.
    
    Allows users to save labeled versions of the tree structure and restore
    them at any point during operation.
    """
    
    def __init__(self):
        """Initialize the VersionManager."""
        self.versions: Dict[str, Dict] = {}
        self.version_metadata: Dict[str, Dict] = {}
        self.persistence = DataPersistence()
        self.current_version = None
    
    def save_version(self, root: Optional[FlightNode], version_name: str) -> bool:
        """
        Save current tree state as a named version.
        
        Args:
            root (FlightNode): Root node of current tree.
            version_name (str): Descriptive name for this version.
            
        Returns:
            bool: True if save successful, False otherwise.
        """
        if not root:
            print("Error: Cannot save version with empty tree.")
            return False
        
        if not version_name or not version_name.strip():
            print("Error: Version name cannot be empty.")
            return False
        
        try:
            # Serialize current tree state
            serialized = self.persistence.serialize_tree_for_storage(root)
            
            if not serialized:
                print("Error: Failed to serialize tree.")
                return False
            
            # Store version
            self.versions[version_name] = serialized
            
            # Store metadata
            self.version_metadata[version_name] = {
                "timestamp": datetime.now().isoformat(),
                "tree_size": self.persistence._count_nodes(root),
                "tree_height": root.height,
                "leaf_count": self.persistence._count_leaves(root)
            }
            
            self.current_version = version_name
            print(f"Version '{version_name}' saved successfully.")
            return True
        
        except Exception as e:
            print(f"Error saving version: {e}")
            return False
    
    def restore_version(self, version_name: str) -> Optional[FlightNode]:
        """
        Restore tree state from a saved version.
        
        Args:
            version_name (str): Name of version to restore.
            
        Returns:
            FlightNode: Root node of restored tree, or None if failed.
        """
        if version_name not in self.versions:
            print(f"Error: Version '{version_name}' not found.")
            print(f"Available versions: {self._get_available_versions()}")
            return None
        
        try:
            serialized_data = self.versions[version_name]
            restored_root = self.persistence.deserialize_tree_from_dict(serialized_data)
            
            if restored_root:
                self.current_version = version_name
                print(f"Version '{version_name}' restored successfully.")
                return restored_root
            else:
                print(f"Error: Failed to deserialize version '{version_name}'.")
                return None
        
        except Exception as e:
            print(f"Error restoring version: {e}")
            return None
    
    def list_versions(self) -> List[str]:
        """
        List all saved version names.
        
        Returns:
            List[str]: List of version names.
        """
        return list(self.versions.keys())
    
    def _get_available_versions(self) -> str:
        """
        Get formatted string of available versions.
        
        Returns:
            str: Comma-separated version names.
        """
        return ", ".join(self.versions.keys()) if self.versions else "None"
    
    def get_version_info(self, version_name: str) -> Optional[Dict]:
        """
        Get metadata about a specific version.
        
        Args:
            version_name (str): Name of version.
            
        Returns:
            dict: Version metadata including timestamp and tree stats.
        """
        if version_name not in self.version_metadata:
            print(f"Error: Version '{version_name}' not found.")
            return None
        
        return self.version_metadata[version_name].copy()
    
    def delete_version(self, version_name: str) -> bool:
        """
        Delete a saved version.
        
        Args:
            version_name (str): Name of version to delete.
            
        Returns:
            bool: True if deletion successful, False otherwise.
        """
        if version_name not in self.versions:
            print(f"Error: Version '{version_name}' not found.")
            return False
        
        try:
            del self.versions[version_name]
            del self.version_metadata[version_name]
            
            if self.current_version == version_name:
                self.current_version = None
            
            print(f"Version '{version_name}' deleted successfully.")
            return True
        
        except Exception as e:
            print(f"Error deleting version: {e}")
            return False
    
    def export_version_to_file(self, version_name: str, file_path: str) -> bool:
        """
        Export a specific version to a JSON file.
        
        Args:
            version_name (str): Name of version to export.
            file_path (str): Path where file will be saved.
            
        Returns:
            bool: True if export successful, False otherwise.
        """
        if version_name not in self.versions:
            print(f"Error: Version '{version_name}' not found.")
            return False
        
        try:
            version_data = self.versions[version_name]
            
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(version_data, file, indent=2, ensure_ascii=False)
            
            print(f"Version '{version_name}' exported to: {file_path}")
            return True
        
        except (IOError, Exception) as e:
            print(f"Error exporting version: {e}")
            return False
    
    def import_version_from_file(self, file_path: str, version_name: str) -> bool:
        """
        Import a previously exported version from file.
        
        Args:
            file_path (str): Path to JSON file.
            version_name (str): Name to assign to imported version.
            
        Returns:
            bool: True if import successful, False otherwise.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            if "root_code" not in data or "tree_structure" not in data:
                print("Error: Invalid version file format.")
                return False
            
            # Validate by attempting to deserialize
            restored = self.persistence.deserialize_tree_from_dict(data)
            if not restored:
                print("Error: Failed to validate imported version data.")
                return False
            
            # Store imported version
            self.versions[version_name] = data
            self.version_metadata[version_name] = {
                "timestamp": datetime.now().isoformat(),
                "source": f"imported from {file_path}",
                "tree_size": self.persistence._count_nodes(restored),
                "tree_height": restored.height,
                "leaf_count": self.persistence._count_leaves(restored)
            }
            
            print(f"Version imported successfully as '{version_name}'.")
            return True
        
        except (IOError, json.JSONDecodeError, Exception) as e:
            print(f"Error importing version: {e}")
            return False
    
    def get_all_versions_info(self) -> Dict[str, Dict]:
        """
        Get information about all saved versions.
        
        Returns:
            dict: Dictionary mapping version names to their metadata.
        """
        return {
            name: self.version_metadata.get(name, {})
            for name in self.versions.keys()
        }
    
    def clear_all_versions(self) -> bool:
        """
        Clear all saved versions.
        
        Returns:
            bool: Always returns True.
        """
        self.versions.clear()
        self.version_metadata.clear()
        self.current_version = None
        print("All versions cleared.")
        return True