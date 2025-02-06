from pytigon_lib.schtools.encrypt import *

# Pytest tests
import pytest


def test_encrypt_decrypt():
    password = "testPassword"
    message = b"test message"

    encrypted = encrypt(message, password)
    decrypted = decrypt(encrypted, password)

    assert decrypted == message.decode("utf-8")


def test_encrypt_decrypt_b64():
    password = "testPassword"
    message = b"test message"

    encrypted = encrypt(message, password, b64=True)
    decrypted = decrypt(encrypted, password, b64=True)

    assert decrypted == message.decode("utf-8")


def test_encrypt_decrypt_failure():
    password = "testPassword"
    message = b"test message"

    encrypted = encrypt(message, password)
    with pytest.raises(ValueError):
        decrypt(encrypted, "wrongPassword")


def test_encrypt_decrypt_b64_failure():
    password = "testPassword"
    message = b"test message"

    encrypted = encrypt(message, password, b64=True)
    with pytest.raises(ValueError):
        decrypt(encrypted, "wrongPassword", b64=True)
