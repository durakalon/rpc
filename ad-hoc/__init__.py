"""
Package du solveur ad-hoc pour le problème de bin packing 3D
"""

from .solver import (
    Item,
    Vehicle,
    Placement,
    VehiclePacker,
    BinPackingSolver,
    SortingHeuristic,
    parse_input,
    format_output,
    solve_problem
)

__version__ = "1.0.0"
__all__ = [
    'Item',
    'Vehicle', 
    'Placement',
    'VehiclePacker',
    'BinPackingSolver',
    'SortingHeuristic',
    'parse_input',
    'format_output',
    'solve_problem'
]
