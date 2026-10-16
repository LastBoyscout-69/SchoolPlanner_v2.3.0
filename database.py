"""
database.py — слой работы с SQLite.

Отвечает за:
    - создание базы данных и таблиц;
    - получение соединения;
    - инициализацию при первом запуске.

Все остальные модули работают с БД через этот файл.
"""

import sqlite3
import os


# Имя файла базы данных (рядом с программой)
DB_FILE = "school.db"


# SQL-запросы для создания таблиц
SCHEMA = """
-- О школе (одна запись)
CREATE TABLE IF NOT EXISTS school (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    address TEXT,
    director TEXT,
    phone TEXT,
    email TEXT,
    academic_year TEXT
);

-- Учителя
CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    notes TEXT
);

-- Предметы
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    difficulty INTEGER DEFAULT 0
);

-- Классы
CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    students INTEGER DEFAULT 25,
    shift INTEGER DEFAULT 1
);

-- Кабинеты
CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    capacity INTEGER DEFAULT 30,
    subject_specific TEXT
);

-- Предметы учителя (много-ко-многим)
CREATE TABLE IF NOT EXISTS teacher_subjects (
    teacher_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    PRIMARY KEY (teacher_id, subject_id),
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- Запрещённые слоты учителя
CREATE TABLE IF NOT EXISTS teacher_unavailable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    day INTEGER NOT NULL,
    slot INTEGER NOT NULL,
    reason TEXT,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
);

-- Учебный план
CREATE TABLE IF NOT EXISTS lesson_plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    hours INTEGER NOT NULL,
    teacher_id INTEGER,
    "group" TEXT,
    paired INTEGER DEFAULT 0,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
);
"""


def get_connection():
    """Возвращает соединение с БД. Если файла нет — создаст."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Создаёт базу данных и таблицы, если их нет."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def reset_db():
    """Полностью удаляет файл БД."""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)


if __name__ == "__main__":
    init_db()
    print(f"База данных создана: {DB_FILE}")