"""
FlightNode class definition for the SkyBalance AVL Flight Management System.

This module defines the fundamental data structure representing a flight node
in the AVL tree. Each node contains flight operational data and tree structure information.
"""

from typing import Optional


class FlightNode:
    """
    Represents a flight node in the AVL tree structure.
    
    Attributes:
        flight_code (str): Unique identifier for the flight.
        origin (str): Departure city.
        destination (str): Arrival city.
        base_price (float): Initial ticket price.
        final_price (float): Current ticket price after adjustments.
        passengers (int): Current passenger count.
        promotion (float): Active promotion discount (0 if none).
        alert (str): Alert status for this flight (empty if none).
        priority (int): Flight priority level (1-5, where 5 is highest).
        height (int): Height of the node in the AVL tree.
        balance_factor (int): Balance factor for AVL property (-1, 0, or 1).
        left (FlightNode): Reference to left child node.
        right (FlightNode): Reference to right child node.
        parent (FlightNode): Reference to parent node.
    """
    
    def __init__(self, flight_code: str, origin: str, destination: str, base_price: float, passengers: int = 0, promotion: float = 0.0, alert: str = "", priority: int = 3):
        """
        Initialize a new flight node.
        
        Args:
            flight_code (str): Unique flight identifier.
            origin (str): Departure city name.
            destination (str): Arrival city name.
            base_price (float): Initial ticket price.
            passengers (int): Initial passenger count. Defaults to 0.
            promotion (float): Promotion discount value. Defaults to 0.0.
            alert (str): Alert message. Defaults to empty string.
            priority (int): Priority level 1-5. Defaults to 3.
        """
        self.flight_code = flight_code
        self.origin = origin
        self.destination = destination
        self.base_price = base_price
        self.final_price = base_price
        self.passengers = passengers
        self.promotion = promotion
        self.alert = alert
        self.priority = priority
        
        # Tree structure attributes
        self.height = 0
        self.balance_factor = 0
        self.left: Optional["FlightNode"] = None
        self.right: Optional["FlightNode"] = None
        self.parent: Optional["FlightNode"] = None
    
    def to_dict(self) -> dict:
        """
        Convert node to dictionary representation.
        
        Returns:
            dict: Dictionary containing all node attributes.
        """
        return {
            "flight_code": self.flight_code,
            "origin": self.origin,
            "destination": self.destination,
            "base_price": self.base_price,
            "final_price": self.final_price,
            "passengers": self.passengers,
            "promotion": self.promotion,
            "alert": self.alert,
            "priority": self.priority,
            "height": self.height,
            "balance_factor": self.balance_factor
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "FlightNode":
        """
        Create a FlightNode instance from a dictionary.
        
        Args:
            data (dict): Dictionary containing flight data.
            
        Returns:
            FlightNode: New instance populated with dictionary values.
        """
        node = cls(
            flight_code=data["flight_code"],
            origin=data["origin"],
            destination=data["destination"],
            base_price=data["base_price"],
            passengers=data.get("passengers", 0),
            promotion=data.get("promotion", 0.0),
            alert=data.get("alert", ""),
            priority=data.get("priority", 3)
        )
        node.final_price = data.get("final_price", data["base_price"])
        node.height = data.get("height", 0)
        node.balance_factor = data.get("balance_factor", 0)
        return node
    
    def __repr__(self) -> str:
        """Return string representation of the flight node."""
        return f"FlightNode({self.flight_code}: {self.origin}->{self.destination})"