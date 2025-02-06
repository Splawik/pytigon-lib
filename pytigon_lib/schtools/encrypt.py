import secrets
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from typing import Union

KDF_ALGORITHM = hashes.SHA256()
KDF_LENGTH = 32
KDF_ITERATIONS = 120000


def _generate_key(password: str, salt: bytes) -> bytes:
    """Generate a key using PBKDF2HMAC."""
    kdf = PBKDF2HMAC(
        algorithm=KDF_ALGORITHM, length=KDF_LENGTH, salt=salt, iterations=KDF_ITERATIONS
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt(plaintext: bytes, password: str, b64: bool = False) -> Union[bytes, str]:
    """Encrypt plaintext using AES-GCM."""
    try:
        salt = base64.b64encode(f"{settings.SECRET_KEY:<32}".encode("utf-8"))
        key = _generate_key(password, salt)
        nonce = secrets.token_bytes(12)  # GCM mode needs 12 fresh bytes every time
        ciphertext = nonce + AESGCM(key).encrypt(nonce, plaintext, b"")
        return base64.b64encode(ciphertext) if b64 else ciphertext
    except Exception as e:
        raise ValueError(f"Encryption failed: {e}")


def decrypt(ciphertext: Union[bytes, str], password: str, b64: bool = False) -> str:
    """Decrypt ciphertext using AES-GCM."""
    try:
        salt = base64.b64encode(f"{settings.SECRET_KEY:<32}".encode("utf-8"))
        key = _generate_key(password, salt)
        if b64:
            ciphertext = base64.b64decode(ciphertext)
        return (
            AESGCM(key).decrypt(ciphertext[:12], ciphertext[12:], b"").decode("utf-8")
        )
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")


if __name__ == "__main__":
    password = "aStrongPassword"
    message = b"a secret message"

    encrypted = encrypt(message, password)
    decrypted = decrypt(encrypted, password)

    print(f"message: {message}")
    print(f"encrypted: {encrypted}")
    print(f"decrypted: {decrypted}")
