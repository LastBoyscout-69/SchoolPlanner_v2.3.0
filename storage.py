"""
storage.py — работа с данными в SQLite.
"""

import json
import os

from database import get_connection, init_db


# Загрузка данных


def _load_teachers(conn):
    """Загружает учителей с их предметами и запретами."""
    cur = conn.execute("SELECT id, name FROM teachers ORDER BY id DESC")
    teachers = []

    for row in cur.fetchall():
        t_id = row["id"]

        cur2 = conn.execute(
            "SELECT s.name FROM teacher_subjects ts "
            "JOIN subjects s ON s.id = ts.subject_id "
            "WHERE ts.teacher_id = ?",
            (t_id,)
        )
        subjects = [r["name"] for r in cur2.fetchall()]

        cur3 = conn.execute(
            "SELECT day, slot, reason FROM teacher_unavailable "
            "WHERE teacher_id = ?",
            (t_id,)
        )
        unavailable = []
        for r in cur3.fetchall():
            if r["reason"]:
                unavailable.append([r["day"], r["slot"], r["reason"]])
            else:
                unavailable.append([r["day"], r["slot"]])

        teachers.append({
            "id": t_id,
            "name": row["name"],
            "subjects": subjects,
            "unavailable_slots": unavailable,
        })
    return teachers


def _load_classes(conn):
    """Загружает классы."""
    cur = conn.execute("SELECT id, name, students FROM classes ORDER BY id DESC")
    return [
        {"id": r["id"], "name": r["name"], "students": r["students"]}
        for r in cur.fetchall()
    ]


def _load_subjects(conn):
    """Загружает предметы с часами и учителями по классам."""
    cur = conn.execute("SELECT id, name FROM subjects ORDER BY id DESC")
    subjects = []

    for row in cur.fetchall():
        s_id = row["id"]

        cur2 = conn.execute(
            "SELECT c.name AS class_name, lp.hours, lp.teacher_id, "
            "t.name AS teacher_name "
            "FROM lesson_plan lp "
            "JOIN classes c ON c.id = lp.class_id "
            "LEFT JOIN teachers t ON t.id = lp.teacher_id "
            "WHERE lp.subject_id = ?",
            (s_id,)
        )
        hours = {}
        teachers_by_class = {}
        for r in cur2.fetchall():
            hours[r["class_name"]] = r["hours"]
            if r["teacher_name"]:
                teachers_by_class[r["class_name"]] = r["teacher_name"]

        subjects.append({
            "id": s_id,
            "name": row["name"],
            "hours": hours,
            "teachers": teachers_by_class,   # ← новое поле
        })
    return subjects

def _load_rooms(conn):
    """Загружает кабинеты."""
    cur = conn.execute(
        "SELECT id, name, capacity, subject_specific FROM rooms ORDER BY id DESC"
    )
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "capacity": r["capacity"],
            "subject_specific": r["subject_specific"] or "",
        }
        for r in cur.fetchall()
    ]
def _load_school(conn):
    """Загружает информацию о школе."""
    cur = conn.execute("SELECT * FROM school LIMIT 1")
    row = cur.fetchone()
    if row is None:
        return {}
    return {
        "name": row["name"] or "",
        "address": row["address"] or "",
        "director": row["director"] or "",
        "phone": row["phone"] or "",
        "email": row["email"] or "",
        "academic_year": row["academic_year"] or "",
    }

def load_data():
    """Загружает все данные из БД."""
    init_db()

    conn = get_connection()
    try:
        return {
            "school": _load_school(conn),
            "teachers": _load_teachers(conn),
            "classes": _load_classes(conn),
            "subjects": _load_subjects(conn),
            "rooms": _load_rooms(conn),
        }
    finally:
        conn.close()


# Сохранение (заглушка — всё меняется через отдельные функции)


def save_data(data):
    """Заглушка. Изменения сохраняются через отдельные функции."""
    pass


# Учителя


