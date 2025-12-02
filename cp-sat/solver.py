"""
CP-SAT Solver for 3D Bin Packing
"""

import sys
from dataclasses import dataclass
from typing import List, Tuple, Optional
from ortools.sat.python import cp_model

@dataclass
class Item:
    """Représente un colis à livrer"""
    id: int
    length: int  # L
    width: int   # W
    height: int  # H
    delivery_time: int  # D
    
    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

@dataclass
class Vehicle:
    """Représente un véhicule disponible"""
    length: int  # L
    width: int   # W
    height: int  # H
    
    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

@dataclass
class Placement:
    """Représente le placement d'un colis dans un véhicule"""
    item_id: int
    vehicle_id: int
    x: int
    y: int
    z: int
    length: int  # Dimension effective selon l'axe x
    width: int   # Dimension effective selon l'axe y
    height: int  # Dimension effective selon l'axe z

def parse_input(input_text: str) -> Tuple[Vehicle, List[Item]]:
    lines = input_text.strip().split('\n')
    if not lines:
        return None, []
        
    # Ligne 1: dimensions du véhicule
    vehicle_dims = list(map(int, lines[0].split()))
    vehicle = Vehicle(vehicle_dims[0], vehicle_dims[1], vehicle_dims[2])
    
    # Ligne 2: nombre de colis
    try:
        nb_items = int(lines[1])
    except IndexError:
        return vehicle, []
    
    # Lignes suivantes: colis
    items = []
    for i in range(nb_items):
        if 2 + i >= len(lines):
            break
        item_data = list(map(int, lines[2 + i].split()))
        item = Item(
            id=i,
            length=item_data[0],
            width=item_data[1],
            height=item_data[2],
            delivery_time=item_data[3] if len(item_data) > 3 else -1
        )
        items.append(item)
    
    return vehicle, items

def solve_cp_sat(vehicle: Vehicle, items: List[Item], max_time_seconds: float = 60.0) -> List[Placement]:
    """
    Résout le problème avec CP-SAT en minimisant le nombre de véhicules.
    """
    model = cp_model.CpModel()

    # Estimation du nombre max de véhicules (borne supérieure)
    # Au pire, 1 véhicule par item
    max_vehicles = len(items)
    
    # Borne inférieure (volume total / volume véhicule)
    total_volume = sum(item.volume for item in items)
    min_vehicles = (total_volume + vehicle.volume - 1) // vehicle.volume
    
    # On peut essayer de résoudre pour un nombre fixe de véhicules, en incrémentant
    # Mais pour un solveur générique, on peut modéliser le tout.
    # Cependant, avec beaucoup de véhicules potentiels, le modèle devient gros.
    # Stratégie : itérer sur le nombre de véhicules k de min_vehicles à max_vehicles.
    
    print(f"Solving for {len(items)} items. Volume LB: {min_vehicles}", file=sys.stderr)

    for k in range(min_vehicles, max_vehicles + 1):
        print(f"Trying with {k} vehicles...", file=sys.stderr)
        placements = solve_for_k_vehicles(vehicle, items, k, max_time_seconds)
        if placements:
            return placements
            
    return []

