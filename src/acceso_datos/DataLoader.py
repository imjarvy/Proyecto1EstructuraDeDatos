"""
DataLoader module for the SkyBalance AVL Flight Management System.

This module handles loading flight data from JSON files and reconstructing
tree structures in both topology and insertion modes.
"""

import json
from typing import Optional, List, Literal
from tkinter import filedialog
from src.modelos.FlightNode import FlightNode


class DataLoader:
    """
    Handles loading and parsing flight data from JSON files.
    
    Supports two reconstruction modes:
    - Topology: Preserves exact parent-child relationships from JSON.
    - Insertion: Builds trees by sequentially inserting flights.
    """
    
    def __init__(self):
        """Initialize the DataLoader."""
        self.raw_data = None
        self.flights_list = []
        self.node_map = {}
    
    def select_and_load_file(self) -> bool:
        """
        Open file dialog for user to select a JSON file.
        
        Returns:
            bool: True if file loaded successfully, False otherwise.
        """
        try:
            file_path = filedialog.askopenfilename(
                title="Select flight data JSON file",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not file_path:
                print("No file selected.")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as file:
                self.raw_data = json.load(file)
            
            print(f"Successfully loaded: {file_path}")
            self._parse_flights()
            return True
        
        except FileNotFoundError:
            print(f"Error: File not found.")
            return False
        except json.JSONDecodeError:
            print("Error: Invalid JSON format.")
            return False
        except Exception as e:
            print(f"Unexpected error loading file: {e}")
            return False
    
    def load_from_path(self, file_path: str) -> bool:
        """
        Load JSON file from a given path (for testing purposes).
        
        Args:
            file_path (str): Path to the JSON file.
            
        Returns:
            bool: True if file loaded successfully, False otherwise.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.raw_data = json.load(file)
            
            self._parse_flights()
            return True
        except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
            print(f"Error loading file: {e}")
            return False
    
    def _parse_flights(self):
        """
        Extract flight data from raw JSON.
        
        Expected JSON structure:
        {
            "flights": [
                {
                    "flight_code": "SK001",
                    "origin": "Bogotá",
                    "destination": "Medellín",
                    "base_price": 250000.0,
                    ...
                }
            ]
        }
        """
        self.flights_list = []
        self.node_map = {}

        if not self.raw_data:
            print("Warning: Loaded JSON is empty.")
            return

        if not isinstance(self.raw_data, dict):
            print("Warning: JSON root must be an object.")
            return

        flights_source = self.raw_data.get("flights")
        if not isinstance(flights_source, list):
            # In topology mode there may be no flights list, this is expected.
            return

        for flight_data in flights_source:
            flight_code = flight_data.get("flight_code")
            if flight_code:
                node = FlightNode.from_dict(flight_data)
                self.flights_list.append(node)
                self.node_map[flight_code] = node

    def get_reconstruction_mode(self) -> Literal["topology", "insertion", "unknown"]:
        """
        Infer the intended reconstruction mode from loaded JSON structure.

        Returns:
            Literal["topology", "insertion", "unknown"]: Detected mode.
        """
        if isinstance(self.raw_data, dict):
            has_topology = "tree_structure" in self.raw_data and "root_code" in self.raw_data
            has_insertion = isinstance(self.raw_data.get("flights"), list)

            if has_topology:
                return "topology"
            if has_insertion:
                return "insertion"

        return "unknown"
    
    def reconstruct_topology_mode(self) -> Optional[FlightNode]:
        """
        Reconstruct tree respecting parent-child topology from JSON.
        
        Expected JSON structure for topology mode:
        {
            "root_code": "SK001",
            "tree_structure": {
                "SK001": {
                    "flight_data": {...},
                    "left_child": "SK002",
                    "right_child": "SK003"
                }
            }
        }
        
        Returns:
            FlightNode: Root node of reconstructed tree, or None if failed.
        """
        if not self.raw_data:
            print("Error: No data loaded.")
            return None

        if self.get_reconstruction_mode() != "topology":
            print("Error: Loaded JSON is not in topology mode.")
            return None

        if "tree_structure" not in self.raw_data or "root_code" not in self.raw_data:
            print("Error: Missing 'tree_structure' or 'root_code' in JSON.")
            return None
        
        tree_structure = self.raw_data["tree_structure"]
        root_code = self.raw_data["root_code"]
        
        # Build nodes first
        self._build_nodes_from_topology(tree_structure)
        
        # Establish parent-child relationships
        root = self._establish_relationships(tree_structure, root_code)
        
        return root
    
    def _build_nodes_from_topology(self, tree_structure: dict):
        """
        Create FlightNode instances from topology structure.
        
        Args:
            tree_structure (dict): Dictionary mapping flight codes to node data.
        """
        self.node_map = {}
        
        for flight_code, node_data in tree_structure.items():
            if "flight_data" not in node_data:
                raise ValueError(
                    f"Invalid topology JSON: node '{flight_code}' is missing 'flight_data'."
                )

            flight_info = node_data["flight_data"]
            node = FlightNode.from_dict(flight_info)
            self.node_map[flight_code] = node
    
    def _establish_relationships(self, tree_structure: dict, root_code: str) -> Optional[FlightNode]:
        """
        Establish parent-child pointers based on topology.
        
        Args:
            tree_structure (dict): Dictionary mapping flight codes to node data.
            root_code (str): Code of the root node.
            
        Returns:
            FlightNode: Root node with established relationships.
        """
        root = self.node_map.get(root_code)
        if not root:
            print(f"Error: Root node '{root_code}' not found.")
            return None
        
        for flight_code, node_data in tree_structure.items():
            current_node = self.node_map[flight_code]
            
            # Establish left child relationship
            left_child_code = node_data.get("left_child")
            if left_child_code and left_child_code in self.node_map:
                left_child = self.node_map[left_child_code]
                current_node.left = left_child
                left_child.parent = current_node
            
            # Establish right child relationship
            right_child_code = node_data.get("right_child")
            if right_child_code and right_child_code in self.node_map:
                right_child = self.node_map[right_child_code]
                current_node.right = right_child
                right_child.parent = current_node
        
        return root
    
    def get_flights_for_insertion(self) -> List[FlightNode]:
        """
        Get the list of flights for insertion mode.
        
        Returns:
            List[FlightNode]: List of flight nodes ready for sequential insertion.
        """
        return self.flights_list.copy()
    
    def get_raw_data(self) -> Optional[dict]:
        """
        Get the raw loaded JSON data.
        
        Returns:
            dict: Raw JSON data, or None if not loaded.
        """
        return self.raw_data