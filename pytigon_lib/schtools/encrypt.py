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
# Salt derived from SECRET_KEY ensures deterministic key derivation
# between encrypt/decrypt calls for the same password. Computed lazily
# from settings so it stays current if SECRET_KEY changes at runtime.
# NOTE: For production use where different salts per message are required,
# prepend the random salt to the ciphertext and extract it during decryption.


def _get_salt() -> bytes:
    """Return the KDF salt derived from Django settings.

    The salt is computed from SECRET_KEY with a fallback for
    environments where it is not set.
    """
    return base64.b64encode(
        f"{getattr(settings, 'SECRET_KEY', 'fallback-key'):<32}".encode("utf-8")
    )


def _generate_key(password: str, salt: bytes) -> bytes:
    """Generate an AES key using PBKDF2HMAC key derivation.

    Args:
        password: The user-provided password.
        salt: Cryptographic salt for the KDF.

    Returns:
        bytes: A 32-byte derived key.
    """
    kdf = PBKDF2HMAC(
        algorithm=KDF_ALGORITHM,
        length=KDF_LENGTH,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt(plaintext: bytes, password: str, b64: bool = False) -> Union[bytes, str]:
    """Encrypt plaintext using AES-GCM with a random nonce.

    The nonce (12 bytes) is prepended to the ciphertext. AES-GCM provides
    both confidentiality and integrity/authentication.

    Args:
        plaintext: The data to encrypt.
        password: The encryption password.
        b64: If True, return base64-encoded ciphertext string.

    Returns:
        Union[bytes, str]: The ciphertext with prepended nonce, optionally base64-encoded.

    Raises:
        ValueError: If encryption fails for any reason.
    """
    try:
        key = _generate_key(password, _get_salt())
        nonce = secrets.token_bytes(
            12
        )  # GCM requires a fresh 12-byte nonce per encryption
        ciphertext = nonce + AESGCM(key).encrypt(nonce, plaintext, b"")
        return base64.b64encode(ciphertext).decode("ascii") if b64 else ciphertext
    except Exception as e:
        raise ValueError(f"Encryption failed: {e}") from e


def decrypt(ciphertext: Union[bytes, str], password: str, b64: bool = False) -> str:
    """Decrypt ciphertext that was encrypted with AES-GCM.

    Extracts the 12-byte nonce from the beginning of the ciphertext and
    uses it together with the derived key for decryption.

    Args:
        ciphertext: The encrypted data (nonce + ciphertext), optionally base64-encoded.
        password: The decryption password.
        b64: If True, ciphertext is treated as a base64-encoded string.

    Returns:
        str: The decrypted plaintext as a UTF-8 string.

    Raises:
        ValueError: If decryption fails (wrong password, corrupted data, etc.).
    """
    try:
        key = _generate_key(password, _get_salt())
        if b64:
            ciphertext = base64.b64decode(ciphertext)
        plaintext = AESGCM(key).decrypt(ciphertext[:12], ciphertext[12:], b"")
        return plaintext.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}") from e


if __name__ == "__main__":
    password = "aStrongPassword"
    message = b"a secret message"

    encrypted = encrypt(message, password)
    decrypted = decrypt(encrypted, password)

    print(f"message: {message}")
    print(f"encrypted: {encrypted}")
    print(f"decrypted: {decrypted}")