def solve_for_k_vehicles(vehicle: Vehicle, items: List[Item], k: int, time_limit: float) -> Optional[List[Placement]]:
    model = cp_model.CpModel()
    
    # Variables
    # Pour chaque item, on a besoin de sa position, ses dimensions (orientation), et son véhicule
    
    # x, y, z coordinates
    x = []
    y = []
    z = []
    
    # Effective dimensions (after rotation)
    lx = []
    ly = []
    lz = []
    
    # Vehicle assignment
    v = []
    
    # Interval variables for non-overlap (we need 3 intervals per item per dimension? No)
    # CP-SAT has AddNoOverlap3D? No.
    # We use NoOverlap2D? No.
    # We use NoOverlap on intervals.
    
    # Since we have multiple bins, we can treat it as a single large bin of size (L*K, W, H) ?
    # Or (L, W, H) and use a vehicle variable.
    # Using vehicle variable makes non-overlap conditional:
    # if v[i] == v[j], then no overlap.
    
    # This implies: v[i] != v[j] OR x_overlap OR y_overlap OR z_overlap is false.
    
    # Let's define variables
    for i, item in enumerate(items):
        # Vehicle index
        v.append(model.NewIntVar(0, k - 1, f'v_{i}'))
        
        # Position
        x.append(model.NewIntVar(0, vehicle.length, f'x_{i}'))
        y.append(model.NewIntVar(0, vehicle.width, f'y_{i}'))
        z.append(model.NewIntVar(0, vehicle.height, f'z_{i}'))
        
        # Dimensions (orientation)
        # 6 orientations possible.
        # We can use 3 variables for dimensions and constrain them.
        l_var = model.NewIntVarFromDomain(cp_model.Domain.FromValues([item.length, item.width, item.height]), f'l_{i}')
        w_var = model.NewIntVarFromDomain(cp_model.Domain.FromValues([item.length, item.width, item.height]), f'w_{i}')
        h_var = model.NewIntVarFromDomain(cp_model.Domain.FromValues([item.length, item.width, item.height]), f'h_{i}')
        
        lx.append(l_var)
        ly.append(w_var)
        lz.append(h_var)
        
        # Constraints on dimensions: must be a permutation of original dimensions
        # We can use a boolean variable for each of the 6 rotations
        # Or simpler: l*w*h = Volume (already true if domain is correct? No, 10*10*10 vs 10*10*20)
        # And l+w+h = sum(dims) (necessary but not sufficient)
        # And l^2 + w^2 + h^2 = sum(dims^2) (sufficient for 3 numbers?)
        # Actually, for 3 numbers, sum and product and sum of squares is usually sufficient to identify the set.
        
        # Or just use booleans for the 6 permutations.
        # (L, W, H), (L, H, W), (W, L, H), (W, H, L), (H, L, W), (H, W, L)
        
        orientations = [
            (item.length, item.width, item.height),
            (item.length, item.height, item.width),
            (item.width, item.length, item.height),
            (item.width, item.height, item.length),
            (item.height, item.length, item.width),
            (item.height, item.width, item.length)
        ]
        # Remove duplicates
        orientations = list(set(orientations))
        
        b_orient = [model.NewBoolVar(f'orient_{i}_{j}') for j in range(len(orientations))]
        model.Add(sum(b_orient) == 1)
        
        model.Add(l_var == sum(b_orient[j] * orientations[j][0] for j in range(len(orientations))))
        model.Add(w_var == sum(b_orient[j] * orientations[j][1] for j in range(len(orientations))))
        model.Add(h_var == sum(b_orient[j] * orientations[j][2] for j in range(len(orientations))))
        
        # Boundary constraints
        # x + lx <= L
        model.Add(x[i] + lx[i] <= vehicle.length)
        model.Add(y[i] + ly[i] <= vehicle.width)
        model.Add(z[i] + lz[i] <= vehicle.height)

    # Non-overlap constraints
    # For every pair i < j
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            # Two items overlap if they are in the same vehicle AND they overlap in all 3 dimensions
            # We want to enforce: NOT (same_vehicle AND overlap_x AND overlap_y AND overlap_z)
            # <=> same_vehicle => (NOT overlap_x OR NOT overlap_y OR NOT overlap_z)
            
            # same_vehicle: v[i] == v[j]
            b_same = model.NewBoolVar(f'same_{i}_{j}')
            model.Add(v[i] == v[j]).OnlyEnforceIf(b_same)
            model.Add(v[i] != v[j]).OnlyEnforceIf(b_same.Not())
            
            # Overlap in X: x[i] < x[j] + lx[j] AND x[j] < x[i] + lx[i]
            # Non-overlap X: x[i] >= x[j] + lx[j] OR x[j] >= x[i] + lx[i]
            
            left = model.NewBoolVar(f'left_{i}_{j}') # i is left of j
            right = model.NewBoolVar(f'right_{i}_{j}') # i is right of j
            
            model.Add(x[i] + lx[i] <= x[j]).OnlyEnforceIf(left)
            model.Add(x[j] + lx[j] <= x[i]).OnlyEnforceIf(right)
            
            # Y
            behind = model.NewBoolVar(f'behind_{i}_{j}')
            front = model.NewBoolVar(f'front_{i}_{j}')
            model.Add(y[i] + ly[i] <= y[j]).OnlyEnforceIf(behind)
            model.Add(y[j] + ly[j] <= y[i]).OnlyEnforceIf(front)
            
            # Z
            below = model.NewBoolVar(f'below_{i}_{j}')
            above = model.NewBoolVar(f'above_{i}_{j}')
            model.Add(z[i] + lz[i] <= z[j]).OnlyEnforceIf(below)
            model.Add(z[j] + lz[j] <= z[i]).OnlyEnforceIf(above)
            
            # If same vehicle, then at least one relative position must be true
            model.AddBoolOr([left, right, behind, front, below, above]).OnlyEnforceIf(b_same)

    # Solver
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.log_search_progress = False # Set to True for debugging
    
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        result = []
        for i in range(len(items)):
            result.append(Placement(
                item_id=items[i].id,
                vehicle_id=solver.Value(v[i]),
                x=solver.Value(x[i]),
                y=solver.Value(y[i]),
                z=solver.Value(z[i]),
                length=solver.Value(lx[i]),
                width=solver.Value(ly[i]),
                height=solver.Value(lz[i])
            ))
        return result
    
    return None

def format_output(placements: List[Placement]) -> str:
    if not placements:
        return "UNSAT"
        
    lines = ["SAT"]
    # Sort by item ID
    placements.sort(key=lambda p: p.item_id)
    
    for p in placements:
        # Format: vehicle_id x y z x_end y_end z_end
        lines.append(f"{p.vehicle_id} {p.x} {p.y} {p.z} {p.x + p.length} {p.y + p.width} {p.z + p.height}")
        
    return "\n".join(lines)

if __name__ == "__main__":
    input_text = sys.stdin.read()
    vehicle, items = parse_input(input_text)
    
    if vehicle and items:
        placements = solve_cp_sat(vehicle, items)
        print(format_output(placements))
    else:
        print("UNSAT")
