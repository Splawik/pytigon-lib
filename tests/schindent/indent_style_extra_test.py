"""Extra tests for :mod:`pytigon_lib.schindent.indent_style` IhtmlToHtml and pipeline."""

import io
from unittest.mock import MagicMock, mock_open, patch

from pytigon_lib.schindent.indent_style import (
    IhtmlToHtml,
    _build_translator,
    _py_to_js_wrapper,
    _space_count,
    _status_close,
    ihtml_to_html_base,
    iter_lines,
    list_with_next_generator,
)

# ---------------------------------------------------------------------------
# list_with_next_generator extra
# ---------------------------------------------------------------------------


class TestListWithNextGeneratorExtra:
    def test_str_items(self):
        result = list(list_with_next_generator(["x", "y", "z"]))
        assert result == [("x", "y"), ("y", "z"), ("z", None)]

    def test_int_items(self):
        result = list(list_with_next_generator([10, 20, 30]))
        assert result == [(10, 20), (20, 30), (30, None)]

    def test_one_item(self):
        result = list(list_with_next_generator([42]))
        assert result == [(42, None)]

    def test_two_items(self):
        result = list(list_with_next_generator(["first", "last"]))
        assert result == [("first", "last"), ("last", None)]

    def test_empty(self):
        assert list(list_with_next_generator([])) == []


# ---------------------------------------------------------------------------
# _build_translator
# ---------------------------------------------------------------------------


class TestBuildTranslator:
    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="test_prj")
    @patch("pytigon_lib.schindent.indent_style.gettext")
    def test_lang_en_returns_identity(self, mock_gettext, mock_prj, mock_settings):
        fn, collected = _build_translator("en")
        assert fn("hello") == "hello"
        assert collected == []
        mock_gettext.translation.assert_not_called()

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="test_prj")
    @patch("pytigon_lib.schindent.indent_style.gettext")
    def test_lang_non_en_no_translation_identity(self, mock_gettext, mock_prj, mock_settings):
        mock_gettext.translation.side_effect = Exception("no mo")
        mock_settings.PRJ_PATH = "/tmp"
        fn, collected = _build_translator("pl")
        assert fn("hello") == "hello"

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="test_prj")
    @patch("pytigon_lib.schindent.indent_style.gettext")
    @patch("builtins.open", new_callable=mock_open, read_data='\n'.join(['_("word1")']))
    def test_translator_loads_existing_words(self, mock_file, mock_gettext, mock_prj, mock_settings):
        mock_t = MagicMock()
        mock_t.gettext.return_value = "translated"
        mock_gettext.translation.return_value = mock_t
        mock_settings.PRJ_PATH = "/tmp"
        fn, collected = _build_translator("pl")
        assert "word1" in collected
        assert fn("hello") == "translated"

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="test_prj")
    @patch("pytigon_lib.schindent.indent_style.gettext")
    def test_translator_short_word_passthrough(self, mock_gettext, mock_prj, mock_settings):
        mock_t = MagicMock()
        mock_t.gettext.return_value = "X"
        mock_gettext.translation.return_value = mock_t
        mock_settings.PRJ_PATH = "/tmp"
        fn, collected = _build_translator("pl")
        assert fn("a") == "a"

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="test_prj")
    @patch("pytigon_lib.schindent.indent_style.gettext")
    @patch("builtins.open", new_callable=mock_open, read_data='_("already")\n')
    def test_translator_dedup_collected_words(self, mock_file, mock_gettext, mock_prj, mock_settings):
        mock_t = MagicMock()
        mock_t.gettext.return_value = "translated"
        mock_gettext.translation.return_value = mock_t
        mock_settings.PRJ_PATH = "/tmp"
        fn, collected = _build_translator("pl")
        fn("already")
        assert collected.count("already") == 1


# ---------------------------------------------------------------------------
# iter_lines
# ---------------------------------------------------------------------------


