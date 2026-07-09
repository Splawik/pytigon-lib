"""Additional tests for :mod:`pytigon_lib.schtools.doc_tools` beyond doc_tools_test.py."""

import os
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schtools.doc_tools import soffice_convert


class TestSofficeConvertExtra:
    def test_handle_format_with_colon_filter(self):
        in_path = "/fake/test.odt"
        tmpdir = "/fake/tmpdir"
        converted = os.path.join(tmpdir, "test.pdf")
        fake_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch("os.path.isfile", side_effect=lambda p: p == in_path or p == converted), \
             patch("tempfile.gettempdir", return_value=tmpdir), \
             patch("subprocess.run", return_value=fake_result) as mock_run, \
             patch("shutil.move"):
            soffice_convert(in_path, "/tmp/out.pdf", "pdf:writer_pdf_Export")
            assert mock_run.called
            assert "--convert-to" in mock_run.call_args[0][0]
            assert "pdf:writer_pdf_Export" in mock_run.call_args[0][0]

    def test_command_arguments_structure(self):
        in_path = "/fake/in.odt"
        tmpdir = "/fake/tmpdir"
        converted = os.path.join(tmpdir, "in.pdf")
        fake_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch("os.path.isfile", side_effect=lambda p: p == in_path or p == converted), \
             patch("tempfile.gettempdir", return_value=tmpdir), \
             patch("subprocess.run", return_value=fake_result) as mock_run, \
             patch("shutil.move") as mock_move:
            soffice_convert(in_path, "/tmp/out.pdf", "pdf")
            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "soffice"
            assert "--headless" in cmd
            assert "--convert-to" in cmd
            assert "pdf" in cmd
            assert "--outdir" in cmd
            assert in_path in cmd
            mock_move.assert_called_once_with(converted, "/tmp/out.pdf")

    def test_stderr_included_in_runtime_error(self):
        run_mock = MagicMock(
            returncode=0, stdout="", stderr="some internal error message"
        )
        with tempfile.NamedTemporaryFile(suffix=".odt", delete=False) as f:
            f.write(b"test")
            in_path = f.name
        try:
            with patch("subprocess.run", return_value=run_mock), patch(
                "os.path.isfile", side_effect=lambda p: p == in_path
            ):
                with pytest.raises(RuntimeError) as exc_info:
                    soffice_convert(in_path, "/tmp/out.pdf", "pdf")
                assert "some internal error message" in str(exc_info.value)
        finally:
            os.unlink(in_path)

    def test_handle_csv_format(self):
        run_mock = MagicMock(returncode=0, stdout="", stderr="")
        with tempfile.NamedTemporaryFile(suffix=".ods", delete=False) as f:
            f.write(b"test spreadsheet")
            in_path = f.name
        try:
            tmpdir = tempfile.gettempdir()
            base = os.path.basename(in_path).replace(".ods", ".csv")
            converted = os.path.join(tmpdir, base)
            with patch("subprocess.run", return_value=run_mock), patch(
                "os.path.isfile", side_effect=lambda p: p == in_path or p == converted
            ), patch("shutil.move") as mock_move:
                soffice_convert(in_path, "/tmp/out.csv", "csv")
                mock_move.assert_called_once()
        finally:
            os.unlink(in_path)

    def test_handle_txt_format(self):
        run_mock = MagicMock(returncode=0, stdout="", stderr="")
        with tempfile.NamedTemporaryFile(suffix=".odt", delete=False) as f:
            f.write(b"test document")
            in_path = f.name
        try:
            tmpdir = tempfile.gettempdir()
            base = os.path.basename(in_path).replace(".odt", ".txt")
            converted = os.path.join(tmpdir, base)
            with patch("subprocess.run", return_value=run_mock), patch(
                "os.path.isfile", side_effect=lambda p: p == in_path or p == converted
            ), patch("shutil.move") as mock_move:
                soffice_convert(in_path, "/tmp/out.txt", "txt")
                mock_move.assert_called_once_with(converted, "/tmp/out.txt")
        finally:
            os.unlink(in_path)

    def test_source_file_is_relative_path(self):
        run_mock = MagicMock(returncode=0, stdout="", stderr="")
        with patch("os.path.isfile", side_effect=lambda p: p.endswith(".odt")), patch(
            "subprocess.run", return_value=run_mock
        ):
            with pytest.raises(RuntimeError, match="Converted file not found"):
                soffice_convert("./relative/path.odt", "/tmp/out.pdf", "pdf")

    def test_subprocess_timeout_included(self):
        in_path = "/fake/in.odt"
        tmpdir = "/fake/tmpdir"
        converted = os.path.join(tmpdir, "in.pdf")
        fake_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch("os.path.isfile", side_effect=lambda p: p == in_path or p == converted), \
             patch("tempfile.gettempdir", return_value=tmpdir), \
             patch("subprocess.run", return_value=fake_result) as mock_run, \
             patch("shutil.move"):
            soffice_convert(in_path, "/tmp/out.pdf", "pdf")
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get("timeout") == 300

    def test_capture_output_is_text_mode(self):
        in_path = "/fake/in.odt"
        tmpdir = "/fake/tmpdir"
        converted = os.path.join(tmpdir, "in.pdf")
        fake_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch("os.path.isfile", side_effect=lambda p: p == in_path or p == converted), \
             patch("tempfile.gettempdir", return_value=tmpdir), \
             patch("subprocess.run", return_value=fake_result) as mock_run, \
             patch("shutil.move"):
            soffice_convert(in_path, "/tmp/out.pdf", "pdf")
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["capture_output"] is True
            assert call_kwargs["text"] is True

    def test_empty_source_filename(self):
        with pytest.raises(FileNotFoundError, match="Source file not found"):
            soffice_convert("", "/tmp/out.pdf", "pdf")

    def test_filter_suffix_extraction_from_colon_format(self):
        run_mock = MagicMock(returncode=0, stdout="", stderr="")
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(b"test")
            in_path = f.name
        try:
            tmpdir = tempfile.gettempdir()
            base = os.path.basename(in_path).replace(".docx", ".odt")
            converted = os.path.join(tmpdir, base)
            with patch("subprocess.run", return_value=run_mock), patch(
                "os.path.isfile",
                side_effect=lambda p: p == in_path or p == converted,
            ), patch("shutil.move") as mock_move:
                soffice_convert(in_path, "/tmp/out.odt", "odt:writer8")
                mock_move.assert_called_once_with(converted, "/tmp/out.odt")
        finally:
            os.unlink(in_path)
