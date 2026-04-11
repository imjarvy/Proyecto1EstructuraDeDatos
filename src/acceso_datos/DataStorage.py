"""
DataStorage module.

Main integration module that coordinates loading, persisting, and versioning
of flight data and tree structures. This is the primary interface for all
data management operations.
"""

from typing import Optional, Dict, Tuple, Literal
from src.modelos.FlightNode import FlightNode
from src.modelos.AVLTree import AVLTree
from src.modelos.BST import BST
from src.acceso_datos.DataLoader import DataLoader
from src.acceso_datos.DataPersistence import DataPersistence
from src.acceso_datos.VersionManager import VersionManager

class DataStorage:
    """
    Central data management system for SkyBalance AVL.
    
    Coordinates loading flight data, persisting tree states, and managing version control across the entire application.
    """
    
    def __init__(self):
        """Initialize DataStorage with all component modules."""
        self.loader = DataLoader()
        self.persistence = DataPersistence()
        self.version_manager = VersionManager()

    def _clone_flight_node(self, node: FlightNode) -> FlightNode:
        """
        Create an independent copy of a flight node.
        
        Cloning is necessary when reconstructing trees from external data
        to prevent mutations from affecting the original parsed data or
        making shared references between AVL and BST trees.
        """
        return FlightNode.from_dict(node.to_dict())

    # ============================================================================
    # PERSISTENCE OPERATIONS
    # ============================================================================

    def load_and_reconstruct(
        self,
        uploaded_file,
        load_type: Literal["topology", "insertion"] = "topology",
        avl_stress_mode: bool = False,
        rebalance_after_load: bool = True,
    ) -> Tuple[Optional[AVLTree], Optional[BST], Optional[str]]:
        """
        Load JSON from file, validate structure, and reconstruct trees.
        
        Args:
            uploaded_file: Flask FileStorage-like object.
            load_type: "topology" or "insertion".
            avl_stress_mode: Whether to enable AVL stress mode.
            rebalance_after_load: Whether to rebalance after insertion mode.
        
        Returns:
            Tuple[Optional[AVLTree], Optional[BST], Optional[str]]: 
                (avl_tree, bst_tree, error_message).
        """
        if uploaded_file is None:
            return None, None, "No se proporcionó ningún archivo"
        
        # Step 1: Get file stream and validate JSON against the specified type
        stream = getattr(uploaded_file, "stream", uploaded_file)
        data, error = self.loader.validate_json_stream(stream, load_type)
        if error:
            return None, None, error
        
        # At this point, data is guaranteed to be Dict (not None) due to the check above
        assert data is not None
        
        # Step 2: Reconstruct based on load type
        try:
            if load_type == "topology":
                avl = self.reconstruct_avl_from_dict(data)
                if avl is None:
                    return None, None, "No se pudo reconstruir el árbol AVL desde la topología"
                return avl, None, None
            
            elif load_type == "insertion":
                result = self.reconstruct_both_from_flights(
                    data,
                    avl_stress_mode=avl_stress_mode,
                    rebalance_after_load=rebalance_after_load,
                )
                if result is None:
                    return None, None, "No se pudo reconstruir los árboles desde el modo inserción"
                avl, bst = result
                return avl, bst, None
            
            else:
                return None, None, f"Tipo de carga desconocido: {load_type}"
        
        except Exception as e:
            return None, None, f"Error durante la reconstrucción: {str(e)}"

    def serialize_tree(self, root: FlightNode) -> Optional[Dict]:
        """
        Serialize a tree root to dictionary for in-memory storage.

        If root is omitted, the current AVL root is used.

        Args:
            root (FlightNode): Root node to serialize. Optional.

        Returns:
            dict: Serialized tree structure, or None if root is empty.
        """
        return self.persistence.serialize_tree_for_storage(root)

    def deserialize_tree_data(self, data: Dict) -> Optional[FlightNode]:
        """
        Deserialize tree data without mutating current storage state.

        Args:
            data (Dict): Serialized tree data.

        Returns:
            FlightNode: Root node of reconstructed tree, or None if failed.
        """
        return self.persistence.deserialize_tree_from_dict(data)
    
    def export_tree(
        self,
        root: Optional[FlightNode] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Export tree to JSON in the user's Downloads folder.

        Args:
            root (FlightNode, optional): Root to export. Uses current AVL root when omitted.

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message).
        """
        if root is None:
            return False, "El árbol está vacío"

        success = self.persistence.export_tree_to_downloads(root)
        if not success:
            return False, "No se pudo exportar el árbol a archivo"

        return True, None
    
    # ============================================================================
    # METADATA OPERATIONS
    # ============================================================================
    
    def get_tree_metadata(self, root: Optional[FlightNode]) -> Dict:
        """
        Calculate metadata for any provided tree root.

        Args:
            root (FlightNode): Root node to inspect.

        Returns:
            dict: Tree statistics (root, height, node count, leaf count).
        """
        if root is None:
            return {
                "root": None,
                "height": 0,
                "node_count": 0,
                "leaf_count": 0,
            }

        return {
            "root": root.flight_code,
            "height": root.height,
            "node_count": self.persistence.count_nodes(root),
            "leaf_count": self.persistence.count_leaves(root),
        }
    
    # ============================================================================
    # VERSION MANAGEMENT OPERATIONS
    # ============================================================================

    def save_avl_version(
        self,
        version_name: str,
        root: Optional[FlightNode] = None,
        rotation_count: Optional[Dict] = None,
        cascade_rebalance_count: int = 0,
        mass_cancellation_count: int = 0,
    ) -> bool:
        """
        Save current AVL tree state as a named version.
        
        Args:
            version_name (str): Descriptive name for this version.
            root (FlightNode): Optional root to persist.
            rotation_count (dict, optional): Rotation counters to persist.
            cascade_rebalance_count (int, optional): Global rebalance counter.
            mass_cancellation_count (int, optional): Mass cancellation counter.
            
        Returns:
            bool: True if save successful, False otherwise.
        """
        return self.version_manager.save_version(
            root,
            version_name,
            rotation_count=rotation_count,
            cascade_rebalance_count=cascade_rebalance_count,
            mass_cancellation_count=mass_cancellation_count,
        )
    
    def restore_avl_version(self, version_name: str) -> Optional[FlightNode]:
        """
        Restore AVL tree from a saved version.
        
        Args:
            version_name (str): Name of version to restore.
            
        Returns:
            FlightNode: Root node of restored tree, or None if failed.
        """
        root = self.version_manager.restore_version(version_name)
        return root
    
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
    
    def get_all_versions_info(self) -> Dict:
        """
        Get information about all saved versions.
        
        Returns:
            dict: Dictionary mapping version names to metadata.
        """
        return self.version_manager.get_all_versions_info()
    
    # ============================================================================
    # IN-MEMORY RECONSTRUCTION OPERATIONS
    # ============================================================================

    def reconstruct_avl_from_dict(self, data: Dict) -> Optional[AVLTree]:
        """
        Rebuild an AVL tree from an already-parsed topology dict.

        Expected keys: root_code, tree_structure.

        Args:
            data (Dict): Parsed JSON payload in topology format.

        Returns:
            AVLTree: Reconstructed tree, or None if data is invalid.
        """
        root = self.deserialize_tree_data(data)
        if root is None:
            return None
        avl = AVLTree()
        avl.root = root
        return avl

    def reconstruct_both_from_flights(
        self,
        data: Dict,
        avl_stress_mode: bool = False,
        rebalance_after_load: bool = True,
    ) -> Optional[Tuple[AVLTree, BST]]:
        """
        Rebuild AVL and BST by inserting flights from an already-parsed dict.

        Expected key: flights (list of flight dicts).

        Args:
            data (Dict): Parsed JSON payload with a 'flights' list.

        Returns:
            Tuple[AVLTree, BST]: Both reconstructed trees, or None if invalid.
        """
        # Use DataLoader's parsed flights
        flights = self.loader.get_parsed_flights()
        if not flights:
            return None

        avl = AVLTree(stress_mode=avl_stress_mode)
        bst = BST()
        for flight_node in flights:
            # Clone for safety (protect original parsed data)
            avl.insert(self._clone_flight_node(flight_node))
            bst.insert(self._clone_flight_node(flight_node))

        if avl_stress_mode and rebalance_after_load:
            avl.global_rebalance()

        return avl, bst