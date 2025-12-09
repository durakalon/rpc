# Solveur CP-SAT

Ce dossier contient un solveur basé sur la programmation par contraintes (CP) utilisant OR-Tools CP-SAT.

## Installation

Nécessite le paquet `ortools` :

```bash
pip install ortools
```

## Utilisation

```bash
python3 run.py [input_file] [-o output_file] [-v] [-t timeout]
```

## Fonctionnement

Le solveur utilise le modèle CP-SAT pour résoudre le problème de Bin Packing 3D.
Il itère sur le nombre de véhicules nécessaires, en commençant par une borne inférieure théorique, jusqu'à trouver une solution réalisable.

Pour chaque nombre de véhicules $k$, il modélise le problème avec :
- Des variables pour la position $(x, y, z)$ et l'orientation de chaque colis.
- Des contraintes de non-chevauchement entre les colis dans le même véhicule.
- Des contraintes de contenance dans les dimensions du véhicule.