def add_teacher_db(name="Новый"):
    """Добавляет учителя. Возвращает id."""
    conn = get_connection()
    try:
        cur = conn.execute("INSERT INTO teachers (name) VALUES (?)", (name,))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_teacher_name(teacher_id, name):
    """Обновляет ФИО учителя."""
    conn = get_connection()
    try:
        conn.execute("UPDATE teachers SET name=? WHERE id=?", (name, teacher_id))
        conn.commit()
    finally:
        conn.close()


def delete_teacher_db(teacher_id):
    """Удаляет учителя."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM teachers WHERE id=?", (teacher_id,))
        conn.commit()
    finally:
        conn.close()


def add_teacher_subject(teacher_id, subject_name):
    """Добавляет предмет учителю (создаёт, если нужно)."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT id FROM subjects WHERE name=?", (subject_name,))
        row = cur.fetchone()
        if row:
            subject_id = row["id"]
        else:
            cur = conn.execute("INSERT INTO subjects (name) VALUES (?)", (subject_name,))
            subject_id = cur.lastrowid

        conn.execute(
            "INSERT OR IGNORE INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)",
            (teacher_id, subject_id)
        )
        conn.commit()
    finally:
        conn.close()


def remove_teacher_subject(teacher_id, subject_name):
    """Убирает предмет у учителя."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM teacher_subjects "
            "WHERE teacher_id=? AND subject_id="
            "(SELECT id FROM subjects WHERE name=?)",
            (teacher_id, subject_name)
        )
        conn.commit()
    finally:
        conn.close()


def set_teacher_unavailable(teacher_id, slots):
    """Устанавливает список запрещённых слотов."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM teacher_unavailable WHERE teacher_id=?", (teacher_id,))
        for item in slots:
            if len(item) >= 2:
                day, slot = item[0], item[1]
                reason = item[2] if len(item) > 2 else ""
                conn.execute(
                    "INSERT INTO teacher_unavailable (teacher_id, day, slot, reason) "
                    "VALUES (?, ?, ?, ?)",
                    (teacher_id, day, slot, reason)
                )
        conn.commit()
    finally:
        conn.close()


# Классы


def add_class_db(name="Новый", students=25):
    """Добавляет класс. Если имя занято — добавляет номер."""
    conn = get_connection()
    try:
        base_name = name
        counter = 1
        while True:
            cur = conn.execute("SELECT id FROM classes WHERE name=?", (name,))
            if cur.fetchone() is None:
                break
            counter += 1
            name = f"{base_name} {counter}"

        cur = conn.execute(
            "INSERT INTO classes (name, students, shift) VALUES (?, ?, 1)",
            (name, students)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_class(class_id, name=None, students=None):
    """Обновляет название и/или число учеников класса."""
    conn = get_connection()
    try:
        if name is not None:
            conn.execute("UPDATE classes SET name=? WHERE id=?", (name, class_id))
        if students is not None:
            conn.execute("UPDATE classes SET students=? WHERE id=?", (students, class_id))
        conn.commit()
    finally:
        conn.close()


def delete_class_db(class_id):
    """Удаляет класс."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM classes WHERE id=?", (class_id,))
        conn.commit()
    finally:
        conn.close()


# Предметы


def add_subject_db(name="Новый предмет"):
    """Добавляет предмет. Если имя занято — добавляет номер."""
    conn = get_connection()
    try:
        base_name = name
        counter = 1
        while True:
            cur = conn.execute("SELECT id FROM subjects WHERE name=?", (name,))
            if cur.fetchone() is None:
                break
            counter += 1
            name = f"{base_name} {counter}"

        cur = conn.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_subject_name(subject_id, new_name):
    """Переименовывает предмет."""
    conn = get_connection()
    try:
        conn.execute("UPDATE subjects SET name=? WHERE id=?", (new_name, subject_id))
        conn.commit()
    finally:
        conn.close()


def delete_subject_db(subject_id):
    """Удаляет предмет."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
        conn.commit()
    finally:
        conn.close()


def set_lesson_hours(class_id, subject_id, hours):
    """Устанавливает количество часов предмета у класса."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT id FROM lesson_plan WHERE class_id=? AND subject_id=?",
            (class_id, subject_id)
        )
        row = cur.fetchone()

        if hours <= 0:
            if row:
                conn.execute("DELETE FROM lesson_plan WHERE id=?", (row["id"],))
        elif row:
            conn.execute("UPDATE lesson_plan SET hours=? WHERE id=?", (hours, row["id"]))
        else:
            conn.execute(
                "INSERT INTO lesson_plan (class_id, subject_id, hours) VALUES (?, ?, ?)",
                (class_id, subject_id, hours)
            )
        conn.commit()
    finally:
        conn.close()


# Кабинеты


def add_room_db(name="101", capacity=30, subject_specific=""):
    """Добавляет кабинет. Если имя занято — добавляет номер."""
    conn = get_connection()
    try:
        base_name = name
        counter = 1
        while True:
            cur = conn.execute("SELECT id FROM rooms WHERE name=?", (name,))
            if cur.fetchone() is None:
                break
            counter += 1
            name = f"{base_name}-{counter}"

        cur = conn.execute(
            "INSERT INTO rooms (name, capacity, subject_specific) VALUES (?, ?, ?)",
            (name, capacity, subject_specific)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_room(room_id, name=None, capacity=None, subject_specific=None):
    """Обновляет поля кабинета."""
    conn = get_connection()
    try:
        if name is not None:
            conn.execute("UPDATE rooms SET name=? WHERE id=?", (name, room_id))
        if capacity is not None:
            conn.execute("UPDATE rooms SET capacity=? WHERE id=?", (capacity, room_id))
        if subject_specific is not None:
            conn.execute("UPDATE rooms SET subject_specific=? WHERE id=?",
                        (subject_specific, room_id))
        conn.commit()
    finally:
        conn.close()


def delete_room_db(room_id):
    """Удаляет кабинет."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM rooms WHERE id=?", (room_id,))
        conn.commit()
    finally:
        conn.close()


