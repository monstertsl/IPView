import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings


def _get_fernet() -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"ipview-salt-v1",
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.ENCRYPT_KEY.encode()))
    return Fernet(key)


def encrypt_data(data: str) -> str:
    if not data:
        return ""
    f = _get_fernet()
    return f.encrypt(data.encode()).decode()


def decrypt_data(data: str) -> str:
    if not data:
        return ""
    f = _get_fernet()
    return f.decrypt(data.encode()).decode()


def encrypt_json(data: dict) -> str:
    return encrypt_data(json.dumps(data))


def decrypt_json(data: str) -> dict:
    return json.loads(decrypt_data(data))
