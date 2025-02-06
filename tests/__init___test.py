from pytigon_lib import *


# Pytest tests
def test_init_paths():
    """Test the init_paths function."""
    import tempfile
    import shutil

    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Test with no project name and no environment path
        init_paths()

        # Test with project name and environment path
        env_path = os.path.join(temp_dir, "env")
        os.makedirs(env_path)
        init_paths(prj_name="test_project", env_path=env_path)

    finally:
        # Clean up
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_init_paths()
