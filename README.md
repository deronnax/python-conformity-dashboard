# Conformité Python

Ce tableau de bord compare des comportements observables de la bibliothèque standard à CPython 3.11.17. Le corpus couvre 16 modules. Il comprend notamment des transactions SQLite, des flux zlib partiels, des groupes de tâches asynchrones, des transitions de fuseau horaire et des expressions régulières atomiques.

## Mesure locale

Utiliser un [CPython 3.11.17 précompilé](https://github.com/astral-sh/python-build-standalone/releases/tag/20261021) et [PyPy 8.0.1 pour Python 3.11](https://doc.pypy.org/release-v8.0.1.html). Aucune dépendance Python à installer.

```sh
/chemin/vers/python3.11 -B measure.py \
  --pypy /chemin/vers/pypy3.11
open dist/index.html  # macOS
```

La commande télécharge l’archive source officielle de CPython, vérifie son SHA-256 et extrait uniquement `Lib/test` dans un dossier temporaire. `--source /chemin/vers/Python-3.11.17.tar.xz` réutilise une archive déjà téléchargée. La page s’ouvre directement à partir des fichiers générés dans `dist/`. `dist/results.json` contient les résultats détaillés.

Le dashboard s’affiche en anglais par défaut et en français si c’est la première langue prise en charge dans les préférences du navigateur. Le menu de langue permet de choisir une autre langue et mémorise ce choix.

Le rendu des deux pages et des tableaux est réalisé en Python avec la bibliothèque standard. Le navigateur gère la préférence de langue et les filtres. Pour régénérer le site à partir d’un rapport existant, utiliser `python3 -B dashboard.py dist/results.json`. Les pages générées sont `dist/index.html` et `dist/fr/index.html`.

`--applications` télécharge dans le dossier temporaire les distributions épinglées de Django 5.2.19, Bottle 0.13.4 et NumPy 2.4.4. Il vérifie leurs empreintes et les extrait pour l’import, sans toucher aux environnements installés. L’essai NumPy vérifie le suffixe d’extension natif attendu par l’interpréteur sur Linux x86-64. Les scénarios testent le rendu Django, un agrégat avec annulation de transaction SQLite, une route WSGI Bottle et des opérations NumPy.

`--rustpython /chemin/vers/rustpython` ajoute un [binaire RustPython](https://formulae.brew.sh/formula/rustpython). `--graalpy /chemin/vers/graalpy` ajoute le [binaire autonome GraalPy](https://github.com/oracle/graalpython/releases/tag/graal-25.5.5). Les deux options sont indépendantes.

## GitHub Actions

Le workflow **Conformité Python** s’exécute sur Linux x86-64 à chaque push sur `main` et peut être lancé manuellement. Il télécharge les binaires précompilés de CPython, PyPy, GraalPy Community 25.5.5 et RustPython 0.6.0 (paquet Homebrew), puis vérifie leurs empreintes. Le lanceur GraalPy natif est autonome.

Dans le résumé de l’exécution, télécharger `dashboard-conformite`, décompresser l’archive puis ouvrir `index.html`. Le workflow active les essais applicatifs. Une incompatibilité observée est un résultat de mesure. Un échec de la référence CPython dans le corpus de la bibliothèque standard rend le job rouge et reste visible dans le rapport si celui-ci a pu être produit.

## Interprétation

- **Cas communs**. Le même appel est exécuté sur tous les interpréteurs sélectionnés. On compare le type et la valeur ou, pour les entrées invalides, la possibilité d’intercepter l’exception avec sa classe publique. Une API absente, un écart de comportement, un délai dépassé et un blocage de la mesure ont des états distincts.
- **Tests CPython**. Les corps des tests sélectionnés tournent sur CPython et PyPy avec les bibliothèques standard de chaque binaire. Une garde dans le harnais JSON permet de charger les méthodes sélectionnées quand l’accélérateur CPython `_json` est absent. Les tests d’optimisations internes et de l’API C sont hors corpus. [Sources CPython v3.11.17](https://github.com/python/cpython/tree/v3.11.17/Lib/test)
- **Périmètre**. Les cas communs portent sur des API publiques de CPython 3.11 et s’appliquent aux binaires et plateformes affichés. GraalPy cible Python 3.13. Le binaire RustPython 0.6.0 annonce Python 3.14 alpha. La présence de modules optionnels dépend de la configuration de chaque binaire. [GraalPy](https://github.com/oracle/graalpython/releases/tag/graal-25.5.5) · [RustPython](https://rustpython.github.io/docs/getting_started/installation.html)
