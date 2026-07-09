import pytest
from unittest.mock import MagicMock, patch

from pytigon_lib.schhtml.basehtmltags import (
    tag_class_map,
    register_tag_map,
    TagPreprocesor,
    TAG_PREPROCESS_MAP,
    get_tag_preprocess_map,
    HTML_TAGS,
    BLOCK_TAGS,
    ATOM_TAGS,
    PAR_TAGS,
    TABLE_TAGS,
    PAGE_TAGS,
    EXTRA_TAGS,
    CSS_TAG,
)


class TestTagClassMap:
    def test_register_tag_map_adds_entry(self):
        test_cls = MagicMock()
        tag_class_map.clear()
        register_tag_map("test_tag", test_cls)
        assert tag_class_map["test_tag"] is test_cls

    def test_register_tag_map_overwrites(self):
        test_cls1 = MagicMock()
        test_cls2 = MagicMock()
        tag_class_map.clear()
        register_tag_map("mytag", test_cls1)
        register_tag_map("mytag", test_cls2)
        assert tag_class_map["mytag"] is test_cls2

    def test_html_tags_configuration(self):
        assert "html" in HTML_TAGS
        assert "head" in HTML_TAGS
        assert "comment" in HTML_TAGS

    def test_block_tags_configuration(self):
        assert "body" in BLOCK_TAGS
        assert "form" in BLOCK_TAGS

    def test_atom_tags_configuration(self):
        assert "br" in ATOM_TAGS
        assert "a" in ATOM_TAGS
        assert "img" in ATOM_TAGS
        assert "calc" in ATOM_TAGS
        assert "hr" in ATOM_TAGS

    def test_par_tags_configuration(self):
        assert "p" in PAR_TAGS
        assert "h1" in PAR_TAGS
        assert "h2" in PAR_TAGS
        assert "span" in PAR_TAGS
        assert "div" in PAR_TAGS
        assert "pre" in PAR_TAGS
        assert "code" in PAR_TAGS

    def test_table_tags_configuration(self):
        assert "table" in TABLE_TAGS
        assert "tr" in TABLE_TAGS
        assert "td" in TABLE_TAGS
        assert "th" in TABLE_TAGS
        assert "caption" in TABLE_TAGS

    def test_page_tags_configuration(self):
        assert "page" in PAGE_TAGS
        assert "header" in PAGE_TAGS
        assert "footer" in PAGE_TAGS
        assert "newpage" in PAGE_TAGS

    def test_extra_tags_configuration(self):
        assert "vimg" in EXTRA_TAGS

    def test_css_tag_configuration(self):
        assert "link" in CSS_TAG


class TestTagPreprocessor:
    def test_register_exact_tag(self):
        tp = TagPreprocesor()
        handler = MagicMock()
        tp.register("myTag", handler)
        assert tp.get_handler("mytag") is handler

    def test_register_case_insensitive(self):
        tp = TagPreprocesor()
        handler = MagicMock()
        tp.register("MyTAG", handler)
        assert tp.get_handler("mytag") is handler

    def test_wildcard_match(self):
        tp = TagPreprocesor()
        handler = MagicMock()
        tp.register("div*", handler)
        assert tp.get_handler("div_abc") is handler

    def test_wildcard_no_match(self):
        tp = TagPreprocesor()
        handler = MagicMock()
        tp.register("div*", handler)
        assert tp.get_handler("span_abc") is None

    def test_exact_takes_priority_over_wildcard(self):
        tp = TagPreprocesor()
        exact_handler = MagicMock()
        wildcard_handler = MagicMock()
        tp.register("div_abc", exact_handler)
        tp.register("div*", wildcard_handler)
        assert tp.get_handler("div_abc") is exact_handler

    def test_wildcard_with_not_tag(self):
        tp = TagPreprocesor()
        handler = MagicMock()
        tp.register("div*", handler, not_tag="div_skip")
        assert tp.get_handler("div_abc") is handler
        assert tp.get_handler("div_skip") is None

    def test_multiple_wildcards(self):
        tp = TagPreprocesor()
        handler1 = MagicMock()
        handler2 = MagicMock()
        tp.register("div*", handler1)
        tp.register("span*", handler2)
        assert tp.get_handler("div_test") is handler1
        assert tp.get_handler("span_test") is handler2


class TestGlobalTagPreprocessor:
    def test_global_preprocessor_exists(self):
        assert TAG_PREPROCESS_MAP is not None
        assert isinstance(TAG_PREPROCESS_MAP, TagPreprocesor)

    def test_register_into_global(self):
        assert TAG_PREPROCESS_MAP is get_tag_preprocess_map()

    def test_get_handler_returns_none_for_unknown(self):
        handler = TAG_PREPROCESS_MAP.get_handler("__unknown_tag_xyz__")
        assert handler is None


class TestModuleImports:
    def test_imports_exist(self):
        from pytigon_lib.schhtml import html_tags

        assert hasattr(html_tags, "HtmlTag")
        assert hasattr(html_tags, "HeaderTag")
        assert hasattr(html_tags, "CommentTag")
