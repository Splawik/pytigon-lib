"""Tests for :mod:`pytigon_lib.schhtml.basedc`."""

import io
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schhtml.basedc import (
    BaseDc,
    NullDc,
    SubDc,
    convert_fun_arg,
)
from pytigon_lib.schhtml.dc_info import (
    BaseDcInfo,
    BaseDcInfoCommon,
    NullDcinfo,
)


class TestBaseDcInit:
    """Tests for :class:`BaseDc` constructor."""

    def test_init_no_args(self):
        dc = BaseDc()
        assert dc.calc_only is False
        assert dc.x == 0
        assert dc.y == 0
        assert dc.rec is False
        assert dc.store == []
        assert dc.width == dc.default_width
        assert dc.height == dc.default_height
        assert dc.output_name is None
        assert dc.output_stream is None
        assert dc.scale == 1.0
        assert dc.notify_callback is None
        assert dc.paging is False
        assert dc.pages == []
        assert dc.base_font_size == 10
        assert dc.handle_html_directly is False
        assert dc.last_style == "None"
        assert isinstance(dc.dc_info, BaseDcInfo)

    def test_init_calc_only_true(self):
        dc = BaseDc(calc_only=True)
        assert dc.calc_only is True

    def test_init_custom_width_height(self):
        dc = BaseDc(width=800, height=600)
        assert dc.width == 800
        assert dc.height == 600

    def test_init_width_none_uses_default(self):
        dc = BaseDc(width=None)
        assert dc.width == dc.default_width

    def test_init_height_none_uses_default(self):
        dc = BaseDc(height=None)
        assert dc.height == dc.default_height

    def test_init_output_name(self):
        dc = BaseDc(output_name="test.pdf")
        assert dc.output_name == "test.pdf"

    def test_init_output_stream(self):
        stream = io.BytesIO()
        dc = BaseDc(output_stream=stream)
        assert dc.output_stream is stream

    def test_init_scale(self):
        dc = BaseDc(scale=2.5)
        assert dc.scale == 2.5

    def test_init_notify_callback(self):
        cb = MagicMock()
        dc = BaseDc(notify_callback=cb)
        assert dc.notify_callback is cb

    def test_init_record_true(self):
        dc = BaseDc(record=True)
        assert dc.rec is True

    def test_init_record_false(self):
        dc = BaseDc(record=False)
        assert dc.rec is False

    def test_default_width_is_a4_width(self):
        dc = BaseDc()
        expected = int(210 * 72 / 25.4)
        assert dc.default_width == expected

    def test_default_height_is_a4_height(self):
        dc = BaseDc()
        expected = int(297 * 72 / 25.4)
        assert dc.default_height == expected


class TestBaseDcProperties:
    """Tests for property accessors on :class:`BaseDc`."""

    def test_dx_property_returns_width(self):
        dc = BaseDc(width=800, height=600)
        assert dc.dx == 800

    def test_dy_property_returns_height(self):
        dc = BaseDc(width=800, height=600)
        assert dc.dy == 600

    def test_dx_property_default(self):
        dc = BaseDc()
        assert dc.dx == dc.default_width

    def test_dy_property_default(self):
        dc = BaseDc()
        assert dc.dy == dc.default_height


class TestBaseDcPaging:
    """Tests for paging methods on :class:`BaseDc`."""

    def test_set_paging_enable(self):
        dc = BaseDc()
        dc.set_paging(True)
        assert dc.paging is True

    def test_set_paging_disable(self):
        dc = BaseDc()
        dc.set_paging(True)
        dc.set_paging(False)
        assert dc.paging is False

    def test_set_paging_default_enable(self):
        dc = BaseDc()
        dc.set_paging()
        assert dc.paging is True

    def test_get_page_count_empty(self):
        dc = BaseDc()
        assert dc.get_page_count() == 0

    def test_get_page_count_after_end_document(self):
        dc = BaseDc(record=True)
        dc.draw_text(10, 10, "test")
        dc.end_document()
        assert dc.get_page_count() == 1

    def test_get_page_count_after_end_page(self):
        dc = BaseDc(record=True)
        dc.draw_text(10, 10, "test")
        dc.end_page()
        assert dc.get_page_count() == 1


