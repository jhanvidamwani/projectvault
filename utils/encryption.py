import os
import base64
from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    secret = os.getenv("SECRET_KEY", "")
    if not secret:
        raise ValueError("SECRET_KEY environment variable is not set")
    key = base64.urlsafe_b64encode(secret.encode().ljust(32)[:32])
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
