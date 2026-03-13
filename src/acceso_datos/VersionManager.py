"""
VersionManager module for the SkyBalance AVL Flight Management System.

This module manages versioning of tree states, allowing users to save and
restore specific snapshots of the system at different points in time.
"""

import json
import re
from pathlib import Path
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
        self.persistence = DataPersistence()
        self.versions_dir = Path(__file__).resolve().parents[2] / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_name(self, version_name: str) -> str:
        """Build a filesystem-safe stem from a user-provided version name."""
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", version_name.strip())
        cleaned = cleaned.strip("._-")
        return cleaned or "version"

    def _version_file_candidates(self) -> List[Path]:
        """Return all JSON files currently stored as versions."""
        return sorted(self.versions_dir.glob("*.json"))

    def _read_version_file(self, file_path: Path) -> Optional[Dict]:
        """Safely read and parse a version JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            if not isinstance(data, dict):
                return None
            return data
        except (OSError, json.JSONDecodeError):
            return None

    def _find_file_by_version_name(self, version_name: str) -> Optional[Path]:
        """Find the JSON file whose metadata matches the requested version name."""
        for file_path in self._version_file_candidates():
            payload = self._read_version_file(file_path)
            if not payload:
                continue
            metadata = payload.get("metadata", {})
            if metadata.get("version_name") == version_name:
                return file_path
        return None

    def _build_version_payload(self, root: FlightNode, version_name: str) -> Optional[Dict]:
        """Create the persisted payload containing metadata and serialized tree."""
        serialized = self.persistence.serialize_tree_for_storage(root)
        if not serialized:
            return None

        metadata = {
            "version_name": version_name,
            "timestamp": datetime.now().isoformat(),
            "tree_size": self.persistence._count_nodes(root),
            "tree_height": root.height,
            "leaf_count": self.persistence._count_leaves(root),
        }
        return {
            "metadata": metadata,
            "tree_data": serialized,
        }

    def _extract_tree_data(self, payload: Dict) -> Optional[Dict]:
        """
        Extract serialized tree data from version payload.

        Supports both new format ({metadata, tree_data}) and legacy plain tree
        format ({root_code, tree_structure}) for backward compatibility.
        """
        if "tree_data" in payload and isinstance(payload.get("tree_data"), dict):
            return payload["tree_data"]

        if "root_code" in payload and "tree_structure" in payload:
            return payload

        return None

    def _write_payload(self, file_path: Path, payload: Dict) -> bool:
        """Persist a payload to disk in UTF-8 JSON format."""
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(payload, file, indent=2, ensure_ascii=False)
            return True
        except OSError as e:
            print(f"Error writing version file '{file_path}': {e}")
            return False
    
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
            payload = self._build_version_payload(root, version_name)
            if not payload:
                print("Error: Failed to serialize tree.")
                return False

            existing_file = self._find_file_by_version_name(version_name)
            if existing_file is not None:
                target_path = existing_file
            else:
                safe_name = self._sanitize_name(version_name)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_path = self.versions_dir / f"{safe_name}_{timestamp}.json"

            if not self._write_payload(target_path, payload):
                return False

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
        version_file = self._find_file_by_version_name(version_name)
        if version_file is None:
            print(f"Error: Version '{version_name}' not found.")
            print(f"Available versions: {self._get_available_versions()}")
            return None
        
        try:
            payload = self._read_version_file(version_file)
            if not payload:
                print(f"Error: Version file for '{version_name}' is unreadable.")
                return None

            tree_data = self._extract_tree_data(payload)
            if not tree_data:
                print(f"Error: Version '{version_name}' has invalid tree data.")
                return None

            restored_root = self.persistence.deserialize_tree_from_dict(tree_data)
            
            if restored_root:
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
        versions = []
        for file_path in self._version_file_candidates():
            payload = self._read_version_file(file_path)
            if not payload:
                continue

            metadata = payload.get("metadata", {})
            version_name = metadata.get("version_name")
            if version_name:
                versions.append(version_name)

        # Keep insertion order by file discovery while removing duplicates.
        return list(dict.fromkeys(versions))
    
    def _get_available_versions(self) -> str:
        """
        Get formatted string of available versions.
        
        Returns:
            str: Comma-separated version names.
        """
        versions = self.list_versions()
        return ", ".join(versions) if versions else "None"
    
    def get_version_info(self, version_name: str) -> Optional[Dict]:
        """
        Get metadata about a specific version.
        
        Args:
            version_name (str): Name of version.
            
        Returns:
            dict: Version metadata including timestamp and tree stats.
        """
        version_file = self._find_file_by_version_name(version_name)
        if version_file is None:
            print(f"Error: Version '{version_name}' not found.")
            return None

        payload = self._read_version_file(version_file)
        if not payload:
            print(f"Error: Version file for '{version_name}' is unreadable.")
            return None

        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            print(f"Error: Version '{version_name}' has invalid metadata.")
            return None

        return metadata.copy()
    
    def delete_version(self, version_name: str) -> bool:
        """
        Delete a saved version.
        
        Args:
            version_name (str): Name of version to delete.
            
        Returns:
            bool: True if deletion successful, False otherwise.
        """
        version_file = self._find_file_by_version_name(version_name)
        if version_file is None:
            print(f"Error: Version '{version_name}' not found.")
            return False
        
        try:
            version_file.unlink()
            
            print(f"Version '{version_name}' deleted successfully.")
            return True
        
        except OSError as e:
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
        version_file = self._find_file_by_version_name(version_name)
        if version_file is None:
            print(f"Error: Version '{version_name}' not found.")
            return False
        
        try:
            payload = self._read_version_file(version_file)
            if not payload:
                print(f"Error: Version file for '{version_name}' is unreadable.")
                return False

            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(payload, file, indent=2, ensure_ascii=False)
            
            print(f"Version '{version_name}' exported to: {file_path}")
            return True
        
        except (OSError, Exception) as e:
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

            if not isinstance(data, dict):
                print("Error: Invalid version file format.")
                return False

            tree_data = self._extract_tree_data(data)
            if not tree_data:
                print("Error: Invalid version file format.")
                return False

            # Validate by attempting to deserialize
            restored = self.persistence.deserialize_tree_from_dict(tree_data)
            if not restored:
                print("Error: Failed to validate imported version data.")
                return False

            payload = {
                "metadata": {
                    "version_name": version_name,
                    "timestamp": datetime.now().isoformat(),
                    "source": f"imported from {file_path}",
                    "tree_size": self.persistence._count_nodes(restored),
                    "tree_height": restored.height,
                    "leaf_count": self.persistence._count_leaves(restored),
                },
                "tree_data": tree_data,
            }

            existing_file = self._find_file_by_version_name(version_name)
            if existing_file is not None:
                target_path = existing_file
            else:
                safe_name = self._sanitize_name(version_name)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_path = self.versions_dir / f"{safe_name}_{timestamp}.json"

            if not self._write_payload(target_path, payload):
                return False
            
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
        info: Dict[str, Dict] = {}
        for file_path in self._version_file_candidates():
            payload = self._read_version_file(file_path)
            if not payload:
                continue

            metadata = payload.get("metadata", {})
            if not isinstance(metadata, dict):
                continue

            version_name = metadata.get("version_name")
            if version_name:
                info[version_name] = metadata.copy()

        return info
    
    def clear_all_versions(self) -> bool:
        """
        Clear all saved versions.
        
        Returns:
            bool: Always returns True.
        """
        try:
            for file_path in self._version_file_candidates():
                file_path.unlink()
            print("All versions cleared.")
            return True
        except OSError as e:
            print(f"Error clearing versions: {e}")
            return False