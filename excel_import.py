"""
excel_import.py — импорт данных из Excel в SQLite.

Два этапа:
    1. Чтение файла Excel — возвращает словари с данными.
    2. Сравнение с БД и обновление — умный импорт.
"""

from openpyxl import load_workbook


def read_school(ws):
    """Читает лист «Школа». Возвращает dict или None."""
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    if not rows or not any(rows[0]):
        return None

    row = rows[0]
    return {
        "name": str(row[0]).strip() if row[0] else "",
        "address": str(row[1]).strip() if row[1] else "",
        "director": str(row[2]).strip() if row[2] else "",
        "phone": str(row[3]).strip() if row[3] else "",
        "email": str(row[4]).strip() if row[4] else "",
        "academic_year": str(row[5]).strip() if row[5] else "",
    }


def read_teachers(ws):
    """Читает лист «Учителя». Возвращает список dict."""
    teachers = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue

        name = str(row[0]).strip()
        if not name:
            continue

        # Предметы через запятую → список
        subjects_raw = str(row[4]).strip() if len(row) > 4 and row[4] else ""
        subjects = [s.strip() for s in subjects_raw.split(",") if s.strip()]

        teachers.append({
            "name": name,
            "phone": str(row[1]).strip() if len(row) > 1 and row[1] else "",
            "email": str(row[2]).strip() if len(row) > 2 and row[2] else "",
            "notes": str(row[3]).strip() if len(row) > 3 and row[3] else "",
            "subjects": subjects,
        })
    return teachers


def read_subjects(ws):
    """Читает лист «Предметы». Возвращает список dict."""
    subjects = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue

        name = str(row[0]).strip()
        if not name:
            continue

        try:
            difficulty = int(row[1]) if len(row) > 1 and row[1] else 0
        except (ValueError, TypeError):
            difficulty = 0

        subjects.append({
            "name": name,
            "difficulty": difficulty,
        })
    return subjects


def read_classes(ws):
    """Читает лист «Классы». Возвращает список dict."""
    classes = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue

        name = str(row[0]).strip()
        if not name:
            continue

        try:
            students = int(row[1]) if len(row) > 1 and row[1] else 25
        except (ValueError, TypeError):
            students = 25

        try:
            shift = int(row[2]) if len(row) > 2 and row[2] else 1
        except (ValueError, TypeError):
            shift = 1

        classes.append({
            "name": name,
            "students": students,
            "shift": shift,
        })
    return classes


def read_rooms(ws):
    """Читает лист «Кабинеты». Возвращает список dict."""
    rooms = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue

        name = str(row[0]).strip()
        if not name:
            continue

        try:
            capacity = int(row[2]) if len(row) > 2 and row[2] else 30
        except (ValueError, TypeError):
            capacity = 30

        rooms.append({
            "name": name,
            "capacity": capacity,
            "subject_specific": str(row[1]).strip() if len(row) > 1 and row[1] else "",
        })
    return rooms


def read_lesson_plan(ws):
    """Читает лист «Учебный план». Возвращает список dict."""
    plan = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0] or not row[1]:
            continue

        class_name = str(row[0]).strip()
        subject_name = str(row[1]).strip()
        if not class_name or not subject_name:
            continue

        try:
            hours = int(row[2]) if len(row) > 2 and row[2] else 0
        except (ValueError, TypeError):
            hours = 0

        if hours <= 0:
            continue

        plan.append({
            "class_name": class_name,
            "subject_name": subject_name,
            "hours": hours,
            "teacher_name": str(row[3]).strip() if len(row) > 3 and row[3] else "",
        })
    return plan


