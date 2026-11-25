# Python Conformity

[Public dashboard](https://deronnax.github.io/python-conformity-dashboard/)

This dashboard compares observable behavior of the standard library with CPython 3.11.17. The corpus covers 17 modules. It includes SQLite transactions, threads appending to one list, partial zlib streams, asyncio task groups, time zone transitions and atomic regular expressions.

## Local measurement

Use a [prebuilt CPython 3.11.17](https://github.com/astral-sh/python-build-standalone/releases/tag/20261021) and [PyPy 8.0.1 for Python 3.11](https://doc.pypy.org/release-v8.0.1.html). There are no Python dependencies to install.

```sh
/path/to/python3.11 -B measure.py \
  --pypy /path/to/pypy3.11
open dist/index.html  # macOS
```

The command downloads the official CPython source archive, checks its SHA-256 and extracts only `Lib/test` into a temporary directory. `--source /path/to/Python-3.11.17.tar.xz` reuses an archive you already have. The page opens straight from the files generated in `dist/`. `dist/results.json` holds the detailed results.

The dashboard is in English by default, and in French when French is the first supported language in the browser preferences. The language menu picks another language and remembers the choice.

Python renders both pages and all tables with the standard library. The browser handles the language preference and the filters. To regenerate the site from an existing report, run `python3 -B dashboard.py dist/results.json`. The generated pages are `dist/index.html` and `dist/fr/index.html`.

`--applications` downloads pinned distributions of Django 5.2.19, Bottle 0.13.4 and NumPy 2.4.4 into the temporary directory. It checks their digests and extracts them for import, leaving installed environments alone. The NumPy scenario checks the native extension suffix the interpreter expects on Linux x86-64. The scenarios cover Django template rendering, an aggregate with a rolled-back SQLite transaction, a Bottle WSGI route and NumPy operations. Their results appear in the Applications tab.

`--packages` adds the 50 most downloaded PyPI projects between 26 October and 24 November 2026 UTC, all file types included. [The ranking and its ClickPy query](pypi-packages.json) also fix the version and the module to import for each project. `python3.11 update_ranking.py` regenerates this file. The chosen version is the newest stable, non-yanked release whose metadata accepts Python 3.11 at the reference date. On each interpreter, pip installs that version and its dependencies from wheels with `--prefix` into a temporary directory private to the test. Unlike `--target`, this option lets pip see the packages bundled with the interpreter, such as cffi on PyPy. The test checks the installed version and imports the named module. When no wheel suits the package itself, the harness queries PyPI. If the release publishes wheels for the same interpreter tag and platform but another ABI, for example `pypy311_pp73` when PyPy 8 requires `pypy311_pp80`, the result is "Other ABI only" rather than "No wheel".

`--rustpython /path/to/rustpython` adds a [RustPython binary](https://github.com/RustPython/RustPython/releases/tag/0.6.0), measured for performance and threads only. It provides no C API, so the shared cases, packages, applications and CPython tests do not apply to it. To build it, run `cargo build --release --locked --features freeze-stdlib --bin rustpython` and use `target/release/rustpython`. `--graalpy /path/to/graalpy` adds the [standalone GraalPy binary](https://github.com/oracle/graalpython/releases/tag/graal-25.5.5). The two options are independent. `--freethreaded /path/to/python3.14t` adds a [free-threaded CPython 3.14](https://github.com/astral-sh/python-build-standalone/releases/tag/20261021). The script rejects a binary that is not a free-threaded build.

## Interpreters and threads

Each run measures `threads.py` on every interpreter: four threads run the same CPU-bound function, and the speedup compares their duration with four sequential calls. About ×1 means the threads take turns (a global lock). A value close to ×4 means they run in parallel. The result depends on the cores of the machine, which are displayed. The **Interpreters** tab shows this speedup, the targeted Python version, the wheel ABI and the GIL state when the interpreter reports it (`sys._is_gil_enabled()`, from Python 3.13).

## Performance

`--benchmarks` times eight programs from `benchmarks.py`, each in its own process: n-body, fannkuch-redux and spectral norm (programs of the Computer Language Benchmarks Game), n-queens, a floating-point computation, then json, `re` and a word count with `collections`. Each program makes a cold first call, two warmup rounds for JIT compilers and at least three timed rounds. The tab shows the median and the ratio to CPython. The detail gives the minimum, the standard deviation and the time of the first call. Each program also prints a checksum of its result: an answer that differs from CPython's is a difference, not a timing. The geometric mean of the ratios summarizes each interpreter and feeds a history chart.

The tests in `tests/test_performance.py` check the kernels against published values. `pystone` is not part of the set: it is a port of Dhrystone, a synthetic workload from 1984 that CPython no longer ships and that JIT compilers optimize in ways unrelated to real code. GitHub runners share their hardware, so differences of about 10% are not significant.

## History

Each run adds a compact snapshot (counts per status, interpreter and view, relative speed) to `history.json`. GitHub Pages replaces the whole site on every deployment, so the workflow downloads the published `history.json`, adds its snapshot and publishes it again. `--history path/to/history.json` does the same locally. A missing or unreadable file starts a new history. The **History** tab draws one line per interpreter, with a table view of the same values.

## GitHub Actions

The **Python Conformity** workflow runs on Linux x86-64 on every push to `main`, every Monday and on demand. It first runs the unit tests with the downloaded CPython. It downloads the prebuilt binaries of CPython, free-threaded CPython 3.14, PyPy and GraalPy Community 25.5.5 and checks their digests. The CPython digests come from the `SHA256SUMS` file of the release. It also checks the digest of the RustPython 0.6.0 source archive, then builds the interpreter with the bundled standard library.

In the run summary, download `dashboard-conformity`, unzip the archive and open `index.html`. The workflow enables the application and package scenarios. An observed incompatibility is a measurement result. A failure of the CPython reference in the standard library corpus turns the job red and stays visible in the report when it could be produced.

On `main`, a successful measurement is then published to GitHub Pages by the `publish` job. This deployment assumes the repository's Pages source is set to **GitHub Actions** (Settings › Pages › Build and deployment).

## Tests

```sh
python3.11 -B -m unittest discover -s tests
```

The tests cover page generation from a fictional report, the classification of missing wheels, and the choice of ranking versions and modules. They do not use the network.

## Interpretation

- **Shared cases**. The same call runs on every selected interpreter. The type and value are compared or, for invalid input, whether the exception can be caught with its public class. A missing API, a behavior difference, a timeout and a blocked measurement have distinct statuses.
- **Differences first**. The shared cases and CPython tests tables initially show only differences and unmeasured cases. Unchecking the filter or adding `?diff=0` to the address shows every case.
- **CPython tests**. The bodies of the selected tests run on CPython and PyPy with each binary's own standard library. A guard in the JSON harness lets the selected methods load when the CPython `_json` accelerator is absent. Tests of internal optimizations and of the C API are out of scope. [CPython v3.11.17 sources](https://github.com/python/cpython/tree/v3.11.17/Lib/test)
- **Scope**. The shared cases cover public CPython 3.11 APIs and apply to the binaries and platforms shown. GraalPy targets Python 3.13. The RustPython 0.6.0 binary announces Python 3.14 alpha and appears only in the Interpreters and Performance views. Optional modules depend on each binary's configuration. [GraalPy](https://github.com/oracle/graalpython/releases/tag/graal-25.5.5) · [RustPython](https://rustpython.github.io/docs/getting_started/installation.html)

## License

The dashboard code, the measurement scenarios and the scripts are distributed under the [MIT license](LICENSE). The interpreters, the CPython test suite and the packages downloaded during measurements are distributed by their projects under their own licenses.
