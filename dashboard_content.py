"""Localized dashboard copy and source links."""

TRANSLATIONS = {
    "en": {
        "title": "Python Conformity",
        "subtitle": "Compare Python implementations by use case, application and standard library behavior.",
        "language": "Language",
        "download": "Download results (JSON)",
        "github": "Source on GitHub",
        "comparison": "Comparison results",
        "suite": "Dashboard view",
        "usesTab": "Use cases",
        "packagesTab": "PyPy packages",
        "packagesTitle": "Top 50 packages by PyPy wheel downloads",
        "packagesWindow": "UTC downloads from {start} through {end}",
        "packagesMethod": "The ranking counts PyPI downloads of wheels tagged for PyPy across versions and platforms. Each check installs the pinned release and its dependencies from wheels, then imports the named module. A missing wheel can belong to the package or a dependency.",
        "packagesEmpty": "Package checks were not run for this report.",
        "package": "Package and import",
        "rank": "Rank",
        "downloads": "PyPy wheel downloads",
        "usesTitle": "Why choose a different Python?",
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
        "allModules": "All modules",
        "appTitle": "Application checks",
        "appMethod": "The checks exercise these scenarios with pinned packages. NumPy requires a Linux x86-64 wheel that matches the interpreter’s native ABI. These checks record behavior and package availability.",
        "appEmpty": "No application checks were run for this report.",
        "appCase": "Scenario",
        "noWheel": "No matching wheel",
        "appNames": {
            "django-template": "Render a template with loops and HTML escaping",
            "django-sqlite": "Query SQLite with the ORM and roll back a transaction",
            "bottle-route": "Dispatch a WSGI route and return JSON",
            "numpy-array": "Broadcast over a strided array and solve a linear system"
        },
        "descriptions": {
            "common": "Each interpreter runs the same calls. Values and exceptions are compared with the CPython reference.",
            "upstream": "Selected test methods from the CPython source tree, run on CPython and PyPy."
        },
        "statuses": {
            "passed": "Passed",
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
        "subtitle": "Comparer les implémentations Python par usage, application et comportement de la bibliothèque standard.",
        "language": "Langue",
        "download": "Télécharger les résultats (JSON)",
        "github": "Code sur GitHub",
        "comparison": "Résultats de la comparaison",
        "suite": "Vue du tableau de bord",
        "usesTab": "Cas d’usage",
        "packagesTab": "Paquets PyPy",
        "packagesTitle": "Les 50 paquets aux wheels PyPy les plus téléchargés",
        "packagesWindow": "Téléchargements du {start} au {end} en UTC",
        "packagesMethod": "Le classement compte les téléchargements PyPI de wheels portant un tag PyPy, toutes versions et plateformes confondues. Chaque essai installe la version fixée et ses dépendances depuis des wheels, puis importe le module indiqué. Un wheel manquant peut concerner le paquet ou l’une de ses dépendances.",
        "packagesEmpty": "Les essais de paquets n’ont pas été lancés pour ce rapport.",
        "package": "Paquet et module importé",
        "rank": "Rang",
        "downloads": "Téléchargements de wheels PyPy",
        "usesTitle": "Pourquoi choisir un autre Python ?",
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
        "allModules": "Tous les modules",
        "appTitle": "Tests applicatifs",
        "appMethod": "Les scénarios utilisent des versions de paquets fixées. NumPy nécessite un paquet binaire Linux x86-64 qui correspond à l’ABI native de l’interpréteur. Ces tests mesurent le comportement et la disponibilité des paquets.",
        "appEmpty": "Ce rapport ne contient aucun test applicatif.",
        "appCase": "Scénario",
        "noWheel": "Aucun binaire compatible",
        "appNames": {
            "django-template": "Rendre un gabarit avec des boucles et de l’échappement HTML",
            "django-sqlite": "Interroger SQLite avec l’ORM et annuler une transaction",
            "bottle-route": "Traiter une route WSGI et renvoyer du JSON",
            "numpy-array": "Diffuser une opération sur une vue à pas et résoudre un système linéaire"
        },
        "descriptions": {
            "common": "Les mêmes appels sur chaque interpréteur. Chaque valeur ou exception est comparée à la référence CPython.",
            "upstream": "Des méthodes de test sélectionnées dans le code source de CPython, exécutées sur CPython et PyPy."
        },
        "statuses": {
            "passed": "Réussi",
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

USE_CASES = [
    {
        "en": {
            "title": "Long-running Python code",
            "text": "PortaOne reported using PyPy to speed up SIP call processing in 2024. A just-in-time compiler can help a service or worker that runs the same Python code repeatedly, once it has warmed up.",
            "sources": [
                "PortaOne’s deployment report",
                "PyPy performance guide"
            ]
        },
        "fr": {
            "title": "Code Python de longue durée",
            "text": "PortaOne a décrit en 2024 comment PyPy accélérait le traitement de ses appels SIP. La compilation à la volée peut accélérer un service ou un processus de traitement qui exécute le même code Python de façon répétée, après une phase de chauffe.",
            "sources": [
                "Retour de déploiement de PortaOne",
                "Guide de performance PyPy"
            ]
        },
        "urls": [
            "https://pypy.org/posts/2024/08/portaone.html",
            "https://pypy.org/performance.html"
        ]
    },
    {
        "en": {
            "title": "Web applications and small APIs",
            "text": "Lincoln Loop tested PyPy on queries from a Django application. Django documents support for corresponding PyPy versions. Templates, database drivers and deployment dependencies each affect how an app runs. Bottle provides a lightweight WSGI example.",
            "sources": [
                "Lincoln Loop’s Django benchmark",
                "Django’s PyPy guidance",
                "Bottle documentation"
            ]
        },
        "fr": {
            "title": "Applications web et petites API",
            "text": "Lincoln Loop a évalué PyPy sur les requêtes d’une application Django. Django documente la compatibilité avec les versions correspondantes de PyPy. Le rendu, les pilotes de base de données et les dépendances de déploiement influencent l’exécution. Bottle fournit un exemple WSGI léger.",
            "sources": [
                "Benchmark Django de Lincoln Loop",
                "Documentation Django sur PyPy",
                "Documentation Bottle"
            ]
        },
        "urls": [
            "https://lincolnloop.com/blog/faster-django-sites-pypy/",
            "https://docs.djangoproject.com/en/5.2/topics/performance/#pypy",
            "https://bottlepy.org/docs/stable/"
        ]
    },
    {
        "en": {
            "title": "Scientific computing",
            "text": "NumPy relies on native extensions. Its PyPI releases list separate wheels for supported interpreter ABIs, and GraalPy publishes compatible builds through its own index. Check the interpreter release and the packages your project needs together.",
            "sources": [
                "NumPy 2.4.4 distributions",
                "GraalPy package compatibility"
            ]
        },
        "fr": {
            "title": "Calcul scientifique",
            "text": "NumPy repose sur des extensions natives. Ses distributions PyPI proposent des paquets binaires adaptés aux ABI prises en charge, et GraalPy publie des binaires dans son propre index. La compatibilité dépend de la version de l’interpréteur et des paquets utilisés par le projet.",
            "sources": [
                "Distributions NumPy 2.4.4",
                "Compatibilité des paquets GraalPy"
            ]
        },
        "urls": [
            "https://pypi.org/project/numpy/2.4.4/#files",
            "https://graalpy.org/python-developers/compatibility/"
        ]
    },
    {
        "en": {
            "title": "Python inside a JVM application",
            "text": "GraalPy can embed Python libraries and scripting in Java, Kotlin or Scala applications. The Quarkiverse integration exposes Python functions as managed Java beans. This scenario uses the JVM embedding API.",
            "sources": [
                "Quarkus GraalPy integration",
                "GraalPy embedding documentation"
            ]
        },
        "fr": {
            "title": "Python dans une application JVM",
            "text": "GraalPy permet d’intégrer des bibliothèques et des scripts Python dans des applications Java, Kotlin ou Scala. L’intégration Quarkiverse expose des fonctions Python sous forme de beans Java gérés. Cet usage passe par l’API d’intégration JVM.",
            "sources": [
                "Intégration GraalPy pour Quarkus",
                "Documentation d’intégration GraalPy"
            ]
        },
        "urls": [
            "https://docs.quarkiverse.io/quarkus-graalpy/dev/index.html",
            "https://graalpy.org/jvm-developers/docs/"
        ]
    },
    {
        "en": {
            "title": "Python scripting in Rust and WebAssembly",
            "text": "Robot Rumble embeds RustPython to run bot code and exchange structured values with its Rust host. RustPython also has an experimental WebAssembly target with a browser demo.",
            "sources": [
                "Robot Rumble’s runner",
                "RustPython WebAssembly documentation"
            ]
        },
        "fr": {
            "title": "Scripts Python dans Rust et WebAssembly",
            "text": "Robot Rumble embarque RustPython pour exécuter les scripts des robots et échanger des valeurs structurées avec son application Rust. RustPython propose aussi une cible WebAssembly expérimentale avec une démo dans le navigateur.",
            "sources": [
                "Exécuteur de Robot Rumble",
                "Documentation WebAssembly de RustPython"
            ]
        },
        "urls": [
            "https://github.com/robot-rumble/logic/blob/master/lang-runners/python/src/main.rs",
            "https://github.com/RustPython/RustPython/blob/main/wasm/README.md"
        ]
    },
    {
        "en": {
            "title": "Programming contests",
            "text": "AtCoder offers PyPy alongside CPython for time-limited submissions. Its published environment uses PyPy 7.3.20 and includes NumPy 2.3.2, an example of a package set selected for a specific runtime release.",
            "sources": [
                "AtCoder’s supported languages and libraries"
            ]
        },
        "fr": {
            "title": "Concours de programmation",
            "text": "AtCoder propose PyPy aux côtés de CPython pour les soumissions à temps limité. Son environnement publié associe PyPy 7.3.20 à NumPy 2.3.2, un exemple de paquets choisis pour une version précise de l’interpréteur.",
            "sources": [
                "Langages et bibliothèques pris en charge par AtCoder"
            ]
        },
        "urls": [
            "https://img.atcoder.jp/file/language-update/2025-10/language-list.html"
        ]
    }
]
