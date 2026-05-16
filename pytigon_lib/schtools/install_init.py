"""Project initialization and dependency installation utilities."""

import configparser
import logging
import os
import shutil
import sys
import zipfile

from pytigon_lib.schfs import extractall
from pytigon_lib.schtools.process import py_manage, py_run

logger = logging.getLogger(__name__)


def _mkdir(path, ext=None):
    """Create a directory if it does not exist.

    Args:
        path: Base path.
        ext: Optional subdirectory name to append to path.
    """
    p = os.path.join(path, ext) if ext else path
    if not os.path.exists(p):
        try:
            os.makedirs(p, exist_ok=True)
        except OSError:
            logger.warning("Could not create directory: %s", p)


def upgrade_test(zip_path, out_path):
    """Check if an upgrade is needed by comparing generation timestamps.

    Args:
        zip_path: Path to the upgrade zip archive.
        out_path: Path to the installed project directory.

    Returns:
        True if the zip archive contains a newer version, False otherwise.
    """
    if not os.path.exists(zip_path):
        return False

    archive = zipfile.ZipFile(zip_path, "r")
    cfg_txt = archive.read("install.ini").decode("utf-8")
    cfg = configparser.ConfigParser()
    cfg.read_string(cfg_txt)
    t1 = cfg["DEFAULT"]["GEN_TIME"]
    ini2 = os.path.join(out_path, "install.ini")
    if os.path.exists(ini2):
        cfg2 = configparser.ConfigParser()
        cfg2.read(ini2)
        t2 = cfg2["DEFAULT"]["GEN_TIME"]
        if t2 < t1:
            return True
    return False


def pip_install(pip_str, prjlib, confirm=False, upgrade=False):
    """Install Python packages to a target directory using pip.

    Args:
        pip_str: Space-separated list of package names/requirements.
        prjlib: Target directory for installation.
        confirm: If True, requires 'Successfully installed' in output to return True.
        upgrade: If True, passes --upgrade to pip.

    Returns:
        True if installation succeeded (when confirm=True), always False when
        confirm=False (caller should check exit code externally).
    """
    packages = [x.strip() for x in pip_str.split(" ") if x]
    print("pip install: ", pip_str)
    exit_code, output_tab, err_tab = py_run(
        [
            "-m",
            "pip",
            "--disable-pip-version-check",
            "install",
            f"--target={prjlib}",
        ]
        + (["--upgrade"] if upgrade else [])
        + packages
    )
    success = False
    if output_tab:
        for pos in output_tab:
            if pos:
                print("pip info: ", pos)
            if "Successfully installed" in pos:
                success = True
    if err_tab:
        for pos in err_tab:
            if pos:
                print("pip error: ", pos)

    return success if confirm else False


def build_all(path):
    """Execute all ``*_build.py`` scripts found under a directory tree.

    Each script is expected to define a ``build(path=...)`` function.
    Uses exec() to run user-provided build scripts in a controlled
    local namespace.

    Args:
        path: Root directory to walk for build scripts.

    Returns:
        True if all builds succeeded, False if any failed.
    """
    ret = True
    for root, dirs, files in os.walk(path):
        for name in files:
            if name.endswith("_build.py"):
                p = os.path.join(root, name)
                with open(p) as f:
                    local_ns = {}
                    buf = f.read()
                    exec(buf, globals(), local_ns)
                    if "build" in local_ns:
                        x = local_ns["build"](path=p.replace("_build.py", ".nim"))
                        if not x:
                            ret = False
    return ret


def upgrade_local_libs():
    """Upgrade locally installed pip packages based on project install.ini."""
    from django.conf import settings

    prjlib = os.path.join(settings.DATA_PATH, settings.PRJ_NAME, "prjlib")
    config_file = os.path.join(settings.PRJ_PATH, settings.PRJ_NAME, "install.ini")
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        if "DEFAULT" in config:
            pip_str = config["DEFAULT"].get("PIP", "")
            if pip_str:
                pip_install(pip_str, prjlib, confirm=True, upgrade=True)


# System management commands that trigger special initialization behavior.
SYS_COMMANDS = frozenset(
    {
        "makeallmigrations",
        "migrate",
        "createautouser",
        "import_projects",
    }
)


def _acquire_lock():
    """Attempt to acquire a multiprocessing lock for serializing init.

    Returns:
        A Lock object or None if multiprocessing is unavailable.
    """
    try:
        import multiprocessing

        lock = multiprocessing.Lock()
        lock.acquire()
        return lock
    except (ImportError, OSError):
        return None


def _release_lock(lock):
    """Release a multiprocessing lock if one was acquired."""
    if lock is not None:
        try:
            lock.release()
        except Exception:
            pass


