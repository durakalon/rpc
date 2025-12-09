"""
MILP Solver for 3D Bin Packing using PuLP (CBC solver)

Ce solveur utilise la Programmation Linéaire en Nombres Entiers Mixtes (MILP).
Avantages par rapport à CP-SAT :
- Meilleure gestion des objectifs linéaires (minimisation)
- Peut être plus rapide sur certaines instances grâce aux coupes LP
- Permet d'utiliser des solveurs commerciaux (Gurobi, CPLEX) si disponibles

Inconvénients :
- Moins flexible pour les contraintes logiques complexes
- Nécessite une linéarisation explicite des disjonctions (Big-M)
"""

import sys
from dataclasses import dataclass
from typing import List, Tuple, Optional
import pulp

@dataclass
class Item:
    """Représente un colis à livrer"""
    id: int
    length: int
    width: int
    height: int
    delivery_time: int
    
    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

@dataclass
class Vehicle:
    """Représente un véhicule disponible"""
    length: int
    width: int
    height: int
    
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
    length: int
    width: int
    height: int

def parse_input(input_text: str) -> Tuple[Vehicle, List[Item]]:
    lines = input_text.strip().split('\n')
    if not lines:
        return None, []
        
    vehicle_dims = list(map(int, lines[0].split()))
    vehicle = Vehicle(vehicle_dims[0], vehicle_dims[1], vehicle_dims[2])
    
    try:
        nb_items = int(lines[1])
    except IndexError:
        return vehicle, []
    
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