def read_excel(filepath):
    """
    Читает все листы Excel.

    Возвращает (успех: bool, данные или ошибка).
    Данные — dict с ключами: school, teachers, subjects, classes, rooms, lesson_plan.
    """
    try:
        wb = load_workbook(filepath, data_only=True)
    except Exception as e:
        return False, f"Не удалось открыть файл: {e}"

    # Проверяем, что все нужные листы есть
    required_sheets = ["Школа", "Учителя", "Предметы", "Классы", "Кабинеты", "Учебный план"]
    missing = [s for s in required_sheets if s not in wb.sheetnames]
    if missing:
        return False, (
            "В файле нет листов: " + ", ".join(missing) +
            "\n\nСкачайте шаблон и заполните его."
        )

    result = {
        "school": read_school(wb["Школа"]),
        "teachers": read_teachers(wb["Учителя"]),
        "subjects": read_subjects(wb["Предметы"]),
        "classes": read_classes(wb["Классы"]),
        "rooms": read_rooms(wb["Кабинеты"]),
        "lesson_plan": read_lesson_plan(wb["Учебный план"]),
    }

    return True, result
from database import get_connection


def import_school(conn, school_data):
    """Импорт школы. Всегда одна запись — обновляем или создаём."""
    if not school_data:
        return

    cur = conn.execute("SELECT id FROM school LIMIT 1")
    row = cur.fetchone()

    if row is None:
        # Создаём
        conn.execute(
            "INSERT INTO school (name, address, director, phone, email, academic_year) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (school_data["name"], school_data["address"], school_data["director"],
             school_data["phone"], school_data["email"], school_data["academic_year"])
        )
    else:
        # Обновляем
        conn.execute(
            "UPDATE school SET name=?, address=?, director=?, phone=?, email=?, "
            "academic_year=? WHERE id=?",
            (school_data["name"], school_data["address"], school_data["director"],
             school_data["phone"], school_data["email"], school_data["academic_year"],
             row["id"])
        )


def import_subjects(conn, subjects_data):
    """Импорт предметов. Ключ — название."""
    for s in subjects_data:
        cur = conn.execute("SELECT id, difficulty FROM subjects WHERE name=?",
                          (s["name"],))
        row = cur.fetchone()

        if row is None:
            conn.execute("INSERT INTO subjects (name, difficulty) VALUES (?, ?)",
                        (s["name"], s["difficulty"]))
        elif row["difficulty"] != s["difficulty"]:
            conn.execute("UPDATE subjects SET difficulty=? WHERE id=?",
                        (s["difficulty"], row["id"]))


def import_classes(conn, classes_data):
    """Импорт классов. Ключ — название."""
    for c in classes_data:
        cur = conn.execute("SELECT id, students, shift FROM classes WHERE name=?",
                          (c["name"],))
        row = cur.fetchone()

        if row is None:
            conn.execute("INSERT INTO classes (name, students, shift) VALUES (?, ?, ?)",
                        (c["name"], c["students"], c["shift"]))
        else:
            if row["students"] != c["students"] or row["shift"] != c["shift"]:
                conn.execute("UPDATE classes SET students=?, shift=? WHERE id=?",
                            (c["students"], c["shift"], row["id"]))


def import_rooms(conn, rooms_data):
    """Импорт кабинетов. Ключ — номер."""
    for r in rooms_data:
        cur = conn.execute(
            "SELECT id, capacity, subject_specific FROM rooms WHERE name=?",
            (r["name"],))
        row = cur.fetchone()

        if row is None:
            conn.execute(
                "INSERT INTO rooms (name, capacity, subject_specific) VALUES (?, ?, ?)",
                (r["name"], r["capacity"], r["subject_specific"]))
        else:
            if (row["capacity"] != r["capacity"]
                    or row["subject_specific"] != r["subject_specific"]):
                conn.execute(
                    "UPDATE rooms SET capacity=?, subject_specific=? WHERE id=?",
                    (r["capacity"], r["subject_specific"], row["id"]))


