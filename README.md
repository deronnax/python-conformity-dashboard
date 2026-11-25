# Conformité Python

Ce tableau de bord compare des comportements observables de la bibliothèque standard à CPython 3.11.17. Le premier corpus couvre `binascii`, `json`, `math` et `struct`. Il contient 25 cas communs et 20 méthodes de la suite CPython sélectionnées une par une.

## Mesure locale

Utiliser un [CPython 3.11.17 précompilé](https://github.com/astral-sh/python-build-standalone/releases/tag/20261021) et [PyPy 8.0.1 pour Python 3.11](https://doc.pypy.org/release-v8.0.1.html). Aucune dépendance Python à installer.

```sh
/chemin/vers/python3.11 -B measure.py \
  --pypy /chemin/vers/pypy3.11
open dist/index.html  # macOS
```

La commande télécharge l’archive source officielle de CPython, vérifie son SHA-256 et extrait uniquement `Lib/test` dans un dossier temporaire. `--source /chemin/vers/Python-3.11.17.tar.xz` réutilise une archive déjà téléchargée. La page s’ouvre directement à partir des fichiers générés dans `dist/`. `dist/results.json` contient les résultats détaillés.

Le dashboard s’affiche en anglais par défaut et en français si c’est la première langue prise en charge dans les préférences du navigateur. Le menu de langue permet de choisir une autre langue et mémorise ce choix.

`--micropython /chemin/vers/micropython` ajoute le [port Unix précompilé](https://formulae.brew.sh/formula/micropython). `--graalpy /chemin/vers/graalpy` ajoute le [binaire autonome GraalPy](https://github.com/oracle/graalpython/releases/tag/graal-25.5.5). Les deux options sont indépendantes.

## GitHub Actions

Le workflow **Conformité Python** s’exécute sur Linux x86-64 à chaque push sur `main` et peut être lancé manuellement. Il télécharge les binaires précompilés de CPython, PyPy, MicroPython Unix 1.29.0 et GraalPy Community 25.5.5, puis vérifie leurs empreintes. GraalPy est utilisé via le lanceur natif autonome, qui ne requiert pas d’installation de Java.

Dans le résumé de l’exécution, télécharger `dashboard-conformite`, décompresser l’archive puis ouvrir `index.html`. Une incompatibilité observée est un résultat de mesure. Une référence CPython qui échoue rend le job rouge et reste visible dans le rapport si celui-ci a pu être produit.

## Interprétation

- **Cas communs**. Le même appel est exécuté sur tous les interpréteurs sélectionnés. On compare le type et la valeur ou, pour les entrées invalides, la possibilité d’intercepter l’exception avec sa classe publique. Une API absente, un écart de comportement, un délai dépassé et un blocage de la mesure ont des états distincts.
- **Tests CPython**. Les corps des tests sélectionnés tournent sur CPython et PyPy avec les bibliothèques standard de chaque binaire. Une garde dans le harnais JSON permet de charger les méthodes sélectionnées quand l’accélérateur CPython `_json` est absent. Les tests d’optimisations internes et de l’API C sont hors corpus. [Sources CPython v3.11.17](https://github.com/python/cpython/tree/v3.11.17/Lib/test)
- **Périmètre**. Les résultats s’appliquent aux cas, binaires et plateformes affichés. MicroPython vise un sous-ensemble de Python et GraalPy 25.5.5 cible Python 3.13. Leur présence dans les cas communs indique quelles API ont le même comportement que CPython 3.11.17 pour ces entrées. [MicroPython](https://docs.micropython.org/en/v1.29.0/genrst/index.html) · [GraalPy](https://github.com/oracle/graalpython/releases/tag/graal-25.5.5)
