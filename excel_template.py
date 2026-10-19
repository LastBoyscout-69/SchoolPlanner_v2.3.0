"""
excel_template.py — генератор шаблона Excel для импорта.

Создаёт файл template.xlsx с 6 листами и шапками.
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment


def create_template(filepath):
    """
    Создаёт шаблон Excel с 6 листами.

    Args:
        filepath: путь, куда сохранить .xlsx

    Returns:
        (успех: bool, сообщение: str)
    """
    try:
        wb = Workbook()

        # Удаляем автоматически созданный лист
        default_sheet = wb.active
        wb.remove(default_sheet)

        # Стиль шапки
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="334155")
        header_align = Alignment(horizontal="center", vertical="center")

        def add_sheet(name, headers, example=None):
            """Добавляет лист с шапкой и примером."""
            ws = wb.create_sheet(title=name)
            for col, header in enumerate(headers, start=1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_align

            if example:
                for col, value in enumerate(example, start=1):
                    ws.cell(row=2, column=col, value=value)

            # Автоширина столбцов
            for col in range(1, len(headers) + 1):
                ws.column_dimensions[chr(64 + col)].width = 25

            return ws

        # Лист 1. Школа
        add_sheet("Школа",
                  ["Название", "Адрес", "Директор", "Телефон", "Email", "Учебный год"],
                  ["МБОУ СОШ №1", "ул. Ленина, 1", "Иванов И.И.", "+7-999-123-45-67",
                   "school@mail.ru", "2025-2026"])

        # Лист 2. Учителя
        add_sheet("Учителя",
                  ["ФИО", "Телефон", "Email", "Заметки", "Предметы"],
                  ["Иванова А.П.", "+7-999-111-11-11", "iva@mail.ru", "",
                   "Математика, Физика"])

        # Лист 3. Предметы
        add_sheet("Предметы",
                  ["Название", "Сложность"],
                  ["Математика", 10])

        # Лист 4. Классы
        add_sheet("Классы",
                  ["Название", "Учеников", "Смена"],
                  ["5А", 25, 1])

        # Лист 4. Кабинеты
        add_sheet("Кабинеты",
                  ["Номер кабинета", "Спец. предмет", "Мест"],
                  ["101", "", 30])

        # Лист 6. Учебный план
        add_sheet("Учебный план",
                  ["Класс", "Предмет", "Часов", "Учитель"],
                  ["5А", "Математика", 5, "Иванова А.П."])

        # Сохраняем
        wb.save(filepath)
        return True, f"Шаблон сохранён: {filepath}"

    except Exception as e:
        return False, f"Ошибка при создании шаблона: {e}"


if __name__ == "__main__":
    ok, msg = create_template("template.xlsx")
    print(msg)