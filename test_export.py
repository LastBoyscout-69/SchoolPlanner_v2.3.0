"""
Тест экспорта в Excel.
Создаёт тестовое расписание и экспортирует его в test_schedule.xlsx
"""

from models import Teacher, SchoolClass, Subject, Room, Lesson
from storage import load_data
from excel_export import export_to_excel


# Загружаем реальные данные из school_data.json
data = load_data()

# Создаём тестовое расписание (несколько уроков)
schedule = [
    Lesson(0, 0, "5А", "Математика", 1, 101),
    Lesson(0, 1, "5А", "Русский язык", 2, 101),
    Lesson(1, 0, "5А", "Физика", 3, 201),
    Lesson(0, 0, "5Б", "Математика", 1, 101),
    Lesson(0, 1, "5Б", "Русский язык", 2, 102),
    Lesson(2, 2, "5Б", "Литература", 2, 102),
]

# Экспорт
ok, message = export_to_excel(schedule, data, "test_schedule.xlsx")
print(message)