def get_lesson_plan_stats():
    """
    Возвращает статистику по учебному плану.

    Возвращает dict:
        {
            "total_rows": int,           # всего строк в lesson_plan
            "classes_with_plan": int,    # классов с планом
            "classes_total": int,        # всего классов
            "hours_by_class": {name: int},  # часы по классам
            "max_hours": int,            # максимум часов у класса
            "too_many_hours": [names],   # классы с > 40 часов
            "teachers_assigned": int,    # строк с учителем
        }
    """
    conn = get_connection()
    try:
        # Всего строк в плане
        cur = conn.execute("SELECT COUNT(*) FROM lesson_plan")
        total_rows = cur.fetchone()[0]

        # Всего классов
        cur = conn.execute("SELECT COUNT(*) FROM classes")
        classes_total = cur.fetchone()[0]

        # Классы с планом
        cur = conn.execute("SELECT COUNT(DISTINCT class_id) FROM lesson_plan")
        classes_with_plan = cur.fetchone()[0]

        # Часы по классам
        cur = conn.execute(
            "SELECT c.name AS name, SUM(lp.hours) AS hours "
            "FROM lesson_plan lp "
            "JOIN classes c ON c.id = lp.class_id "
            "GROUP BY c.id"
        )
        hours_by_class = {r["name"]: r["hours"] for r in cur.fetchall()}

        max_hours = max(hours_by_class.values()) if hours_by_class else 0
        too_many_hours = [n for n, h in hours_by_class.items() if h > 40]

        # Строки с учителем
        cur = conn.execute(
            "SELECT COUNT(*) FROM lesson_plan WHERE teacher_id IS NOT NULL"
        )
        teachers_assigned = cur.fetchone()[0]

        return {
            "total_rows": total_rows,
            "classes_with_plan": classes_with_plan,
            "classes_total": classes_total,
            "hours_by_class": hours_by_class,
            "max_hours": max_hours,
            "too_many_hours": too_many_hours,
            "teachers_assigned": teachers_assigned,
        }
    finally:
        conn.close()
# Экспорт


def export_json(filepath="school_data.json"):
    """Экспорт всех данных в JSON (резервная копия)."""
    data = load_data()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath