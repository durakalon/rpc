# CP-SAT Fast Solver

Solveur CP-SAT simplifié et rapide pour le problème de bin packing 3D.

## Différences avec cp-sat

| Fonctionnalité | cp-sat | cp-sat-fast |
|----------------|--------|-------------|
| Gravité | z=0 forcé | Libre (3D complet) |
| Objectif | Aucun | Aucun |
| Multi-threading | Oui (8 workers) | Oui (8 workers) |
| Orientations | Filtrage valides | Filtrage valides |
| LIFO delivery | Oui | Oui |

## Usage

```bash
# Depuis stdin
cat input.txt | python run.py

# Depuis fichier
python run.py -i input.txt

# Avec timeout
python run.py -i input.txt -t 120

# Sortie vers fichier
python run.py -i input.txt -o output.txt
```

## Performance

Cette version est plus rapide car :
1. **Pas de contrainte z=0** : Permet d'utiliser tout l'espace 3D
2. **Pas de fonction objectif** : Mode faisabilité pure (trouve une solution valide, pas nécessairement optimale)
3. **Moins de variables** : Pas de variables de support pour la gravité

## Quand utiliser cp-sat-fast vs cp-sat ?

- **cp-sat-fast** : Pour les instances difficiles où trouver une solution est le principal défi
- **cp-sat** : Pour les instances où une solution "réaliste" (gravité) est requise