class TestBaseDcState:
    """Tests for state save/restore on :class:`BaseDc`."""

    def test_state_returns_expected_keys(self):
        dc = BaseDc(width=800, height=600)
        state = dc.state()
        assert len(state) == 9
        assert state[0] == 0
        assert state[1] == 800
        assert state[2] == 600
        assert state[3] == 10
        assert state[4] is False
        assert state[5] == 0
        assert state[6] == 0

    def test_state_includes_styles(self):
        dc = BaseDc()
        dc.dc_info.styles.append("test_style")
        state = dc.state()
        assert state[7] == ["test_style"]

    def test_state_after_record_pages(self):
        dc = BaseDc(record=True)
        dc.draw_text(10, 10, "hello")
        dc.end_document()
        state = dc.state()
        assert state[0] == 1

    def test_restore_state_updates_attributes(self):
        dc = BaseDc()
        state = [2, 100, 200, 12, True, 50, 60, ["a", "b"], "st1"]
        dc.restore_state(state)
        assert dc.width == 100
        assert dc.height == 200
        assert dc.base_font_size == 12
        assert dc.paging is True
        assert dc._maxwidth == 50
        assert dc._maxheight == 60
        assert dc.dc_info.styles == ["a", "b"]
        assert dc.last_style == "st1"


class TestBaseDcSizeMethods:
    """Tests for size-related methods on :class:`BaseDc`."""

    def test_get_size_returns_width_height(self):
        dc = BaseDc(width=800, height=600)
        assert dc.get_size() == [800, 600]

    def test_get_max_sizes_initial(self):
        dc = BaseDc()
        assert dc.get_max_sizes() == (0, 0)

    def test_test_point_updates_maxwidth(self):
        dc = BaseDc()
        dc.test_point(100, 50)
        assert dc._maxwidth == 100

    def test_test_point_updates_maxheight(self):
        dc = BaseDc()
        dc.test_point(50, 200)
        assert dc._maxheight == 200

    def test_test_point_does_not_lower_max(self):
        dc = BaseDc()
        dc.test_point(100, 200)
        dc.test_point(10, 20)
        assert dc._maxwidth == 100
        assert dc._maxheight == 200
        assert dc.get_max_sizes() == (100, 200)

    def test_set_base_font_size(self):
        dc = BaseDc()
        dc.set_base_font_size(14)
        assert dc.base_font_size == 14


class TestBaseDcScale:
    """Tests for scale methods on :class:`BaseDc`."""

    def test_set_scale(self):
        dc = BaseDc(scale=1.0)
        dc.set_scale(2.0)
        assert dc.scale == 2.0

    def test_is_calc_only_default_false(self):
        dc = BaseDc()
        assert dc.is_calc_only() is False

    def test_is_calc_only_true(self):
        dc = BaseDc(calc_only=True)
        assert dc.is_calc_only() is True


class TestBaseDcRgb:
    """Tests for :class:`BaseDc.rgbfromhex`."""

    def test_rgb_3_digit_hex(self):
        dc = BaseDc()
        assert dc.rgbfromhex("#f00") == (240, 0, 0)

    def test_rgb_3_digit_hex_white(self):
        dc = BaseDc()
        assert dc.rgbfromhex("#fff") == (240, 240, 240)

    def test_rgb_6_digit_hex(self):
        dc = BaseDc()
        assert dc.rgbfromhex("#ff0000") == (255, 0, 0)

    def test_rgb_6_digit_hex_green(self):
        dc = BaseDc()
        assert dc.rgbfromhex("#00ff00") == (0, 255, 0)

    def test_rgb_invalid_hex_returns_zero(self):
        dc = BaseDc()
        with pytest.raises(ValueError):
            dc.rgbfromhex("invalid")

    def test_rgb_empty_hex_returns_zero(self):
        dc = BaseDc()
        assert dc.rgbfromhex("") == (0, 0, 0)


