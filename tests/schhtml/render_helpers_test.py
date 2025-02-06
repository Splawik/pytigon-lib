from pytigon_lib.schhtml.render_helpers import *


# Pytest tests
def test_sizes_from_attr():
    assert sizes_from_attr("10px", None) == [10, 10, 10, 10]
    assert sizes_from_attr("10px 20px", None) == [20, 20, 10, 10]
    assert sizes_from_attr("10px 20px 30px 40px", None) == [40, 20, 10, 30]


def test_get_size():
    class MockRender:
        def get_size(self):
            return [1, 2, 3, 4]

    render_list = [MockRender(), MockRender()]
    assert get_size(render_list) == [2, 4, 6, 8]


if __name__ == "__main__":
    pytest.main()
