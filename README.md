# Conformité Python

[Dashboard public](https://deronnax.github.io/python-conformity-dashboard/)

Ce tableau de bord compare des comportements observables de la bibliothèque standard à CPython 3.11.17. Le corpus couvre 17 modules. Il comprend notamment des transactions SQLite, des threads qui ajoutent à une même liste, des flux zlib partiels, des groupes de tâches asynchrones, des transitions de fuseau horaire et des expressions régulières atomiques.

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

`--applications` télécharge dans le dossier temporaire les distributions épinglées de Django 5.2.19, Bottle 0.13.4 et NumPy 2.4.4. Il vérifie leurs empreintes et les extrait pour l’import, sans toucher aux environnements installés. L’essai NumPy vérifie le suffixe d’extension natif attendu par l’interpréteur sur Linux x86-64. Les scénarios testent le rendu Django, un agrégat avec annulation de transaction SQLite, une route WSGI Bottle et des opérations NumPy. Leurs résultats apparaissent dans l’onglet Applications.

`--packages` ajoute les 50 projets les plus téléchargés sur PyPI entre le 26 octobre et le 24 novembre 2026 en UTC, tous types de fichiers confondus. [Le classement et sa requête ClickPy](pypi-packages.json) fixent aussi la version et le module à importer pour chaque projet. `python3.11 update_ranking.py` régénère ce fichier. La version retenue est la dernière version stable non retirée dont les métadonnées acceptent Python 3.11 à la date de référence. Sur chaque interpréteur, pip installe cette version et ses dépendances depuis des wheels avec `--prefix` dans un dossier temporaire propre au test. Contrairement à `--target`, cette option laisse pip voir les paquets fournis avec l’interpréteur, comme cffi sur PyPy. Le test vérifie la version installée et l’import du module indiqué. Quand aucun wheel ne convient au paquet lui-même, le harnais consulte PyPI. Si la version publie des wheels pour le même tag d’interpréteur et la même plateforme mais une autre ABI, par exemple `pypy311_pp73` pour PyPy 8 qui exige `pypy311_pp80`, le résultat est « Autre ABI seulement » et non « Aucun wheel ».

`--rustpython /chemin/vers/rustpython` ajoute un [binaire RustPython](https://github.com/RustPython/RustPython/releases/tag/0.6.0). Pour les essais SQLite, compiler RustPython avec `cargo build --release --locked --features freeze-stdlib,sqlite --bin rustpython` et utiliser `target/release/rustpython`. `--graalpy /chemin/vers/graalpy` ajoute le [binaire autonome GraalPy](https://github.com/oracle/graalpython/releases/tag/graal-25.5.5). Les deux options sont indépendantes. `--freethreaded /chemin/vers/python3.14t` ajoute un [CPython 3.14 sans GIL](https://github.com/astral-sh/python-build-standalone/releases/tag/20261021). Le script refuse un binaire qui n’est pas une version sans GIL.

## Interpréteurs et threads

Chaque exécution mesure `threads.py` sur chaque interpréteur : quatre threads exécutent la même fonction qui sature le processeur, et l’accélération compare leur durée à celle de quatre appels successifs. Environ ×1 signifie que les threads passent à tour de rôle (un verrou global). Une valeur proche de ×4 signifie qu’ils s’exécutent en parallèle. Le résultat dépend des cœurs de la machine, qui sont affichés. L’onglet **Interpréteurs** montre cette accélération, la version de Python visée, l’ABI des wheels et l’état du GIL quand l’interpréteur le communique (`sys._is_gil_enabled()`, à partir de Python 3.13).

## Performance

`--benchmarks` chronomètre huit programmes de `benchmarks.py`, chacun dans son propre processus : n corps, fannkuch-redux et norme spectrale (programmes du Computer Language Benchmarks Game), n reines, un calcul en virgule flottante, puis json, `re` et un comptage de mots avec `collections`. Chaque programme fait un premier appel à froid, deux tours de chauffe pour les compilateurs JIT et au moins trois tours chronométrés. L’onglet affiche la médiane et le rapport à CPython. Le détail donne le minimum, l’écart type et le temps du premier appel. Chaque programme imprime aussi un condensat de son résultat : une réponse différente de celle de CPython est un écart, pas un temps. La moyenne géométrique des rapports résume chaque interpréteur et alimente une courbe de l’historique.

Les tests de `tests/test_performance.py` vérifient les noyaux contre les valeurs publiées. `pystone` n’en fait pas partie : c’est un portage de Dhrystone, une charge synthétique de 1984 qui n’est plus fournie avec CPython et que les compilateurs JIT optimisent sans rapport avec du code réel. Les machines GitHub partagent leur matériel, donc des écarts d’environ 10 % ne sont pas significatifs.

## Historique

Chaque exécution ajoute un instantané compact (décomptes par état, interpréteur et vue, vitesse relative) à `history.json`. GitHub Pages remplace tout le site à chaque déploiement : le workflow télécharge donc l’`history.json` publié, y ajoute son instantané et le republie. `--history chemin/history.json` fait de même en local. Un fichier absent ou illisible démarre un nouvel historique. L’onglet **Historique** trace une courbe par interpréteur, avec une vue en tableau des mêmes valeurs.

## GitHub Actions

Le workflow **Conformité Python** s’exécute sur Linux x86-64 à chaque push sur `main`, chaque lundi et sur demande. Il lance d’abord les tests unitaires avec le CPython téléchargé. Il télécharge les binaires précompilés de CPython, CPython 3.14 sans GIL, PyPy et GraalPy Community 25.5.5 et vérifie leurs empreintes. Les empreintes de CPython proviennent du fichier `SHA256SUMS` de la publication. Il vérifie aussi l’empreinte de l’archive source de RustPython 0.6.0, puis compile l’interpréteur avec la bibliothèque standard intégrée et le module natif `_sqlite3`.

Dans le résumé de l’exécution, télécharger `dashboard-conformite`, décompresser l’archive puis ouvrir `index.html`. Le workflow active les essais applicatifs et les essais de paquets. Une incompatibilité observée est un résultat de mesure. Un échec de la référence CPython dans le corpus de la bibliothèque standard rend le job rouge et reste visible dans le rapport si celui-ci a pu être produit.

Sur `main`, une mesure réussie est ensuite publiée sur GitHub Pages par le job `publier`. Ce déploiement suppose que la source Pages du dépôt soit réglée sur **GitHub Actions** (Settings › Pages › Build and deployment).

## Tests

```sh
python3.11 -B -m unittest discover -s tests
```

Les tests couvrent la génération des pages à partir d’un rapport fictif, le classement des wheels manquants et le choix des versions et des modules du classement. Ils n’accèdent pas au réseau.

## Interprétation

- **Cas communs**. Le même appel est exécuté sur tous les interpréteurs sélectionnés. On compare le type et la valeur ou, pour les entrées invalides, la possibilité d’intercepter l’exception avec sa classe publique. Une API absente, un écart de comportement, un délai dépassé et un blocage de la mesure ont des états distincts.
- **Écarts d’abord**. Les tableaux des cas communs et des tests CPython n’affichent au départ que les écarts et les cas non mesurés. Décocher le filtre ou ajouter `?diff=0` à l’adresse affiche tous les cas.
- **Tests CPython**. Les corps des tests sélectionnés tournent sur CPython et PyPy avec les bibliothèques standard de chaque binaire. Une garde dans le harnais JSON permet de charger les méthodes sélectionnées quand l’accélérateur CPython `_json` est absent. Les tests d’optimisations internes et de l’API C sont hors corpus. [Sources CPython v3.11.17](https://github.com/python/cpython/tree/v3.11.17/Lib/test)
- **Périmètre**. Les cas communs portent sur des API publiques de CPython 3.11 et s’appliquent aux binaires et plateformes affichés. GraalPy cible Python 3.13. Le binaire RustPython 0.6.0 annonce Python 3.14 alpha. La présence de modules optionnels dépend de la configuration de chaque binaire. [GraalPy](https://github.com/oracle/graalpython/releases/tag/graal-25.5.5) · [RustPython](https://rustpython.github.io/docs/getting_started/installation.html)

## Licence

Le code du dashboard, les scénarios de mesure et les scripts sont distribués sous [licence MIT](LICENSE). Les interpréteurs, la suite de tests CPython et les paquets téléchargés pendant les mesures sont distribués par leurs projets respectifs sous leurs propres licences.