class TestBaseDcRecord:
    """Tests for record/play mechanism on :class:`BaseDc`."""

    def test_record_stores_when_rec_true(self):
        dc = BaseDc(record=True)
        dc.record("draw_text", (10, 10, "hello"))
        assert dc.store == [("draw_text", (10, 10, "hello"))]

    def test_record_does_not_store_when_rec_false(self):
        dc = BaseDc(record=False)
        dc.record("draw_text", (10, 10, "hello"))
        assert dc.store == []

    def test_record_with_no_args(self):
        dc = BaseDc(record=True)
        dc.record("fill")
        assert dc.store == [("fill", None)]

    def test_play_calls_methods_on_pages(self):
        dc = BaseDc(record=True)
        dc.draw_text(10, 10, "hello")
        dc.end_page()
        dc.play()
        assert dc.last_style == "None"

    def test_play_single_page(self):
        dc = BaseDc(record=True)
        dc.draw_text(10, 10, "p1")
        dc.end_page()
        dc.rec = True
        dc.draw_text(20, 20, "p2")
        dc.end_page()
        assert dc.get_page_count() == 2
        dc.play(page=0)
        assert dc.last_style == "None"


class TestBaseDcSubdc:
    """Tests for :class:`BaseDc.subdc` method."""

    def test_subdc_returns_subdc_instance(self):
        dc = BaseDc(width=800, height=600)
        sub = dc.subdc(10, 20, 100, 200)
        assert isinstance(sub, SubDc)
        assert sub.x == 10
        assert sub.y == 20
        assert sub.dx == 100
        assert sub.dy == 200

    def test_subdc_calls_test_point_when_reg_max(self):
        dc = BaseDc(width=800, height=600)
        sub = dc.subdc(10, 20, 100, 200, reg_max=True)
        assert dc._maxwidth == 110
        assert dc._maxheight == 220

    def test_subdc_no_test_point_when_reg_max_false(self):
        dc = BaseDc(width=800, height=600)
        sub = dc.subdc(10, 20, 100, 200, reg_max=False)
        assert dc._maxwidth == 0
        assert dc._maxheight == 0


class TestBaseDcSaveLoad:
    """Tests for save/load to ZIP on :class:`BaseDc`."""

    def test_save_and_load_roundtrip(self):
        dc = BaseDc(record=True, width=800, height=600)
        dc.set_paging(True)
        dc.draw_text(10, 10, "hello")
        dc.end_document()

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_name = tmp.name

        try:
            dc.save(tmp_name)
            assert zipfile.is_zipfile(tmp_name)

            dc2 = BaseDc()
            dc2.load(tmp_name)
            assert dc2.width == 800
            assert dc2.height == 600
            assert dc2.paging is True
            assert dc2.get_page_count() == 1
        finally:
            import os
            os.remove(tmp_name)


