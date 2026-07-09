"""Tests for :mod:`pytigon_lib.schtools.wiki`."""

import pytest

from pytigon_lib.schtools.wiki import make_href, wiki_from_str, wikify

from django.conf import settings


class TestWikiFromStr:
    def test_empty_returns_index(self):
        assert wiki_from_str("") == "index"

    def test_none_returns_index(self):
        assert wiki_from_str(None) == "index"

    def test_question_mark_prefix(self):
        result = wiki_from_str("?some_page")
        assert len(result) > 0

    def test_simple_word(self):
        result = wiki_from_str("Hello")
        assert len(result) > 0

    def test_hyphen_splits(self):
        result = wiki_from_str("Hello-World")
        assert "World" not in result

    def test_multiple_words_joined(self):
        result = wiki_from_str("Hello World")
        assert " " not in result

    def test_non_ascii_stripped(self):
        result = wiki_from_str("Zazólc Gesla")
        assert "&" not in result
        assert "#" not in result

    def test_truncation_to_32_chars(self):
        result = wiki_from_str("A very long page name that exceeds the thirty two character limit")
        assert len(result) <= 32

    def test_only_spaces_returns_index(self):
        assert wiki_from_str("   ") == "index"

    def test_single_character(self):
        result = wiki_from_str("a")
        assert len(result) > 0

    def test_polish_characters(self):
        result = wiki_from_str("Zażółć gęślą jaźń")
        assert isinstance(result, str)


class TestMakeHref:
    def setup_method(self):
        self._orig_url_root = getattr(settings, "URL_ROOT_FOLDER", None)
        settings.URL_ROOT_FOLDER = ""

    def teardown_method(self):
        if self._orig_url_root is not None:
            settings.URL_ROOT_FOLDER = self._orig_url_root

    def test_returns_html_anchor(self):
        href = make_href("TestPage")
        assert href.startswith("<a ")
        assert "TestPage" in href

    def test_new_window_target(self):
        href = make_href("TestPage", new_win=True)
        assert "_top2" in href

    def test_self_target(self):
        href = make_href("TestPage", new_win=False)
        assert "_self" in href

    def test_btn_class(self):
        href = make_href("TestPage", btn=True)
        assert "btn-secondary" in href

    def test_no_btn_class(self):
        href = make_href("TestPage", btn=False)
        assert "schbtn" in href

    def test_with_path(self):
        href = make_href("TestPage", path="custom_path")
        assert "custom_path" in href

    def test_with_section(self):
        href = make_href("TestPage", section="docs")
        assert "schwiki/docs" in href

    def test_closing_tag(self):
        href = make_href("TestPage")
        assert href.endswith("</a>")


class TestWikify:
    def test_empty_returns_empty(self):
        assert wikify("") == ""

    def test_none_returns_none(self):
        assert wikify(None) is None

    def test_no_wiki_syntax_returns_original(self):
        assert wikify("Plain text") == "Plain text"

    def test_simple_wiki_link(self):
        result = wikify("See [[TestPage]] for info")
        assert "<a " in result
        assert "TestPage" in result
        assert "[[" not in result

    def test_new_window_modifier(self):
        result = wikify("Open [[^TestPage]] here")
        assert "_top2" in result

    def test_btn_modifier(self):
        result = wikify("Click [[#TestPage]]")
        assert "btn-secondary" in result

    def test_section_override(self):
        result = wikify("[[Page;docs]]")
        assert "schwiki/docs" in result

    def test_unclosed_wiki_preserved(self):
        result = wikify("[[unclosed")
        assert "[[unclosed" in result

    def test_multiple_links(self):
        result = wikify("See [[Page1]] and [[Page2]]")
        assert "Page1" in result
        assert "Page2" in result
        assert result.count("<a ") == 2

    def test_with_path(self):
        result = wikify("Check [[Page]]", path="custom")
        assert "custom" in result

    def test_empty_brackets_preserved(self):
        result = wikify("before [[]] after")
        assert "[[]]" in result

    def test_with_default_section(self):
        result = wikify("[[Page]]", section="default_sec")
        assert "schwiki/default_sec" in result
