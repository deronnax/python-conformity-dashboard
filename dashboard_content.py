"""Localized dashboard copy and source links."""

TRANSLATIONS = {
    "en": {
        "title": "Python Conformity",
        "subtitle": "Compare package compatibility and standard library behavior across Python implementations.",
        "language": "Language",
        "download": "Download results (JSON)",
        "github": "Source on GitHub",
        "comparison": "Comparison results",
        "suite": "Dashboard view",
        "packagesTab": "PyPI packages",
        "packagesTitle": "Top 50 packages by PyPI downloads",
        "packagesWindow": "UTC downloads from {start} through {end}",
        "packagesMethod": "The ranking counts every PyPI download of each project, whatever its version, file type or platform. Each check installs the pinned release and its dependencies from wheels, then imports the named module. A missing wheel can belong to the package or a dependency. “Other ABI only” means the release has wheels for this Python version and platform, built for another ABI of the interpreter, such as PyPy 7.3 (pp73) instead of PyPy 8 (pp80).",
        "packagesPassedOn": "Packages imported on {runtime}",
        "packagesEmpty": "Package checks were not run for this report.",
        "package": "Package and import",
        "rank": "Rank",
        "downloads": "PyPI downloads",
        "interpretersTab": "Interpreters",
        "interpretersMethod": "Four threads run the same CPU-bound function. The speedup compares them with four sequential calls. About ×1 means the threads take turns, as under a global interpreter lock. A value close to the number of workers means they run in parallel. The measurement is limited by the cores of the machine that ran it.",
        "interpreter": "Interpreter",
        "pythonVersion": "Python",
        "abi": "Wheel ABI",
        "gil": "GIL",
        "gilEnabled": "Enabled",
        "gilDisabled": "Disabled",
        "gilUnknown": "Not reported",
        "threadsSpeedup": "Thread speedup",
        "threadsDetail": "{workers} threads · {cores} cores",
        "historyTab": "History",
        "historyIntro": "Each measurement run adds one point. The same projects and releases are tested every time, so a change reflects the interpreters and the ecosystem.",
        "historyFirst": "The history starts with this run. The measurement repeats every Monday, so each chart gains a point every week.",
        "historyTable": "Table view",
        "historyDate": "Run",
        "historyCharts": {
            "packages": "Top 50 packages imported",
            "applications": "Application scenarios passed",
            "common": "Shared cases passed",
            "threads": "Thread speedup (4 CPU-bound threads)"
        },
        "applicationsTab": "Applications",
        "applicationsEmpty": "Application checks were not run for this report.",
        "applicationsPassedOn": "Scenarios passed on {runtime}",
        "scenario": "Scenario",
        "applicationTitles": {
            "django-template": "Render a template with autoescaping",
            "django-sqlite": "Aggregate rows after a rolled-back SQLite transaction",
            "bottle-route": "Route a WSGI request to a JSON handler",
            "numpy-array": "Slice arrays and solve a linear system"
        },
        "commonTab": "Shared cases",
        "upstreamTab": "CPython tests",
        "summaries": "Results by interpreter",
        "module": "Module",
        "onlyDifferences": "Differences and unmeasured cases",
        "caseTable": "Test case table",
        "methodology": "Methodology and scope",
        "methodCases": "Shared cases compare observed types and values with CPython. For invalid inputs, they check whether callers can catch the exception using the expected public class.",
        "methodUpstream": "The CPython tests view runs selected upstream test methods on CPython and PyPy. The JSON test harness enables the CPython accelerator when available. Shared cases import the module as usual.",
        "methodScope": "These results apply to the cases, versions and platform shown. The shared cases cover APIs available in CPython 3.11. A module can be unavailable in a specific build. Each row links to the source test.",
        "reference": "CPython reference",
        "source": "View source test",
        "passedOn": "Cases passed on {runtime}",
        "case": "Case",
        "empty": "No cases match these filters.",
        "noDifferences": "No differences or unmeasured cases. Clear the filter to see every case.",
        "observations": {
            "raises": "Raises {exception}",
            "unexpected": "Raises an unexpected {exception}",
            "returns": "Returns {value} ({type})",
            "returnsNone": "Returns None"
        },
        "allModules": "All modules",
        "descriptions": {
            "common": "Each interpreter runs the same calls. Values and exceptions are compared with the CPython reference.",
            "applications": "Small scenarios with pinned releases of Django, Bottle and NumPy, run on each interpreter from isolated wheel directories.",
            "upstream": "Selected test methods from the CPython source tree, run on CPython and PyPy."
        },
        "statuses": {
            "passed": "Passed",
            "noWheel": "No wheel",
            "otherAbi": "Other ABI only",
            "different": "Different",
            "missing": "Missing API",
            "skipped": "Skipped",
            "error": "Test error",
            "installError": "Installation failed",
            "installTimeout": "Installation timed out",
            "installerUnavailable": "Installer unavailable",
            "importError": "Import failed",
            "blocked": "Measurement blocked",
            "crash": "Process interrupted",
            "timeout": "Timed out",
            "unverified": "Invalid reference"
        },
        "totals": {
            "noWheel": ["missing wheel", "missing wheels"],
            "otherAbi": ["wheel for another ABI only", "wheels for another ABI only"],
            "installError": ["failed installation", "failed installations"],
            "installTimeout": ["installation timeout", "installation timeouts"],
            "installerUnavailable": ["installer unavailable", "installer unavailable"],
            "importError": ["failed import", "failed imports"],
            "different": [
                "difference",
                "differences"
            ],
            "missing": [
                "missing API",
                "missing APIs"
            ],
            "skipped": [
                "skipped test",
                "skipped tests"
            ],
            "error": [
                "test error",
                "test errors"
            ],
            "blocked": [
                "blocked measurement",
                "blocked measurements"
            ],
            "crash": [
                "interrupted process",
                "interrupted processes"
            ],
            "timeout": [
                "timeout",
                "timeouts"
            ],
            "unverified": [
                "invalid reference",
                "invalid references"
            ]
        },
        "caseUnit": "cases"
    },
    "fr": {
        "title": "Conformité Python",
        "subtitle": "Comparer les implémentations Python selon leur compatibilité avec les paquets et leur bibliothèque standard.",
        "language": "Langue",
        "download": "Télécharger les résultats (JSON)",
        "github": "Code sur GitHub",
        "comparison": "Résultats de la comparaison",
        "suite": "Vue du tableau de bord",
        "packagesTab": "Paquets PyPI",
        "packagesTitle": "Les 50 paquets les plus téléchargés sur PyPI",
        "packagesWindow": "Téléchargements du {start} au {end} en UTC",
        "packagesMethod": "Le classement compte tous les téléchargements PyPI de chaque projet, quels que soient la version, le type de fichier et la plateforme. Chaque essai installe la version fixée et ses dépendances depuis des wheels, puis importe le module indiqué. Un wheel manquant peut concerner le paquet ou l’une de ses dépendances. « Autre ABI seulement » signifie que la version publie des wheels pour cette version de Python et cette plateforme, mais compilés pour une autre ABI de l’interpréteur, par exemple PyPy 7.3 (pp73) au lieu de PyPy 8 (pp80).",
        "packagesPassedOn": "Paquets importés sur {runtime}",
        "packagesEmpty": "Les essais de paquets n’ont pas été lancés pour ce rapport.",
        "package": "Paquet et module importé",
        "rank": "Rang",
        "downloads": "Téléchargements PyPI",
        "interpretersTab": "Interpréteurs",
        "interpretersMethod": "Quatre threads exécutent la même fonction qui sature le processeur. L’accélération les compare à quatre appels successifs. Une valeur proche de ×1 signifie que les threads passent à tour de rôle, comme avec un verrou global de l’interpréteur. Une valeur proche du nombre de threads signifie qu’ils s’exécutent en parallèle. La mesure est limitée par les cœurs de la machine qui l’a faite.",
        "interpreter": "Interpréteur",
        "pythonVersion": "Python",
        "abi": "ABI des wheels",
        "gil": "GIL",
        "gilEnabled": "Activé",
        "gilDisabled": "Désactivé",
        "gilUnknown": "Non communiqué",
        "threadsSpeedup": "Accélération des threads",
        "threadsDetail": "{workers} threads · {cores} cœurs",
        "historyTab": "Historique",
        "historyIntro": "Chaque exécution ajoute un point. Les mêmes projets et les mêmes versions sont testés à chaque fois : une variation reflète donc les interpréteurs et l’écosystème.",
        "historyFirst": "L’historique commence avec cette exécution. La mesure se répète chaque lundi, donc chaque courbe gagne un point par semaine.",
        "historyTable": "Vue en tableau",
        "historyDate": "Exécution",
        "historyCharts": {
            "packages": "Les 50 paquets importés",
            "applications": "Scénarios applicatifs réussis",
            "common": "Cas communs réussis",
            "threads": "Accélération des threads (4 threads sur le processeur)"
        },
        "applicationsTab": "Applications",
        "applicationsEmpty": "Les essais applicatifs n’ont pas été lancés pour ce rapport.",
        "applicationsPassedOn": "Scénarios réussis sur {runtime}",
        "scenario": "Scénario",
        "applicationTitles": {
            "django-template": "Rendre un gabarit avec échappement automatique",
            "django-sqlite": "Agréger des lignes après l’annulation d’une transaction SQLite",
            "bottle-route": "Router une requête WSGI vers un gestionnaire JSON",
            "numpy-array": "Découper des tableaux et résoudre un système linéaire"
        },
        "commonTab": "Cas communs",
        "upstreamTab": "Tests CPython",
        "summaries": "Résultats par interpréteur",
        "module": "Module",
        "onlyDifferences": "Écarts et cas non mesurés",
        "caseTable": "Tableau des cas",
        "methodology": "Méthode et périmètre",
        "methodCases": "Les cas communs comparent les types et valeurs observés à ceux de CPython. Pour les entrées invalides, on vérifie que le code appelant peut intercepter l’exception avec la classe publique attendue.",
        "methodUpstream": "La vue Tests CPython exécute une sélection de méthodes d’origine sur CPython et PyPy. Pour JSON, le harnais active son accélérateur CPython uniquement s’il est disponible. Les cas communs chargent le module normalement.",
        "methodScope": "Les résultats portent sur ces cas, ces versions et cette plateforme. Les cas communs couvrent des API disponibles dans CPython 3.11. Un module peut être absent d’un binaire donné. Chaque ligne donne accès à son cas source.",
        "reference": "Référence CPython",
        "source": "Voir le test source",
        "passedOn": "Cas réussis sur {runtime}",
        "case": "Cas",
        "empty": "Aucun cas pour ces filtres.",
        "noDifferences": "Aucun écart ni cas non mesuré. Décochez le filtre pour voir tous les cas.",
        "observations": {
            "raises": "Lève {exception}",
            "unexpected": "Lève une exception inattendue : {exception}",
            "returns": "Renvoie {value} ({type})",
            "returnsNone": "Renvoie None"
        },
        "allModules": "Tous les modules",
        "descriptions": {
            "common": "Les mêmes appels sur chaque interpréteur. Chaque valeur ou exception est comparée à la référence CPython.",
            "applications": "De petits scénarios avec des versions épinglées de Django, Bottle et NumPy, exécutés sur chaque interpréteur depuis des dossiers de wheels isolés.",
            "upstream": "Des méthodes de test sélectionnées dans le code source de CPython, exécutées sur CPython et PyPy."
        },
        "statuses": {
            "passed": "Réussi",
            "noWheel": "Aucun wheel",
            "otherAbi": "Autre ABI seulement",
            "different": "Différent",
            "missing": "API absente",
            "skipped": "Ignoré",
            "error": "Erreur du test",
            "installError": "Échec de l’installation",
            "installTimeout": "Installation trop longue",
            "installerUnavailable": "Installateur indisponible",
            "importError": "Échec de l’import",
            "blocked": "Mesure bloquée",
            "crash": "Processus interrompu",
            "timeout": "Délai dépassé",
            "unverified": "Référence invalide"
        },
        "totals": {
            "noWheel": ["wheel manquant", "wheels manquants"],
            "otherAbi": ["wheel pour une autre ABI seulement", "wheels pour une autre ABI seulement"],
            "installError": ["échec de l’installation", "échecs de l’installation"],
            "installTimeout": ["installation trop longue", "installations trop longues"],
            "installerUnavailable": ["installateur indisponible", "installateur indisponible"],
            "importError": ["échec de l’import", "échecs de l’import"],
            "different": [
                "écart",
                "écarts"
            ],
            "missing": [
                "API absente",
                "API absentes"
            ],
            "skipped": [
                "test ignoré",
                "tests ignorés"
            ],
            "error": [
                "erreur de test",
                "erreurs de test"
            ],
            "blocked": [
                "mesure bloquée",
                "mesures bloquées"
            ],
            "crash": [
                "processus interrompu",
                "processus interrompus"
            ],
            "timeout": [
                "délai dépassé",
                "délais dépassés"
            ],
            "unverified": [
                "référence invalide",
                "références invalides"
            ]
        },
        "caseUnit": "cas"
    }
}
