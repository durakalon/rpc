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
    
    n = len(items)
    
    # --- VARIABLES ---
    
    # 1. Coordonnées Globales (Approche "Giant Bin")
    # On aligne virtuellement les K véhicules sur l'axe X.
    # X_global va de 0 à K * L.
    # Le véhicule k occupe l'intervalle [k*L, (k+1)*L].
    x_global = [model.NewIntVar(0, k * vehicle.length, f'x_global_{i}') for i in range(n)]
    y = [model.NewIntVar(0, vehicle.width, f'y_{i}') for i in range(n)]
    z = [model.NewIntVar(0, vehicle.height, f'z_{i}') for i in range(n)]
    
    # 2. Coordonnées Locales & Index Véhicule
    # x_local est la position relative dans le véhicule (0 à L)
    x_local = [model.NewIntVar(0, vehicle.length, f'x_local_{i}') for i in range(n)]
    bin_idx = [model.NewIntVar(0, k - 1, f'bin_{i}') for i in range(n)]
    
    # 3. Dimensions effectives (après rotation)
    lx = [model.NewIntVar(0, max(vehicle.length, vehicle.width, vehicle.height), f'lx_{i}') for i in range(n)]
    ly = [model.NewIntVar(0, max(vehicle.length, vehicle.width, vehicle.height), f'ly_{i}') for i in range(n)]
    lz = [model.NewIntVar(0, max(vehicle.length, vehicle.width, vehicle.height), f'lz_{i}') for i in range(n)]

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
        # x_global = bin_idx * L + x_local
        model.Add(x_global[i] == bin_idx[i] * vehicle.length + x_local[i])
        
        # C. Limites du véhicule (Boundary)
        # L'objet doit tenir entièrement dans son véhicule assigné
        model.Add(x_local[i] + lx[i] <= vehicle.length)
        model.Add(y[i] + ly[i] <= vehicle.width)
        model.Add(z[i] + lz[i] <= vehicle.height)

        # D. Gravité (Option 1 : Au sol)
        is_on_floor = model.NewBoolVar(f'floor_{i}')
        model.Add(z[i] == 0).OnlyEnforceIf(is_on_floor)
        model.Add(z[i] != 0).OnlyEnforceIf(is_on_floor.Not())
        supports[i].append(is_on_floor)

    # Symmetry Breaking : Si on a des items, on force le premier dans le premier véhicule
    # Cela évite de tester les permutations de véhicules vides/pleins identiques
    if n > 0:
        model.Add(bin_idx[0] == 0)

    # --- CONTRAINTES DE PAIRE ---
    
    for i in range(n):
        for j in range(i + 1, n):
            # E. Non-chevauchement (Non-overlap)
            # On utilise les coordonnées GLOBALES.
            # Si deux objets sont dans des véhicules différents, leurs x_global sont disjoints,
            # donc la contrainte "left" ou "right" sera satisfaite trivialement.
            
            left = model.NewBoolVar(f'left_{i}_{j}')   # i à gauche de j
            right = model.NewBoolVar(f'right_{i}_{j}')  # i à droite de j
            behind = model.NewBoolVar(f'behind_{i}_{j}') # i derrière j (Y)
            front = model.NewBoolVar(f'front_{i}_{j}')   # i devant j (Y)
            below = model.NewBoolVar(f'below_{i}_{j}')   # i dessous j (Z)
            above = model.NewBoolVar(f'above_{i}_{j}')   # i dessus j (Z)
            
            model.Add(x_global[i] + lx[i] <= x_global[j]).OnlyEnforceIf(left)
            model.Add(x_global[j] + lx[j] <= x_global[i]).OnlyEnforceIf(right)
            model.Add(y[i] + ly[i] <= y[j]).OnlyEnforceIf(behind)
            model.Add(y[j] + ly[j] <= y[i]).OnlyEnforceIf(front)
            model.Add(z[i] + lz[i] <= z[j]).OnlyEnforceIf(below)
            model.Add(z[j] + lz[j] <= z[i]).OnlyEnforceIf(above)
            
            # Ils ne doivent pas se chevaucher (au moins une séparation active)
            model.AddBoolOr([left, right, behind, front, below, above])
            
            # F. Délais de livraison (Delivery Time - LIFO)
            # Si i doit être livré AVANT j (D_i < D_j), i doit être plus proche de la porte.
            # Porte supposée à x_local = Length. Donc i doit avoir un x_local plus grand.
            # Cette contrainte ne s'applique que s'ils sont dans le MÊME véhicule.
            
            if items[i].delivery_time != -1 and items[j].delivery_time != -1:
                b_same_bin = model.NewBoolVar(f'same_bin_{i}_{j}')
                model.Add(bin_idx[i] == bin_idx[j]).OnlyEnforceIf(b_same_bin)
                model.Add(bin_idx[i] != bin_idx[j]).OnlyEnforceIf(b_same_bin.Not())
                
                if items[i].delivery_time < items[j].delivery_time:
                    model.Add(x_local[i] >= x_local[j]).OnlyEnforceIf(b_same_bin)
                elif items[i].delivery_time > items[j].delivery_time:
                    model.Add(x_local[j] >= x_local[i]).OnlyEnforceIf(b_same_bin)

            # G. Gravité (Option 2 : Supporté par un autre objet)
            # j supporte i SI :
            # 1. j est juste en dessous de i (contact Z)
            # 2. Ils se chevauchent physiquement en X et Y (Area > 0)
            # Note : Le chevauchement X global implique qu'ils sont dans le même véhicule.
            
            # Cas 1: j supporte i
            j_supports_i = model.NewBoolVar(f'supp_{j}_{i}')
            
            # Contact Z
            model.Add(z[j] + lz[j] == z[i]).OnlyEnforceIf(j_supports_i)
            
            # Chevauchement X Global (Strict inequality for overlap > 0)
            # x_start_i < x_end_j  AND  x_start_j < x_end_i
            model.Add(x_global[i] + 1 <= x_global[j] + lx[j]).OnlyEnforceIf(j_supports_i)
            model.Add(x_global[j] + 1 <= x_global[i] + lx[i]).OnlyEnforceIf(j_supports_i)
            
            # Chevauchement Y
            model.Add(y[i] + 1 <= y[j] + ly[j]).OnlyEnforceIf(j_supports_i)
            model.Add(y[j] + 1 <= y[i] + ly[i]).OnlyEnforceIf(j_supports_i)
            
            supports[i].append(j_supports_i)
            
            # Cas 2: i supporte j (Symétrique)
            i_supports_j = model.NewBoolVar(f'supp_{i}_{j}')
            
            model.Add(z[i] + lz[i] == z[j]).OnlyEnforceIf(i_supports_j)
            model.Add(x_global[j] + 1 <= x_global[i] + lx[i]).OnlyEnforceIf(i_supports_j)
            model.Add(x_global[i] + 1 <= x_global[j] + lx[j]).OnlyEnforceIf(i_supports_j)
            model.Add(y[j] + 1 <= y[i] + ly[i]).OnlyEnforceIf(i_supports_j)
            model.Add(y[i] + 1 <= y[j] + ly[j]).OnlyEnforceIf(i_supports_j)
            
            supports[j].append(i_supports_j)

    # Application Gravité : Chaque objet doit être supporté (Sol OU Autre objet)
    for i in range(n):
        model.AddBoolOr(supports[i])

    # --- OBJECTIF & HEURISTIQUES ---

    # 1. Fonction Objectif : Compactage
    # On veut remplir "du fond vers la sortie" (Minimiser X)
    # Et "par le bas" (Minimiser Z)
    # Priorité : X > Z > Y
    # Cela permet de tasser les objets au fond et en bas, évitant les trous.
    
    # Coefficients pour l'ordre lexicographique
    # On s'assure que la minimisation de X l'emporte sur Z, et Z sur Y.
    coeff_y = 1
    coeff_z = vehicle.width + 1
    coeff_x = (vehicle.height + 1) * coeff_z
    
    # On minimise la somme pondérée des coordonnées
    model.Minimize(sum(
        coeff_x * x_global[i] + 
        coeff_z * z[i] + 
        coeff_y * y[i] 
        for i in range(n)
    ))

    # 2. Stratégie de Recherche (Heuristique)
    # On guide le solveur pour qu'il explore d'abord les positions au fond et en bas.
    # Cela accélère grandement la recherche d'une première solution valide et compacte.
    model.AddDecisionStrategy(x_global, cp_model.CHOOSE_LOWEST_MIN, cp_model.SELECT_MIN_VALUE)
    model.AddDecisionStrategy(z, cp_model.CHOOSE_LOWEST_MIN, cp_model.SELECT_MIN_VALUE)
    model.AddDecisionStrategy(y, cp_model.CHOOSE_LOWEST_MIN, cp_model.SELECT_MIN_VALUE)

    # --- RÉSOLUTION ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.log_search_progress = True
    # solver.parameters.num_search_workers = 8 # Activer si multi-coeur disponible
    
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
