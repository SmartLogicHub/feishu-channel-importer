"""配置管理器：加密存储/读取飞书应用凭证"""
import json
import os
from pathlib import Path
from cryptography.fernet import Fernet

from .models import AppConfig

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".feishu_importer")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.enc")
KEY_FILE = os.path.join(CONFIG_DIR, ".key")
APP_CONFIG_FILE = os.path.join(CONFIG_DIR, "app_config.json")


def _ensure_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def _get_cipher():
    """获取加密器，如果密钥文件不存在则创建"""
    _ensure_dir()
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
    return Fernet(key)


def save_credentials(app_id: str, app_secret: str, app_token: str = ""):
    """加密保存凭证"""
    cipher = _get_cipher()
    data = json.dumps({"app_id": app_id, "app_secret": app_secret, "app_token": app_token}).encode()
    encrypted = cipher.encrypt(data)
    with open(CONFIG_FILE, 'wb') as f:
        f.write(encrypted)


def load_credentials() -> dict | None:
    """读取凭证，不存在则返回 None"""
    if not os.path.exists(CONFIG_FILE):
        return None
    cipher = _get_cipher()
    with open(CONFIG_FILE, 'rb') as f:
        encrypted = f.read()
    try:
        data = cipher.decrypt(encrypted)
        return json.loads(data.decode())
    except Exception:
        return None


def clear_credentials():
    """清除保存的凭证"""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
    if os.path.exists(KEY_FILE):
        os.remove(KEY_FILE)


def save_app_config(config: AppConfig, path: str | os.PathLike | None = None):
    """Save non-secret application settings as UTF-8 JSON."""
    target = Path(path or APP_CONFIG_FILE)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(config.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(target)


def load_app_config(path: str | os.PathLike | None = None) -> AppConfig:
    """Load non-secret application settings or return a default configuration."""
    target = Path(path or APP_CONFIG_FILE)
    if not target.exists():
        return AppConfig()
    data = json.loads(target.read_text(encoding="utf-8"))
    return AppConfig.from_dict(data)


def clear_app_config(path: str | os.PathLike | None = None):
    target = Path(path or APP_CONFIG_FILE)
    if target.exists():
        target.unlink()
