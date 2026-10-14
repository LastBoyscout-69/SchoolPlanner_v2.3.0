"""
Управление лицензией SchoolPlanner.
- Хранение ключа в %APPDATA% и %LOCALAPPDATA%
- Офлайн-проверка ключа по алгоритму
- Демо-режим с ограничением
"""

import os
import json
import hashlib

APP_NAME = "SchoolPlanner"
LICENSE_FILE = "license.json"
DEMO_MAX_CLASSES = 5

# Секретный соль для генерации ключей.
# ВАЖНО: не публикуй это значение! Оно используется и в keygen.py
SECRET_SALT = "SchoolPlanner_2026_SecretKey_v1"


def _get_paths():
    """Возвращает список путей, где искать/хранить license.json."""
    paths = []
    # %APPDATA%\SchoolPlanner\license.json
    appdata = os.environ.get("APPDATA")
    if appdata:
        paths.append(os.path.join(appdata, APP_NAME, LICENSE_FILE))
    # %LOCALAPPDATA%\SchoolPlanner\license.json
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        paths.append(os.path.join(localappdata, APP_NAME, LICENSE_FILE))
    return paths


def _generate_key_from_number(n):
    """
    Генерирует ключ из числа n.
    Формат: SP-XXXX-XXXX-XXXX
    """
    # Формируем строку из n + соль
    raw = f"{SECRET_SALT}-{n}"
    # Считаем md5
    h = hashlib.md5(raw.encode()).hexdigest().upper()
    # Берём 12 символов и разбиваем на 3 группы по 4
    part1 = h[0:4]
    part2 = h[4:8]
    part3 = h[8:12]
    return f"SP-{part1}-{part2}-{part3}"


def is_valid_key(key):
    """
    Проверяет, является ли ключ валидным.
    Перебирает все возможные n от 1 до 10000 и сверяет сгенерированный ключ.
    """
    if not key:
        return False
    key = key.strip().upper()
    if not key.startswith("SP-"):
        return False
    # Проверяем все n от 1 до 100000
    for n in range(1, 100000):
        if _generate_key_from_number(n) == key:
            return True
    return False


def load_license():
    """
    Загружает данные лицензии.
    Возвращает dict с полями:
      - activated: bool
      - key: str или None
    """
    for path in _get_paths():
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("activated") and data.get("key"):
                    # проверим, что ключ всё ещё валидный
                    if is_valid_key(data["key"]):
                        return {"activated": True, "key": data["key"]}
            except (json.JSONDecodeError, IOError):
                continue
    return {"activated": False, "key": None}


def save_license(key):
    """
    Сохраняет ключ во ВСЕ доступные пути.
    Возвращает True, если хотя бы в один путь удалось сохранить.
    """
    data = {"activated": True, "key": key.strip().upper()}
    saved_anywhere = False
    for path in _get_paths():
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            saved_anywhere = True
        except (IOError, OSError):
            continue
    return saved_anywhere


def is_activated():
    """Быстрая проверка: активирована ли программа."""
    return load_license().get("activated", False)