def import_teachers(conn, teachers_data):
    """Импорт учителей. Ключ — ФИО."""
    for t in teachers_data:
        cur = conn.execute(
            "SELECT id, phone, email, notes FROM teachers WHERE name=?",
            (t["name"],))
        row = cur.fetchone()

        if row is None:
            # Создаём учителя
            conn.execute(
                "INSERT INTO teachers (name, phone, email, notes) VALUES (?, ?, ?, ?)",
                (t["name"], t["phone"], t["email"], t["notes"]))
            teacher_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        else:
            teacher_id = row["id"]
            # Обновляем поля, если различаются
            if (row["phone"] != t["phone"] or row["email"] != t["email"]
                    or row["notes"] != t["notes"]):
                conn.execute(
                    "UPDATE teachers SET phone=?, email=?, notes=? WHERE id=?",
                    (t["phone"], t["email"], t["notes"], teacher_id))

        # Обновляем предметы учителя
        conn.execute("DELETE FROM teacher_subjects WHERE teacher_id=?", (teacher_id,))
        for subj_name in t["subjects"]:
            cur = conn.execute("SELECT id FROM subjects WHERE name=?", (subj_name,))
            subj_row = cur.fetchone()
            if subj_row:
                conn.execute(
                    "INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)",
                    (teacher_id, subj_row["id"]))


def import_lesson_plan(conn, plan_data):
    """Импорт учебного плана. Ключ — класс + предмет."""
    for p in plan_data:
        # Ищем класс
        cur = conn.execute("SELECT id FROM classes WHERE name=?", (p["class_name"],))
        class_row = cur.fetchone()
        if not class_row:
            continue

        # Ищем предмет
        cur = conn.execute("SELECT id FROM subjects WHERE name=?", (p["subject_name"],))
        subject_row = cur.fetchone()
        if not subject_row:
            continue

        # Ищем учителя (если указан)
        teacher_id = None
        if p["teacher_name"]:
            cur = conn.execute("SELECT id FROM teachers WHERE name=?", (p["teacher_name"],))
            teacher_row = cur.fetchone()
            if teacher_row:
                teacher_id = teacher_row["id"]

        class_id = class_row["id"]
        subject_id = subject_row["id"]

        # Проверяем, есть ли уже такая запись
        cur = conn.execute(
            "SELECT id, hours, teacher_id FROM lesson_plan "
            "WHERE class_id=? AND subject_id=?",
            (class_id, subject_id))
        row = cur.fetchone()

        if row is None:
            conn.execute(
                "INSERT INTO lesson_plan (class_id, subject_id, hours, teacher_id) "
                "VALUES (?, ?, ?, ?)",
                (class_id, subject_id, p["hours"], teacher_id))
        else:
            if row["hours"] != p["hours"] or row["teacher_id"] != teacher_id:
                conn.execute(
                    "UPDATE lesson_plan SET hours=?, teacher_id=? WHERE id=?",
                    (p["hours"], teacher_id, row["id"]))


def import_from_excel(filepath):
    """
    Главная функция импорта.

    Читает Excel → пишет в SQL → возвращает отчёт.

    Returns:
        (успех: bool, сообщение: str)
    """
    # Читаем Excel
    ok, data = read_excel(filepath)
    if not ok:
        return False, data

    conn = get_connection()
    try:
        # Очищаем таблицы перед импортом
        conn.execute("DELETE FROM lesson_plan")
        conn.execute("DELETE FROM teacher_subjects")
        conn.execute("DELETE FROM teacher_unavailable")

        # Импортируем по порядку
        import_school(conn, data["school"])
        import_subjects(conn, data["subjects"])
        import_classes(conn, data["classes"])
        import_rooms(conn, data["rooms"])
        import_teachers(conn, data["teachers"])
        import_lesson_plan(conn, data["lesson_plan"])

        conn.commit()
        return True, (
            f"Импорт завершён:\n"
            f"  Учителей: {len(data['teachers'])}\n"
            f"  Предметов: {len(data['subjects'])}\n"
            f"  Классов: {len(data['classes'])}\n"
            f"  Кабинетов: {len(data['rooms'])}\n"
            f"  Строк плана: {len(data['lesson_plan'])}"
        )
    except Exception as e:
        conn.rollback()
        return False, f"Ошибка импорта: {e}"
    finally:
        conn.close()

if __name__ == "__main__":
    ok, msg = import_from_excel("template.xlsx")
    print(msg)