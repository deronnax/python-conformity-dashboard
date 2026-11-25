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
        "packagesTab": "PyPy packages",
        "packagesTitle": "Top 50 packages by PyPy wheel downloads",
        "packagesWindow": "UTC downloads from {start} through {end}",
        "packagesMethod": "The ranking counts PyPI downloads of wheels tagged for PyPy across versions and platforms. Each check installs the pinned release and its dependencies from wheels, then imports the named module. A missing wheel can belong to the package or a dependency. “Other ABI only” means the release has wheels for this Python version and platform, built for another ABI of the interpreter, such as PyPy 7.3 (pp73) instead of PyPy 8 (pp80).",
        "packagesPassedOn": "Packages imported on {runtime}",
        "packagesEmpty": "Package checks were not run for this report.",
        "package": "Package and import",
        "rank": "Rank",
        "downloads": "PyPy wheel downloads",
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
        "packagesTab": "Paquets PyPy",
        "packagesTitle": "Les 50 paquets aux wheels PyPy les plus téléchargés",
        "packagesWindow": "Téléchargements du {start} au {end} en UTC",
        "packagesMethod": "Le classement compte les téléchargements PyPI de wheels portant un tag PyPy, toutes versions et plateformes confondues. Chaque essai installe la version fixée et ses dépendances depuis des wheels, puis importe le module indiqué. Un wheel manquant peut concerner le paquet ou l’une de ses dépendances. « Autre ABI seulement » signifie que la version publie des wheels pour cette version de Python et cette plateforme, mais compilés pour une autre ABI de l’interpréteur, par exemple PyPy 7.3 (pp73) au lieu de PyPy 8 (pp80).",
        "packagesPassedOn": "Paquets importés sur {runtime}",
        "packagesEmpty": "Les essais de paquets n’ont pas été lancés pour ce rapport.",
        "package": "Paquet et module importé",
        "rank": "Rang",
        "downloads": "Téléchargements de wheels PyPy",
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
