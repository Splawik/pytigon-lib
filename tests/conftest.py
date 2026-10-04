"""Shared pytest configuration for the pytigon-lib test suite.

The suite mixes pure unit tests with tests that need the full Pytigon
application project (``pytigon`` + a real settings module + the standard
projects). The latter are listed in :data:`INTEGRATION_PATHS`; they are only
collected when both are true:

* the ``pytigon`` package is importable, and
* ``PYTIGON_TEST_FULL=1`` is set.

That keeps the default run fast and, crucially, makes a fresh checkout of the
library testable on its own (the integration modules import ``pytigon`` at
module level, so they must not even be collected without it).

The pytest bootstrap lives here rather than in a ``tests/plugins`` package on
purpose: several Pytigon repositories ship a top-level ``plugins`` package, and
importing them through ``sys.path`` is ambiguous when more than one test tree is
on the path.
"""

import asyncio
import importlib.util
import inspect
import os
import tempfile

import pytest

_PYTIGON_IMPORTABLE = importlib.util.find_spec("pytigon") is not None
RUN_INTEGRATION = _PYTIGON_IMPORTABLE and os.environ.get("PYTIGON_TEST_FULL") == "1"

# Set by ``pytest_configure``; read by ``pytest_terminal_summary``.
HAS_PYTIGON = False

# Paths relative to this conftest (the ``tests`` directory). They used to be
# ``--ignore`` arguments in pyproject.toml; keeping one list makes the boundary
# between unit and integration tests explicit.
INTEGRATION_PATHS = (
    "schdjangoext",
    "schviews",
    "schhttptools/test.py",
    "schhttptools/test2.py",
    "schindent/test.py",
    "schindent/test2.py",
    "schindent/ihtml2html_test.py",
    "schhtml/gen_pdf_test.py",
    "schhtml/pdfdc_test.py",
    "schspreadsheet/gen_doc_test.py",
    "schfs/schfs__init___test.py",
    "schfs/vfstools_test.py",
    "schtools/schhtmlgen_test.py",
)

collect_ignore = [] if RUN_INTEGRATION else list(INTEGRATION_PATHS)

_STANDALONE_HINT = (
    "The 'pytigon' package is not installed, so the test suite is running in "
    "standalone mode: tests that need the full Pytigon stack are not collected. "
    "Install them with: pip install -e '.[test-full]'"
)


def _configure_standalone() -> None:
    """Configure a minimal in-memory Django for the standalone suite."""
    import django
    from django.conf import settings

    if settings.configured:
        return

    # A full test project would set this; in standalone mode it must not point
    # at a settings module that does not exist.
    os.environ.pop("DJANGO_SETTINGS_MODULE", None)

    temp_path = tempfile.gettempdir()

    settings.configure(
        SECRET_KEY="pytigon-lib-tests",
        DEBUG=True,
        USE_TZ=True,
        DEFAULT_AUTO_FIELD="django.db.models.AutoField",
        # Used by schfs.vfstools (temporary file names) and
        # schhttptools.httpclient (writing last_error.html).
        TEMP_PATH=temp_path,
        DATA_PATH=temp_path,
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "django.contrib.sessions",
            "django.contrib.messages",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        MIDDLEWARE=[],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "DIRS": [],
                "OPTIONS": {"context_processors": []},
            }
        ],
        STATIC_URL="/static/",
    )
    django.setup()


def _relative_to_tests(path, config):
    """Return *path* relative to the ``tests`` directory, in posix form."""
    rel = str(path).replace("\\", "/")
    marker = "/tests/"
    index = rel.rfind(marker)
    if index != -1:
        return rel[index + len(marker):]
    for prefix in (
        "tests/",
        str(config.rootpath).replace("\\", "/").rstrip("/") + "/tests/",
    ):
        if rel.startswith(prefix):
            return rel[len(prefix):]
    return rel


def _is_integration(rel_path):
    return any(
        rel_path == path or rel_path.startswith(path + "/")
        for path in INTEGRATION_PATHS
    )


def pytest_configure(config):
    """Initialise Django, with or without the ``pytigon`` project."""
    global HAS_PYTIGON

    import django

    os.environ.setdefault("SECRET_KEY", "anawa")
    os.environ["SCRIPT_MODE"] = "1"

    # The suite uses ``@pytest.mark.asyncio`` but pytest-asyncio is not part of
    # the declared dependencies, so register the marker and run coroutine tests
    # through a minimal event-loop runner (see ``pytest_pyfunc_call`` below).
    config.addinivalue_line(
        "markers", "asyncio: run the test coroutine in a fresh event loop"
    )

    force_standalone = os.environ.get("PYTIGON_TEST_STANDALONE") == "1"

    init = None
    if not force_standalone:
        try:
            from pytigon.django_min_init import init as pytigon_init
        except ImportError:
            pytigon_init = None
        init = pytigon_init

    if init is not None:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings_app")
        init(prj="_schtest", pytigon_standard=True)
        HAS_PYTIGON = True
    else:
        HAS_PYTIGON = False
        _configure_standalone()

    django.setup()


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Explain the standalone run so the missing integration tests are visible."""
    if not HAS_PYTIGON:
        terminalreporter.write_sep("-", "pytigon-lib standalone mode")
        terminalreporter.write_line(_STANDALONE_HINT)


def pytest_collection_modifyitems(config, items):
    """Mark integration tests collected during a full run."""
    if not RUN_INTEGRATION:
        return
    for item in items:
        if _is_integration(_relative_to_tests(item.fspath, config)):
            item.add_marker(pytest.mark.django)


def pytest_pyfunc_call(pyfuncitem):
    """Run ``async def`` tests without depending on pytest-asyncio.

    Declaring a new dependency is not an option here, so when no async plugin
    owns the test the coroutine is driven with :func:`asyncio.run`. A test that
    pytest-asyncio (plugin name ``asyncio``) or anyio (via the ``anyio`` mark)
    already claims is left to that plugin.
    """
    func = pyfuncitem.obj
    if not inspect.iscoroutinefunction(func):
        return None

    pluginmanager = pyfuncitem.config.pluginmanager
    if pluginmanager.hasplugin("asyncio"):
        return None
    if pyfuncitem.get_closest_marker("anyio"):
        return None

    argnames = pyfuncitem._fixtureinfo.argnames
    kwargs = {name: pyfuncitem.funcargs[name] for name in argnames}
    asyncio.run(func(**kwargs))
    return True