class TestBaseDcIntrinsicMethods:
    """Tests for methods called internally (record wrappers)."""

    def test_fill_records(self):
        dc = BaseDc(record=True)
        dc.fill(1, 2, 3)
        assert dc.store == [("fill", (1, 2, 3))]

    def test_draw_records(self):
        dc = BaseDc(record=True)
        dc.draw()
        assert dc.store == [("draw", ())]

    def test_set_color_records(self):
        dc = BaseDc(record=True)
        dc.set_color(255, 0, 0)
        assert dc.store == [("set_color", (255, 0, 0))]

    def test_set_line_width_records(self):
        dc = BaseDc(record=True)
        dc.set_line_width(3)
        assert dc.store == [("set_line_width", (3,))]

    def test_set_style_records_and_updates_last_style(self):
        dc = BaseDc(record=True)
        dc.set_style("heading1")
        assert dc.last_style == "heading1"
        assert dc.store == [("set_style", ("heading1",))]

    def test_add_line_records(self):
        dc = BaseDc(record=True)
        dc.add_line(0, 0, 10, 10)
        assert dc.store == [("add_line", (0, 0, 10, 10))]

    def test_add_rectangle_records(self):
        dc = BaseDc(record=True)
        dc.add_rectangle(0, 0, 50, 50)
        assert dc.store == [("add_rectangle", (0, 0, 50, 50))]

    def test_add_arc_records(self):
        dc = BaseDc(record=True)
        dc.add_arc(50, 50, 25, 0, 360)
        assert dc.store == [("add_arc", (50, 50, 25, 0, 360))]

    def test_add_ellipse_records(self):
        dc = BaseDc(record=True)
        dc.add_ellipse(50, 50, 100, 80)
        assert dc.store == [("add_ellipse", (50, 50, 100, 80))]

    def test_add_polygon_records(self):
        dc = BaseDc(record=True)
        dc.add_polygon((0, 0), (10, 0), (5, 10))
        assert dc.store == [("add_polygon", ((0, 0), (10, 0), (5, 10)))]

    def test_add_spline_records(self):
        dc = BaseDc(record=True)
        dc.add_spline((0, 0), (10, 10), True)
        assert dc.store == [("add_spline", ((0, 0), (10, 10), True))]

    def test_draw_text_records(self):
        dc = BaseDc(record=True)
        dc.draw_text(10, 10, "hello")
        assert dc.store == [("draw_text", (10, 10, "hello"))]

    def test_draw_rotated_text_records(self):
        dc = BaseDc(record=True)
        dc.draw_rotated_text(10, 10, "hello", 90)
        assert dc.store == [("draw_rotated_text", (10, 10, "hello", 90))]

    def test_draw_image_records(self):
        dc = BaseDc(record=True)
        dc.draw_image(0, 0, 50, 50, 1, b"data")
        assert dc.store == [("draw_image", (0, 0, 50, 50, 1, b"data"))]


class TestBaseDcGetDcInfo:
    """Tests for :class:`BaseDc.get_dc_info`."""

    def test_get_dc_info_returns_base_dc_info(self):
        dc = BaseDc()
        info = dc.get_dc_info()
        assert isinstance(info, BaseDcInfo)

    def test_get_dc_info_returned_object_has_dc_ref(self):
        dc = BaseDc()
        info = dc.get_dc_info()
        assert info.dc is dc


class TestBaseDcNotify:
    """Tests for notify_callback usage on :class:`BaseDc`."""

    def test_start_page_calls_notify_callback(self):
        cb = MagicMock()
        dc = BaseDc(notify_callback=cb)
        dc.start_page()
        cb.assert_called_once_with("start_page", {"dc": dc})

    def test_end_page_calls_notify_callback(self):
        cb = MagicMock()
        dc = BaseDc(notify_callback=cb, record=True)
        dc.draw_text(10, 10, "x")
        dc.end_page()
        cb.assert_called_once_with("end_page", {"dc": dc})

    def test_start_page_no_notify_callback_does_not_raise(self):
        dc = BaseDc(notify_callback=None)
        dc.start_page()

    def test_end_page_no_notify_callback_does_not_raise(self):
        dc = BaseDc(notify_callback=None, record=True)
        dc.draw_text(10, 10, "x")
        dc.end_page()


class TestBaseDcClose:
    """Tests for :class:`BaseDc.close`."""

    def test_close_does_nothing_be_default(self):
        dc = BaseDc()
        dc.close()


