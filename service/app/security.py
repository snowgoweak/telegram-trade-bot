from cryptography.fernet import Fernet

from service.app.config import settings

ENCRYPTION_KEY = settings.ENCRYPTION_KEY
cipher = Fernet(
    ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
)


def encrypt_private_key(private_key: str) -> str:
    """Шифруем приватный ключ (строку) и возвращаем base64-encoded результат."""
    encrypted_bytes = cipher.encrypt(private_key.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_private_key(encrypted_key: str) -> str:
    """Расшифровываем base64-encoded зашифрованный приватный ключ и возвращаем строку."""
    decrypted_bytes = cipher.decrypt(encrypted_key.encode("utf-8"))
    return decrypted_bytes.decode("utf-8")