class TestIterLines:
    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name")
    def test_iter_lines_table_basic(self, mock_prj, mock_settings):
        mock_prj.return_value = "prj"
        mock_settings.PRJ_PATH = "/tmp"
        stream = io.StringIO("[col1 | col2]\ndata")
        results = list(iter_lines(stream, None, "en"))
        assert any("<tr><td>" in r for r in results)

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name")
    def test_iter_lines_table_header(self, mock_prj, mock_settings):
        mock_prj.return_value = "prj"
        mock_settings.PRJ_PATH = "/tmp"
        stream = io.StringIO("[[h1 | h2]]\ndata")
        results = list(iter_lines(stream, None, "en"))
        assert any("<tr><th>" in r for r in results)

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name")
    def test_iter_lines_translate_prefix(self, mock_prj, mock_settings):
        mock_prj.return_value = "prj"
        mock_settings.PRJ_PATH = "/tmp"
        stream = io.StringIO("_translatable text\nnormal")
        results = list(iter_lines(stream, None, "en"))
        assert any(".translatable text" in r for r in results)

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name")
    def test_iter_lines_ends_with_dot(self, mock_prj, mock_settings):
        mock_prj.return_value = "prj"
        mock_settings.PRJ_PATH = "/tmp"
        stream = io.StringIO("line1\nline2")
        results = list(iter_lines(stream, None, "en"))
        assert results[-1] == "."

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name")
    def test_iter_lines_no_translate_prefix_double_underscore(self, mock_prj, mock_settings):
        mock_prj.return_value = "prj"
        mock_settings.PRJ_PATH = "/tmp"
        stream = io.StringIO("__init__\nplain")
        results = list(iter_lines(stream, None, "en"))
        assert any("plain" in r for r in results)

    @patch("pytigon_lib.schindent.indent_style.gettext")
    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name")
    def test_iter_lines_saves_translate_file(self, mock_prj, mock_settings, mock_gettext):
        mock_prj.return_value = "prj"
        mock_settings.PRJ_PATH = "/tmp/python"
        mock_gettext.translation.side_effect = Exception("no")
        stream = io.StringIO("_translatable text")
        m_open = mock_open()
        with patch("builtins.open", m_open):
            list(iter_lines(stream, "test.ihtml", "pl"))
        assert m_open.call_count >= 1

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name")
    def test_iter_lines_no_save_site_packages(self, mock_prj, mock_settings):
        mock_prj.return_value = "prj"
        mock_settings.PRJ_PATH = "/tmp/site-packages/django"
        stream = io.StringIO("_translatable text")
        with patch("builtins.open", mock_open()) as mock_file:
            list(iter_lines(stream, "test.ihtml", "en"))
            mock_file.assert_not_called()

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name")
    def test_iter_lines_inline_translate(self, mock_prj, mock_settings):
        mock_prj.return_value = "prj"
        mock_settings.PRJ_PATH = "/tmp"
        stream = io.StringIO('<span>_("translate me")</span>')
        results = list(iter_lines(stream, None, "en"))
        assert any("translate me" in r for r in results)


# ---------------------------------------------------------------------------
# _space_count extra
# ---------------------------------------------------------------------------


class TestSpaceCountExtra:
    def test_leading_spaces(self):
        assert _space_count("   text") == 3

    def test_only_spaces(self):
        assert _space_count("     ") == 5

    def test_no_spaces(self):
        assert _space_count("text") == 0

    def test_empty(self):
        assert _space_count("") == 0


# ---------------------------------------------------------------------------
# _status_close extra
# ---------------------------------------------------------------------------


