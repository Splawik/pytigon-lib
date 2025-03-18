def pytest_configure(config):
    from pytigon.django_min_init import init
    init(prj="_schtest", pytigon_standard=True)

def pytest_unconfigure(config):
    pass
