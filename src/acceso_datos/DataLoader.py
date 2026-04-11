"""
DataLoader module.

This module handles loading and parsing JSON data from file streams.
Coordinates with DataPersistence for object conversion.
"""

import json
from typing import Optional, Literal, Tuple
from src.modelos.FlightNode import FlightNode

class DataLoader:
    """
    Handles loading and parsing JSON data from file streams.
    
    Responsibilities:
    - Read JSON from streams (Flask uploads)
    - Validate JSON structure matches expected topology/insertion format
    - Expose raw parsed data to orchestrators
    """
    
    def __init__(self):
        """Initialize the DataLoader."""
        self.raw_data = None
    
    def load_from_stream(self, stream) -> Tuple[bool, Optional[str]]:
        """
        Load and parse JSON content from an open file-like stream.

        Args:
            stream: Readable stream that provides JSON content.

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message).
        """
        try:
            if hasattr(stream, "seek"):
                stream.seek(0)
            self.raw_data = json.load(stream)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"JSON inválido: {e}"
        except Exception as e:
            return False, f"Error leyendo archivo: {e}"

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
    
    def get_raw_data(self) -> Optional[dict]:
        """
        Get the raw loaded JSON data.
        
        Returns:
            dict: Raw JSON data, or None if not loaded.
        """
        return self.raw_data

    def get_parsed_flights(self):
        """
        Get flights from loaded insertion-mode JSON, parsed as FlightNode objects.
        
        Returns:
            List[FlightNode]: Flight objects parsed from the JSON.
        """
        if not self.raw_data or "flights" not in self.raw_data:
            return []
        
        flights = []
        for flight_data in self.raw_data.get("flights", []):
            if isinstance(flight_data, dict) and "flight_code" in flight_data:
                node = FlightNode.from_dict(flight_data)
                flights.append(node)
        
        return flights

    def validate_json_stream(self, stream, load_type: Literal["topology", "insertion"]) -> Tuple[Optional[dict], Optional[str]]:
        """
        Load JSON from stream and validate it matches the expected load_type. This prevents loading topology JSON when insertion is expected, and vice versa.
        
        Args:
            stream: Readable stream with JSON content.
            load_type: Expected type ("topology" or "insertion").
        
        Returns:
            Tuple[Optional[Dict], Optional[str]]: (validated_data, error_message).
                - If successful: error_message is None.
                - If any error: data is None and error_message is descriptive.
        """
        # Step 1: Load and parse JSON
        ok, error = self.load_from_stream(stream)
        if not ok:
            return None, error or "No se pudo leer el JSON."
        
        data = self.get_raw_data()
        if not isinstance(data, dict):
            return None, "El JSON debe ser un objeto raíz válido."
        
        # Step 2: Auto-detect actual type from structure
        detected_type = self.get_reconstruction_mode()
        if detected_type == "unknown":
            return None, (
                "El archivo JSON no contiene una estructura válida. "
                "Debe ser topología (root_code + tree_structure) "
                "o inserción (flights)."
            )
        
        # Step 3: Validate detected type matches expected type
        if detected_type != load_type:
            return None, (
                f"El archivo es de tipo {detected_type}, "
                f"pero se esperaba {load_type}."
            )
        
        return data, None