import tempfile
import os
from os import environ
from pytigon_lib.schtools.platform_info import platform_name

#                Client(appimage,emscripten)     Client/DEV                  Server                          Android                         pytigon-lib
#
#ROOT_PATH       site-packages/pytigon           ./                          /home/www-data/www/pytigon                site-packages/pytigon           None
#SERW_PATH       site-packages/pytigon/schserw   ./schserw                   site-packages/pytigon/schserw   site-packages/pytigon/schserw   None
#DATA_PATH       ~/.pytigon                      ~/.pytigon                  /home/www-data/.pytigon         STORAGE/pytigon_data            ~/.pytigon
#LOG_PATH        console                         console                     /var/log                        STORAGE/pytigon_data            ~/.pytigon
#TEMP_PATH       %TEMP%                          %TEMP%                      %TEMP%                          %TEMP%                          %TEMP%
#PRJ_PATH        ~/.pytigon/prj                  ./prj                       /home/www-data/pytigon/prj            SORAGE/pytigon/prj              ~/.pytigon/prj
#PRJ_PATH_ALT    site-packages/pytigon/prj       site-packages/pytigon/prj   site-packages/pytigon/prj      site-packages/pytigon/prj       None
#STATIC_PATH     site-packages/pytigon/static    site-packages/pytigon/staticsite-packages/pytigon/static   site-packages/pytigon/static    site-packages/pytigon/static

PRJ_NAME = None

def get_main_paths(prj_name=None):
    global PRJ_NAME

    if prj_name:
        PRJ_NAME = prj_name

    ret = {}
    platform_type="standard"

    ret["TEMP_PATH"] = tempfile.gettempdir()

    try:
        import pytigon.schserw as pytigon_schserw
    except:
        pytigon_schserw = None

    pytigon_path = None
    if pytigon_schserw:
        serw_path = os.path.dirname(os.path.abspath(pytigon_schserw.__file__))
        pytigon_path = os.path.abspath(os.path.join(serw_path, ".."))
    else:
        serw_path = None

    if 'PYTIGON_ROOT_PATH' in environ:
        root_path = environ['PYTIGON_ROOT_PATH']
    else:
        if serw_path:
            root_path = os.path.abspath(os.path.join(serw_path, ".."))
        else:
            root_path = None
    home_path = os.path.expanduser("~")

    ret['SERW_PATH'] = serw_path
    ret['ROOT_PATH'] = root_path
    ret['PYTIGON_PATH'] = pytigon_path

    if 'START_PATH' in environ:
        cwd = environ['START_PATH']
    else:
        cwd = os.path.abspath(os.getcwd())

    if platform_name() == "Android":
        platform_type = 'android'
    elif not pytigon_schserw:
        platform_type = 'pytigon-li b'
    elif '/home/www-data' in cwd:
        platform_type = 'webserver'
        home_path = '/home/www-data/'
    elif os.path.exists(os.path.join(cwd, "prj")):
        platform_type = 'dev'

    ret['PLATFORM_TYPE'] = platform_type

    if "DATA_PATH" in environ:
        ret['DATA_PATH'] = data_path = environ["DATA_PATH"]
        if platform_type == 'webserver':
            ret["LOG_PATH"] = "/var/log"
        elif platform_type == "pytiogn-lib":
            ret["LOG_PATH"] = data_path
        ret['LOG_PATH'] = None
        ret["PRJ_PATH"] = os.path.join(data_path, "prj")
        ret["PRJ_PATH_ALT"] = os.path.join(root_path, "prj")
    else:
        if platform_type == 'android':
            p1 = p2 = None
            if "SECONDARY_STORAGE" in environ:
                p1 = os.path.join(environ["SECONDARY_STORAGE"], "pytigon_data")
            if "EXTERNAL_STORAGE" in environ:
                p2 = os.path.join(environ["EXTERNAL_STORAGE"], "pytigon_data")
            if p1:
                if os.path.exists(p2):
                    data_path = p2
                else:
                    data_path = p1
            else:
                data_path = p2
            ret["DATA_PATH"] = ret["LOG_PATH"] = data_path
            ret["PRJ_PATH"] = os.path.abspath(os.path.join(data_path, "..", "pytigon", "prj"))
            ret["PRJ_PATH_ALT"] = os.path.join(root_path, "prj")

        elif platform_type == "webserver":
            ret["DATA_PATH"] = data_path = os.path.join(home_path, ".pytigon")
            ret["LOG_PATH"] = "/var/log"
            ret["PRJ_PATH"] = os.path.join(data_path, "prj")
            ret["PRJ_PATH_ALT"] = os.path.join(pytigon_path, "prj")
        else:
            ret["DATA_PATH"] = data_path = os.path.join(home_path, ".pytigon")
            ret["LOG_PATH"] = data_path
            cwd_prj = os.path.join(cwd, "prj")
            if os.path.exists(cwd_prj):
                ret["PRJ_PATH"] = cwd_prj
                ret["PRJ_PATH_ALT"] = os.path.join(root_path, "prj")
            else:
                ret["PRJ_PATH"] = os.path.join(data_path, "prj")
                ret["PRJ_PATH_ALT"] = os.path.join(root_path, "prj")

        if 'STATIC_PATH' in environ:
            static_path = environ['STATIC_PATH']
        elif pytigon_path:
            static_path = os.path.join(pytigon_path, "static")
        else:
            static_path = None

        if platform_type == "webserver":
            if PRJ_NAME:
                ret['STATIC_PATH'] = os.path.join(data_path, "static", PRJ_NAME)
            else:
                ret['STATIC_PATH'] = os.path.join(data_path, "static")
            ret['STATICFILES_DIR'] = os.path.join(pytigon_path, "static")
        else:
            ret['STATIC_PATH'] = static_path
            ret['STATICFILES_DIR'] = static_path

    return ret

def get_prj_name():
    global PRJ_NAME
    return PRJ_NAME