class TestBaseDcScaleImage:
    """Tests for :class:`BaseDc._scale_image`."""

    def test_scale_0_no_scaling(self):
        dc = BaseDc()
        result = dc._scale_image(0, 0, 100, 50, 0, 200, 100)
        assert result == (1, 1)

    def test_scale_1_fit_both(self):
        dc = BaseDc()
        xs, ys = dc._scale_image(0, 0, 200, 100, 1, 100, 50)
        assert xs == 2.0
        assert ys == 2.0

    def test_scale_2_larger_dimension(self):
        dc = BaseDc()
        xs, ys = dc._scale_image(0, 0, 200, 50, 2, 100, 50)
        assert xs == 2.0
        assert ys == 2.0

    def test_scale_3_smaller_dimension(self):
        dc = BaseDc()
        xs, ys = dc._scale_image(0, 0, 200, 200, 3, 100, 50)
        assert xs == 2.0
        assert ys == 2.0

    def test_scale_4_or_above_no_scaling(self):
        dc = BaseDc()
        result = dc._scale_image(0, 0, 200, 100, 4, 100, 50)
        assert result == (1, 1)

    def test_scale_1_dx_zero_dy_positive(self):
        dc = BaseDc()
        xs, ys = dc._scale_image(0, 0, 0, 100, 1, 100, 50)
        assert ys == 2.0
        assert xs == 2.0

    def test_scale_1_both_zero(self):
        dc = BaseDc()
        result = dc._scale_image(0, 0, 0, 0, 1, 100, 50)
        assert result == (1, 1)


class TestBaseDcEndDocument:
    """Tests for :class:`BaseDc.end_document`."""

    def test_end_document_stores_when_store_not_empty(self):
        dc = BaseDc(record=True)
        dc.draw_text(10, 10, "hello")
        dc.end_document()
        assert dc.pages == [dc.store]
        assert len(dc.pages) == 1

    def test_end_document_does_not_store_when_store_empty(self):
        dc = BaseDc()
        dc.end_document()
        assert dc.pages == []


class TestBaseDcStartEndPage:
    """Tests for start_page/end_page on :class:`BaseDc`."""

    def test_start_page_resets_store_when_not_empty(self):
        dc = BaseDc(record=True)
        dc.draw_text(10, 10, "hello")
        dc.start_page()
        assert dc.store == []

    def test_start_page_resets_last_style(self):
        dc = BaseDc()
        dc.last_style = "heading1"
        dc.start_page()
        assert dc.last_style == "None"

    def test_end_page_resets_last_style(self):
        dc = BaseDc(record=True)
        dc.draw_text(10, 10, "x")
        dc.end_page()
        assert dc.last_style == "None"

    def test_start_page_stores_previous_page(self):
        dc = BaseDc(record=True)
        dc.draw_text(10, 10, "x")
        first_store = dc.store
        dc.start_page()
        assert dc.pages == [first_store]


class TestBaseDcPlayStr:
    """Tests for :class:`BaseDc.play_str`."""

    def test_play_str_parses_json_actions(self):
        dc = BaseDc(record=True)
        dc.play_str('["set_style", ["heading1"]]\n["draw_text", [10, 10, "hi"]]')
        assert dc.last_style == "heading1"
        # json_loads produces tuples for JSON arrays, so draw_text args are (10, 10, "hi")
        assert any(p[0] == "draw_text" and p[1] == (10, 10, "hi") for p in dc.store)

    def test_play_str_handles_empty_string(self):
        dc = BaseDc(record=True)
        dc.play_str("")
        assert dc.store == []

    def test_play_str_skips_blank_lines(self):
        dc = BaseDc(record=True)
        dc.play_str('["set_style", ["h1"]]\n\n["draw", []]')
        assert dc.last_style == "h1"
        assert any(p[0] == "draw" and p[1] == () for p in dc.store)


class TestBaseDcAnnotate:
    """Tests for :class:`BaseDc.annotate`."""

    def test_annotate_does_nothing(self):
        dc = BaseDc()
        dc.annotate("bookmark", {"page": 1})


