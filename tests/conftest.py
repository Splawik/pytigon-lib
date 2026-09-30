import asyncio
import inspect

pytest_plugins = [
    "plugins.pytigon_plugin",
]


def pytest_configure(config):
    import django
    from django.conf import settings

    # The suite uses ``@pytest.mark.asyncio`` but pytest-asyncio is not part of
    # the declared dependencies, so register the marker and run coroutine tests
    # through a minimal event-loop runner (see ``pytest_pyfunc_call`` below).
    config.addinivalue_line(
        "markers", "asyncio: run the test coroutine in a fresh event loop"
    )
    django.setup()


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
