"""
VersionManager module.

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
        """
        Convert a user-provided version name to a filesystem-safe string.
        
        Args:
            version_name (str): Original version name provided by user
            
        Returns:
            str: Filesystem-safe name using alphanumeric, dots, hyphens, underscores
        """
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", version_name.strip())
        cleaned = cleaned.strip("._-")
        return cleaned or "version"

    def _version_file_candidates(self) -> List[Path]:
        """
        Retrieve all version files currently stored on disk.
        
        Returns:
            List[Path]: Sorted list of Path objects for all JSON files in the versions directory. Empty list if no versions exist.
        """
        return sorted(self.versions_dir.glob("*.json"))

    def _read_version_file(self, file_path: Path) -> Optional[Dict]:
        """
        Safely read and parse a version JSON file from disk.
        
        Args:
            file_path (Path): Path to the JSON version file to read
            
        Returns:
            Optional[Dict]: Parsed JSON content as dict, or None if unreadable
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            if not isinstance(data, dict):
                return None
            return data
        except (OSError, json.JSONDecodeError):
            return None

    def _find_file_by_version_name(self, version_name: str) -> Optional[Path]:
        """
        Locate the JSON file for a specific version by name.
        
        Args:
            version_name (str): Exact version name to search for
            
        Returns:
            Optional[Path]: Path to the matching version file, or None if not found
        """
        for file_path in self._version_file_candidates():
            payload = self._read_version_file(file_path)
            if not payload:
                continue
            metadata = payload.get("metadata", {})
            if metadata.get("version_name") == version_name:
                return file_path
        return None

    def _build_version_payload(self, root: FlightNode, version_name: str, rotation_count: Optional[Dict] = None, cascade_rebalance_count: int = 0, mass_cancellation_count: int = 0) -> Optional[Dict]:
        """
        Create a complete version payload with tree data and metadata.
        
        Combines the serialized tree structure with comprehensive metadata including
        timestamp, tree statistics, and operation counters. This payload is what
        gets written to disk when a version is saved.
        
        Args:
            root (FlightNode): Root node of the tree to serialize
            version_name (str): User-provided descriptive name for this version
            rotation_count (dict, optional): Rotation counters {LL, RR, LR, RL}
            cascade_rebalance_count (int, optional): Number of cascade rebalancing
            mass_cancellation_count (int, optional): Reserved for future use. Default: 0
            
        Returns:
            Optional[Dict]: Complete version payload with structure:
                {
                    "metadata": {
                        "version_name": str,
                        "timestamp": ISO format string,
                        "tree_size": int,
                        "tree_height": int,
                        "leaf_count": int,
                        "rotation_count": dict,
                        "cascade_rebalance_count": int,
                        "mass_cancellation_count": int
                    },
                    "tree_data": {...}
                }
                Returns None if tree serialization fails.
        """
        serialized = self.persistence.serialize_tree_for_storage(root)
        if not serialized:
            return None

        metadata = {
            "version_name": version_name,
            "timestamp": datetime.now().isoformat(),
            "tree_size": self.persistence.count_nodes(root),
            "tree_height": root.height,
            "leaf_count": self.persistence.count_leaves(root),
            "rotation_count": rotation_count or {"LL": 0, "RR": 0, "LR": 0, "RL": 0},
            "cascade_rebalance_count": cascade_rebalance_count,
            "mass_cancellation_count": mass_cancellation_count,
        }
        return {"metadata": metadata, "tree_data": serialized}

    def _extract_tree_data(self, payload: Dict) -> Optional[Dict]:
        """
        Extract serialized tree data from a version payload.
        
        Args:
            payload (Dict): Complete version payload from a version file
            
        Returns:
            Optional[Dict]: Extracted tree data in standard format 
                           {"root_code": "...", "tree_structure": {...}},
                           or None if payload format is invalid/unrecognized.
        """
        if "tree_data" in payload and isinstance(payload.get("tree_data"), dict):
            return payload["tree_data"]

        if "root_code" in payload and "tree_structure" in payload:
            return payload

        return None

    def _write_payload(self, file_path: Path, payload: Dict) -> bool:
        """
        Write a version payload to disk as UTF-8 JSON.
        
        Args:
            file_path (Path): Destination file path where JSON will be written
            payload (Dict): Data structure to serialize
            
        Returns:
            bool: True if write successful, False on any I/O error
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(payload, file, indent=2, ensure_ascii=False)
            return True
        except OSError as e:
            print(f"Error writing version file '{file_path}': {e}")
            return False
    
    def save_version(self, root: Optional[FlightNode], version_name: str, rotation_count: Optional[Dict] = None, cascade_rebalance_count: int = 0, mass_cancellation_count: int = 0) -> bool:
        """
        Save current tree state as a named version.
        
        Args:
            root (Optional[FlightNode]): Root node of the tree to save.
            version_name (str): Descriptive name for this version. 
            rotation_count (dict, optional): Rotation operation counts 
            cascade_rebalance_count (int, optional): Number of cascade 
            mass_cancellation_count (int, optional): Reserved for future use. 
            
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
            payload = self._build_version_payload(root, version_name, rotation_count=rotation_count, cascade_rebalance_count=cascade_rebalance_count, mass_cancellation_count=mass_cancellation_count)
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
            Optional[FlightNode]: Root node of the restored tree, or None if restoration fails.
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
    
    def _get_available_versions(self) -> str:
        """
        Get formatted string of available versions.
        
        Returns:
            str: Comma-separated version names.
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
        versions = list(dict.fromkeys(versions))
        return ", ".join(versions) if versions else "None"
    
    def get_version_info(self, version_name: str) -> Optional[Dict]:
        """
        Get metadata about a specific version.
        
        Args:
            version_name (str): Name of version.
            
        Returns:
            Optional[Dict]: Metadata dictionary

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