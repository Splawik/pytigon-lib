"""Tests for :mod:`pytigon_lib.schtools.encrypt`."""

import base64

import pytest

from pytigon_lib.schtools.encrypt import _generate_key, _get_salt, decrypt, encrypt


class TestEncryptSalt:
    def test_salt_returns_bytes(self):
        salt = _get_salt()
        assert isinstance(salt, bytes)

    def test_salt_base64_format(self):
        salt = _get_salt()
        assert len(salt) > 0


class TestEncryptGenerateKey:
    def test_generate_key_returns_32_bytes(self):
        salt = b"test-salt-16bytes"
        key = _generate_key("password", salt)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_same_password_same_salt_yields_same_key(self):
        salt = b"test-salt-16bytes"
        k1 = _generate_key("mypassword", salt)
        k2 = _generate_key("mypassword", salt)
        assert k1 == k2

    def test_different_passwords_yield_different_keys(self):
        salt = b"test-salt-16bytes"
        k1 = _generate_key("pass1", salt)
        k2 = _generate_key("pass2", salt)
        assert k1 != k2


class TestEncryptDecrypt:
    def test_encrypt_returns_bytes_by_default(self):
        result = encrypt(b"hello", "password")
        assert isinstance(result, bytes)

    def test_encrypt_returns_string_with_b64(self):
        result = encrypt(b"hello", "password", b64=True)
        assert isinstance(result, str)

    def test_roundtrip_bytes(self):
        message = b"a secret message"
        encrypted = encrypt(message, "password")
        decrypted = decrypt(encrypted, "password")
        assert decrypted == "a secret message"

    def test_roundtrip_b64(self):
        message = b"another secret"
        encrypted = encrypt(message, "password", b64=True)
        decrypted = decrypt(encrypted, "password", b64=True)
        assert decrypted == "another secret"

    def test_encrypt_non_empty_ciphertext(self):
        result = encrypt(b"hello", "password")
        assert len(result) > 12

    def test_wrong_password_raises(self):
        encrypted = encrypt(b"hello", "correct_password")
        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt(encrypted, "wrong_password")

    def test_empty_plaintext(self):
        encrypted = encrypt(b"", "password")
        decrypted = decrypt(encrypted, "password")
        assert decrypted == ""

    def test_encrypt_produces_different_outputs(self):
        e1 = encrypt(b"hello", "password")
        e2 = encrypt(b"hello", "password")
        assert e1 != e2

    def test_corrupted_ciphertext_raises(self):
        encrypted = encrypt(b"hello", "password")
        corrupted = encrypted[:8] + b"\x00" * (len(encrypted) - 8)
        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt(corrupted, "password")

    def test_decrypt_invalid_b64_raises(self):
        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt("not-valid-base64!!!", "password", b64=True)

    def test_encrypt_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Encryption failed"):
            encrypt(None, "password")
