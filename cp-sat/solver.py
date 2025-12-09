"""
CP-SAT Solver for 3D Bin Packing
Version complète avec gravité et support
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


def solve_cp_sat(vehicle: Vehicle, items: List[Item], max_time_seconds: float = 60.0, verbose: bool = False) -> List[Placement]:
    """
    Résout le problème avec CP-SAT en minimisant le nombre de véhicules.
    """
    # Borne inférieure (volume total / volume véhicule)
    total_volume = sum(item.volume for item in items)
    min_vehicles = max(1, (total_volume + vehicle.volume - 1) // vehicle.volume)
    
    # Borne supérieure : au pire 1 véhicule par item
    max_vehicles = len(items)
    
    if verbose:
        print(f"Solving for {len(items)} items. Volume LB: {min_vehicles}", file=sys.stderr)

    for k in range(min_vehicles, max_vehicles + 1):
        if verbose:
            print(f"Trying with {k} vehicles...", file=sys.stderr)
        placements = solve_for_k_vehicles(vehicle, items, k, max_time_seconds, verbose)
        if placements:
            return placements
            
    return []


def solve_for_k_vehicles(vehicle: Vehicle, items: List[Item], k: int, time_limit: float, verbose: bool = False) -> Optional[List[Placement]]:
    model = cp_model.CpModel()
    
    n = len(items)
    L, W, H = vehicle.length, vehicle.width, vehicle.height
    
    # --- VARIABLES ---
    
    # Position X globale (dans le "giant bin" de taille k*L)
    x_global = [model.NewIntVar(0, k * L, f'x_global_{i}') for i in range(n)]
    y = [model.NewIntVar(0, W, f'y_{i}') for i in range(n)]
    z = [model.NewIntVar(0, H, f'z_{i}') for i in range(n)]
    
    # Position X locale dans le véhicule
    x_local = [model.NewIntVar(0, L, f'x_local_{i}') for i in range(n)]
    
    # Index du véhicule
    bin_idx = [model.NewIntVar(0, k - 1, f'bin_{i}') for i in range(n)]
    
    # Dimensions effectives (après rotation)
    lx = [model.NewIntVar(0, max(L, W, H), f'lx_{i}') for i in range(n)]
    ly = [model.NewIntVar(0, max(L, W, H), f'ly_{i}') for i in range(n)]
    lz = [model.NewIntVar(0, max(L, W, H), f'lz_{i}') for i in range(n)]

    # Liste des supports valides pour la gravité
    supports = [[] for _ in range(n)]

    # --- CONTRAINTES INDIVIDUELLES ---

    for i, item in enumerate(items):
        # A. Orientation (6 rotations possibles)
        orientations = list(set([
            (item.length, item.width, item.height),
            (item.length, item.height, item.width),
            (item.width, item.length, item.height),
            (item.width, item.height, item.length),
            (item.height, item.length, item.width),
            (item.height, item.width, item.length)
        ]))
        
        b_orient = [model.NewBoolVar(f'orient_{i}_{j}') for j in range(len(orientations))]
        model.Add(sum(b_orient) == 1)
        
        model.Add(lx[i] == sum(b_orient[j] * orientations[j][0] for j in range(len(orientations))))
        model.Add(ly[i] == sum(b_orient[j] * orientations[j][1] for j in range(len(orientations))))
        model.Add(lz[i] == sum(b_orient[j] * orientations[j][2] for j in range(len(orientations))))

        # B. Lien Global <-> Local
        model.Add(x_global[i] == bin_idx[i] * L + x_local[i])

        # C. Limites du véhicule (Boundary)
        model.Add(x_local[i] + lx[i] <= L)
        model.Add(y[i] + ly[i] <= W)
        model.Add(z[i] + lz[i] <= H)

        # D. Gravité (Option 1 : Au sol)
        is_on_floor = model.NewBoolVar(f'floor_{i}')
        model.Add(z[i] == 0).OnlyEnforceIf(is_on_floor)
        model.Add(z[i] != 0).OnlyEnforceIf(is_on_floor.Not())
        supports[i].append(is_on_floor)

    # Symmetry Breaking : Premier item dans le premier véhicule
    if n > 0:
        model.Add(bin_idx[0] == 0)

    # --- CONTRAINTES DE PAIRE ---
    
    for i in range(n):
        for j in range(i + 1, n):
            # E. Non-chevauchement (Non-overlap)
            left = model.NewBoolVar(f'left_{i}_{j}')
            right = model.NewBoolVar(f'right_{i}_{j}')
            behind = model.NewBoolVar(f'behind_{i}_{j}')
            front = model.NewBoolVar(f'front_{i}_{j}')
            below = model.NewBoolVar(f'below_{i}_{j}')
            above = model.NewBoolVar(f'above_{i}_{j}')
            
            model.Add(x_global[i] + lx[i] <= x_global[j]).OnlyEnforceIf(left)
            model.Add(x_global[j] + lx[j] <= x_global[i]).OnlyEnforceIf(right)
            model.Add(y[i] + ly[i] <= y[j]).OnlyEnforceIf(behind)
            model.Add(y[j] + ly[j] <= y[i]).OnlyEnforceIf(front)
            model.Add(z[i] + lz[i] <= z[j]).OnlyEnforceIf(below)
            model.Add(z[j] + lz[j] <= z[i]).OnlyEnforceIf(above)
            
            # Au moins une séparation active
            model.AddBoolOr([left, right, behind, front, below, above])
            
            # F. Délais de livraison (Delivery Time - LIFO)
            if items[i].delivery_time != -1 and items[j].delivery_time != -1:
                b_same_bin = model.NewBoolVar(f'same_bin_{i}_{j}')
                model.Add(bin_idx[i] == bin_idx[j]).OnlyEnforceIf(b_same_bin)
                model.Add(bin_idx[i] != bin_idx[j]).OnlyEnforceIf(b_same_bin.Not())
                
                if items[i].delivery_time < items[j].delivery_time:
                    model.Add(x_local[i] >= x_local[j]).OnlyEnforceIf(b_same_bin)
                elif items[i].delivery_time > items[j].delivery_time:
                    model.Add(x_local[j] >= x_local[i]).OnlyEnforceIf(b_same_bin)

            # G. Gravité (Option 2 : Supporté par un autre objet)
            # j supporte i
            j_supports_i = model.NewBoolVar(f'supp_{j}_{i}')
            model.Add(z[j] + lz[j] == z[i]).OnlyEnforceIf(j_supports_i)
            model.Add(x_global[i] + 1 <= x_global[j] + lx[j]).OnlyEnforceIf(j_supports_i)
            model.Add(x_global[j] + 1 <= x_global[i] + lx[i]).OnlyEnforceIf(j_supports_i)
            model.Add(y[i] + 1 <= y[j] + ly[j]).OnlyEnforceIf(j_supports_i)
            model.Add(y[j] + 1 <= y[i] + ly[i]).OnlyEnforceIf(j_supports_i)
            supports[i].append(j_supports_i)
            
            # i supporte j
            i_supports_j = model.NewBoolVar(f'supp_{i}_{j}')
            model.Add(z[i] + lz[i] == z[j]).OnlyEnforceIf(i_supports_j)
            model.Add(x_global[j] + 1 <= x_global[i] + lx[i]).OnlyEnforceIf(i_supports_j)
            model.Add(x_global[i] + 1 <= x_global[j] + lx[j]).OnlyEnforceIf(i_supports_j)
            model.Add(y[j] + 1 <= y[i] + ly[i]).OnlyEnforceIf(i_supports_j)
            model.Add(y[i] + 1 <= y[j] + ly[j]).OnlyEnforceIf(i_supports_j)
            supports[j].append(i_supports_j)

    # Application Gravité : Chaque objet doit être supporté
    for i in range(n):
        model.AddBoolOr(supports[i])

    # --- OBJECTIF : Compactage ---
    coeff_y = 1
    coeff_z = W + 1
    coeff_x = (H + 1) * coeff_z
    
    model.Minimize(sum(
        coeff_x * x_global[i] + coeff_z * z[i] + coeff_y * y[i] 
        for i in range(n)
    ))

    # Stratégie de Recherche
    model.AddDecisionStrategy(x_global, cp_model.CHOOSE_LOWEST_MIN, cp_model.SELECT_MIN_VALUE)
    model.AddDecisionStrategy(z, cp_model.CHOOSE_LOWEST_MIN, cp_model.SELECT_MIN_VALUE)
    model.AddDecisionStrategy(y, cp_model.CHOOSE_LOWEST_MIN, cp_model.SELECT_MIN_VALUE)

    # --- RÉSOLUTION ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.log_search_progress = False
    
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        result = []
        for i in range(n):
            result.append(Placement(
                item_id=items[i].id,
                vehicle_id=solver.Value(bin_idx[i]),
                x=solver.Value(x_local[i]),
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
    placements.sort(key=lambda p: p.item_id)
    
    for p in placements:
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
