from pytigon_lib.schhtml.wxgc import *

# Pytest tests
import pytest


def test_graphics_context_dc():
    app = wx.App(False)
    dc = GraphicsContextDc(calc_only=True)
    assert dc.ctx is not None
    dc.close()
    del app


def test_graphics_context_dcinfo():
    app = wx.App(False)
    dc = GraphicsContextDc(calc_only=True)
    info = GraphicsContextDcinfo(dc)
    assert info.get_line_dy(10) == 30
    dc.close()
    del app


if __name__ == "__main__":
    pytest.main()
