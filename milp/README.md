# Solveur MILP (Mixed Integer Linear Programming)

Ce solveur utilise la Programmation Linéaire en Nombres Entiers Mixtes via la bibliothèque PuLP avec le solveur CBC.

## Installation

```bash
pip install pulp
```

## Utilisation

```bash
# Via stdin/stdout
python run.py < input.txt > output.txt

# Avec fichiers
python run.py -i input.txt -o output.txt

# Avec timeout
python run.py -i input.txt -t 120
```

## Formulation MILP

### Variables

- **Positions** : `x[i], y[i], z[i]` (continues)
- **Dimensions** : `lx[i], ly[i], lz[i]` (liées à l'orientation)
- **Orientation** : `orient[i][r]` (binaire) - 1 si item i a rotation r
- **Véhicule** : `bin_assign[i][b]` (binaire) - 1 si item i dans véhicule b
- **Séparation** : `sep[i][j][d]` (binaire) - 1 si items i,j séparés sur axe d

### Contraintes

1. **Boundary** : Les items restent dans le véhicule
2. **Non-overlap** : Via Big-M pour les contraintes disjonctives
3. **Gravité** : Simplifiée (tous les items au sol)

### Objectif

Minimiser la somme des coordonnées X (compacter vers le fond).

## Avantages vs CP-SAT

- Meilleure relaxation linéaire
- Coupes automatiques du solveur LP
- Compatible avec solveurs commerciaux (Gurobi, CPLEX)

## Inconvénients

- Big-M peut affaiblir la relaxation
- Contraintes logiques moins naturelles
- Gravité complète difficile à linéariser
