import base64
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings

KDF_ALGORITHM = hashes.SHA256()
KDF_LENGTH = 32
KDF_ITERATIONS = 120000
# Length of the per-message random salt prepended to the ciphertext.
SALT_LENGTH = 16

# Legacy fallback salt derived from SECRET_KEY — used to decrypt ciphertext
# produced by older versions of this module that did not prepend a random
# salt. New ciphertexts always use a fresh random salt.


def _get_salt() -> bytes:
    """Return the legacy KDF salt derived from Django settings.

    Only used for decrypting ciphertexts produced by older versions
    that did not prepend a random salt. New ``encrypt`` calls generate a
    fresh random salt per message.
    """
    return base64.b64encode(
        f"{getattr(settings, 'SECRET_KEY', 'fallback-key'):<32}".encode()
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


def encrypt(plaintext: bytes, password: str, b64: bool = False) -> bytes | str:
    """Encrypt plaintext using AES-GCM with a random salt and nonce.

    The format is ``salt (16B) + nonce (12B) + ciphertext``. A fresh
    random salt is generated per call so that the same plaintext
    encrypted with the same password yields a different key and thus a
    different ciphertext, defeating precomputed-key attacks.

    Args:
        plaintext: The data to encrypt.
        password: The encryption password.
        b64: If True, return base64-encoded ciphertext string.

    Returns:
        Union[bytes, str]: The ciphertext with prepended salt and nonce,
        optionally base64-encoded.

    Raises:
        ValueError: If encryption fails for any reason.
    """
    try:
        salt = secrets.token_bytes(SALT_LENGTH)
        key = _generate_key(password, salt)
        nonce = secrets.token_bytes(
            12
        )  # GCM requires a fresh 12-byte nonce per encryption
        ciphertext = salt + nonce + AESGCM(key).encrypt(nonce, plaintext, b"")
        return base64.b64encode(ciphertext).decode("ascii") if b64 else ciphertext
    except Exception as e:
        raise ValueError(f"Encryption failed: {e}") from e


def decrypt(ciphertext: bytes | str, password: str, b64: bool = False) -> str:
    """Decrypt ciphertext that was encrypted with AES-GCM.

    Supports the current format ``salt (16B) + nonce (12B) + ciphertext``
    and falls back to the legacy format ``nonce (12B) + ciphertext``
    (with the deterministic SECRET_KEY-derived salt) for ciphertexts
    produced by older versions.

    Args:
        ciphertext: The encrypted data, optionally base64-encoded.
        password: The decryption password.
        b64: If True, ciphertext is treated as a base64-encoded string.

    Returns:
        str: The decrypted plaintext as a UTF-8 string.

    Raises:
        ValueError: If decryption fails (wrong password, corrupted data, etc.).
    """
    try:
        if b64:
            ciphertext = base64.b64decode(ciphertext)
        # New format: salt + nonce + ciphertext
        if len(ciphertext) >= SALT_LENGTH + 12:
            salt = ciphertext[:SALT_LENGTH]
            nonce = ciphertext[SALT_LENGTH : SALT_LENGTH + 12]
            try:
                key = _generate_key(password, salt)
                plaintext = AESGCM(key).decrypt(nonce, ciphertext[SALT_LENGTH + 12 :], b"")
                return plaintext.decode("utf-8")
            except InvalidTag:
                pass  # Fall through to legacy format
        # Legacy format: nonce (12B) + ciphertext with deterministic salt
        key = _generate_key(password, _get_salt())
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