def solve_milp(vehicle: Vehicle, items: List[Item], max_time_seconds: float = 60.0, verbose: bool = False) -> List[Placement]:
    """
    Résout le problème avec MILP en cherchant le nombre minimal de véhicules.
    """
    total_volume = sum(item.volume for item in items)
    min_vehicles = max(1, (total_volume + vehicle.volume - 1) // vehicle.volume)
    max_vehicles = len(items)
    
    if verbose:
        print(f"MILP: Solving for {len(items)} items. Volume LB: {min_vehicles}", file=sys.stderr)

    for k in range(min_vehicles, max_vehicles + 1):
        if verbose:
            print(f"MILP: Trying with {k} vehicles...", file=sys.stderr)
        placements = solve_for_k_vehicles(vehicle, items, k, max_time_seconds)
        if placements:
            return placements
            
    return []

def solve_for_k_vehicles(vehicle: Vehicle, items: List[Item], k: int, time_limit: float) -> Optional[List[Placement]]:
    """
    Résout le problème MILP pour exactement k véhicules.
    
    Formulation :
    - Variables continues : x[i], y[i], z[i] (positions)
    - Variables binaires : 
        - orientation[i][r] : 1 si item i a rotation r
        - sep[i][j][d] : 1 si items i,j sont séparés sur dimension d
        - bin_assign[i][b] : 1 si item i est dans véhicule b
    """
    n = len(items)
    L, W, H = vehicle.length, vehicle.width, vehicle.height
    
    # Big-M (borne supérieure pour les contraintes disjonctives)
    M = max(L, W, H) * k + 1
    
    # Créer le modèle
    model = pulp.LpProblem("3D_Bin_Packing", pulp.LpMinimize)
    
    # --- VARIABLES ---
    
    # Positions (continues mais bornées)
    x = [pulp.LpVariable(f'x_{i}', lowBound=0, upBound=k*L, cat='Continuous') for i in range(n)]
    y = [pulp.LpVariable(f'y_{i}', lowBound=0, upBound=W, cat='Continuous') for i in range(n)]
    z = [pulp.LpVariable(f'z_{i}', lowBound=0, upBound=H, cat='Continuous') for i in range(n)]
    
    # Dimensions effectives après rotation
    lx = [pulp.LpVariable(f'lx_{i}', lowBound=0, cat='Continuous') for i in range(n)]
    ly = [pulp.LpVariable(f'ly_{i}', lowBound=0, cat='Continuous') for i in range(n)]
    lz = [pulp.LpVariable(f'lz_{i}', lowBound=0, cat='Continuous') for i in range(n)]
    
    # Variables d'orientation (binaires)
    # Pour simplifier, on considère 6 rotations par item
    orientations_per_item = []
    orient_vars = []
    
    for i, item in enumerate(items):
        orients = list(set([
            (item.length, item.width, item.height),
            (item.length, item.height, item.width),
            (item.width, item.length, item.height),
            (item.width, item.height, item.length),
            (item.height, item.length, item.width),
            (item.height, item.width, item.length)
        ]))
        orientations_per_item.append(orients)
        o_vars = [pulp.LpVariable(f'orient_{i}_{r}', cat='Binary') for r in range(len(orients))]
        orient_vars.append(o_vars)
        
        # Une seule orientation
        model += pulp.lpSum(o_vars) == 1, f"one_orient_{i}"
        
        # Lier dimensions à l'orientation
        model += lx[i] == pulp.lpSum(o_vars[r] * orients[r][0] for r in range(len(orients))), f"lx_def_{i}"
        model += ly[i] == pulp.lpSum(o_vars[r] * orients[r][1] for r in range(len(orients))), f"ly_def_{i}"
        model += lz[i] == pulp.lpSum(o_vars[r] * orients[r][2] for r in range(len(orients))), f"lz_def_{i}"
    
    # Variables d'assignation au véhicule (binaires)
    bin_assign = [[pulp.LpVariable(f'bin_{i}_{b}', cat='Binary') for b in range(k)] for i in range(n)]
    
    for i in range(n):
        # Chaque item dans exactement un véhicule
        model += pulp.lpSum(bin_assign[i][b] for b in range(k)) == 1, f"one_bin_{i}"
    
    # Position x locale dans le véhicule
    x_local = [pulp.LpVariable(f'x_local_{i}', lowBound=0, upBound=L, cat='Continuous') for i in range(n)]
    
    # Lien x_global = bin_idx * L + x_local
    # On utilise : x[i] = sum_b (bin_assign[i][b] * b * L) + x_local[i]
    for i in range(n):
        model += x[i] == pulp.lpSum(bin_assign[i][b] * b * L for b in range(k)) + x_local[i], f"x_global_{i}"
    
    # --- CONTRAINTES ---
    
    # 1. Limites du véhicule (Boundary)
    for i in range(n):
        model += x_local[i] + lx[i] <= L, f"bound_x_{i}"
        model += y[i] + ly[i] <= W, f"bound_y_{i}"
        model += z[i] + lz[i] <= H, f"bound_z_{i}"
    
    # 2. Non-chevauchement (Big-M formulation)
    # Pour chaque paire (i, j), au moins une des 6 séparations doit être vraie
    for i in range(n):
        for j in range(i + 1, n):
            # Variables de séparation (6 directions)
            sep_left = pulp.LpVariable(f'sep_left_{i}_{j}', cat='Binary')    # i à gauche de j
            sep_right = pulp.LpVariable(f'sep_right_{i}_{j}', cat='Binary')  # i à droite de j
            sep_behind = pulp.LpVariable(f'sep_behind_{i}_{j}', cat='Binary') # i derrière j
            sep_front = pulp.LpVariable(f'sep_front_{i}_{j}', cat='Binary')   # i devant j
            sep_below = pulp.LpVariable(f'sep_below_{i}_{j}', cat='Binary')   # i dessous j
            sep_above = pulp.LpVariable(f'sep_above_{i}_{j}', cat='Binary')   # i dessus j
            
            # Au moins une séparation active
            model += sep_left + sep_right + sep_behind + sep_front + sep_below + sep_above >= 1, f"sep_{i}_{j}"
            
            # Big-M constraints pour la séparation
            # Si sep_left=1 : x[i] + lx[i] <= x[j]
            # Sinon (sep_left=0) : x[i] + lx[i] <= x[j] + M (toujours vrai)
            model += x[i] + lx[i] <= x[j] + M * (1 - sep_left), f"left_{i}_{j}"
            model += x[j] + lx[j] <= x[i] + M * (1 - sep_right), f"right_{i}_{j}"
            model += y[i] + ly[i] <= y[j] + M * (1 - sep_behind), f"behind_{i}_{j}"
            model += y[j] + ly[j] <= y[i] + M * (1 - sep_front), f"front_{i}_{j}"
            model += z[i] + lz[i] <= z[j] + M * (1 - sep_below), f"below_{i}_{j}"
            model += z[j] + lz[j] <= z[i] + M * (1 - sep_above), f"above_{i}_{j}"
    
    # 3. Gravité simplifiée : z[i] = 0 (tout au sol)
    # Note: La gravité complète avec support nécessite des variables supplémentaires
    # Pour le MILP, on simplifie en mettant tout au sol par défaut
    for i in range(n):
        model += z[i] == 0, f"gravity_{i}"
    
    # 4. Symmetry Breaking
    if n > 0:
        model += bin_assign[0][0] == 1, "sym_break"
    
    # --- OBJECTIF ---
    # Minimiser la somme des positions X (compacter vers le fond)
    model += pulp.lpSum(x[i] for i in range(n)), "minimize_x"
    
    # --- RÉSOLUTION ---
    solver = pulp.PULP_CBC_CMD(msg=1, timeLimit=time_limit)
    
    status = model.solve(solver)
    
    if status == pulp.LpStatusOptimal or status == pulp.LpStatusNotSolved:
        # Vérifier si une solution a été trouvée
        if all(x[i].varValue is not None for i in range(n)):
            result = []
            for i in range(n):
                # Trouver le véhicule assigné
                vehicle_id = 0
                for b in range(k):
                    if bin_assign[i][b].varValue is not None and bin_assign[i][b].varValue > 0.5:
                        vehicle_id = b
                        break
                
                result.append(Placement(
                    item_id=items[i].id,
                    vehicle_id=vehicle_id,
                    x=int(round(x_local[i].varValue)),
                    y=int(round(y[i].varValue)),
                    z=int(round(z[i].varValue)),
                    length=int(round(lx[i].varValue)),
                    width=int(round(ly[i].varValue)),
                    height=int(round(lz[i].varValue))
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
        placements = solve_milp(vehicle, items)
        print(format_output(placements))
    else:
        print("UNSAT")