class TestStatusCloseExtra:
    def test_status_zero(self):
        line = (2, "div", "content", 0)
        assert _status_close(0, line, (2, "span", None, 0)) == 0

    def test_status_two(self):
        line = (2, "div", "content", 2)
        assert _status_close(2, line, (2, "span", None, 0)) == 0

    def test_status_one(self):
        line = (2, "div", "content", 1)
        assert _status_close(1, line, (2, "span", None, 0)) == 1

    def test_status_three(self):
        line = (2, "div", "content", 3)
        assert _status_close(3, line, (2, "span", None, 0)) == 2

    def test_status_four_shallow_next(self):
        line = (4, "div", "content", 4)
        assert _status_close(4, line, (4, "span", None, 0)) == 1

    def test_status_four_deeper_next(self):
        line = (4, "div", "content", 4)
        assert _status_close(4, line, (6, "span", None, 0)) == 3


# ---------------------------------------------------------------------------
# IhtmlToHtml constructor
# ---------------------------------------------------------------------------


class TestIhtmlToHtmlInit:
    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_init_file_mode(self, mock_settings):
        c = IhtmlToHtml(
            file_name="test.ihtml",
            simple_close_tags=["br", "input"],
            auto_close_tags=["div", "span"],
            no_auto_close_tags=["pre"],
            lang="pl",
        )
        assert c.file_name == "test.ihtml"
        assert c.input_str is None
        assert c.simple_close_tags == ["br", "input"]
        assert c.auto_close_tags == ["div", "span"]
        assert c.no_auto_close_tags == ["pre"]
        assert c.lang == "pl"
        assert c.no_convert is False
        assert c.code == []
        assert c.buffer == []
        assert c.output == []
        assert c.output_processors is None

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_init_string_mode(self, mock_settings):
        c = IhtmlToHtml(
            file_name=None,
            simple_close_tags=[],
            auto_close_tags=[],
            no_auto_close_tags=[],
            input_str="div\n    span",
            lang="de",
        )
        assert c.file_name is None
        assert c.input_str == "div\n    span"

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_init_with_output_processors(self, mock_settings):
        proc = lambda x: x.upper()  # noqa: E731
        c = IhtmlToHtml(
            file_name=None,
            simple_close_tags=[],
            auto_close_tags=[],
            no_auto_close_tags=[],
            input_str="div",
            output_processors={"upper": proc},
        )
        assert c.output_processors == {"upper": proc}

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_init_default_lang_en(self, mock_settings):
        c = IhtmlToHtml(
            file_name="test.ihtml",
            simple_close_tags=[],
            auto_close_tags=[],
            no_auto_close_tags=[],
        )
        assert c.lang == "en"


# ---------------------------------------------------------------------------
# IhtmlToHtml._flush_buffer
# ---------------------------------------------------------------------------


