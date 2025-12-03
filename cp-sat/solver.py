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


def get_valid_orientations(item: Item, vehicle: Vehicle) -> List[Tuple[int, int, int]]:
    """Retourne les orientations valides pour un item dans un véhicule."""
    all_orientations = list(set([
        (item.length, item.width, item.height),
        (item.length, item.height, item.width),
        (item.width, item.length, item.height),
        (item.width, item.height, item.length),
        (item.height, item.length, item.width),
        (item.height, item.width, item.length)
    ]))
    return [o for o in all_orientations 
            if o[0] <= vehicle.length and o[1] <= vehicle.width and o[2] <= vehicle.height]


def estimate_best_orientation(item: Item, vehicle: Vehicle) -> Optional[Tuple[int, int, int]]:
    """
    Estime la meilleure orientation pour un colis.
    Stratégie : maximiser l'utilisation de X (profondeur), minimiser Z (hauteur).
    Pour un colis "gros" (>50% d'une dimension), on peut souvent fixer l'orientation.
    """
    valid = get_valid_orientations(item, vehicle)
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0]
    
    # Trier par : X décroissant (remplir en profondeur), puis Z croissant (stable)
    valid.sort(key=lambda o: (-o[0], o[2], o[1]))
    return valid[0]


def estimate_vehicles_ffd(vehicle: Vehicle, items: List[Item]) -> int:
    """
    First Fit Decreasing (FFD) heuristique pour estimer le nombre de véhicules.
    Retourne une borne supérieure réaliste.
    """
    if not items:
        return 0
    
    # Trier les items par volume décroissant
    sorted_items = sorted(items, key=lambda it: it.volume, reverse=True)
    
    # Simuler un placement glouton simplifié (en 1D par volume)
    bins = []  # Liste des volumes restants par véhicule
    vehicle_vol = vehicle.volume
    
    for item in sorted_items:
        # Trouver le premier véhicule où l'item rentre
        placed = False
        for i, remaining in enumerate(bins):
            if remaining >= item.volume:
                bins[i] -= item.volume
                placed = True
                break
        
        if not placed:
            # Nouveau véhicule
            bins.append(vehicle_vol - item.volume)
    
    return len(bins)