class TestBaseDcInfo:
    """Tests for :class:`BaseDcInfo`."""

    def test_init(self):
        dc = BaseDc()
        info = BaseDcInfo(dc)
        assert info.dc is dc
        assert info.styles == []

    def test_get_text_width(self):
        info = BaseDcInfo(None)
        w = info.get_text_width("hello", "default")
        assert w == 60

    def test_get_text_width_empty(self):
        info = BaseDcInfo(None)
        w = info.get_text_width("", "default")
        assert w == 0

    def test_get_text_height(self):
        info = BaseDcInfo(None)
        h = info.get_text_height("hello", "default")
        assert h == 12

    def test_get_line_dy(self):
        info = BaseDcInfo(None)
        assert info.get_line_dy(2) == 24

    def test_get_style_id_new(self):
        info = BaseDcInfo(None)
        info.styles = []
        idx = info.get_style_id("bold")
        assert idx == 0
        assert info.styles == ["bold"]

    def test_get_style_id_existing(self):
        info = BaseDcInfo(None)
        info.styles = ["bold", "italic"]
        idx = info.get_style_id("italic")
        assert idx == 1
        assert info.styles == ["bold", "italic"]

    def test_get_multiline_text_width(self):
        info = BaseDcInfo(None)
        opt, minsize, maxsize = info.get_multiline_text_width(
            "a b c d e f g h i j k l m n o p q r s t", "default"
        )
        assert opt > 0
        assert minsize == 12
        assert maxsize > 0

    def test_get_multiline_text_height_raises_attributeerror_due_to_bug(self):
        """BaseDcInfo.get_multiline_text_height has a bug: txt.dc.split() should be txt.split()."""
        info = BaseDcInfo(None)
        with pytest.raises(AttributeError):
            info.get_multiline_text_height("hello world foo bar", 200, "default")

    def test_get_extents(self):
        info = BaseDcInfo(None)
        dx, dx_space, dy_up, dy_down = info.get_extents("hi", "default")
        assert dx == 24
        assert dx_space == 12
        assert dy_up == 6
        assert dy_down == 6


class TestSubDc:
    """Tests for :class:`SubDc`."""

    def test_init_from_basedc(self):
        dc = BaseDc(width=800, height=600)
        sub = SubDc(dc, 10, 20, 100, 200)
        assert sub.x == 10
        assert sub.y == 20
        assert sub.dx == 100
        assert sub.dy == 200
        assert sub._parent is dc

    def test_init_from_subdc_chains_parent(self):
        dc = BaseDc(width=800, height=600)
        sub1 = SubDc(dc, 10, 20, 100, 200)
        sub2 = SubDc(sub1, 5, 5, 50, 50)
        assert sub2._parent is dc

    def test_init_reg_max_true_updates_parent(self):
        dc = BaseDc(width=800, height=600)
        SubDc(dc, 10, 20, 100, 200, reg_max=True)
        assert dc._maxwidth == 110
        assert dc._maxheight == 220

    def test_init_reg_max_false_does_not_update_parent(self):
        dc = BaseDc(width=800, height=600)
        SubDc(dc, 10, 20, 100, 200, reg_max=False)
        assert dc._maxwidth == 0
        assert dc._maxheight == 0

    def test_get_size(self):
        dc = BaseDc(width=800, height=600)
        sub = SubDc(dc, 10, 20, 100, 200)
        assert sub.get_size() == [100, 200]

    def test_subdc_method_creates_new_subdc(self):
        dc = BaseDc(width=800, height=600)
        sub1 = SubDc(dc, 10, 20, 100, 200)
        sub2 = sub1.subdc(5, 5, 50, 50)
        assert isinstance(sub2, SubDc)
        assert sub2.x == 15
        assert sub2.y == 25

    def test_getattribute_falls_back_to_parent(self):
        dc = BaseDc(width=800, height=600)
        sub = SubDc(dc, 10, 20, 100, 200)
        assert sub.dc_info is dc.dc_info

    def test_getattribute_uses_own_attributes_first(self):
        dc = BaseDc(width=800, height=600)
        sub = SubDc(dc, 10, 20, 100, 200)
        assert sub.x == 10

    def test_add_line_delegates_to_parent(self):
        dc = BaseDc(width=800, height=600, record=True)
        sub = SubDc(dc, 10, 20, 100, 200)
        sub.add_line(0, 0, 50, 50)
        assert dc.store == [("add_line", (10, 20, 50, 50))]

    def test_add_rectangle_delegates_to_parent(self):
        dc = BaseDc(width=800, height=600, record=True)
        sub = SubDc(dc, 10, 20, 100, 200)
        sub.add_rectangle(0, 0, 50, 50)
        assert dc.store == [("add_rectangle", (10, 20, 50, 50))]

    def test_draw_text_delegates_to_parent(self):
        dc = BaseDc(width=800, height=600, record=True)
        sub = SubDc(dc, 10, 20, 100, 200)
        sub.draw_text(0, 0, "hello")
        assert dc.store == [("draw_text", (10, 20, "hello"))]

    def test_add_polygon_translates_coords(self):
        dc = BaseDc(width=800, height=600, record=True)
        sub = SubDc(dc, 10, 20, 100, 200)
        sub.add_polygon([(0, 0), (10, 0)])
        assert dc.store == [("add_polygon", ([(10, 20), (20, 20)],))]

    def test_add_spline_translates_coords(self):
        dc = BaseDc(width=800, height=600, record=True)
        sub = SubDc(dc, 10, 20, 100, 200)
        sub.add_spline([(0, 0)], True)
        assert dc.store == [("add_spline", ([(10, 20)], True))]


