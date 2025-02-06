from pytigon_lib.schtasks.term_tools import *

# Pytest tests
import pytest


def test_convert_m():
    assert convert_m("0") == (None, None)
    assert convert_m("1") == ("<strong>", "</strong>")
    assert convert_m("31") == ("<span color='#f00'>", "</span>")
    assert convert_m("1;31") == ("<strong><span color='#f00'>", "</span></strong>")
    assert convert_m("invalid") == ("", "")


def test_convert_ansi_codes():
    assert convert_ansi_codes("31m") == ("<span color='#f00'>", "</span>")
    assert convert_ansi_codes("1m") == ("<strong>", "</strong>")
    assert convert_ansi_codes("invalid") == ("", "")


def test_ansi_to_txt():
    ansi_text = "\033[1;31mHello\033[0m World"
    expected_output = "<strong><span color='#f00'>Hello</span></strong> World"
    assert ansi_to_txt(ansi_text) == expected_output

    ansi_text = "\033[1mBold\033[0m \033[32mGreen\033[0m"
    expected_output = "<strong>Bold</strong> <span color='#0f0'>Green</span>"
    assert ansi_to_txt(ansi_text) == expected_output


if __name__ == "__main__":
    pytest.main()
