# pytigon-lib tests

The test suite runs in two modes.

## Standalone (default)

Runs without the `pytigon` application project:

```
pip install -e ".[dev]"
pytest tests/
```

Tests that need the full Pytigon stack are listed in `INTEGRATION_PATHS`
(`tests/conftest.py`) and are **not collected** in this mode, because those
modules import `pytigon` at import time. A fresh checkout of the library is
therefore testable on its own — this is what the `pytigon-lib` CI job runs.

## Full (with the Pytigon project)

Runs the unit tests *and* the integration tests:

```
pip install -e ".[test-full]"      # pulls pytigon + pytigon-standard-prj
PYTIGON_TEST_FULL=1 pytest tests/
```

Integration tests are marked `django`, so they can be selected on their own:

```
PYTIGON_TEST_FULL=1 pytest tests/ -m django
```

> The integration suite is heavy (some tests start servers, render documents or
> touch the filesystem) and can take a long time. Run it per directory while
> iterating, for example:
> `PYTIGON_TEST_FULL=1 pytest tests/schdjangoext`
>
> Run the directories **one at a time**. Some of them share process-wide state
> (the fsspec instance cache and the virtual filesystem mounts), so combining
> `tests/schhtml` with `tests/schfs` in a single run makes the temp-directory
> cleanup in `tests/schfs/vfstools_test.py` fail with
> `OSError: Directory not empty`, even though each directory passes on its own.
> Per-directory runs are green:
>
> | Directory | Result (full mode) |
> |---|---|
> | `tests/schviews` | 186 passed |
> | `tests/schfs` | 205 passed |
> | `tests/schhtml` | 790 passed, 1 skipped (golden) |
> | `tests/schspreadsheet` | 97 passed, 1 skipped (golden) |
> | `tests/schindent` | 314 passed, 3 skipped (golden) |
> | `tests/schtools` | 615 passed |
> | `tests/schhttptools` | 141 passed |
> | `tests/schdjangoext` | see below |

`tests/schfs/conftest.py` used to configure a minimal Django at import time.
Pytest imports a directory's `conftest.py` *before* `pytest_configure` of the
root one, so that file silently replaced the project settings and made results
depend on which paths were passed on the command line. The root `conftest.py`
now always owns the configuration, and the directory-level file was removed.

## Standalone-mode override

`PYTIGON_TEST_STANDALONE=1` forces the minimal standalone Django configuration
even when `pytigon` happens to be importable. It exists to test the standalone
path itself:

```
PYTIGON_TEST_STANDALONE=1 pytest tests/
```

## Golden tests

Tests that compare rendered output against committed reference files depend on
the local LibreOffice version, fonts and PDF libraries, and on reference files
that predate current renderer behaviour. They are marked `golden` and skipped
unless `PYTIGON_GOLDEN_TESTS=1` is set:

```
PYTIGON_GOLDEN_TESTS=1 pytest tests/schhtml tests/schspreadsheet tests/schindent
```

Affected: `tests/schhtml/gen_pdf_test.py`,
`tests/schspreadsheet/gen_doc_test.py`, `tests/schindent/ihtml2html_test.py`.

## Known state of the integration suite

`tests/schdjangoext` is **not green** and is not part of the CI gate. Measured
on Python 3.14 / Django 6: **280 passed, 15 skipped, 48 failed, 17 errors**.
The failures cluster into a few root causes, all of them test-suite rot rather
than product regressions:

| Area | Count | Cause |
|---|---|---|
| `django_storage_test.py` | 21 | expectations predate the change that derives `base_url` from `MEDIA_URL` |
| `models_test.py` | 8 + 17 errors | test scaffolding predates Django 6 (`Abstract models cannot be instantiated`) and Python 3.14 (`__bases__ assignment: 'object' deallocator differs from 'Base'`) |
| `arrow_tools_test.py` | 8 | the fallback tests assume `pyarrow` is absent; development environments have it installed |
| `server_test.py`, `spreadsheet_render_test.py`, `schdjangoext_tools_*_test.py` | 12 | stale expectations against current settings (e.g. `make_href`, `MEDIA_ROOT`) |

Everything else in the integration suite is green: `schviews` 186, `schfs` 205,
`schhtml` 790, `schspreadsheet` 97, `schindent` 314, `schtools` 615,
`schhttptools` 141.
