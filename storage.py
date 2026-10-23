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
    cur = conn.execute("SELECT id, name, students, boys, girls FROM classes ORDER BY id DESC")
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "students": r["students"],
            "boys": r["boys"] or 0,
            "girls": r["girls"] or 0
        }
        for r in cur.fetchall()
    ]

def _load_subjects(conn):
    """Загружает предметы с часами и учителями по классам."""
    cur = conn.execute("SELECT id, name, color, difficulty FROM subjects ORDER BY id DESC")
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
            "teachers": teachers_by_class,
            "color": row["color"] or "",
            "difficulty": row["difficulty"] or 0,  # <--- Добавили сложность
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
    """Добавляет класс."""
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
            "INSERT INTO classes (name, students, boys, girls, shift) VALUES (?, ?, 0, 0, 1)",
            (name, students)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_class(class_id, name=None, students=None, boys=None, girls=None):
    """Обновляет поля класса. Если переданы boys или girls — пересчитывает students."""
    conn = get_connection()
    try:
        # Если передали мальчиков или девочек, сначала узнаем текущие значения
        if boys is not None or girls is not None:
            cur = conn.execute("SELECT boys, girls FROM classes WHERE id=?", (class_id,))
            row = cur.fetchone()
            current_boys = boys if boys is not None else row["boys"]
            current_girls = girls if girls is not None else row["girls"]
            students = current_boys + current_girls  # Автоматический пересчет

        if name is not None:
            conn.execute("UPDATE classes SET name=? WHERE id=?", (name, class_id))
        if students is not None:
            conn.execute("UPDATE classes SET students=? WHERE id=?", (students, class_id))
        if boys is not None:
            conn.execute("UPDATE classes SET boys=? WHERE id=?", (boys, class_id))
        if girls is not None:
            conn.execute("UPDATE classes SET girls=? WHERE id=?", (girls, class_id))

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
    """
    conn = get_connection()
    try:
        cur = conn.execute("SELECT COUNT(*) FROM lesson_plan")
        total_rows = cur.fetchone()[0]

        cur = conn.execute("SELECT COUNT(*) FROM classes")
        classes_total = cur.fetchone()[0]

        cur = conn.execute("SELECT COUNT(DISTINCT class_id) FROM lesson_plan")
        classes_with_plan = cur.fetchone()[0]

        cur = conn.execute(
            "SELECT c.name AS name, SUM(lp.hours) AS hours "
            "FROM lesson_plan lp "
            "JOIN classes c ON c.id = lp.class_id "
            "GROUP BY c.id"
        )
        hours_by_class = {r["name"]: r["hours"] for r in cur.fetchall()}

        max_hours = max(hours_by_class.values()) if hours_by_class else 0
        too_many_hours = [n for n, h in hours_by_class.items() if h > 40]

        cur = conn.execute("SELECT COUNT(*) FROM lesson_plan WHERE teacher_id IS NOT NULL")
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


# --- Звонки ---

def load_bells():
    """Загружает расписание звонков из БД. Если пусто — создаёт дефолтное."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT slot, start_time, end_time, break_time FROM bell_schedule ORDER BY slot")
        bells = [dict(row) for row in cur.fetchall()]

        if not bells:
            default_bells = [
                {"slot": 1, "start_time": "08:30", "end_time": "09:15", "break_time": 10},
                {"slot": 2, "start_time": "09:25", "end_time": "10:10", "break_time": 20},
                {"slot": 3, "start_time": "10:30", "end_time": "11:15", "break_time": 20},
                {"slot": 4, "start_time": "11:35", "end_time": "12:20", "break_time": 10},
                {"slot": 5, "start_time": "12:30", "end_time": "13:15", "break_time": 10},
                {"slot": 6, "start_time": "13:25", "end_time": "14:10", "break_time": 10},
                {"slot": 7, "start_time": "14:20", "end_time": "15:05", "break_time": 10},
                {"slot": 8, "start_time": "15:15", "end_time": "16:00", "break_time": 0},
            ]
            for b in default_bells:
                conn.execute(
                    "INSERT INTO bell_schedule (slot, start_time, end_time, break_time) VALUES (?, ?, ?, ?)",
                    (b["slot"], b["start_time"], b["end_time"], b["break_time"])
                )
            conn.commit()
            return default_bells

        return bells
    finally:
        conn.close()


def save_bells(bells):
    """Сохраняет изменения звонков в БД."""
    conn = get_connection()
    try:
        for b in bells:
            conn.execute(
                "UPDATE bell_schedule SET start_time=?, end_time=?, break_time=? WHERE slot=?",
                (b["start_time"], b["end_time"], b["break_time"], b["slot"])
            )
        conn.commit()
    finally:
        conn.close()


# --- Экспорт ---

def export_json(filepath="school_data.json"):
    """Экспорт всех данных в JSON (резервная копия)."""
    data = load_data()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath
def save_schedule_db(schedule):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM schedule")
        for l in schedule:
            conn.execute(
                "INSERT INTO schedule (day, slot, class_name, subject, teacher_id, room_id) VALUES (?, ?, ?, ?, ?, ?)",
                (l.day, l.slot, l.class_name, l.subject, l.teacher_id, l.room_id)
            )
        conn.commit()
    finally:
        conn.close()

def load_schedule_db():
    conn = get_connection()
    try:
        cur = conn.execute("SELECT * FROM schedule ORDER BY day, slot")
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
def set_subject_color(subject_id, color):
    """Устанавливает цвет предмета."""
    conn = get_connection()
    try:
        conn.execute("UPDATE subjects SET color=? WHERE id=?", (color, subject_id))
        conn.commit()
    finally:
        conn.close()
def update_school_info(name, address, director, phone, email, academic_year):
    """Сохраняет информацию о школе."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT id FROM school LIMIT 1")
        row = cur.fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO school (name, address, director, phone, email, academic_year) VALUES (?, ?, ?, ?, ?, ?)",
                (name, address, director, phone, email, academic_year)
            )
        else:
            conn.execute(
                "UPDATE school SET name=?, address=?, director=?, phone=?, email=?, academic_year=? WHERE id=?",
                (name, address, director, phone, email, academic_year, row["id"])
            )
        conn.commit()
    finally:
        conn.close()
def set_subject_difficulty(subject_id, difficulty):
    """Устанавливает сложность предмета."""
    conn = get_connection()
    try:
        conn.execute("UPDATE subjects SET difficulty=? WHERE id=?", (difficulty, subject_id))
        conn.commit()
    finally:
        conn.close()