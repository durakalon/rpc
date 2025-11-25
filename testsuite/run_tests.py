"""
Script d'exécution et de test pour les solveurs
Permet de tester un solveur sur toutes les instances et d'en valider les résultats
"""

import sys
import time
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from validator import validate_solution


@dataclass
class TestResult:
    """Résultat d'un test sur une instance"""
    instance: str
    league: str
    solver: str
    status: str  # SAT, UNSAT, TIMEOUT, ERROR
    valid: bool
    nb_vehicles: int
    execution_time: float
    error_message: Optional[str] = None


class SolverRunner:
    """Exécute un solveur sur des instances de test"""
    
    def __init__(self, solver_command: List[str], solver_name: str, 
                 timeout: int = 300, verbose: bool = False):
        """
        Args:
            solver_command: Commande pour exécuter le solveur (ex: ["python", "ad-hoc/run.py"])
            solver_name: Nom du solveur pour les rapports
            timeout: Timeout en secondes
            verbose: Mode verbeux
        """
        self.solver_command = solver_command
        self.solver_name = solver_name
        self.timeout = timeout
        self.verbose = verbose
        self.results: List[TestResult] = []
    
    def run_instance(self, instance_file: Path, output_dir: Path) -> TestResult:
        """
        Exécute le solveur sur une instance
        
        Returns:
            TestResult avec les métriques
        """
        league = instance_file.parent.name
        instance_name = instance_file.stem
        
        # Créer le fichier de sortie
        solver_output_dir = output_dir / self.solver_name / league
        solver_output_dir.mkdir(parents=True, exist_ok=True)
        output_file = solver_output_dir / f"{instance_name}.out"
        
        if self.verbose:
            print(f"  Testing {instance_name}...", end=" ", flush=True)
        
        # Construire la commande
        cmd = self.solver_command + ["-i", str(instance_file), "-o", str(output_file)]
        
        # Exécuter avec timeout
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                timeout=self.timeout,
                capture_output=True,
                text=True
            )
            execution_time = time.time() - start_time
            
            if result.returncode != 0:
                if self.verbose:
                    print(f"ERROR (code {result.returncode})")
                return TestResult(
                    instance=instance_name,
                    league=league,
                    solver=self.solver_name,
                    status="ERROR",
                    valid=False,
                    nb_vehicles=0,
                    execution_time=execution_time,
                    error_message=result.stderr[:200] if result.stderr else "Unknown error"
                )
        
        except subprocess.TimeoutExpired:
            execution_time = self.timeout
            if self.verbose:
                print(f"TIMEOUT ({self.timeout}s)")
            return TestResult(
                instance=instance_name,
                league=league,
                solver=self.solver_name,
                status="TIMEOUT",
                valid=False,
                nb_vehicles=0,
                execution_time=execution_time,
                error_message=f"Timeout after {self.timeout}s"
            )
        
        # Valider la solution
        is_valid = validate_solution(str(instance_file), str(output_file), verbose=False)
        
        # Parser le statut et compter les véhicules
        status, nb_vehicles = self._parse_output(output_file)
        
        if self.verbose:
            if is_valid:
                print(f"[OK] {status} [{nb_vehicles} vehicules, {execution_time:.3f}s]")
            else:
                print(f"[ERR] INVALID")
        
        return TestResult(
            instance=instance_name,
            league=league,
            solver=self.solver_name,
            status=status,
            valid=is_valid,
            nb_vehicles=nb_vehicles,
            execution_time=execution_time
        )
    
    def _parse_output(self, output_file: Path) -> tuple:
        """Parse le fichier de sortie pour extraire le statut et le nombre de véhicules"""
        try:
            with open(output_file, 'r') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            if not lines:
                return "INVALID", 0
            
            status = lines[0]
            if status not in ["SAT", "UNSAT"]:
                return "INVALID", 0
            
            if status == "UNSAT":
                return "UNSAT", 0
            
            # Compter les véhicules utilisés
            vehicles = set()
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    vehicles.add(int(parts[0]))
            
            return "SAT", len(vehicles)
        
        except Exception as e:
            return "ERROR", 0
    
    def run_all_instances(self, instances_dir: Path, output_dir: Path, 
                         leagues: Optional[List[str]] = None):
        """
        Exécute le solveur sur toutes les instances
        
        Args:
            instances_dir: Dossier contenant les instances
            output_dir: Dossier pour les résultats
            leagues: Liste des leagues à tester (None = toutes)
        """
        if leagues is None:
            leagues = ["bronze", "silver", "gold"]
        
        print(f"\n" + "="*60)
        print(f"  Testing {self.solver_name:^45s}")
        print("="*60 + "\n")
        
        for league in leagues:
            league_dir = instances_dir / league
            if not league_dir.exists():
                print(f"[WARN] League {league} not found, skipping...")
                continue
            
            instances = sorted(league_dir.glob("*.txt"))
            if not instances:
                print(f"[WARN] No instances found in {league}")
                continue
            
            print(f"\n=== {league.upper()} ({len(instances)} instances) ===")
            
            for instance in instances:
                result = self.run_instance(instance, output_dir)
                self.results.append(result)
        
        self._print_summary()
        self._save_results(output_dir)
    
    def _print_summary(self):
        """Affiche un résumé des résultats"""
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        
        by_league = {}
        for result in self.results:
            if result.league not in by_league:
                by_league[result.league] = []
            by_league[result.league].append(result)
        
        for league in ["bronze", "silver", "gold"]:
            if league not in by_league:
                continue
            
            results = by_league[league]
            total = len(results)
            valid = sum(1 for r in results if r.valid)
            sat = sum(1 for r in results if r.status == "SAT")
            unsat = sum(1 for r in results if r.status == "UNSAT")
            timeout = sum(1 for r in results if r.status == "TIMEOUT")
            error = sum(1 for r in results if r.status == "ERROR")
            
            avg_time = sum(r.execution_time for r in results if r.valid) / max(valid, 1)
            avg_vehicles = sum(r.nb_vehicles for r in results if r.status == "SAT") / max(sat, 1)
            
            print(f"\n{league.upper()}:")
            print(f"  Total: {total}")
            print(f"  Valid: {valid}/{total} ({valid/total*100:.1f}%)")
            print(f"  SAT: {sat}, UNSAT: {unsat}, TIMEOUT: {timeout}, ERROR: {error}")
            if sat > 0:
                print(f"  Avg vehicles: {avg_vehicles:.1f}")
            print(f"  Avg time: {avg_time:.3f}s")
    
    def _save_results(self, output_dir: Path):
        """Sauvegarde les résultats en JSON"""
        results_file = output_dir / f"{self.solver_name}_results.json"
        
        with open(results_file, 'w') as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)
        
        print(f"\n[OK] Results saved to: {results_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test runner for solvers")
    parser.add_argument("--solver", type=str, required=True,
                       help="Path to solver script (e.g., ../ad-hoc/run.py)")
    parser.add_argument("--name", type=str, required=True,
                       help="Solver name for reports")
    parser.add_argument("--instances", type=str, default="instances",
                       help="Instances directory")
    parser.add_argument("--output", type=str, default="results",
                       help="Output directory")
    parser.add_argument("--leagues", type=str, nargs="+",
                       choices=["bronze", "silver", "gold"],
                       help="Leagues to test (default: all)")
    parser.add_argument("--timeout", type=int, default=300,
                       help="Timeout per instance (seconds)")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Construire la commande du solveur
    solver_path = Path(args.solver)
    if not solver_path.exists():
        print(f"[ERR] Solver not found: {solver_path}")
        sys.exit(1)
    
    solver_command = ["python", str(solver_path)]
    
    # Créer le runner
    runner = SolverRunner(
        solver_command=solver_command,
        solver_name=args.name,
        timeout=args.timeout,
        verbose=args.verbose
    )
    
    # Exécuter les tests
    instances_dir = Path(args.instances)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    runner.run_all_instances(instances_dir, output_dir, args.leagues)


if __name__ == "__main__":
    main()
