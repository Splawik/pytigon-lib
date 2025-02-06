from pytigon_lib.schtools.platform_info import *


# Pytest tests
def test_platform_name():
    # Mock platform.system() and environ for testing
    original_system = platform.system
    original_environ = environ.copy()

    # Test Linux
    platform.system = lambda: "Linux"
    environ.clear()
    assert platform_name() == "Linux"

    # Test Android
    platform.system = lambda: "Linux"
    environ["ANDROID_ARGUMENT"] = "some_value"
    assert platform_name() == "Android"

    # Test Windows
    platform.system = lambda: "Windows"
    environ.clear()
    assert platform_name() == "Windows"

    # Test Unknown (simulate error)
    platform.system = lambda: "Unknown"
    assert platform_name() == "Unknown"

    # Restore original functions and environment
    platform.system = original_system
    environ.update(original_environ)


if __name__ == "__main__":
    print(f"Running on: {platform_name()}")