def solve_cp_sat(vehicle: Vehicle, items: List[Item], max_time_seconds: float = 60.0) -> List[Placement]:
    """
    Résout le problème avec CP-SAT en minimisant le nombre de véhicules.
    """
    model = cp_model.CpModel()

    # Borne inférieure (volume total / volume véhicule)
    total_volume = sum(item.volume for item in items)
    min_vehicles = max(1, (total_volume + vehicle.volume - 1) // vehicle.volume)
    
    # Borne supérieure via FFD (plus réaliste que n véhicules)
    max_vehicles_ffd = estimate_vehicles_ffd(vehicle, items)
    
    # On ajoute une marge de 1 pour les cas difficiles
    max_vehicles = min(len(items), max_vehicles_ffd + 1)
    
    print(f"Solving for {len(items)} items. Volume LB: {min_vehicles}, FFD UB: {max_vehicles_ffd}", file=sys.stderr)

    for k in range(min_vehicles, max_vehicles + 1):
        print(f"Trying with {k} vehicles...", file=sys.stderr)
        placements = solve_for_k_vehicles(vehicle, items, k, max_time_seconds)
        if placements:
            return placements
            
    return []

def solve_for_k_vehicles(vehicle: Vehicle, items: List[Item], k: int, time_limit: float) -> Optional[List[Placement]]:
    model = cp_model.CpModel()
    
    n = len(items)
    L, W, H = vehicle.length, vehicle.width, vehicle.height
    
    # --- VARIABLES ---
    
    x_global = [model.NewIntVar(0, k * L, f'x_global_{i}') for i in range(n)]
    y = [model.NewIntVar(0, W, f'y_{i}') for i in range(n)]
    z = [model.NewIntVar(0, H, f'z_{i}') for i in range(n)]
    
    x_local = [model.NewIntVar(0, L, f'x_local_{i}') for i in range(n)]
    bin_idx = [model.NewIntVar(0, k - 1, f'bin_{i}') for i in range(n)]
    
    lx = [model.NewIntVar(0, max(L, W, H), f'lx_{i}') for i in range(n)]
    ly = [model.NewIntVar(0, max(L, W, H), f'ly_{i}') for i in range(n)]
    lz = [model.NewIntVar(0, max(L, W, H), f'lz_{i}') for i in range(n)]

    # --- CONTRAINTES INDIVIDUELLES ---

    for i, item in enumerate(items):
        # Obtenir les orientations valides (filtrage rapide)
        valid_orientations = get_valid_orientations(item, vehicle)
        
        if not valid_orientations:
            return None  # UNSAT immédiat
        
        if len(valid_orientations) == 1:
            # Une seule orientation -> fixer directement (le plus rapide)
            o = valid_orientations[0]
            model.Add(lx[i] == o[0])
            model.Add(ly[i] == o[1])
            model.Add(lz[i] == o[2])
        else:
            # Plusieurs orientations -> contrainte de table
            model.AddAllowedAssignments([lx[i], ly[i], lz[i]], valid_orientations)

        # Lien Global <-> Local
        model.Add(x_global[i] == bin_idx[i] * L + x_local[i])
        
        # Limites du véhicule (Boundary)
        model.Add(x_local[i] + lx[i] <= L)
        model.Add(y[i] + ly[i] <= W)
        model.Add(z[i] + lz[i] <= H)
        
        # GRAVITÉ SIMPLIFIÉE : tout au sol (z=0)
        # C'est une approximation mais BEAUCOUP plus rapide (évite O(n²) contraintes)
        model.Add(z[i] == 0)

    # Symmetry Breaking : Premier item en position (0,0,0) du premier véhicule
    if n > 0:
        model.Add(bin_idx[0] == 0)
        model.Add(x_local[0] == 0)
        model.Add(y[0] == 0)

    # --- CONTRAINTES DE PAIRE ---
    
    for i in range(n):
        for j in range(i + 1, n):
            # Non-chevauchement (6 directions possibles)
            left = model.NewBoolVar(f'left_{i}_{j}')
            right = model.NewBoolVar(f'right_{i}_{j}')
            behind = model.NewBoolVar(f'behind_{i}_{j}')
            front = model.NewBoolVar(f'front_{i}_{j}')
            
            model.Add(x_global[i] + lx[i] <= x_global[j]).OnlyEnforceIf(left)
            model.Add(x_global[j] + lx[j] <= x_global[i]).OnlyEnforceIf(right)
            model.Add(y[i] + ly[i] <= y[j]).OnlyEnforceIf(behind)
            model.Add(y[j] + ly[j] <= y[i]).OnlyEnforceIf(front)
            
            # Avec z=0 pour tous, pas besoin de below/above
            # Au moins une séparation active
            model.AddBoolOr([left, right, behind, front])
            
            # Délais de livraison (LIFO) - seulement si pertinent
            if items[i].delivery_time != -1 and items[j].delivery_time != -1:
                if items[i].delivery_time != items[j].delivery_time:
                    b_same_bin = model.NewBoolVar(f'same_bin_{i}_{j}')
                    model.Add(bin_idx[i] == bin_idx[j]).OnlyEnforceIf(b_same_bin)
                    model.Add(bin_idx[i] != bin_idx[j]).OnlyEnforceIf(b_same_bin.Not())
                    
                    if items[i].delivery_time < items[j].delivery_time:
                        model.Add(x_local[i] >= x_local[j]).OnlyEnforceIf(b_same_bin)
                    else:
                        model.Add(x_local[j] >= x_local[i]).OnlyEnforceIf(b_same_bin)

    # --- RÉSOLUTION (Mode faisabilité pure - pas d'optimisation) ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.log_search_progress = False
    solver.parameters.num_search_workers = 8
    
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