class TestFlushBuffer:
    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_flush_empty_buffer(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        c._flush_buffer(0)
        assert c.output == []

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_flush_single_at_level(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        c.buffer = [[2, "</div>", 0]]
        c._flush_buffer(2)
        assert len(c.output) == 1
        assert c.output[0] == [2, "</div>", 0]
        assert len(c.buffer) == 0

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_flush_multiple_at_levels(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        c.buffer = [[2, "</p>", 0], [4, "</span>", 1], [6, "</div>", 0]]
        c._flush_buffer(4)
        assert len(c.buffer) == 1
        assert c.buffer[0][1] == "</p>"
        assert len(c.output) == 2
        assert c.output[0][1] == "</div>"
        assert c.output[1][1] == "</span>"

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_flush_none_match(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        c.buffer = [[4, "</div>", 0]]
        c._flush_buffer(6)
        assert len(c.buffer) == 1
        assert len(c.output) == 0

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_flush_negative_min_indent(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        c.buffer = [[4, "</div>", 0], [2, "</span>", 0]]
        c._flush_buffer(-1)
        assert len(c.buffer) == 0
        assert len(c.output) == 2


# ---------------------------------------------------------------------------
# IhtmlToHtml.transform_line
# ---------------------------------------------------------------------------


class TestTransformLine:
    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_plain_text_line(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str=".")
        line = (0, None, "hello world", 0)
        c.transform_line(line, (0, None, "more", 0))
        assert len(c.output) == 1
        assert c.output[0][1] == "hello world"

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_both_none_skipped(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str=".")
        c.transform_line((0, None, None, 0), (0, None, None, 1))
        assert len(c.output) >= 1
        assert c.output[0][1] is None

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_flushes_buffer_first(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        c.buffer = [[2, "</span>", 0]]
        c.transform_line((4, "div", None, 0), (4, None, None, 0))
        assert len(c.buffer) == 2
        assert c.buffer[1][1] == "</div>"

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_is_percent_tag_delegates(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="%")
        line = (0, "% if x", None, 0)
        c.transform_line(line, (0, None, None, 0))
        assert any("{% if x %}" in o[1] for o in c.output)

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_is_html_tag_delegates(self, mock_settings):
        c = IhtmlToHtml(None, ["br"], [], [], input_str="br")
        line = (0, "p", "text", 0)
        next_line = (0, None, None, 0)
        c.transform_line(line, next_line)
        assert any("<p>" in o[1] for o in c.output)
        assert any("</p>" in o[1] for o in c.buffer)


# ---------------------------------------------------------------------------
# IhtmlToHtml._transform_template_line
# ---------------------------------------------------------------------------


class TestTransformTemplateLine:
    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_double_percent_block_inline(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="%")
        line = (0, "%% my_block", "content", 0)
        next_line = (0, "span", None, 0)
        c._transform_template_line(line, next_line)
        assert any("{% block my_block %}" in o[1] and "{% endblock %}" in o[1] for o in c.output)

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_double_percent_block_deferred(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="%")
        line = (0, "%% my_block", "content", 0)
        next_line = (4, "span", None, 0)
        c._transform_template_line(line, next_line)
        assert any("{% block my_block %}" in o[1] and "{% endblock %}" not in o[1] for o in c.output)
        assert any("{% endblock %}" in o[1] for o in c.buffer)

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_single_percent_with_auto_close(self, mock_settings):
        c = IhtmlToHtml(None, [], ["if"], [], input_str="%")
        line = (0, "% if x:", "content", 0)
        next_line = (4, "span", None, 0)
        c._transform_template_line(line, next_line)
        assert any("{% if x %}" in o[1] for o in c.output)
        assert any("{% endif %}" in o[1] for o in c.buffer)

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_single_percent_ext_triggers_autoclose(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="%")
        line = (0, "% if_ext x:", "content", 0)
        next_line = (4, "span", None, 0)
        c._transform_template_line(line, next_line)
        assert any("{% endif_ext %}" in o[1] for o in c.buffer)

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_single_percent_no_autoclose(self, mock_settings):
        c = IhtmlToHtml(None, [], [], ["if"], input_str="%")
        line = (0, "% if:", "content", 0)
        next_line = (4, "span", None, 0)
        c._transform_template_line(line, next_line)
        assert all("{% endif %}" not in o[1] for o in c.buffer)

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_single_percent_html_content(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="%")
        line = (0, "% if x", "extra html", 0)
        next_line = (0, None, None, 0)
        c._transform_template_line(line, next_line)
        assert any("extra html" in o[1] for o in c.output)


# ---------------------------------------------------------------------------
# IhtmlToHtml._transform_html_line
# ---------------------------------------------------------------------------


class TestTransformHtmlLine:
    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_next_closes_with_content(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        line = (0, "div", "text", 0)
        next_line = (0, "span", None, 0)
        c._transform_html_line(line, next_line)
        assert any("<div>" in o[1] and "</div>" in o[1] for o in c.output)

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_next_closes_simple_close_tag(self, mock_settings):
        c = IhtmlToHtml(None, ["br"], [], [], input_str="br")
        line = (0, "br", None, 0)
        next_line = (0, "span", None, 0)
        c._transform_html_line(line, next_line)
        assert any("<br />" in o[1] for o in c.output)

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_next_deeper_defers_close(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        line = (0, "div", None, 0)
        next_line = (4, "span", None, 0)
        c._transform_html_line(line, next_line)
        assert any("<div>" in o[1] and "</div>" not in o[1] for o in c.output)
        assert any("</div>" in o[1] for o in c.buffer)

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_next_deeper_with_content(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        line = (0, "div", "child text", 0)
        next_line = (4, "span", None, 0)
        c._transform_html_line(line, next_line)
        assert any("child text" in o[1] for o in c.output)

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_next_is_none_none(self, mock_settings):
        c = IhtmlToHtml(None, ["br"], [], [], input_str="br")
        line = (0, "br", None, 0)
        next_line = (0, None, None, 0)
        c._transform_html_line(line, next_line)
        assert any("<br>" in o[1] for o in c.output)


# ---------------------------------------------------------------------------
# IhtmlToHtml.transform
# ---------------------------------------------------------------------------


class TestTransform:
    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_empty_code_does_nothing(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str=".")
        c.code = []
        c.transform()
        assert c.output == []

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_single_line_flushed(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str=".")
        c.code = [(0, None, "hello", 0)]
        c.buffer = [[2, "</div>", 0]]
        c.transform()
        assert c.output
        assert c.buffer == []

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_two_lines_paired(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str=".")
        c.code = [(0, None, "line1", 0), (0, None, "line2", 1)]
        c.transform()
        assert len(c.output) >= 2

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_last_line_uses_sentinel(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str=".")
        c.code = [(0, "div", "text", 0)]
        c.transform()
        assert any("<div>" in o[1] for o in c.output)


# ---------------------------------------------------------------------------
# IhtmlToHtml._read_input
# ---------------------------------------------------------------------------


class TestReadInput:
    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_string_input(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="div\n    span")
        stream = c._read_input()
        assert "div" in stream.getvalue()

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_file_input(self, mock_settings):
        mock_file = MagicMock()
        mock_file.readline.return_value = "div class=foo\n"
        mock_file.read.return_value = "div class=foo\n    span\n        text"
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        with patch("builtins.open", return_value=mock_file):
            c = IhtmlToHtml("test.ihtml", [], [], [])
            stream = c._read_input()
            assert "div" in stream.getvalue()

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_file_with_reference(self, mock_settings):
        main = "@@@ref\n  span"
        ref = "div\n    p"
        m_open = mock_open()
        m_open.side_effect = [
            mock_open(read_data=main).return_value,
            mock_open(read_data=ref).return_value,
        ]
        with patch("builtins.open", m_open):
            c = IhtmlToHtml("test.ihtml", [], [], [])
            stream = c._read_input()
            assert "div" in stream.getvalue()

    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_empty_string_input(self, mock_settings):
        c = IhtmlToHtml(None, [], [], [], input_str="")
        stream = c._read_input()
        assert stream.getvalue() == ""


# ---------------------------------------------------------------------------
# IhtmlToHtml._pre_process_all_lines
# ---------------------------------------------------------------------------


class TestPreProcessAllLines:
    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_simple_html_line(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div class=foo")
        stream = io.StringIO("div class=foo\n")
        c._pre_process_all_lines(stream)
        assert len(c.code) >= 2

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_no_convert_marker(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        stream = io.StringIO("^^^")
        c._pre_process_all_lines(stream)
        assert c.no_convert is True

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_raw_marker_detected(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        stream = io.StringIO("div>>>raw content<<<\nspan")
        c._pre_process_all_lines(stream)
        assert len(c.code) >= 1

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_js_marker_detected(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        stream = io.StringIO("div{:}js code<<<\nspan")
        c._pre_process_all_lines(stream)
        assert len(c.code) >= 2

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_pscript_detected(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        stream = io.StringIO("pscript...|||\nspan")
        c._pre_process_all_lines(stream)
        assert len(c.code) >= 2

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_markdown_marker_detected(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        stream = io.StringIO("div###># md heading<<<\nspan")
        c._pre_process_all_lines(stream)
        assert len(c.code) >= 2

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_script_python_detected(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        stream = io.StringIO("script language=python...|||\nspan")
        c._pre_process_all_lines(stream)
        assert len(c.code) >= 2

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_py2javascript_detected(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        stream = io.StringIO("script language=py2javascript...|||\nspan")
        c._pre_process_all_lines(stream)
        assert len(c.code) >= 2

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_component_detected(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        stream = io.StringIO("%component...|||\nspan")
        c._pre_process_all_lines(stream)
        assert len(c.code) >= 2

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_pscript_line_detected(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        stream = io.StringIO("  pscript...|||\nspan")
        c._pre_process_all_lines(stream)
        assert len(c.code) >= 2

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_empty_line(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        stream = io.StringIO("\nspan")
        c._pre_process_all_lines(stream)
        assert any(o[1] is None and o[2] is None for o in c.code)


# ---------------------------------------------------------------------------
# IhtmlToHtml.process
# ---------------------------------------------------------------------------


class TestProcess:
    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_process_simple(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div\n  span")
        c.process()
        assert len(c.code) > 0
        assert len(c.output) > 0


# ---------------------------------------------------------------------------
# IhtmlToHtml.to_str
# ---------------------------------------------------------------------------


class TestToStr:
    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_to_str_beautiful(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div\n  span")
        c.process()
        result = c.to_str(beauty=True)
        assert isinstance(result, str)
        assert "<div>" in result

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_to_str_compact(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div\n  span")
        c.process()
        result = c.to_str(beauty=False)
        assert isinstance(result, str)
        assert "<div>" in result

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_to_str_no_convert(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="plain text")
        c.no_convert = True
        result = c.to_str()
        assert result == "plain text"

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_to_str_no_convert_file(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        with patch("builtins.open", mock_open(read_data="file content")):
            c = IhtmlToHtml("test.ihtml", [], [], [])
            c.no_convert = True
            result = c.to_str()
            assert result == "file content"

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_to_str_empty_output(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="string only")
        c.output = []
        result = c.to_str()
        assert result == ""

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_to_str_inline_optimize(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div\n  span")
        c.process()
        c.output = [[0, "<inline:>\n  text  \n</inline:>", 0]]
        result = c.to_str()
        assert "  " not in result or "<inline:>" not in result

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_to_str_output_processors(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        proc = lambda x: x.upper()  # noqa: E731
        c = IhtmlToHtml(
            None, [], [], [], input_str=".", output_processors={"upper": proc}
        )
        c.output = [[0, "before@@(upper-hello)after", 0]]
        result = c.to_str()
        assert "HELLO" in result

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    def test_to_str_backslash_newline_removed(self, mock_prj, mock_settings):
        mock_settings.PRJ_PATH = "/tmp"
        c = IhtmlToHtml(None, [], [], [], input_str="div")
        c.process()
        c.output = [[0, "line1\\\nline2", 0]]
        result = c.to_str()
        assert "\\\n" not in result


# ---------------------------------------------------------------------------
# _optimize_inline
# ---------------------------------------------------------------------------


class TestOptimizeInline:
    def test_remove_spaces_around_inline(self):
        result = IhtmlToHtml._optimize_inline(" <inline:>text</inline:> ")
        assert result == "text"

    def test_joins_multiline_inline(self):
        result = IhtmlToHtml._optimize_inline("<inline:>\n  a\n  b\n</inline:>")
        assert "a" in result
        assert "b" in result

    def test_no_inline_tags_unchanged(self):
        result = IhtmlToHtml._optimize_inline("<div>text</div>")
        assert result == "<div>text</div>"

    def test_multiple_inline_blocks(self):
        result = IhtmlToHtml._optimize_inline(
            "<inline:>a\nb\n</inline:>x<inline:>c\nd\n</inline:>"
        )
        assert "a b" in result
        assert "c d" in result
        assert "x" in result

    def test_normalize_repeatedly(self):
        result = IhtmlToHtml._optimize_inline("\n<inline:>text</inline:>\n")
        assert result == "text"


# ---------------------------------------------------------------------------
# ConwertToHtml alias
# ---------------------------------------------------------------------------


class TestConwertToHtmlAlias:
    @patch("pytigon_lib.schindent.indent_style.settings")
    def test_backward_compat_alias(self, mock_settings):
        from pytigon_lib.schindent.indent_style import ConwertToHtml

        assert ConwertToHtml is IhtmlToHtml


# ---------------------------------------------------------------------------
# ihtml_to_html_base
# ---------------------------------------------------------------------------


class TestIhtmlToHtmlBase:
    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    @patch("pytigon_lib.schindent.indent_style.IhtmlToHtml.process")
    @patch("pytigon_lib.schindent.indent_style.IhtmlToHtml.to_str")
    def test_returns_html_string(self, mock_to_str, mock_process, mock_prj, mock_settings):
        mock_to_str.return_value = "<div></div>"
        result = ihtml_to_html_base(None, "div")
        assert isinstance(result, str)

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    @patch("pytigon_lib.schindent.indent_style.IhtmlToHtml.process")
    @patch("pytigon_lib.schindent.indent_style.IhtmlToHtml.to_str")
    def test_error_returns_empty(self, mock_to_str, mock_process, mock_prj, mock_settings):
        mock_process.side_effect = Exception("fail")
        result = ihtml_to_html_base(None, "div")
        assert result == ""

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    @patch("pytigon_lib.schindent.indent_style.IhtmlToHtml.process")
    @patch("pytigon_lib.schindent.indent_style.IhtmlToHtml.to_str")
    def test_passes_lang_param(self, mock_to_str, mock_process, mock_prj, mock_settings):
        mock_to_str.return_value = "<div></div>"
        result = ihtml_to_html_base(None, "div", lang="pl")
        assert isinstance(result, str)

    @patch("pytigon_lib.schindent.indent_style.settings")
    @patch("pytigon_lib.schindent.indent_style.get_prj_name", return_value="prj")
    @patch("pytigon_lib.schindent.indent_style.IhtmlToHtml.process")
    @patch("pytigon_lib.schindent.indent_style.IhtmlToHtml.to_str")
    def test_default_lang_is_en(self, mock_to_str, mock_process, mock_prj, mock_settings):
        mock_to_str.return_value = "<div></div>"
        result = ihtml_to_html_base(None, "div")
        assert result == "<div></div>"


# ---------------------------------------------------------------------------
# _py_to_js_wrapper
# ---------------------------------------------------------------------------


class TestPyToJsWrapper:
    @patch("pytigon_lib.schindent.indent_style.py_to_js_compile")
    def test_simple_script(self, mock_compile):
        mock_compile.return_value = (False, "// compiled")
        result = _py_to_js_wrapper("x = 1")
        assert result == "// compiled"

    @patch("pytigon_lib.schindent.indent_style.py_to_js_compile")
    def test_compile_error(self, mock_compile):
        mock_compile.return_value = (True, "syntax error")
        result = _py_to_js_wrapper("invalid")
        assert result == "syntax error"

    @patch("pytigon_lib.schindent.indent_style.py_to_js_compile")
    def test_indented_script(self, mock_compile):
        mock_compile.return_value = (False, "// compiled")
        result = _py_to_js_wrapper("    x = 1\n    y = 2")
        assert result == "// compiled"

    @patch("pytigon_lib.schindent.indent_style.py_to_js_compile")
    def test_all_blank_lines_before_code(self, mock_compile):
        mock_compile.return_value = (False, "// compiled")
        result = _py_to_js_wrapper("\n\nx = 1")
        assert result == "// compiled"