def init(prj, root_path, data_path, prj_path, static_app_path, paths=None):
    """Initialize a project: extract archives, run migrations, install deps.

    This is the main entry point for first-run project setup. It handles
    zip extraction, database creation, Django migrations, pip installation,
    and static file copying.

    Args:
        prj: Project name (e.g. 'schdevtools').
        root_path: Root installation directory.
        data_path: Data directory for databases and media.
        prj_path: Path where project sources live.
        static_app_path: Path for application static files.
        paths: Optional list of additional directories to create.
    """
    if prj == "_schall":
        return

    lock = _acquire_lock()

    _root_path = os.path.normpath(root_path)
    _data_path = os.path.normpath(data_path)
    _prj_path = os.path.normpath(prj_path)
    _static_app_path = os.path.normpath(static_app_path)
    is_data_path = os.path.exists(os.path.join(_data_path, "install.ini"))
    is_dev = prj in ("schdevtools", "schmanage", "_schsetup")
    is_static_path = os.path.exists(_static_app_path)
    upgrade = False

    if is_data_path and is_dev:
        if upgrade_test(
            os.path.join(os.path.join(_root_path, "install"), ".pytigon.zip"),
            _data_path,
        ):
            upgrade = True
            print("Upgrade data")

    if not is_data_path:
        zip_file2 = os.path.join(os.path.join(_root_path, "install"), ".pytigon.zip")
        if not os.path.exists(_data_path):
            os.makedirs(_data_path)
        if os.path.exists(zip_file2) and is_dev:
            extractall(zipfile.ZipFile(zip_file2), _data_path)
        if not os.path.exists(os.path.join(_data_path, "media")):
            media_path = os.path.join(os.path.join(_data_path, "media"))
            os.makedirs(media_path)
            os.makedirs(os.path.join(media_path, "filer_public"))
            os.makedirs(os.path.join(media_path, "filer_private"))
            os.makedirs(os.path.join(media_path, "filer_public_tumbnails"))
            os.makedirs(os.path.join(media_path, "filer_private_thumbnails"))
        if not os.path.exists(os.path.join(_data_path, "doc")):
            doc_path = os.path.join(os.path.join(_data_path, "doc"))
            os.makedirs(doc_path)

        if SYS_COMMANDS.intersection(sys.argv):
            prjs = []
        elif is_dev:
            prjs = [ff for ff in os.listdir(_prj_path) if not ff.startswith("_")]
        else:
            prjs = [
                prj,
            ]

        tmp = os.getcwd()
        for app in prjs:
            path = os.path.join(_prj_path, app)
            if os.path.isdir(path):
                db_path = os.path.join(os.path.join(_data_path, app), f"{app}.db")
                os.chdir(path)
                print("python: pytigon: init: ", path)
                if not os.path.exists(db_path):
                    print("python: pytigon: init: create:", db_path)
                    exit_code, output_tab, err_tab = py_manage(
                        ["makeallmigrations"], False
                    )
                    if err_tab:
                        print(err_tab)
                    exit_code, output_tab, err_tab = py_manage(["migrate"], False)
                    if err_tab:
                        print(err_tab)
                    exit_code, output_tab, err_tab = py_manage(
                        ["createautouser"], False
                    )
                    if err_tab:
                        print(err_tab)
                    if app == "schdevtools":
                        print("python: pytigon: import_projects!")
                        exit_code, output_tab, err_tab = py_manage(
                            ["import_projects"], False
                        )
                        print("python: pytigon: projects imported!")
                        if err_tab:
                            print(err_tab)
        os.chdir(tmp)

    if upgrade:
        zip_file2 = os.path.join(os.path.join(_root_path, "install"), ".pytigon.zip")
        if not os.path.exists(_data_path):
            os.makedirs(_data_path)
        if os.path.exists(zip_file2):
            extractall(zipfile.ZipFile(zip_file2), _data_path, exclude=[r".*\.db"])

    if not is_static_path:
        p2 = os.path.join(os.path.join(_root_path, "static"), "app")
        if os.path.exists(p2):
            shutil.copytree(p2, _static_app_path)

    _paths = [
        "",
        "cache",
        "plugins_cache",
        "_schall",
        "schdevtools",
        "prj",
        "temp",
        "static",
        prj,
    ]
    for p in _paths:
        _mkdir(_data_path, p)
    if paths:
        for p in paths:
            _mkdir(p)

    prjlib = os.path.join(_data_path, prj, "prjlib")
    if not os.path.exists(prjlib) or not os.path.exists(
        os.path.join(prjlib, "install.txt")
    ):
        ok = True
        if not os.path.exists(prjlib):
            os.mkdir(prjlib)
        config_file = os.path.join(prj_path, prj, "install.ini")
        if os.path.exists(config_file):
            config = configparser.ConfigParser()
            config.read(config_file)
            if "DEFAULT" in config:
                pip_str = config["DEFAULT"].get("PIP", "")
                if pip_str:
                    x = pip_install(pip_str, prjlib, confirm=True)
                    if not x:
                        ok = False
        x = build_all(os.path.join(_prj_path, prj))
        if not x:
            ok = False
        if ok:
            with open(os.path.join(prjlib, "install.txt"), "w") as f:
                f.write("OK")

    if os.path.exists(prjlib):
        if prjlib not in sys.path:
            sys.path.append(prjlib)

    syslib = os.path.join(_data_path, prj, "syslib")
    if not os.path.exists(syslib):
        os.makedirs(syslib)
        with open(os.path.join(syslib, "__init__.py"), "w") as f:
            f.write(" ")

    _release_lock(lock)
