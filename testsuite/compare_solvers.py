"""
Script de comparaison de solveurs
Compare les performances de différents solveurs selon plusieurs indicateurs
"""

import json
import sys
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
import statistics


@dataclass
class SolverMetrics:
    """Métriques agrégées pour un solveur"""
    name: str
    total_instances: int
    valid_solutions: int
    sat_count: int
    unsat_count: int
    timeout_count: int
    error_count: int
    avg_execution_time: float
    median_execution_time: float
    total_vehicles: int
    avg_vehicles_per_sat: float
    success_rate: float


class SolverComparator:
    """Compare les performances de plusieurs solveurs"""
    
    def __init__(self):
        self.solvers_data: Dict[str, List[dict]] = {}
    
    def load_results(self, results_file: Path) -> str:
        """
        Charge les résultats d'un solveur
        
        Returns:
            Nom du solveur
        """
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        if not results:
            raise ValueError(f"No results in {results_file}")
        
        solver_name = results[0]['solver']
        self.solvers_data[solver_name] = results
        
        return solver_name
    
    def compute_metrics(self, solver_name: str, league: str = None) -> SolverMetrics:
        """
        Calcule les métriques pour un solveur
        
        Args:
            solver_name: Nom du solveur
            league: Filtrer par league (None = toutes)
        """
        results = self.solvers_data[solver_name]
        
        # Filtrer par league si spécifié
        if league:
            results = [r for r in results if r['league'] == league]
        
        if not results:
            return None
        
        total = len(results)
        valid = sum(1 for r in results if r['valid'])
        sat = sum(1 for r in results if r['status'] == 'SAT')
        unsat = sum(1 for r in results if r['status'] == 'UNSAT')
        timeout = sum(1 for r in results if r['status'] == 'TIMEOUT')
        error = sum(1 for r in results if r['status'] == 'ERROR')
        
        exec_times = [r['execution_time'] for r in results if r['valid']]
        avg_time = statistics.mean(exec_times) if exec_times else 0
        median_time = statistics.median(exec_times) if exec_times else 0
        
        sat_results = [r for r in results if r['status'] == 'SAT']
        total_vehicles = sum(r['nb_vehicles'] for r in sat_results)
        avg_vehicles = total_vehicles / len(sat_results) if sat_results else 0
        
        success_rate = valid / total if total > 0 else 0
        
        return SolverMetrics(
            name=solver_name,
            total_instances=total,
            valid_solutions=valid,
            sat_count=sat,
            unsat_count=unsat,
            timeout_count=timeout,
            error_count=error,
            avg_execution_time=avg_time,
            median_execution_time=median_time,
            total_vehicles=total_vehicles,
            avg_vehicles_per_sat=avg_vehicles,
            success_rate=success_rate
        )
    
    def compare_all(self, leagues: List[str] = None):
        """
        Compare tous les solveurs chargés
        
        Args:
            leagues: Leagues à analyser (None = toutes)
        """
        if not self.solvers_data:
            print("No solver data loaded")
            return
        
        if leagues is None:
            leagues = ["bronze", "silver", "gold", "overall"]
        
        print("\n" + "="*70)
        print("                   COMPARAISON DES SOLVEURS")
        print("="*70 + "\n")
        
        for league in leagues:
            if league == "overall":
                print("\n" + "="*70)
                print("OVERALL (toutes leagues confondues)")
                print("="*70)
                self._print_comparison_table(None)
            else:
                print("\n" + "="*70)
                print(f"{league.upper()}")
                print("="*70)
                self._print_comparison_table(league)
    
    def _print_comparison_table(self, league: str = None):
        """Affiche un tableau comparatif"""
        
        # Calculer les métriques pour chaque solveur
        metrics_list = []
        for solver_name in self.solvers_data.keys():
            metrics = self.compute_metrics(solver_name, league)
            if metrics:
                metrics_list.append(metrics)
        
        if not metrics_list:
            print("  No data for this league")
            return
        
        # En-tête
        print(f"\n{'Solveur':<20} {'Success':>8} {'SAT':>6} {'UNSAT':>6} {'Timeout':>8} {'Temps Moy':>11} {'Véh. Moy':>10}")
        print("-" * 85)
        
        # Lignes
        for m in sorted(metrics_list, key=lambda x: (-x.success_rate, x.avg_execution_time)):
            print(f"{m.name:<20} "
                  f"{m.success_rate:>7.1%} "
                  f"{m.sat_count:>6} "
                  f"{m.unsat_count:>6} "
                  f"{m.timeout_count:>8} "
                  f"{m.avg_execution_time:>10.3f}s "
                  f"{m.avg_vehicles_per_sat:>9.1f}")
        
        # Analyse détaillée
        self._print_detailed_analysis(metrics_list, league)
    
    def _print_detailed_analysis(self, metrics_list: List[SolverMetrics], league: str = None):
        """Affiche une analyse détaillée"""
        
        if len(metrics_list) < 2:
            return
        
        print("\n" + "-"*85)
        print("ANALYSE DÉTAILLÉE")
        print("-"*85)
        
        # Meilleur taux de succes
        best_success = max(metrics_list, key=lambda m: m.success_rate)
        print(f"\n[OK] Meilleur taux de succes:")
        print(f"  {best_success.name}: {best_success.success_rate:.1%} "
              f"({best_success.valid_solutions}/{best_success.total_instances})")
        
        # Plus rapide
        valid_solvers = [m for m in metrics_list if m.valid_solutions > 0]
        if valid_solvers:
            fastest = min(valid_solvers, key=lambda m: m.avg_execution_time)
            print(f"\n[FAST] Plus rapide:")
            print(f"  {fastest.name}: {fastest.avg_execution_time:.3f}s (moyenne)")
        
        # Moins de véhicules
        sat_solvers = [m for m in metrics_list if m.sat_count > 0]
        if sat_solvers:
            best_vehicles = min(sat_solvers, key=lambda m: m.avg_vehicles_per_sat)
            print(f"\n[MIN] Moins de vehicules utilises:")
            print(f"  {best_vehicles.name}: {best_vehicles.avg_vehicles_per_sat:.1f} véhicules en moyenne")
            print(f"  Total: {best_vehicles.total_vehicles} véhicules pour {best_vehicles.sat_count} instances SAT")
        
        # Comparaison paire à paire
        if len(metrics_list) == 2:
            self._print_pairwise_comparison(metrics_list[0], metrics_list[1])
    
    def _print_pairwise_comparison(self, m1: SolverMetrics, m2: SolverMetrics):
        """Compare deux solveurs en détail"""
        print(f"\n" + "="*85)
        print(f"COMPARAISON: {m1.name} vs {m2.name}")
        print("="*85)
        
        # Succès
        diff_success = (m1.success_rate - m2.success_rate) * 100
        winner_success = m1.name if diff_success > 0 else m2.name
        print(f"\nTaux de succès: {winner_success} est meilleur de {abs(diff_success):.1f}%")
        
        # Temps
        if m1.avg_execution_time > 0 and m2.avg_execution_time > 0:
            ratio_time = m1.avg_execution_time / m2.avg_execution_time
            if ratio_time > 1:
                print(f"Temps d'exécution: {m2.name} est {ratio_time:.1f}× plus rapide")
            else:
                print(f"Temps d'exécution: {m1.name} est {1/ratio_time:.1f}× plus rapide")
        
        # Véhicules
        if m1.avg_vehicles_per_sat > 0 and m2.avg_vehicles_per_sat > 0:
            diff_vehicles = m1.avg_vehicles_per_sat - m2.avg_vehicles_per_sat
            if abs(diff_vehicles) > 0.1:
                winner_vehicles = m2.name if diff_vehicles > 0 else m1.name
                print(f"Véhicules: {winner_vehicles} utilise {abs(diff_vehicles):.1f} véhicules de moins en moyenne")
        
        # Recommandation
        print(f"\n{'─'*85}")
        print("RECOMMANDATION:")
        
        # Critère de décision
        if m1.success_rate > m2.success_rate + 0.05:  # 5% de différence
            print(f"→ {m1.name} recommandé (meilleur taux de succès)")
        elif m2.success_rate > m1.success_rate + 0.05:
            print(f"→ {m2.name} recommandé (meilleur taux de succès)")
        elif m1.avg_vehicles_per_sat < m2.avg_vehicles_per_sat - 0.5:
            print(f"→ {m1.name} recommandé (moins de véhicules)")
        elif m2.avg_vehicles_per_sat < m1.avg_vehicles_per_sat - 0.5:
            print(f"→ {m2.name} recommandé (moins de véhicules)")
        elif m1.avg_execution_time < m2.avg_execution_time * 0.8:
            print(f"→ {m1.name} recommandé (plus rapide)")
        elif m2.avg_execution_time < m1.avg_execution_time * 0.8:
            print(f"→ {m2.name} recommandé (plus rapide)")
        else:
            print("→ Performances comparables, choix selon le contexte")
    
    def generate_report(self, output_file: Path):
        """Génère un rapport JSON détaillé"""
        report = {
            'solvers': list(self.solvers_data.keys()),
            'leagues': {}
        }
        
        for league in ["bronze", "silver", "gold", "overall"]:
            league_key = league if league != "overall" else "all"
            report['leagues'][league_key] = {}
            
            for solver_name in self.solvers_data.keys():
                metrics = self.compute_metrics(
                    solver_name, 
                    None if league == "overall" else league
                )
                if metrics:
                    report['leagues'][league_key][solver_name] = {
                        'success_rate': metrics.success_rate,
                        'avg_time': metrics.avg_execution_time,
                        'median_time': metrics.median_execution_time,
                        'avg_vehicles': metrics.avg_vehicles_per_sat,
                        'sat': metrics.sat_count,
                        'unsat': metrics.unsat_count,
                        'timeout': metrics.timeout_count,
                        'error': metrics.error_count
                    }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n[OK] Rapport sauvegarde: {output_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare solver performances")
    parser.add_argument("results", nargs="+", help="Result JSON files to compare")
    parser.add_argument("--leagues", nargs="+", 
                       choices=["bronze", "silver", "gold", "overall"],
                       help="Leagues to analyze (default: all)")
    parser.add_argument("--output", type=str, help="Output report file (JSON)")
    
    args = parser.parse_args()
    
    comparator = SolverComparator()
    
    # Charger les résultats
    print("Loading results...")
    for result_file in args.results:
        path = Path(result_file)
        if not path.exists():
            print(f"[ERR] File not found: {result_file}")
            continue
        
        solver_name = comparator.load_results(path)
        print(f"  [OK] Loaded: {solver_name}")
    
    if not comparator.solvers_data:
        print("[ERR] No valid results loaded")
        sys.exit(1)
    
    # Comparer
    comparator.compare_all(args.leagues)
    
    # Générer rapport si demandé
    if args.output:
        comparator.generate_report(Path(args.output))


if __name__ == "__main__":
    main()
