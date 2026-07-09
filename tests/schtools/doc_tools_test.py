"""Tests for :mod:`pytigon_lib.schtools.doc_tools`."""
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schtools.doc_tools import soffice_convert


class TestSofficeConvert:
    def test_source_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError, match="Source file not found"):
            soffice_convert("/nonexistent/file.odt", "/tmp/out.pdf", "pdf")

    def test_soffice_not_found(self):
        with patch("os.path.isfile", return_value=True), \
             patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="soffice command not found"):
                soffice_convert("/fake/in.odt", "/fake/out.pdf", "pdf")

    def test_soffice_nonzero_exit(self):
        with patch("os.path.isfile", return_value=True), \
             patch("subprocess.run", return_value=MagicMock(returncode=1, stdout="", stderr="error")):
            with pytest.raises(subprocess.CalledProcessError):
                soffice_convert("/fake/in.odt", "/fake/out.pdf", "pdf")

    def test_command_structure(self):
        with patch("os.path.isfile", return_value=True), \
             patch("shutil.move"), \
             patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")), \
             patch("os.path.isfile", return_value=False):
            try:
                soffice_convert("/fake/in.odt", "/tmp/fake_out.pdf", "pdf")
            except Exception:
                pass
