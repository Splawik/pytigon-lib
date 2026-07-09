"""Tests for :class:`pytigon_lib.schtools.install.Ptig`."""

import io
import os
import tempfile
import zipfile

import pytest

from pytigon_lib.schtools.install import Ptig


def _build_ptig_zip(prj_name="myproject", version="1.0", license_text="MIT", readme_text="# README", db_content=b"db") -> bytes:
    meta_dir = f"{prj_name}-{version}.dist-info"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{meta_dir}/", "")
        zf.writestr(f"{prj_name}/LICENSE", license_text)
        zf.writestr(f"{prj_name}/README.md", readme_text)
        zf.writestr(f"{meta_dir}/{prj_name}.db", db_content)
    body = buf.getvalue()
    return b"# header\n" + body


def _write_ptig_file(path, prj_name="myproject", version="1.0", **kwargs):
    content = _build_ptig_zip(prj_name=prj_name, version=version, **kwargs)
    with open(path, "wb") as f:
        f.write(content)


class TestPtigInit:
    def test_with_temp_file_parses_prj_name(self):
        with tempfile.NamedTemporaryFile(suffix=".ptig", delete=False) as tmp:
            _write_ptig_file(tmp.name, "testprj", "2.0")
            tmp.close()
            ptig = Ptig(tmp.name)
            assert ptig.prj_name == "testprj"
            ptig.close()
            os.unlink(tmp.name)

    def test_with_temp_file_parses_version(self):
        with tempfile.NamedTemporaryFile(suffix=".ptig", delete=False) as tmp:
            _write_ptig_file(tmp.name, "foo", "3.2.1")
            tmp.close()
            ptig = Ptig(tmp.name)
            assert ptig.version == "3"
            ptig.close()
            os.unlink(tmp.name)

    def test_version_single_segment(self):
        with tempfile.NamedTemporaryFile(suffix=".ptig", delete=False) as tmp:
            _write_ptig_file(tmp.name, "simple", "5")
            tmp.close()
            ptig = Ptig(tmp.name)
            assert ptig.version == "5"
            ptig.close()
            os.unlink(tmp.name)

    def test_with_file_like_object(self):
        data = _build_ptig_zip("ioprj", "0.1")
        buf = io.BytesIO(data)
        ptig = Ptig(buf)
        assert ptig.prj_name == "ioprj"
        assert ptig.version == "0"

    def test_no_dist_info_sets_prj_name_none(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("somefile.txt", "content")
        data = b"# header\n" + buf.getvalue()
        bio = io.BytesIO(data)
        ptig = Ptig(bio)
        assert ptig.prj_name is None
        assert ptig.meta_path is None

    def test_extract_to_is_none_initially(self):
        with tempfile.NamedTemporaryFile(suffix=".ptig", delete=False) as tmp:
            _write_ptig_file(tmp.name)
            tmp.close()
            ptig = Ptig(tmp.name)
            assert ptig.extract_to is None
            ptig.close()
            os.unlink(tmp.name)


class TestPtigIsOk:
    def test_is_ok_true_when_prj_name_found(self):
        with tempfile.NamedTemporaryFile(suffix=".ptig", delete=False) as tmp:
            _write_ptig_file(tmp.name, "okprj", "1.0")
            tmp.close()
            ptig = Ptig(tmp.name)
            assert ptig.is_ok() is True
            ptig.close()
            os.unlink(tmp.name)

    def test_is_ok_false_when_no_dist_info(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("somefile.txt", "content")
        data = b"# header\n" + buf.getvalue()
        ptig = Ptig(io.BytesIO(data))
        assert ptig.is_ok() is False


class TestPtigGetLicense:
    def test_returns_license_content(self):
        with tempfile.NamedTemporaryFile(suffix=".ptig", delete=False) as tmp:
            _write_ptig_file(tmp.name, license_text="Apache-2.0")
            ptig = Ptig(tmp.name)
            result = ptig.get_license()
            assert result == "Apache-2.0"
            ptig.close()
            os.unlink(tmp.name)

    def test_returns_empty_string_when_license_missing(self):
        meta_dir = "no-license-1.0.dist-info"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(f"{meta_dir}/", "")
            zf.writestr("no-license/README.md", "# hi")
            zf.writestr(f"{meta_dir}/no-license.db", b"db")
        data = b"# header\n" + buf.getvalue()
        ptig = Ptig(io.BytesIO(data))
        assert ptig.get_license() == ""


class TestPtigGetReadme:
    def test_returns_readme_content(self):
        with tempfile.NamedTemporaryFile(suffix=".ptig", delete=False) as tmp:
            _write_ptig_file(tmp.name, readme_text="# My Project\n\nDescription here.")
            ptig = Ptig(tmp.name)
            result = ptig.get_readme()
            assert result == "# My Project\n\nDescription here."
            ptig.close()
            os.unlink(tmp.name)

    def test_returns_empty_string_when_readme_missing(self):
        meta_dir = "noreadme-1.0.dist-info"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(f"{meta_dir}/", "")
            zf.writestr("noreadme/LICENSE", "MIT")
            zf.writestr(f"{meta_dir}/noreadme.db", b"db")
        data = b"# header\n" + buf.getvalue()
        ptig = Ptig(io.BytesIO(data))
        assert ptig.get_readme() == ""


class TestPtigGetDb:
    def test_returns_db_bytes(self):
        with tempfile.NamedTemporaryFile(suffix=".ptig", delete=False) as tmp:
            _write_ptig_file(tmp.name, db_content=b"\x00\x01\x02\x03")
            ptig = Ptig(tmp.name)
            result = ptig.get_db()
            assert result == b"\x00\x01\x02\x03"
            ptig.close()
            os.unlink(tmp.name)

    def test_returns_empty_db(self):
        with tempfile.NamedTemporaryFile(suffix=".ptig", delete=False) as tmp:
            _write_ptig_file(tmp.name, db_content=b"")
            ptig = Ptig(tmp.name)
            result = ptig.get_db()
            assert result == b""
            ptig.close()
            os.unlink(tmp.name)


class TestPtigClose:
    def test_close_closes_archive(self):
        with tempfile.NamedTemporaryFile(suffix=".ptig", delete=False) as tmp:
            _write_ptig_file(tmp.name)
            ptig = Ptig(tmp.name)
            ptig.close()
            os.unlink(tmp.name)


class TestPtigContextManager:
    def test_with_statement_parses_prj_name(self):
        with tempfile.NamedTemporaryFile(suffix=".ptig", delete=False) as tmp:
            _write_ptig_file(tmp.name, "ctxprj", "4.0")
            tmp_name = tmp.name
        ptig = Ptig(tmp_name)
        assert ptig.prj_name == "ctxprj"
        assert ptig.version == "4"
        ptig.close()
        os.unlink(tmp_name)

    def test_context_manager_enter_returns_self(self):
        with tempfile.NamedTemporaryFile(suffix=".ptig", delete=False) as tmp:
            _write_ptig_file(tmp.name)
            with Ptig(tmp.name) as ptig:
                assert isinstance(ptig, Ptig)
            os.unlink(tmp.name)

    def test_context_manager_exit_closes(self):
        with tempfile.NamedTemporaryFile(suffix=".ptig", delete=False) as tmp:
            _write_ptig_file(tmp.name)
            with Ptig(tmp.name):
                pass
            os.unlink(tmp.name)

    def test_context_manager_with_file_like_object(self):
        data = _build_ptig_zip("ctxio", "9.0")
        with Ptig(io.BytesIO(data)) as ptig:
            assert ptig.prj_name == "ctxio"
            assert ptig.is_ok() is True

    def test_context_manager_exception_propagates(self):
        data = _build_ptig_zip("errprj", "1.0")
        with pytest.raises(ValueError):
            with Ptig(io.BytesIO(data)):
                raise ValueError("deliberate error")