class TestNullDc:
    """Tests for :class:`NullDc`."""

    def test_init(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        assert ndc._ref_dc is dc
        assert ndc._maxwidth == 0
        assert ndc._maxheight == 0

    def test_get_dc_info_delegates(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        assert ndc.get_dc_info() is dc.dc_info

    def test_get_max_sizes(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        ndc._maxwidth = 100
        ndc._maxheight = 200
        assert ndc.get_max_sizes() == (100, 200)

    def test_test_point_updates_max(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        ndc.test_point(100, 200)
        assert ndc._maxwidth == 100
        assert ndc._maxheight == 200

    def test_test_point_ignores_huge_values(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        ndc.test_point(20000000, 50)
        assert ndc._maxwidth == 0
        assert ndc._maxheight == 0

    def test_subdc_returns_subdc(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        sub = ndc.subdc(10, 20, 100, 200)
        assert isinstance(sub, SubDc)

    def test_add_line_calls_test_point(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        ndc.add_line(0, 0, 100, 200)
        assert ndc._maxwidth == 100
        assert ndc._maxheight == 200

    def test_add_rectangle_calls_test_point(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        ndc.add_rectangle(0, 0, 50, 100)
        assert ndc._maxwidth == 50
        assert ndc._maxheight == 100

    def test_add_rounded_rectangle_calls_test_point(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        ndc.add_rounded_rectangle(0, 0, 30, 40, 5)
        assert ndc._maxwidth == 30
        assert ndc._maxheight == 40

    def test_add_arc_calls_test_point(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        ndc.add_arc(0, 0, 25, 0, 360)
        assert ndc._maxwidth == 25
        assert ndc._maxheight == 25

    def test_add_ellipse_calls_test_point(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        ndc.add_ellipse(0, 0, 100, 80)
        assert ndc._maxwidth == 100
        assert ndc._maxheight == 80

    def test_add_polygon_calls_test_point(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        ndc.add_polygon([(10, 20), (30, 40)])
        assert ndc._maxwidth == 30
        assert ndc._maxheight == 40

    def test_add_spline_calls_test_point(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        ndc.add_spline([(5, 10), (15, 20)], True)
        assert ndc._maxwidth == 15
        assert ndc._maxheight == 20

    def test_draw_text_calls_test_point(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        ndc.draw_text(100, 200, "hello")
        assert ndc._maxwidth == 100
        assert ndc._maxheight == 200

    def test_draw_image_calls_test_point(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        ndc.draw_image(10, 20, 50, 60, 1, b"data")
        assert ndc._maxwidth == 60
        assert ndc._maxheight == 80

    def test_getattribute_private_attr(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        assert ndc._ref_dc is dc

    def test_getattribute_falls_back_to_ref_dc(self):
        dc = BaseDc(width=800, height=600)
        ndc = NullDc(dc)
        assert ndc.scale == 1.0


class TestNullDcInfo:
    """Tests for :class:`NullDcinfo`."""

    def test_init(self):
        dc = BaseDc(width=800, height=600)
        info = NullDcinfo(dc)
        assert info.dc is dc

    def test_get_style_id_returns_zero(self):
        dc = BaseDc(width=800, height=600)
        info = NullDcinfo(dc)
        assert info.get_style_id("anything") == 0

    def test_get_multiline_text_width_returns_100(self):
        dc = BaseDc(width=800, height=600)
        info = NullDcinfo(dc)
        assert info.get_multiline_text_width("text", "default") == 100

    def test_get_multiline_text_height_returns_100_empty(self):
        dc = BaseDc(width=800, height=600)
        info = NullDcinfo(dc)
        result = info.get_multiline_text_height("text", 100, "default")
        assert result == (100, [])

    def test_get_extents(self):
        dc = BaseDc(width=800, height=600)
        info = NullDcinfo(dc)
        result = info.get_extents("word", "default")
        assert result == (100, 0, 0, 20)


class TestConvertFunArg:
    """Tests for :func:`convert_fun_arg` decorator."""

    def test_no_args(self):
        class Obj:
            x = 10
            y = 20

            @convert_fun_arg
            def method(self, *args, **kwargs):
                return (args, kwargs)

        obj = Obj()
        result = obj.method()
        assert result == ((), {})

    def test_positional_xy(self):
        class Obj:
            x = 10
            y = 20

            @convert_fun_arg
            def method(self, x, y):
                return (x, y)

        obj = Obj()
        assert obj.method(0, 0) == (10, 20)

    def test_positional_xy_with_extra(self):
        class Obj:
            x = 10
            y = 20
            dx = 100
            dy = 200

            @convert_fun_arg
            def method(self, x, y, extra):
                return (x, y, extra)

        obj = Obj()
        assert obj.method(0, 0, "extra") == (10, 20, "extra")

    def test_positional_xy_dx_dy(self):
        class Obj:
            x = 10
            y = 20
            dx = 100
            dy = 200

            @convert_fun_arg
            def method(self, x, y, dx, dy):
                return (x, y, dx, dy)

        obj = Obj()
        assert obj.method(0, 0, 50, 100) == (10, 20, 50, 100)

    def test_positional_xy_dx_dy_minus_one(self):
        class Obj:
            x = 10
            y = 20
            dx = 100
            dy = 200

            @convert_fun_arg
            def method(self, x, y, dx, dy):
                return (x, y, dx, dy)

        obj = Obj()
        assert obj.method(0, 0, -1, -1) == (10, 20, 100, 200)

    def test_keyword_xy(self):
        class Obj:
            x = 10
            y = 20

            @convert_fun_arg
            def method(self, x=0, y=0):
                return (x, y)

        obj = Obj()
        assert obj.method(x=5, y=15) == (15, 35)

    def test_keyword_xy_dx_dy(self):
        class Obj:
            x = 10
            y = 20
            dx = 100
            dy = 200

            @convert_fun_arg
            def method(self, x=0, y=0, dx=0, dy=0):
                return (x, y, dx, dy)

        obj = Obj()
        assert obj.method(x=5, y=15, dx=50, dy=30) == (15, 35, 50, 30)

    def test_keyword_xy_dx_dy_minus_one(self):
        class Obj:
            x = 10
            y = 20
            dx = 100
            dy = 200

            @convert_fun_arg
            def method(self, x=0, y=0, dx=0, dy=0):
                return (x, y, dx, dy)

        obj = Obj()
        assert obj.method(x=5, y=15, dx=-1, dy=-1) == (15, 35, 95, 185)
