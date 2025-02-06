from pytigon_lib.schhtml.cairodc import *


# Pytest tests
def test_cairo_dc_initialization():
    dc = CairoDc(calc_only=True)
    assert dc.calc_only
    assert dc.width == 595
    assert dc.height == 841


def test_cairo_dc_set_color():
    dc = CairoDc(calc_only=True)
    dc.set_color(255, 0, 0)
    assert (
        pow(sum(dc.ctx.get_source().get_rgba()) - sum((1.0, 0.0, 0.0, 1.0)), 2) < 0.001
    )


def test_cairo_dc_draw_text():
    dc = CairoDc(calc_only=True)
    dc.draw_text(10, 10, "Test")
    assert (
        pow(sum(dc.ctx.get_source().get_rgba()) - sum((0.0, 0.0, 0.0, 1.0)), 2) < 0.001
    )
