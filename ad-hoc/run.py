"""
Script d'exécution du solveur ad-hoc
Permet de tester différentes heuristiques et de comparer les résultats
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

from solver import (
    solve_problem, 
    SortingHeuristic, 
    parse_input, 
    BinPackingSolver
)


def read_input_file(filepath: str) -> str:
    """Lit un fichier d'entrée"""
    with open(filepath, 'r') as f:
        return f.read()


def write_output_file(filepath: str, content: str):
    """Écrit le résultat dans un fichier"""
    with open(filepath, 'w') as f:
        f.write(content)


def solve_with_best_heuristic(input_text: str, verbose: bool = False) -> Tuple[str, SortingHeuristic, int]:
    """
    Essaie toutes les heuristiques et retourne la meilleure solution
    Retourne: (output, meilleure_heuristique, nombre_de_véhicules)
    """
    heuristics = [
        SortingHeuristic.VOLUME_DECREASING,
        SortingHeuristic.LONGEST_SIDE_DECREASING,
        SortingHeuristic.AREA_DECREASING,
        SortingHeuristic.HEIGHT_DECREASING,
    ]
    
    best_result = None
    best_heuristic = None
    best_nb_vehicles = float('inf')
    
    vehicle, items = parse_input(input_text)
    
    for heuristic in heuristics:
        solver = BinPackingSolver(vehicle, items, heuristic)
        success = solver.solve()
        
        if success:
            nb_vehicles = len(solver.vehicles)
            
            if verbose:
                stats = solver.get_statistics()
                print(f"Heuristique: {heuristic.value}", file=sys.stderr)
                print(f"  Véhicules: {nb_vehicles}", file=sys.stderr)
                print(f"  Utilisation: {stats['average_utilization']:.2%}", file=sys.stderr)
            
            if nb_vehicles < best_nb_vehicles:
                best_nb_vehicles = nb_vehicles
                best_heuristic = heuristic
                best_result = solver
    
    if best_result is None:
        # Aucune heuristique n'a trouvé de solution
        return "UNSAT", heuristics[0], 0
    
    # Formater la sortie avec la meilleure solution
    from solver import format_output
    output = format_output(best_result)
    
    return output, best_heuristic, best_nb_vehicles


def main():
    parser = argparse.ArgumentParser(
        description="Solveur ad-hoc pour le problème de bin packing 3D",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  # Résoudre depuis stdin vers stdout
  python run.py < input.txt > output.txt
  
  # Résoudre depuis un fichier
  python run.py -i input.txt -o output.txt
  
  # Trouver la meilleure heuristique
  python run.py -i input.txt --best -v
  
  # Utiliser une heuristique spécifique
  python run.py -i input.txt --heuristic volume
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        help='Fichier d\'entrée (défaut: stdin)',
        default=None
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Fichier de sortie (défaut: stdout)',
        default=None
    )
    
    parser.add_argument(
        '--heuristic',
        type=str,
        choices=['volume', 'longest_side', 'area', 'height'],
        default='volume',
        help='Heuristique de tri à utiliser (défaut: volume)'
    )
    
    parser.add_argument(
        '--best',
        action='store_true',
        help='Essaie toutes les heuristiques et sélectionne la meilleure'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Mode verbeux (affiche les statistiques sur stderr)'
    )
    
    args = parser.parse_args()
    
    # Lecture de l'entrée
    if args.input:
        input_text = read_input_file(args.input)
    else:
        input_text = sys.stdin.read()
    
    # Résolution
    if args.best:
        output, best_heuristic, nb_vehicles = solve_with_best_heuristic(input_text, args.verbose)
        if args.verbose and output != "UNSAT":
            print(f"\nMeilleure heuristique: {best_heuristic.value}", file=sys.stderr)
            print(f"Nombre de véhicules: {nb_vehicles}", file=sys.stderr)
    else:
        # Conversion de l'heuristique
        heuristic_map = {
            'volume': SortingHeuristic.VOLUME_DECREASING,
            'longest_side': SortingHeuristic.LONGEST_SIDE_DECREASING,
            'area': SortingHeuristic.AREA_DECREASING,
            'height': SortingHeuristic.HEIGHT_DECREASING,
        }
        heuristic = heuristic_map[args.heuristic]
        output = solve_problem(input_text, heuristic, args.verbose)
    
    # Écriture de la sortie
    if args.output:
        write_output_file(args.output, output)
        if args.verbose:
            print(f"\nRésultat écrit dans: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
