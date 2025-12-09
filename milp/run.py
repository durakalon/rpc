"""
Script d'exécution du solveur MILP
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

from solver import solve_milp, parse_input, format_output

def read_input_file(filepath: str) -> str:
    """Lit un fichier d'entrée"""
    with open(filepath, 'r') as f:
        return f.read()

def write_output_file(filepath: str, content: str):
    """Écrit le résultat dans un fichier"""
    with open(filepath, 'w') as f:
        f.write(content)

def main():
    parser = argparse.ArgumentParser(description='Solveur MILP pour le problème de bin packing 3D')
    
    parser.add_argument(
        '-i', '--input',
        nargs='?',
        type=str,
        help='Fichier d\'entrée (défaut: stdin)',
        default=None
    )
    
    parser.add_argument(
        '-o', '--output',
        nargs='?',
        type=str,
        help='Fichier de sortie (défaut: stdout)',
        default=None
    )
    
    parser.add_argument(
        '-t', '--timeout',
        type=float,
        help='Temps maximum en secondes (défaut: 60)',
        default=60.0
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Mode verbeux'
    )
    
    args = parser.parse_args()
    
    # Lecture de l'entrée
    if args.input:
        input_text = read_input_file(args.input)
    else:
        input_text = sys.stdin.read()
    
    # Parsing
    vehicle, items = parse_input(input_text)
    
    if not vehicle or not items:
        result = "UNSAT"
    else:
        if args.verbose:
            print(f"Vehicle: {vehicle.length}x{vehicle.width}x{vehicle.height}", file=sys.stderr)
            print(f"Items: {len(items)}", file=sys.stderr)
        
        # Résolution
        placements = solve_milp(vehicle, items, max_time_seconds=args.timeout, verbose=args.verbose)
        result = format_output(placements)
    
    # Écriture de la sortie
    if args.output:
        write_output_file(args.output, result)
    else:
        print(result)

if __name__ == "__main__":
    main()
