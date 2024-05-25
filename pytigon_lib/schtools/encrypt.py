import secrets
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

KDF_ALGORITHM = hashes.SHA256()
KDF_LENGTH = 32
KDF_ITERATIONS = 120000


def encrypt(plaintext: bytes, password: str, b64: bool = False) -> bytes:
    salt = base64.b64encode(f"{settings.SECRET_KEY:<32}".encode("utf-8"))
    kdf = PBKDF2HMAC(
        algorithm=KDF_ALGORITHM, length=KDF_LENGTH, salt=salt, iterations=KDF_ITERATIONS
    )
    key = kdf.derive(password.encode("utf-8"))
    nonce = secrets.token_bytes(12)  # GCM mode needs 12 fresh bytes every time
    ciphertext = nonce + AESGCM(key).encrypt(nonce, plaintext, b"")
    if b64:
        return base64.b64encode(ciphertext)
    else:
        return ciphertext


def decrypt(ciphertext: bytes, password: str, b64: bool = False) -> str:
    salt = base64.b64encode(f"{settings.SECRET_KEY:<32}".encode("utf-8"))

    kdf = PBKDF2HMAC(
        algorithm=KDF_ALGORITHM, length=KDF_LENGTH, salt=salt, iterations=KDF_ITERATIONS
    )
    key = kdf.derive(password.encode("utf-8"))
    if b64:
        ciphertext = base64.b64decode(ciphertext)
    return AESGCM(key).decrypt(ciphertext[:12], ciphertext[12:], b"")


if __name__ == "__main__":
    password = "aStrongPassword"
    message = b"a secret message"

    encrypted = encrypt(message, password)
    decrypted = decrypt(encrypted, password)

    print(f"message: {message}")
    print(f"encrypted: {encrypted}")
    print(f"decrypted: {decrypted}")
