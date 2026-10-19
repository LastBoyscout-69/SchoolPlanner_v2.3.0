"""
SchoolPlanner — генератор школьного расписания.

Модуль desktop_app.py — точка входа приложения.
"""

import os
import flet as ft

from storage import (
    load_data,
    save_data,
    add_teacher_db,
    update_teacher_name,
    delete_teacher_db,
    add_teacher_subject,
    remove_teacher_subject,
    set_teacher_unavailable,
    add_class_db,
    update_class,
    delete_class_db,
    add_subject_db,
    update_subject_name,
    delete_subject_db,
    set_lesson_hours,
    add_room_db,
    update_room,
    delete_room_db,
    get_lesson_plan_stats,
)
from models import Teacher, SchoolClass, Subject, Room
from scheduler import Scheduler
import license as lic
from excel_export import export_to_excel
from excel_import import import_from_excel
from substitutions import find_substitutes

# Дни недели
DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт"]

# Уроков в день (8)
SLOTS_PER_DAY = 8

# Версия
APP_VERSION = "v2.2.0"

# Палитра цветов для предметов
SUBJECT_COLORS = [
    "#6366f1",
    "#ef4444",
    "#10b981",
    "#f59e0b",
    "#8b5cf6",
    "#06b6d4",
    "#ec4899",
    "#84cc16",
    "#f97316",
    "#14b8a6",
    "#a855f7",
    "#eab308",
]


def main(page: ft.Page):
    """Точка входа Flet-приложения."""

    # Лицензия
    is_activated = lic.is_activated()

    # Настройки окна
    title_suffix = "" if is_activated else " (ДЕМО)"
    page.title = f"SchoolPlanner {APP_VERSION}{title_suffix}"
    page.window.width = 1800
    page.window.height = 1000
    page.window.min_width = 1000
    page.window.min_height = 600
    page.window.left = 80
    page.window.top = 30

    # Тема
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed="#6366f1")

    # Палитра
    BG = "#1e293b"
    ACCENT = "#6366f1"
    ACCENT_2 = "#22d3ee"
    CARD_BG = "#334155"
    CARD_BORDER = "#475569"
    TEXT_MAIN = "#f1f5f9"
    TEXT_MUTED = "#cbd5e1"

    # Загрузка данных
    data = load_data()

    # Состояние расписания
    editable_schedule = []
    selected_lesson = {"obj": None}
    schedule_container = ft.Column(spacing=4)

    def reload_and_render():
        """Перечитывает данные из БД и перерисовывает вкладки."""
        nonlocal data
        data = load_data()
        render_teachers()
        render_classes()
        render_subjects()
        render_rooms()

    # Хелперы

    def subject_color(subject_name):
        """Возвращает HEX-цвет предмета по его индексу."""
        if not subject_name:
            return SUBJECT_COLORS[0]
        for i, s in enumerate(data["subjects"]):
            if s["name"] == subject_name:
                return SUBJECT_COLORS[i % len(SUBJECT_COLORS)]
        return "#64748b"

    def class_badge(name):
        """Метка класса: "10а" → "10а", "Новый" → "Н"."""
        if not name:
            return "?"
        digits, letter = "", ""
        for ch in name:
            if ch.isdigit() and not letter:
                digits += ch
            elif ch.isalpha() and digits and not letter:
                letter = ch
        if digits and letter:
            return f"{digits}{letter}"
        if digits:
            return digits
        return name[:1].upper()

    def teacher_badge(name):
        """Первая буква ФИО учителя."""
        return name[:1].upper() if name else "?"

    def page_title(text, subtitle=""):
        """Заголовок вкладки."""
        col = [ft.Text(text, size=26, weight=ft.FontWeight.BOLD, color=TEXT_MAIN)]
        if subtitle:
            col.append(ft.Text(subtitle, size=13, color=TEXT_MUTED))
        return ft.Column(col, spacing=2)

    def show_snack(message, color="#10b981"):
        """Показывает уведомление внизу экрана."""
        snack = ft.SnackBar(
            content=ft.Text(message, color="white"),
            bgcolor=color,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # Баннер демо-версии

    demo_banner = ft.Container()

    def render_demo_banner():
        """Показывает/скрывает баннер демо-версии."""
        if lic.is_activated():
            demo_banner.content = None
            demo_banner.visible = False
            demo_banner.height = 0
            demo_banner.padding = 0
        else:
            demo_banner.content = ft.Container(
                content=ft.Row(
                    [
                        ft.Text("🔓", size=20),
                        ft.Column(
                            [
                                ft.Text(
                                    "Демо-версия",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color="#fbbf24",
                                ),
                                ft.Text(
                                    f"Ограничение: не более {lic.DEMO_MAX_CLASSES} классов. "
                                    "Введите ключ активации, чтобы снять ограничение.",
                                    size=12,
                                    color="#fde68a",
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.Button(
                            "🔑 Ввести ключ",
                            on_click=open_activation_dialog,
                            style=ft.ButtonStyle(
                                bgcolor="#f59e0b",
                                color="white",
                                padding=ft.Padding.symmetric(
                                    horizontal=20, vertical=12
                                ),
                                shape=ft.RoundedRectangleBorder(radius=8),
                            ),
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor="#78350f",
                border=ft.Border.all(1, "#f59e0b"),
                border_radius=10,
                padding=15,
                margin=ft.Margin.only(left=20, right=20, top=10, bottom=0),
            )
            demo_banner.visible = True
            demo_banner.height = None

        try:
            demo_banner.update()
        except AssertionError:
            pass

    # Диалог активации

    def open_activation_dialog(e):
        """Открывает диалог ввода ключа."""
        key_field = ft.TextField(
            label="Ключ активации",
            hint_text="SP-XXXX-XXXX-XXXX",
            width=400,
            border_color=CARD_BORDER,
            focused_border_color=ACCENT,
            text_size=16,
        )
        status_text = ft.Text("", size=13, color="#ef4444")

        def try_activate(e):
            key = (key_field.value or "").strip().upper()

            if not key:
                status_text.value, status_text.color = "❌ Введите ключ.", "#ef4444"
                status_text.update()
                return

            if not key.startswith("SP-"):
                status_text.value, status_text.color = (
                    "❌ Ключ должен начинаться с SP-",
                    "#ef4444",
                )
                status_text.update()
                return

            if not lic.is_valid_key(key):
                status_text.value = "❌ Неверный ключ. Проверьте и попробуйте снова."
                status_text.color = "#ef4444"
                status_text.update()
                return

            if lic.save_license(key):
                status_text.value, status_text.color = (
                    "✅ Программа активирована!",
                    "#10b981",
                )
                status_text.update()
                dlg.open = False
                page.update()
                render_demo_banner()
                page.title = f"SchoolPlanner {APP_VERSION}"
                page.update()
            else:
                status_text.value, status_text.color = (
                    "❌ Не удалось сохранить ключ.",
                    "#ef4444",
                )
                status_text.update()

        def close_dialog(e):
            dlg.open = False
            page.update()

        key_field.on_submit = try_activate

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("🔑 Активация программы", color=TEXT_MAIN),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Введите ключ активации, который вы получили от разработчика.",
                            color=TEXT_MUTED,
                            size=13,
                        ),
                        ft.Text(
                            "Формат ключа: SP-XXXX-XXXX-XXXX",
                            color=TEXT_MUTED,
                            size=12,
                            italic=True,
                        ),
                        ft.Divider(color=CARD_BORDER),
                        key_field,
                        status_text,
                    ],
                    spacing=10,
                ),
                width=440,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=close_dialog),
                ft.Button(
                    "✅ Активировать",
                    on_click=try_activate,
                    style=ft.ButtonStyle(
                        bgcolor=ACCENT,
                        color="white",
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # Вкладка «Учителя»

    teachers_list = ft.Column(spacing=10)

    def open_slots_dialog(teacher_id, teacher_name, unavailable_slots):
        """Диалог запрещённых слотов для учителя."""
        unavailable = {}
        for item in unavailable_slots:
            if isinstance(item, list) and len(item) >= 2:
                reason = item[2] if len(item) > 2 else ""
                unavailable[(item[0], item[1])] = reason

        grid_container = ft.Column(spacing=4)

        def rebuild_grid():
            grid_container.controls.clear()

            header = ft.Row(
                [
                    ft.Container(width=60, padding=5),
                    *[
                        ft.Container(
                            content=ft.Text(
                                d, weight=ft.FontWeight.BOLD, color=TEXT_MAIN, size=14
                            ),
                            width=170,
                            padding=5,
                            alignment=ft.Alignment.CENTER,
                        )
                        for d in DAY_NAMES
                    ],
                ],
                spacing=4,
            )
            grid_container.controls.append(header)

            for slot in range(8):
                row_cells = [
                    ft.Container(
                        content=ft.Text(str(slot + 1), size=14, color=TEXT_MAIN),
                        width=60,
                        padding=5,
                        alignment=ft.Alignment.CENTER,
                    )
                ]

                for day in range(5):

                    def make_click(d, s):
                        def handler(e):
                            if (d, s) not in unavailable:
                                unavailable[(d, s)] = ""
                                rebuild_grid()
                                try:
                                    grid_container.update()
                                except AssertionError:
                                    pass

                        return handler

                    def make_reason_change(d, s):
                        def handler(e):
                            unavailable[(d, s)] = e.control.value

                        return handler

                    def make_clear(d, s):
                        def handler(e):
                            unavailable.pop((d, s), None)
                            rebuild_grid()
                            try:
                                grid_container.update()
                            except AssertionError:
                                pass

                        return handler

                    if (day, slot) in unavailable:
                        cell = ft.Container(
                            content=ft.Row(
                                [
                                    ft.TextField(
                                        value=unavailable[(day, slot)],
                                        hint_text="Причина…",
                                        text_size=11,
                                        border_color="#ef4444",
                                        focused_border_color="#ef4444",
                                        content_padding=ft.Padding.symmetric(
                                            horizontal=6, vertical=2
                                        ),
                                        on_change=make_reason_change(day, slot),
                                        expand=True,
                                    ),
                                    ft.IconButton(
                                        ft.Icons.CLOSE,
                                        icon_size=14,
                                        icon_color="#ef4444",
                                        on_click=make_clear(day, slot),
                                        width=30,
                                    ),
                                ],
                                spacing=2,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            width=170,
                            height=55,
                            bgcolor="#4a1e1e",
                            border=ft.Border.all(2, "#ef4444"),
                            border_radius=6,
                            padding=4,
                        )
                    else:
                        cell = ft.Container(
                            content=ft.Text("+", size=18, color="#64748b"),
                            width=170,
                            height=55,
                            bgcolor=CARD_BG,
                            border=ft.Border.all(1, CARD_BORDER),
                            border_radius=6,
                            alignment=ft.Alignment.CENTER,
                            on_click=make_click(day, slot),
                            ink=True,
                        )
                    row_cells.append(cell)

                grid_container.controls.append(ft.Row(row_cells, spacing=4))

        rebuild_grid()

        def save_and_close(e):
            slots = [[d, s, reason] for (d, s), reason in unavailable.items()]
            set_teacher_unavailable(teacher_id, slots)
            dlg.open = False
            page.update()
            reload_and_render()

        def close_dialog(e):
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"🚫 Запрещённые слоты: {teacher_name}", color=TEXT_MAIN),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "🚫 Как это работает",
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "• Нажми «+» в клетке, чтобы запретить слот.\n"
                                        "• Введи причину прямо в клетке.\n"
                                        "• Нажми «✖» — чтобы снять запрет.",
                                        size=12,
                                        color=TEXT_MUTED,
                                    ),
                                ],
                                spacing=2,
                            ),
                            bgcolor="#1e3a5f",
                            padding=12,
                            border_radius=8,
                        ),
                        ft.Divider(color=CARD_BORDER),
                        grid_container,
                    ],
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=1050,
                height=700,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=close_dialog),
                ft.Button(
                    "💾 Сохранить",
                    on_click=save_and_close,
                    style=ft.ButtonStyle(
                        bgcolor=ACCENT,
                        color="white",
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def render_teachers():
        """Перерисовывает карточки учителей из SQL."""
        teachers_list.controls.clear()
        all_subjects = [s["name"] for s in data["subjects"]]

        for t in data["teachers"]:
            t_id = t["id"]

            def make_name_submit(tid):
                def handler(e):
                    update_teacher_name(tid, e.control.value)
                    reload_and_render()

                return handler

            def make_del(tid):
                def handler(e):
                    delete_teacher_db(tid)
                    reload_and_render()

                return handler

            def make_subj_selected(tid):
                def handler(e):
                    val = e.control.value
                    if val:
                        add_teacher_subject(tid, val)
                        reload_and_render()
                    e.control.value = None

                return handler

            name_field = ft.TextField(
                value=t["name"],
                label="ФИО (Enter — обновить)",
                width=300,
                on_submit=make_name_submit(t_id),
                border_color=CARD_BORDER,
                focused_border_color=ACCENT,
            )

            subj_dropdown = ft.Dropdown(
                label="➕ Добавить предмет",
                width=280,
                options=[ft.DropdownOption(key=s, text=s) for s in all_subjects],
                on_select=make_subj_selected(t_id),
                border_color=CARD_BORDER,
                focused_border_color=ACCENT,
            )

            chips = ft.Row(spacing=3, wrap=True)
            for s in t["subjects"]:

                def make_remove(tid, subj):
                    def handler(e):
                        remove_teacher_subject(tid, subj)
                        reload_and_render()

                    return handler

                chips.controls.append(
                    ft.Chip(label=ft.Text(s), on_delete=make_remove(t_id, s))
                )

            unavailable_list = t.get("unavailable_slots", [])
            if unavailable_list:
                lines = [f"Запрещённых слотов: {len(unavailable_list)}"]
                for item in unavailable_list[:5]:
                    reason = item[2] if len(item) > 2 and item[2] else ""
                    line = f"• {DAY_NAMES[item[0]]}, {item[1] + 1} урок"
                    if reason:
                        line += f" — {reason}"
                    lines.append(line)
                if len(unavailable_list) > 5:
                    lines.append(f"...и ещё {len(unavailable_list) - 5}")
                tooltip = "\n".join(lines)
            else:
                tooltip = "Запрещённых слотов нет"

            row = ft.Row(
                [
                    ft.Container(
                        content=ft.Text(
                            teacher_badge(t["name"]),
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color="white",
                        ),
                        width=44,
                        height=44,
                        bgcolor=ACCENT,
                        border_radius=22,
                        alignment=ft.Alignment.CENTER,
                    ),
                    name_field,
                    subj_dropdown,
                    ft.Container(
                        content=chips, width=420, padding=ft.Padding.only(left=10)
                    ),
                    ft.IconButton(
                        ft.Icons.BLOCK,
                        icon_color="#f59e0b" if unavailable_list else "#94a3b8",
                        tooltip=("🚫 Запрещённые слоты\n\n" + tooltip),
                        on_click=lambda e, tid=t_id, nm=t[
                            "name"
                        ], u=unavailable_list: open_slots_dialog(tid, nm, u),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE, icon_color="red", on_click=make_del(t_id)
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            )

            teachers_list.controls.append(
                ft.Container(
                    content=row,
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, CARD_BORDER),
                    border_radius=12,
                    padding=15,
                )
            )
        page.update()

    def add_teacher(e):
        """Добавляет учителя в БД."""
        add_teacher_db("Новый")
        reload_and_render()

    # Вкладка «Классы»

    classes_list = ft.Column(spacing=12)

    def render_classes():
        """Перерисовывает карточки классов из SQL."""
        classes_list.controls.clear()

        wrapper = ft.Row(wrap=True, spacing=15, run_spacing=15, expand=True)
        classes_list.controls.append(wrapper)

        for c in data["classes"]:
            c_id = c["id"]

            def make_name_submit(cid):
                def handler(e):
                    update_class(cid, name=e.control.value)
                    reload_and_render()

                return handler

            def make_stud_submit(cid):
                def handler(e):
                    try:
                        update_class(cid, students=int(e.control.value))
                        reload_and_render()
                    except ValueError:
                        pass

                return handler

            def make_del(cid):
                def handler(e):
                    delete_class_db(cid)
                    reload_and_render()

                return handler

            card_content = ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(
                                    class_badge(c["name"]),
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color="white",
                                ),
                                width=50,
                                height=50,
                                bgcolor=ACCENT,
                                border_radius=12,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE,
                                icon_color="red",
                                on_click=make_del(c_id),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.TextField(
                        value=c["name"],
                        label="Название (Enter — обновить)",
                        on_submit=make_name_submit(c_id),
                        border_color=CARD_BORDER,
                        focused_border_color=ACCENT,
                    ),
                    ft.TextField(
                        value=str(c["students"]),
                        label="Учеников (Enter — обновить)",
                        on_submit=make_stud_submit(c_id),
                        border_color=CARD_BORDER,
                        focused_border_color=ACCENT,
                    ),
                ],
                spacing=8,
            )

            wrapper.controls.append(
                ft.Container(
                    content=card_content,
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, CARD_BORDER),
                    border_radius=12,
                    padding=15,
                    width=300,
                )
            )

        page.update()

    def add_class(e):
        """Добавляет класс в БД."""
        add_class_db("Новый", 25)
        reload_and_render()

    # Вкладка «Предметы»

    subjects_list = ft.Column(spacing=5)

    def render_subjects():
        """Перерисовывает карточки предметов из SQL."""
        subjects_list.controls.clear()
        classes = data["classes"]

        for s in data["subjects"]:
            s_id = s["id"]

            def make_name_submit(sid):
                def handler(e):
                    update_subject_name(sid, e.control.value)
                    reload_and_render()

                return handler

            def make_del(sid):
                def handler(e):
                    delete_subject_db(sid)
                    reload_and_render()

                return handler

            hours_inputs = []
            for c in classes:
                c_id = c["id"]
                c_name = c["name"]
                current_hours = s["hours"].get(c_name, 0)

                def make_hours_submit(cid, sid):
                    def handler(e):
                        try:
                            h = int(e.control.value or 0)
                            set_lesson_hours(cid, sid, h)
                            reload_and_render()
                        except ValueError:
                            pass

                    return handler

                hours_inputs.append(
                    ft.Column(
                        [
                            ft.Text(c_name, size=12, color=TEXT_MUTED),
                            ft.TextField(
                                value=str(current_hours),
                                width=70,
                                on_submit=make_hours_submit(c_id, s_id),
                                on_blur=make_hours_submit(c_id, s_id),
                                border_color=CARD_BORDER,
                                focused_border_color=ACCENT,
                            ),
                        ],
                        spacing=2,
                    )
                )

            subjects_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.TextField(
                                        value=s["name"],
                                        label="Предмет (Enter — обновить)",
                                        width=250,
                                        on_submit=make_name_submit(s_id),
                                        border_color=CARD_BORDER,
                                        focused_border_color=ACCENT,
                                    ),
                                    ft.IconButton(
                                        ft.Icons.DELETE,
                                        icon_color="red",
                                        on_click=make_del(s_id),
                                    ),
                                ]
                            ),
                            ft.Row(hours_inputs, wrap=True),
                        ]
                    ),
                    padding=15,
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, CARD_BORDER),
                    border_radius=12,
                    margin=ft.Margin.only(bottom=10),
                )
            )

        page.update()

    def add_subject(e):
        """Добавляет предмет в БД."""
        add_subject_db("Новый предмет")
        reload_and_render()

    # Вкладка «Кабинеты»

    rooms_list = ft.Column(spacing=12)

    def render_rooms():
        """Перерисовывает карточки кабинетов из SQL."""
        rooms_list.controls.clear()

        wrapper = ft.Row(wrap=True, spacing=15, run_spacing=15, expand=True)
        rooms_list.controls.append(wrapper)

        for r in data["rooms"]:
            r_id = r["id"]

            def make_name_submit(rid):
                def handler(e):
                    update_room(rid, name=e.control.value)
                    reload_and_render()

                return handler

            def make_capacity_submit(rid):
                def handler(e):
                    try:
                        update_room(rid, capacity=int(e.control.value))
                        reload_and_render()
                    except ValueError:
                        pass

                return handler

            def make_spec_submit(rid):
                def handler(e):
                    update_room(rid, subject_specific=e.control.value)
                    reload_and_render()

                return handler

            def make_del(rid):
                def handler(e):
                    delete_room_db(rid)
                    reload_and_render()

                return handler

            card_content = ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(ft.Icons.MEETING_ROOM, color="white"),
                                width=50,
                                height=50,
                                bgcolor=ACCENT_2,
                                border_radius=12,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE,
                                icon_color="red",
                                on_click=make_del(r_id),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.TextField(
                        value=r["name"],
                        label="Название (Enter — обновить)",
                        on_submit=make_name_submit(r_id),
                        border_color=CARD_BORDER,
                        focused_border_color=ACCENT,
                    ),
                    ft.TextField(
                        value=str(r["capacity"]),
                        label="Мест (Enter — обновить)",
                        on_submit=make_capacity_submit(r_id),
                        border_color=CARD_BORDER,
                        focused_border_color=ACCENT,
                    ),
                    ft.TextField(
                        value=r["subject_specific"],
                        label="Спец. для предмета (Enter — обновить)",
                        on_submit=make_spec_submit(r_id),
                        border_color=CARD_BORDER,
                        focused_border_color=ACCENT,
                    ),
                ],
                spacing=8,
            )

            wrapper.controls.append(
                ft.Container(
                    content=card_content,
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, CARD_BORDER),
                    border_radius=12,
                    padding=15,
                    width=300,
                )
            )

        page.update()

    def add_room(e):
        """Добавляет кабинет в БД."""
        add_room_db("101", 30, "")
        reload_and_render()

    # Вкладка «Расписание»

    schedule_output = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def find_lesson(class_name, teacher_id, day, slot):
        for l in editable_schedule:
            if class_name is not None:
                if l.class_name == class_name and l.day == day and l.slot == slot:
                    return l
            else:
                if l.teacher_id == teacher_id and l.day == day and l.slot == slot:
                    return l
        return None

    def move_lesson(clicked_lesson, day, slot):
        """Клик по ячейке: выбрать / переместить / поменять."""
        sel = selected_lesson["obj"]

        if clicked_lesson is None:
            if sel is None:
                return
            sel.day, sel.slot = day, slot
            selected_lesson["obj"] = None
        elif sel is None:
            selected_lesson["obj"] = clicked_lesson
        elif sel is clicked_lesson:
            selected_lesson["obj"] = None
        else:
            sel.day, sel.slot, clicked_lesson.day, clicked_lesson.slot = (
                clicked_lesson.day,
                clicked_lesson.slot,
                sel.day,
                sel.slot,
            )
            selected_lesson["obj"] = None

        render_schedule()
        page.update()

    def open_substitution_dialog(lesson):
            """Диалог поиска замены для урока."""
            candidates = find_substitutes(
                data,
                editable_schedule,
                lesson.day,
                lesson.slot,
                lesson.class_name,
                lesson.subject,
                lesson.teacher_id,
            )

            # Имя текущего учителя
            original_name = next(
                (t["name"] for t in data["teachers"] if t["id"] == lesson.teacher_id),
                "—",
            )

            content_controls = [
                ft.Text(
                    f"{lesson.class_name} · {lesson.subject}",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_MAIN,
                ),
                ft.Text(
                    f"{DAY_NAMES[lesson.day]}, {lesson.slot + 1} урок · "
                    f"текущий: {original_name}",
                    size=13,
                    color=TEXT_MUTED,
                ),
                ft.Divider(color=CARD_BORDER),
            ]

            if not candidates:
                content_controls.append(
                    ft.Text(
                        "❌ Свободных учителей с этим предметом нет.",
                        color="#ef4444",
                        size=14,
                    )
                )
            else:
                content_controls.append(
                    ft.Text(
                        f"Кандидатов: {len(candidates)}",
                        size=13,
                        color=TEXT_MUTED,
                    )
                )

                def make_assign(teacher_id, teacher_name):
                    def handler(e):
                        lesson.teacher_id = teacher_id
                        dlg.open = False
                        page.update()
                        render_schedule()
                        page.update()
                        show_snack(f"✅ Замена: {teacher_name}", "#10b981")

                    return handler

                for c in candidates:
                    t = c["teacher"]
                    badges = []
                    if c["already_in_class"]:
                        badges.append(
                            ft.Container(
                                content=ft.Text("уже в классе", size=10, color="white"),
                                bgcolor="#f59e0b",
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                border_radius=10,
                            )
                        )

                    content_controls.append(
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Text(t["name"], size=14, color=TEXT_MAIN, width=250),
                                    ft.Text(
                                        f"нагрузка: {c['current_load']}",
                                        size=12,
                                        color=TEXT_MUTED,
                                    ),
                                    *badges,
                                    ft.Container(expand=True),
                                    ft.Button(
                                        "Назначить",
                                        on_click=make_assign(t["id"], t["name"]),
                                        style=ft.ButtonStyle(
                                            bgcolor=ACCENT,
                                            color="white",
                                            shape=ft.RoundedRectangleBorder(radius=6),
                                        ),
                                    ),
                                ],
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            padding=8,
                            border=ft.Border.all(1, CARD_BORDER),
                            border_radius=8,
                            margin=ft.Margin.only(bottom=4),
                        )
                    )

            def close_dialog(e):
                dlg.open = False
                page.update()

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("🔁 Замена учителя", color=TEXT_MAIN),
                content=ft.Container(
                    content=ft.Column(
                        content_controls,
                        spacing=6,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    width=800,
                    height=500,
                ),
                actions=[
                    ft.TextButton("Отмена", on_click=close_dialog),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )

            page.overlay.append(dlg)
            dlg.open = True
            page.update()


    def make_schedule_header():
        """Шапка таблицы: Урок + дни недели."""
        header_cells = [
            ft.Container(
                content=ft.Text("Урок", weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                expand=1,
                padding=8,
                alignment=ft.Alignment.CENTER,
            )
        ]
        for d in DAY_NAMES:
            header_cells.append(
                ft.Container(
                    content=ft.Text(d, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    expand=3,
                    padding=8,
                    alignment=ft.Alignment.CENTER,
                    bgcolor=CARD_BG,
                    border_radius=6,
                )
            )
        return ft.Row(header_cells, spacing=4)

    def make_lesson_cell(lesson, is_selected, on_click):
        """Ячейка урока: предмет сверху, ФИО слева, каб. справа."""
        border_color = "#facc15" if is_selected else "transparent"
        border_width = 3 if is_selected else 0

        teacher_name = ""
        for t in data["teachers"]:
            if t["id"] == lesson.teacher_id:
                teacher_name = t["name"]
                break

        short_name = teacher_name.split()[0] if teacher_name else ""

        # Фолбэк, если кабинет не найден или room_id == None
        room_label = next(
            (r["name"] for r in data["rooms"] if r["id"] == lesson.room_id),
            "—",
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        lesson.subject,
                        color="white",
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Row(
                        [
                            ft.Text(short_name, color="#e2e8f0", size=13, italic=True),
                            ft.Container(expand=True),
                            ft.Text(f"каб. {room_label}", color="#f1f5f9", size=13),
                            ft.IconButton(
                                ft.Icons.SWAP_HORIZ,
                                icon_size=22,
                                icon_color="#f1f5f9",
                                tooltip="Найти замену",
                                on_click=lambda e, l=lesson: open_substitution_dialog(l),
                                width=28,
                                height=28,
                            ),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),                ],
                spacing=2,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=3,
            padding=8,
            alignment=ft.Alignment.CENTER,
            bgcolor=subject_color(lesson.subject),
            border_radius=8,
            border=ft.Border.all(border_width, border_color),
            on_click=on_click,
            ink=True,
        )

    def make_empty_cell(on_click):
        """Пустая ячейка (прочерк)."""
        return ft.Container(
            content=ft.Text("—", color="#64748b", size=14),
            expand=3,
            padding=8,
            alignment=ft.Alignment.CENTER,
            on_click=on_click,
            ink=True,
        )

    def render_table(items, mode):
        """Рисует таблицу расписания по классам или учителям."""
        for item in items:
            if mode == "class":
                title = f"Класс {item}"
            else:
                title = f"Учитель {item}"
                for t in data["teachers"]:
                    if t["id"] == item:
                        title = t["name"]
                        break

            schedule_container.controls.append(
                ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=TEXT_MAIN)
            )

            rows = [make_schedule_header()]

            for slot in range(SLOTS_PER_DAY):
                row_cells = [
                    ft.Container(
                        content=ft.Text(str(slot + 1), color=TEXT_MAIN),
                        expand=1,
                        padding=8,
                        alignment=ft.Alignment.CENTER,
                    )
                ]

                for day in range(5):
                    if mode == "class":
                        l = find_lesson(item, None, day, slot)
                    else:
                        l = find_lesson(None, item, day, slot)

                    is_selected = selected_lesson["obj"] is l and l is not None

                    def make_click(lesson, d, s):
                        return lambda e: move_lesson(lesson, d, s)

                    if l:
                        row_cells.append(
                            make_lesson_cell(l, is_selected, make_click(l, day, slot))
                        )
                    else:
                        row_cells.append(make_empty_cell(make_click(None, day, slot)))

                rows.append(ft.Row(row_cells, spacing=4))

            schedule_container.controls.append(ft.Column(rows, spacing=4))
            schedule_container.controls.append(ft.Divider(color=CARD_BORDER))

    def render_schedule():
        """Перерисовывает расписание."""
        schedule_container.controls.clear()

        class_names = sorted(set(l.class_name for l in editable_schedule))
        if class_names:
            schedule_container.controls.append(
                ft.Text(
                    "📚 По классам", size=16, weight=ft.FontWeight.BOLD, color=TEXT_MAIN
                )
            )
            render_table(class_names, "class")

        teacher_ids = sorted(set(l.teacher_id for l in editable_schedule))
        if teacher_ids:
            schedule_container.controls.append(
                ft.Text(
                    "👩‍🏫 По учителям",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_MAIN,
                )
            )
            render_table(teacher_ids, "teacher")

    def export_schedule_to_excel(e):
        """Экспорт расписания в Excel."""
        if not editable_schedule:
            show_snack("❌ Сначала составьте расписание!", "#ef4444")
            return

        filepath = os.path.join(os.getcwd(), "Расписание.xlsx")
        ok, message = export_to_excel(editable_schedule, data, filepath)
        show_snack(f"{'✅' if ok else '❌'} {message}", "#10b981" if ok else "#ef4444")

    def build_warnings_block(warnings):
        """Сворачивающийся блок с предупреждениями."""
        if not warnings:
            return ft.Container()

        details = ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text("⚠️", size=14),
                                    ft.Text(
                                        p.title,
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color="#f59e0b",
                                    ),
                                ],
                                spacing=6,
                            ),
                            ft.Text(p.details, size=12, color=TEXT_MUTED),
                        ],
                        spacing=4,
                    ),
                    padding=8,
                    border=ft.Border.all(1, "#f59e0b"),
                    border_radius=8,
                    margin=ft.Margin.only(bottom=4),
                )
                for p in warnings
            ],
            spacing=4,
            visible=False,
        )

        def toggle(e):
            details.visible = not details.visible
            arrow.content = ft.Icon(
                (
                    ft.Icons.KEYBOARD_ARROW_DOWN
                    if not details.visible
                    else ft.Icons.KEYBOARD_ARROW_UP
                ),
                color="#f59e0b",
                size=18,
            )
            try:
                details.update()
                arrow.update()
            except AssertionError:
                pass

        arrow = ft.Container(
            content=ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, color="#f59e0b", size=18),
            on_click=toggle,
            ink=True,
            padding=4,
            border_radius=6,
        )

        header = ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        f"⚠️ {len(warnings)} предупреждений",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color="#f59e0b",
                    ),
                    arrow,
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_click=toggle,
            ink=True,
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            border_radius=8,
        )

        return ft.Column([header, details], spacing=2)

    def render_combine_problem(message):
        """Карточка с проблемой составления и кнопками действий."""
        hints = []
        actions = []

        msg_lower = message.lower()

        if "класс" in msg_lower and "превышает" in msg_lower:
            hints.append("📌 У одного из классов слишком много часов.")
            hints.append("   Норма — не более 40 часов в неделю.")
            actions.append(("🏫 Перейти к классам", 3))
            actions.append(("📚 Перейти к предметам", 4))

        elif "не назначен учитель" in msg_lower:
            hints.append("📌 У одного из предметов нет учителя.")
            actions.append(("👩‍🏫 Перейти к учителям", 2))

        elif "учитель" in msg_lower and "превышает" in msg_lower:
            hints.append("📌 У одного из учителей слишком много часов.")
            hints.append("   Норма — не более 40 уроков в неделю.")
            actions.append(("👩‍🏫 Перейти к учителям", 2))

        elif "кабинет" in msg_lower:
            hints.append("📌 Не хватает кабинетов.")
            actions.append(("🚪 Перейти к кабинетам", 5))

        elif "лимит" in msg_lower or "секунд" in msg_lower:
            hints.append("📌 Алгоритм не нашёл решение за отведённое время.")
            hints.append("   Упростите задачу: уберите лишнюю нагрузку.")
            actions.append(("🧙 Вернуться в мастер", 1))

        else:
            hints.append("📌 Алгоритм не смог найти решение.")
            hints.append("   Проверьте данные вручную.")

        content_controls = [
            ft.Text(
                "🧩 Не удалось составить расписание",
                size=18,
                weight=ft.FontWeight.BOLD,
                color="#ef4444",
            ),
            ft.Text(message, size=13, color=TEXT_MUTED),
            ft.Divider(color=CARD_BORDER),
            ft.Text(
                "Что можно сделать:",
                size=14,
                weight=ft.FontWeight.BOLD,
                color=TEXT_MAIN,
            ),
        ]

        for hint in hints:
            content_controls.append(ft.Text(hint, size=13, color=TEXT_MAIN))

        if actions:
            content_controls.append(ft.Divider(color=CARD_BORDER))
            content_controls.append(
                ft.Text(
                    "Быстрый переход:",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_MAIN,
                )
            )

            buttons = []
            for label, tab_index in actions:

                def make_handler(idx):
                    def handler(e):
                        try:
                            tabs.selected_index = idx
                            page.update()
                        except Exception:
                            pass

                    return handler

                buttons.append(
                    ft.Button(
                        label,
                        on_click=make_handler(tab_index),
                        style=ft.ButtonStyle(
                            bgcolor=ACCENT,
                            color="white",
                            padding=ft.Padding.symmetric(horizontal=15, vertical=10),
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                    )
                )

            content_controls.append(ft.Row(buttons, spacing=10, wrap=True))

        return ft.Container(
            content=ft.Column(content_controls, spacing=10),
            bgcolor=CARD_BG,
            border=ft.Border.all(2, "#ef4444"),
            border_radius=10,
            padding=20,
        )

    def check_demo_limit():
        """Проверяет демо-лимит. True — можно продолжать."""
        if lic.is_activated():
            return True

        if len(data["classes"]) <= lic.DEMO_MAX_CLASSES:
            return True

        schedule_output.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "🔓 Демо-версия",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color="#fbbf24",
                        ),
                        ft.Text(
                            f"В демо-версии можно составить расписание "
                            f"не более чем для {lic.DEMO_MAX_CLASSES} классов.\n"
                            f"Сейчас у вас классов: {len(data['classes'])}.\n\n"
                            f"Чтобы снять ограничение, введите ключ активации.",
                            size=13,
                            color="#fde68a",
                        ),
                        ft.Button(
                            "🔑 Ввести ключ активации",
                            on_click=open_activation_dialog,
                            style=ft.ButtonStyle(
                                bgcolor="#f59e0b",
                                color="white",
                                padding=ft.Padding.symmetric(
                                    horizontal=20, vertical=12
                                ),
                                shape=ft.RoundedRectangleBorder(radius=8),
                            ),
                        ),
                    ],
                    spacing=10,
                ),
                bgcolor="#78350f",
                border=ft.Border.all(1, "#f59e0b"),
                border_radius=10,
                padding=20,
            )
        )
        page.update()
        return False

    def build_schedule(e):
        """Составляет расписание через OR-Tools."""
        schedule_output.controls.clear()
        selected_lesson["obj"] = None
        # Переключаемся на вкладку «Расписание»
        try:
            tabs.selected_index = 0
            page.update()
        except Exception:
            pass

        if not check_demo_limit():
            return

        from advisor import analyze

        problems = analyze(data)

        errors = [p for p in problems if p.severity == "error"]
        warnings = [p for p in problems if p.severity == "warning"]

        schedule_output.controls.append(
            ft.Row(
                [
                    ft.Text(
                        "🔍 Анализ данных",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_MAIN,
                    ),
                    ft.Container(
                        content=ft.Text(
                            f"{len(errors)} ошибок · {len(warnings)} предупреждений",
                            size=12,
                            color="white",
                        ),
                        bgcolor=(
                            "#ef4444"
                            if errors
                            else ("#f59e0b" if warnings else "#10b981")
                        ),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                        border_radius=20,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

        for p in problems:
            if p.severity != "error":
                continue
            block_controls = [
                ft.Row(
                    [
                        ft.Text("❌", size=18),
                        ft.Text(
                            p.title, size=16, weight=ft.FontWeight.BOLD, color="#ef4444"
                        ),
                    ],
                    spacing=8,
                ),
                ft.Text(p.details, size=13, color=TEXT_MUTED),
            ]
            if p.recommendations:
                block_controls.append(
                    ft.Column(
                        [
                            ft.Text(f"💡 {r}", size=13, color=TEXT_MAIN)
                            for r in p.recommendations
                        ],
                        spacing=4,
                    )
                )

            schedule_output.controls.append(
                ft.Container(
                    content=ft.Column(block_controls, spacing=8),
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, "#ef4444"),
                    border_radius=10,
                    padding=15,
                    margin=ft.Margin.only(bottom=8),
                )
            )

        if errors:
            schedule_output.controls.append(
                ft.Container(
                    content=ft.Text(
                        "⚠️ Исправь ошибки выше и нажми «Составить» снова.",
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color="#ef4444",
                    ),
                    padding=15,
                )
            )
            page.update()
            return

        schedule_output.controls.append(ft.Divider(color=CARD_BORDER, height=20))

        teachers = [
            Teacher(
                t["id"],
                t["name"],
                t["subjects"],
                [tuple(x) for x in t.get("unavailable_slots", [])],
            )
            for t in data["teachers"]
            if t["subjects"]
        ]
        classes = [
            SchoolClass(c["id"], c["name"], c["students"]) for c in data["classes"]
        ]
        subjects = [
            Subject(s["name"], s["hours"], s.get("teachers", {}))
            for s in data["subjects"]
        ]
        rooms = [
            Room(r["id"], r["name"], r["capacity"], r["subject_specific"] or None)
            for r in data["rooms"]
        ]

        if not teachers or not classes or not subjects or not rooms:
            schedule_output.controls.append(
                ft.Text(
                    "Заполни все разделы: учителя, классы, предметы, кабинеты.",
                    color="red",
                    size=16,
                )
            )
            page.update()
            return

        scheduler = Scheduler(teachers, classes, subjects, rooms)
        ok, message = scheduler.solve()

        if not ok:
            schedule_output.controls.append(render_combine_problem(message))
            page.update()
            return

        editable_schedule.clear()
        editable_schedule.extend(scheduler.schedule)

        # ---------- ПРОВЕРКА КАБИНЕТОВ ----------
        room_conflicts = []
        busy_rooms_check = {}

        for l in editable_schedule:
            key = (l.day, l.slot, l.room_id)
            if key in busy_rooms_check:
                # Нашли накладку! Запоминаем, кто и где пересекся
                room_name = next(
                    (r["name"] for r in data["rooms"] if r["id"] == l.room_id),
                    str(l.room_id),
                )
                day_name = DAY_NAMES[l.day]
                room_conflicts.append(
                    f"{day_name}, {l.slot + 1} урок: каб. {room_name} (класс {l.class_name})"
                )
            else:
                busy_rooms_check[key] = True

        # ---------- ФОРМИРУЕМ ЗАГОЛОВОК ----------
        header_row = [ft.Text("✅ Расписание составлено!", color="green", size=18)]

        if not room_conflicts:
            header_row.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE, color="#10b981", size=16
                            ),
                            ft.Text(
                                "Кабинеты в порядке",
                                color="#10b981",
                                size=13,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                        spacing=5,
                    ),
                    bgcolor="#064e3b",
                    padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                    border_radius=8,
                )
            )
        else:
            header_row.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.ERROR, color="#ef4444", size=16),
                            ft.Text(
                                f"Накладки в кабинетах: {len(room_conflicts)}",
                                color="#ef4444",
                                size=13,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                        spacing=5,
                    ),
                    bgcolor="#450a0a",
                    padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                    border_radius=8,
                )
            )

        # Предупреждения (было в старом коде)
        if warnings:
            header_row.append(build_warnings_block(warnings))

        header_row.append(
            ft.Text(
                "(клик по уроку → клик по клетке — переместить)",
                color=TEXT_MUTED,
                size=12,
            )
        )

        schedule_output.controls.append(
            ft.Row(
                header_row,
                spacing=15,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

        # Если есть накладки — выводим их списком
        if room_conflicts:
            conflict_rows = [
                ft.Text(c, color="#ef4444", size=12) for c in room_conflicts[:10]
            ]
            if len(room_conflicts) > 10:
                conflict_rows.append(
                    ft.Text(
                        f"...и ещё {len(room_conflicts) - 10}",
                        color="#ef4444",
                        size=12,
                        italic=True,
                    )
                )

            schedule_output.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "❌ Детали накладок:",
                                color="#ef4444",
                                weight=ft.FontWeight.BOLD,
                                size=14,
                            ),
                            *conflict_rows,
                        ],
                        spacing=4,
                    ),
                    bgcolor="#450a0a",
                    padding=15,
                    border_radius=10,
                    margin=ft.Margin.only(bottom=20),
                )
            )

        all_subj_names = sorted(set(l.subject for l in editable_schedule))
        if all_subj_names:
            legend_items = [
                ft.Row(
                    [
                        ft.Container(
                            width=12,
                            height=12,
                            bgcolor=subject_color(sname),
                            border_radius=3,
                        ),
                        ft.Text(sname, color=TEXT_MUTED, size=11),
                    ],
                    spacing=4,
                )
                for sname in all_subj_names
            ]
            schedule_output.controls.append(
                ft.Container(
                    content=ft.Row(legend_items, spacing=15, wrap=True),
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, CARD_BORDER),
                    border_radius=8,
                    padding=10,
                    margin=ft.Margin.only(top=8, bottom=10),
                )
            )

        schedule_output.controls.append(schedule_container)
        render_schedule()

        page.update()

    # Мастер

    wizard_state = {"step": 1}

    WIZARD_STEPS = [
        "1. Школа",
        "2. Учителя",
        "3. Классы",
        "4. Предметы",
        "5. Кабинеты",
        "6. Учебный план",
        "7. Составление",
    ]

    wizard_content = ft.Column(spacing=15, expand=True)
    wizard_progress = ft.Row(
        spacing=4, wrap=True, alignment=ft.MainAxisAlignment.CENTER
    )

    def render_wizard_progress():
        """Рисует верхнюю панель с шагами — кликабельные."""
        wizard_progress.controls.clear()
        current = wizard_state["step"]
        statuses = check_wizard_statuses()

        for i, name in enumerate(WIZARD_STEPS, start=1):
            status = statuses.get(i, "empty")

            if i == current:
                color = ACCENT
                text_color = "white"
            elif status == "ok":
                color = "#10b981"
                text_color = "white"
            elif status == "warning":
                color = "#f59e0b"
                text_color = "white"
            else:
                color = "#ef4444"
                text_color = "white"

            # Кликабельная кнопка-шаг
            def make_click(step_num):
                def handler(e):
                    go_to_step(step_num)

                return handler

            wizard_progress.controls.append(
                ft.Container(
                    content=ft.Text(
                        name, size=13, color=text_color, weight=ft.FontWeight.BOLD
                    ),
                    bgcolor=color,
                    padding=ft.Padding.symmetric(horizontal=15, vertical=10),
                    border_radius=8,
                    on_click=make_click(i),
                    ink=True,
                    tooltip=f"Перейти к шагу {i}",
                )
            )

            if i < len(WIZARD_STEPS):
                wizard_progress.controls.append(
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.ARROW_FORWARD, color=TEXT_MUTED, size=16
                        ),
                        padding=ft.Padding.symmetric(horizontal=2),
                    )
                )

    def check_wizard_statuses():
        """Проверяет статус каждого шага мастера."""
        statuses = {}

        # Шаг 1: Школа
        school = data.get("school", {})
        statuses[1] = "ok" if school.get("name") else "empty"

        # Шаг 2: Учителя
        teachers = data["teachers"]
        if not teachers:
            statuses[2] = "empty"
        else:
            has_problems = any(not t.get("subjects") for t in teachers)
            statuses[2] = "warning" if has_problems else "ok"

        # Шаг 3: Классы
        classes = data["classes"]
        if not classes:
            statuses[3] = "empty"
        else:
            has_problems = any(c.get("students", 0) <= 0 for c in classes)
            statuses[3] = "warning" if has_problems else "ok"

        # Шаг 4: Предметы
        subjects = data["subjects"]
        if not subjects:
            statuses[4] = "empty"
        else:
            has_problems = False
            for s in subjects:
                has_teacher = any(
                    s["name"] in t.get("subjects", []) for t in data["teachers"]
                )
                total_hours = sum(s.get("hours", {}).values())
                if not has_teacher or total_hours == 0:
                    has_problems = True
                    break
            statuses[4] = "warning" if has_problems else "ok"

        # Шаг 5: Кабинеты
        rooms = data["rooms"]
        if not rooms:
            statuses[5] = "empty"
        else:
            has_problems = any(r.get("capacity", 0) <= 0 for r in rooms)
            statuses[5] = "warning" if has_problems else "ok"

        # Шаг 6: Учебный план
        stats = get_lesson_plan_stats()
        if stats["total_rows"] == 0:
            statuses[6] = "empty"
        elif (
            stats["too_many_hours"]
            or stats["classes_with_plan"] < stats["classes_total"]
        ):
            statuses[6] = "warning"
        else:
            statuses[6] = "ok"

        # Шаг 7
        statuses[7] = "ok"

        return statuses

    def go_to_step(step):
        """Переключение шага мастера."""
        if 1 <= step <= 7:
            wizard_state["step"] = step
        render_wizard_progress()
        render_wizard()
        try:
            wizard_progress.update()
        except AssertionError:
            pass

    def render_wizard():
        """Перерисовывает содержимое текущего шага."""
        wizard_content.controls.clear()
        step = wizard_state["step"]

        wizard_content.controls.append(
            ft.Text(
                WIZARD_STEPS[step - 1],
                size=22,
                weight=ft.FontWeight.BOLD,
                color=TEXT_MAIN,
            )
        )

        # Шаг 1: Школа
        if step == 1:
            school = data.get("school", {})
            is_filled = bool(school.get("name"))
            status_text = "✅ Заполнено" if is_filled else "⚠️ Не заполнено"
            status_color = "#10b981" if is_filled else "#f59e0b"

            fields = [
                ("Название", school.get("name", "")),
                ("Адрес", school.get("address", "")),
                ("Директор", school.get("director", "")),
                ("Телефон", school.get("phone", "")),
                ("Email", school.get("email", "")),
                ("Учебный год", school.get("academic_year", "")),
            ]

            info_rows = []
            for label, value in fields:
                info_rows.append(
                    ft.Row(
                        [
                            ft.Text(f"{label}:", width=120, color=TEXT_MUTED, size=13),
                            ft.Text(value or "—", color=TEXT_MAIN, size=13),
                        ],
                        spacing=10,
                    )
                )

            wizard_content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        "Информация о школе",
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            status_text, size=12, color="white"
                                        ),
                                        bgcolor=status_color,
                                        padding=ft.Padding.symmetric(
                                            horizontal=10, vertical=4
                                        ),
                                        border_radius=20,
                                    ),
                                ],
                                spacing=15,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Divider(color=CARD_BORDER),
                            *info_rows,
                        ],
                        spacing=8,
                    ),
                    padding=20,
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, CARD_BORDER),
                    border_radius=10,
                )
            )

        # Шаг 2: Учителя
        elif step == 2:
            teachers = data["teachers"]
            count = len(teachers)

            problems = []
            for t in teachers:
                if not t.get("subjects"):
                    problems.append(f"У {t['name']} нет предметов")

            is_ok = count > 0 and not problems
            n = len(problems)
            word = "проблема" if n == 1 else ("проблемы" if 2 <= n <= 4 else "проблем")
            status_text = "✅ Всё ок" if is_ok else f"⚠️ {n} {word}"
            status_color = "#10b981" if is_ok else "#f59e0b"

            rows = []
            for t in teachers[:10]:
                rows.append(
                    ft.Row(
                        [
                            ft.Text(t["name"], color=TEXT_MAIN, size=13, width=200),
                            ft.Text(
                                ", ".join(t["subjects"]) or "—",
                                color=TEXT_MUTED,
                                size=12,
                            ),
                        ],
                        spacing=10,
                    )
                )

            problem_rows = [
                ft.Text(f"⚠️ {p}", color="#f59e0b", size=12) for p in problems[:5]
            ]

            wizard_content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        f"Учителей: {count}",
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            status_text, size=12, color="white"
                                        ),
                                        bgcolor=status_color,
                                        padding=ft.Padding.symmetric(
                                            horizontal=10, vertical=4
                                        ),
                                        border_radius=20,
                                    ),
                                ],
                                spacing=15,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Divider(color=CARD_BORDER),
                            *rows,
                            *problem_rows,
                        ],
                        spacing=6,
                    ),
                    padding=20,
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, CARD_BORDER),
                    border_radius=10,
                )
            )

        # Шаг 3: Классы
        elif step == 3:
            classes = data["classes"]
            count = len(classes)

            problems = []
            for c in classes:
                if c.get("students", 0) <= 0:
                    problems.append(f"У класса «{c['name']}» не указано число учеников")

            is_ok = count > 0 and not problems
            n = len(problems)
            word = "проблема" if n == 1 else ("проблемы" if 2 <= n <= 4 else "проблем")
            status_text = "✅ Всё ок" if is_ok else f"⚠️ {n} {word}"
            status_color = "#10b981" if is_ok else "#f59e0b"

            rows = []
            for c in classes[:15]:
                rows.append(
                    ft.Row(
                        [
                            ft.Text(c["name"], color=TEXT_MAIN, size=13, width=100),
                            ft.Text(
                                f"{c.get('students', 0)} учеников",
                                color=TEXT_MUTED,
                                size=12,
                            ),
                        ],
                        spacing=10,
                    )
                )

            problem_rows = [
                ft.Text(f"⚠️ {p}", color="#f59e0b", size=12) for p in problems[:5]
            ]

            wizard_content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        f"Классов: {count}",
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            status_text, size=12, color="white"
                                        ),
                                        bgcolor=status_color,
                                        padding=ft.Padding.symmetric(
                                            horizontal=10, vertical=4
                                        ),
                                        border_radius=20,
                                    ),
                                ],
                                spacing=15,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Divider(color=CARD_BORDER),
                            *rows,
                            *problem_rows,
                        ],
                        spacing=6,
                    ),
                    padding=20,
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, CARD_BORDER),
                    border_radius=10,
                )
            )

        # Шаг 4: Предметы
        elif step == 4:
            subjects = data["subjects"]
            count = len(subjects)

            problems = []
            for s in subjects:
                has_teacher = any(
                    s["name"] in t.get("subjects", []) for t in data["teachers"]
                )
                if not has_teacher:
                    problems.append(f"У предмета «{s['name']}» нет учителя")

                total_hours = sum(s.get("hours", {}).values())
                if total_hours == 0:
                    problems.append(f"У предмета «{s['name']}» нет часов")

            is_ok = count > 0 and not problems
            n = len(problems)
            word = "проблема" if n == 1 else ("проблемы" if 2 <= n <= 4 else "проблем")
            status_text = "✅ Всё ок" if is_ok else f"⚠️ {n} {word}"
            status_color = "#10b981" if is_ok else "#f59e0b"

            rows = []
            for s in subjects[:10]:
                total_hours = sum(s.get("hours", {}).values())
                has_teacher = any(
                    s["name"] in t.get("subjects", []) for t in data["teachers"]
                )
                teacher_status = "✅" if has_teacher else "❌"
                rows.append(
                    ft.Row(
                        [
                            ft.Text(teacher_status, size=14, width=25),
                            ft.Text(s["name"], color=TEXT_MAIN, size=13, width=200),
                            ft.Text(f"{total_hours} ч/нед", color=TEXT_MUTED, size=12),
                        ],
                        spacing=8,
                    )
                )

            problem_rows = [
                ft.Text(f"⚠️ {p}", color="#f59e0b", size=12) for p in problems[:8]
            ]

            wizard_content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        f"Предметов: {count}",
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            status_text, size=12, color="white"
                                        ),
                                        bgcolor=status_color,
                                        padding=ft.Padding.symmetric(
                                            horizontal=10, vertical=4
                                        ),
                                        border_radius=20,
                                    ),
                                ],
                                spacing=15,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Divider(color=CARD_BORDER),
                            *rows,
                            *problem_rows,
                        ],
                        spacing=6,
                    ),
                    padding=20,
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, CARD_BORDER),
                    border_radius=10,
                )
            )

        # Шаг 5: Кабинеты
        elif step == 5:
            rooms = data["rooms"]
            count = len(rooms)

            problems = []
            for r in rooms:
                if r.get("capacity", 0) <= 0:
                    problems.append(f"У кабинета {r['name']} не указана вместимость")

            is_ok = count > 0 and not problems
            n = len(problems)
            word = "проблема" if n == 1 else ("проблемы" if 2 <= n <= 4 else "проблем")
            status_text = "✅ Всё ок" if is_ok else f"⚠️ {n} {word}"
            status_color = "#10b981" if is_ok else "#f59e0b"

            rows = []
            for r in rooms[:15]:
                spec = r.get("subject_specific", "")
                spec_text = f"  ({spec})" if spec else ""
                rows.append(
                    ft.Row(
                        [
                            ft.Text(r["name"], color=TEXT_MAIN, size=13, width=100),
                            ft.Text(
                                f"{r.get('capacity', 0)} мест{spec_text}",
                                color=TEXT_MUTED,
                                size=12,
                            ),
                        ],
                        spacing=10,
                    )
                )

            problem_rows = [
                ft.Text(f"⚠️ {p}", color="#f59e0b", size=12) for p in problems[:5]
            ]

            wizard_content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        f"Кабинетов: {count}",
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            status_text, size=12, color="white"
                                        ),
                                        bgcolor=status_color,
                                        padding=ft.Padding.symmetric(
                                            horizontal=10, vertical=4
                                        ),
                                        border_radius=20,
                                    ),
                                ],
                                spacing=15,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Divider(color=CARD_BORDER),
                            *rows,
                            *problem_rows,
                        ],
                        spacing=6,
                    ),
                    padding=20,
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, CARD_BORDER),
                    border_radius=10,
                )
            )

        # Шаг 6: Учебный план
        elif step == 6:
            stats = get_lesson_plan_stats()

            total = stats["total_rows"]
            classes_with = stats["classes_with_plan"]
            classes_total = stats["classes_total"]
            max_h = stats["max_hours"]
            too_many = stats["too_many_hours"]
            assigned = stats["teachers_assigned"]

            if total == 0:
                status_text = "❌ План не загружен"
                status_color = "#ef4444"
            elif too_many:
                status_text = f"⚠️ {len(too_many)} классов с перегрузом"
                status_color = "#f59e0b"
            elif classes_with < classes_total:
                missing = classes_total - classes_with
                status_text = f"⚠️ {missing} классов без плана"
                status_color = "#f59e0b"
            else:
                status_text = "✅ Всё ок"
                status_color = "#10b981"

            info_rows = [
                ft.Row(
                    [
                        ft.Text("Строк в плане:", width=200, color=TEXT_MUTED, size=13),
                        ft.Text(str(total), color=TEXT_MAIN, size=13),
                    ],
                    spacing=10,
                ),
                ft.Row(
                    [
                        ft.Text(
                            "Классов с планом:", width=200, color=TEXT_MUTED, size=13
                        ),
                        ft.Text(
                            f"{classes_with} из {classes_total}",
                            color=TEXT_MAIN,
                            size=13,
                        ),
                    ],
                    spacing=10,
                ),
                ft.Row(
                    [
                        ft.Text(
                            "Максимум часов у класса:",
                            width=200,
                            color=TEXT_MUTED,
                            size=13,
                        ),
                        ft.Text(f"{max_h} (норма ≤ 40)", color=TEXT_MAIN, size=13),
                    ],
                    spacing=10,
                ),
                ft.Row(
                    [
                        ft.Text(
                            "Строк с учителем:", width=200, color=TEXT_MUTED, size=13
                        ),
                        ft.Text(f"{assigned} из {total}", color=TEXT_MAIN, size=13),
                    ],
                    spacing=10,
                ),
            ]

            problem_rows = []
            if too_many:
                problem_rows.append(
                    ft.Text(
                        f"⚠️ Перегруз у классов: {', '.join(too_many)}",
                        color="#f59e0b",
                        size=12,
                    )
                )

            def do_import(e):
                ok, msg = import_from_excel("template.xlsx")
                if ok:
                    show_snack(f"✅ {msg}", "#10b981")
                    reload_and_render()
                    render_wizard_progress()
                    render_wizard()
                else:
                    show_snack(f"❌ {msg}", "#ef4444")

            import_button = ft.Button(
                "📥 Импорт из Excel",
                on_click=do_import,
                style=ft.ButtonStyle(
                    bgcolor="#10b981",
                    color="white",
                    padding=ft.Padding.symmetric(horizontal=20, vertical=14),
                    shape=ft.RoundedRectangleBorder(radius=10),
                ),
            )

            wizard_content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        "Статистика учебного плана",
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            status_text, size=12, color="white"
                                        ),
                                        bgcolor=status_color,
                                        padding=ft.Padding.symmetric(
                                            horizontal=10, vertical=4
                                        ),
                                        border_radius=20,
                                    ),
                                ],
                                spacing=15,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Divider(color=CARD_BORDER),
                            *info_rows,
                            *problem_rows,
                            ft.Divider(color=CARD_BORDER),
                            ft.Text(
                                "Файл должен лежать рядом с программой: template.xlsx",
                                color=TEXT_MUTED,
                                size=12,
                                italic=True,
                            ),
                            import_button,
                        ],
                        spacing=10,
                    ),
                    padding=20,
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, CARD_BORDER),
                    border_radius=10,
                )
            )

        # Шаг 7: Составление
        else:
            statuses = check_wizard_statuses()
            empty_steps = [i for i, s in statuses.items() if s == "empty" and i < 7]
            warning_steps = [i for i, s in statuses.items() if s == "warning" and i < 7]

            if empty_steps:
                ready_text = f"❌ Не готово: шаги {', '.join(map(str, empty_steps))} не заполнены"
                ready_color = "#ef4444"
            elif warning_steps:
                ready_text = f"⚠️ Можно составить, но есть проблемы на шагах {', '.join(map(str, warning_steps))}"
                ready_color = "#f59e0b"
            else:
                ready_text = "✅ Всё готово к составлению!"
                ready_color = "#10b981"

            summary = [
                ("Школа", data.get("school", {}).get("name") or "—"),
                ("Учителей", str(len(data["teachers"]))),
                ("Классов", str(len(data["classes"]))),
                ("Предметов", str(len(data["subjects"]))),
                ("Кабинетов", str(len(data["rooms"]))),
            ]

            summary_rows = []
            for label, value in summary:
                summary_rows.append(
                    ft.Row(
                        [
                            ft.Text(f"{label}:", width=120, color=TEXT_MUTED, size=13),
                            ft.Text(value, color=TEXT_MAIN, size=13),
                        ],
                        spacing=10,
                    )
                )

            wizard_content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        "Готовность к составлению",
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            ready_text, size=12, color="white"
                                        ),
                                        bgcolor=ready_color,
                                        padding=ft.Padding.symmetric(
                                            horizontal=10, vertical=4
                                        ),
                                        border_radius=20,
                                    ),
                                ],
                                spacing=15,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Divider(color=CARD_BORDER),
                            *summary_rows,
                            ft.Divider(color=CARD_BORDER),
                            ft.Text(
                                "Нажмите «Составить расписание» — алгоритм начнёт работу.",
                                color=TEXT_MUTED,
                                size=13,
                            ),
                        ],
                        spacing=8,
                    ),
                    padding=20,
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, CARD_BORDER),
                    border_radius=10,
                )
            )

        # Кнопки навигации
        nav_buttons = []
        if step > 1:
            nav_buttons.append(
                ft.Button(
                    "← Назад",
                    on_click=lambda e: go_to_step(step - 1),
                    style=ft.ButtonStyle(
                        bgcolor=CARD_BG,
                        color=TEXT_MAIN,
                        padding=ft.Padding.symmetric(horizontal=20, vertical=14),
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                )
            )

        if step < 7:
            nav_buttons.append(
                ft.Button(
                    "Далее →",
                    on_click=lambda e: go_to_step(step + 1),
                    style=ft.ButtonStyle(
                        bgcolor=ACCENT,
                        color="white",
                        padding=ft.Padding.symmetric(horizontal=20, vertical=14),
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                )
            )
        else:
            nav_buttons.append(
                ft.Button(
                    "🚀 Составить расписание",
                    on_click=build_schedule,
                    style=ft.ButtonStyle(
                        bgcolor="#10b981",
                        color="white",
                        padding=ft.Padding.symmetric(horizontal=24, vertical=18),
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                )
            )

        wizard_content.controls.append(
            ft.Row(nav_buttons, spacing=10, alignment=ft.MainAxisAlignment.END)
        )

        try:
            wizard_content.update()
        except AssertionError:
            pass

    # Вкладки

    def make_tab_content(title, subtitle, button_text, on_click, content):
        """Универсальная вкладка."""
        return ft.Container(
            content=ft.Column(
                [
                    page_title(title, subtitle),
                    ft.Button(
                        button_text,
                        on_click=on_click,
                        style=ft.ButtonStyle(
                            bgcolor=ACCENT,
                            color="white",
                            padding=ft.Padding.symmetric(horizontal=20, vertical=14),
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                    ),
                    content,
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=30,
            expand=True,
            bgcolor=BG,
        )

    tabs = ft.Tabs(
        length=7,
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.Container(
                    content=ft.TabBar(
                        tabs=[
                            ft.Tab(label="📅 Расписание"),
                            ft.Tab(label="🧙 Мастер"),
                            ft.Tab(label="👩‍🏫 Учителя"),
                            ft.Tab(label="🏫 Классы"),
                            ft.Tab(label="📚 Предметы"),
                            ft.Tab(label="🚪 Кабинеты"),
                            ft.Tab(label="❓ Справка"),
                        ]
                    ),
                    bgcolor=CARD_BG,
                    padding=ft.Padding.symmetric(horizontal=20, vertical=8),
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        # Расписание
                        ft.Container(
                            content=ft.Column(
                                [
                                    page_title(
                                        "Расписание",
                                        "Составь и посмотри готовое расписание",
                                    ),
                                    ft.Row(
                                        [
                                            ft.Button(
                                                "🚀 Составить расписание",
                                                on_click=build_schedule,
                                                style=ft.ButtonStyle(
                                                    bgcolor=ACCENT,
                                                    color="white",
                                                    padding=ft.Padding.symmetric(
                                                        horizontal=24, vertical=18
                                                    ),
                                                    shape=ft.RoundedRectangleBorder(
                                                        radius=10
                                                    ),
                                                ),
                                            ),
                                            ft.Button(
                                                "📊 Экспорт в Excel",
                                                on_click=export_schedule_to_excel,
                                                style=ft.ButtonStyle(
                                                    bgcolor="#10b981",
                                                    color="white",
                                                    padding=ft.Padding.symmetric(
                                                        horizontal=24, vertical=18
                                                    ),
                                                    shape=ft.RoundedRectangleBorder(
                                                        radius=10
                                                    ),
                                                ),
                                            ),
                                        ],
                                        spacing=15,
                                    ),
                                    schedule_output,
                                ],
                                expand=True,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            padding=30,
                            expand=True,
                            bgcolor=BG,
                        ),
                        # Мастер
                        ft.Container(
                            content=ft.Column(
                                [
                                    page_title(
                                        "Мастер расписания",
                                        "Пошаговое составление с проверками",
                                    ),
                                    ft.Container(
                                        content=wizard_progress,
                                        padding=ft.Padding.only(bottom=20),
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    wizard_content,
                                ],
                                expand=True,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            padding=30,
                            expand=True,
                            bgcolor=BG,
                        ),
                        # Учителя
                        make_tab_content(
                            "Учителя",
                            "Список и предметы",
                            "➕ Добавить учителя",
                            add_teacher,
                            teachers_list,
                        ),
                        # Классы
                        make_tab_content(
                            "Классы",
                            "Классы и количество учеников",
                            "➕ Добавить класс",
                            add_class,
                            classes_list,
                        ),
                        # Предметы
                        ft.Container(
                            content=ft.Column(
                                [
                                    page_title(
                                        "Предметы", "Нагрузка в часах по классам"
                                    ),
                                    # Кнопка «Добавить» — обратно вверх
                                    ft.Button(
                                        "➕ Добавить предмет",
                                        on_click=add_subject,
                                        style=ft.ButtonStyle(
                                            bgcolor=ACCENT,
                                            color="white",
                                            padding=ft.Padding.symmetric(
                                                horizontal=20, vertical=14
                                            ),
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                        ),
                                    ),
                                    # Подсказка про Enter
                                    ft.Container(
                                        content=ft.Row(
                                            [
                                                ft.Icon(
                                                    ft.Icons.KEYBOARD,
                                                    color="#fbbf24",
                                                    size=22,
                                                ),
                                                ft.Column(
                                                    [
                                                        ft.Text(
                                                            "Как сохранить часы",
                                                            size=14,
                                                            weight=ft.FontWeight.BOLD,
                                                            color="#fbbf24",
                                                        ),
                                                        ft.Text(
                                                            "Введи число и нажми Enter. "
                                                            "Tab переключает вкладки, а не поля.",
                                                            size=13,
                                                            color="#fde68a",
                                                        ),
                                                    ],
                                                    spacing=2,
                                                    expand=True,
                                                ),
                                            ],
                                            spacing=12,
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        ),
                                        bgcolor="#78350f",
                                        border=ft.Border.all(2, "#f59e0b"),
                                        border_radius=10,
                                        padding=15,
                                        margin=ft.Margin.only(top=10, bottom=15),
                                    ),
                                    subjects_list,
                                ],
                                expand=True,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            padding=30,
                            expand=True,
                            bgcolor=BG,
                        ),
                        # Кабинеты
                        make_tab_content(
                            "Кабинеты",
                            "Аудитории и вместимость",
                            "➕ Добавить кабинет",
                            add_room,
                            rooms_list,
                        ),
                        # Справка
                        ft.Container(
                            content=ft.Column(
                                [
                                    page_title("Справка", "Правила и ограничения"),
                                    ft.Text(
                                        "Ниже — что можно и нельзя делать.",
                                        color=TEXT_MUTED,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "🚀 Быстрый старт",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "1. Заполните данные одним из способов:\n"
                                        "   • вручную через вкладки Учителя/Классы/Предметы/Кабинеты;\n"
                                        "   • импортом из Excel (через Мастер → Шаг 6).\n"
                                        "2. Пройдите Мастер расписания (7 шагов с проверками).\n"
                                        "3. Нажмите «Составить расписание».\n"
                                        "4. Экспортируйте в Excel при необходимости.",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "🧙 Мастер расписания",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "7 шагов с автоматическими проверками:\n"
                                        "• Шаг 1. Школа — информация об учреждении.\n"
                                        "• Шаг 2. Учителя — проверка, что у всех есть предметы.\n"
                                        "• Шаг 3. Классы — проверка количества учеников.\n"
                                        "• Шаг 4. Предметы — проверка учителей и часов.\n"
                                        "• Шаг 5. Кабинеты — проверка вместимости.\n"
                                        "• Шаг 6. Учебный план — статистика и импорт из Excel.\n"
                                        "• Шаг 7. Составление — итоговая проверка и запуск.\n\n"
                                        "Цвет прогресса:\n"
                                        "• 🟢 зелёный — всё в порядке\n"
                                        "• 🟡 жёлтый — есть предупреждения\n"
                                        "• 🔴 красный — данные не заполнены",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "📥 Импорт из Excel",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "Файл должен лежать рядом с программой: template.xlsx\n\n"
                                        "Структура файла — 6 листов:\n"
                                        "• Школа — название, адрес, директор\n"
                                        "• Учителя — ФИО, предметы (через запятую)\n"
                                        "• Предметы — название, сложность\n"
                                        "• Классы — название, учеников, смена\n"
                                        "• Кабинеты — номер, спец. предмет, мест\n"
                                        "• Учебный план — класс, предмет, часов, учитель\n\n"
                                        "⚠️ ВАЖНО: при импорте программа может задать вопросы,\n"
                                        "если данные различаются. Отвечайте внимательно —\n"
                                        "неверный ответ может привести к потере данных.",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "🔑 Лицензия",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "• Демо-версия: не более 5 классов.\n"
                                        "• Полная версия: без ограничений.\n"
                                        "• Ключ: SP-XXXX-XXXX-XXXX.\n"
                                        "• Ключ вводится один раз, хранится в системе.\n"
                                        "• При обновлении программы ключ сохраняется.",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "📌 Общие правила",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "• Всего в неделе: 5 дней × 8 уроков = 40 слотов.\n"
                                        "• Сумма часов класса ≤ 40.\n"
                                        "• Нагрузка учителя ≤ 40 уроков в неделю.\n"
                                        "• Один учитель не может вести два урока одновременно.\n"
                                        "• В одном кабинете не может идти два урока одновременно.",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "✏️ Редактирование расписания",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "• Изменения в полях — по Enter.\n"
                                        "• Клик по уроку → клик по клетке — переместить.\n"
                                        "• Клик по занятой клетке — поменять уроки местами.",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "⚠️ Если расписание не составляется",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "1. Проверьте, что у каждого предмета есть учитель.\n"
                                        "2. Проверьте, что сумма часов класса ≤ 40.\n"
                                        "3. Проверьте нагрузку учителей (не более 40 ч).\n"
                                        "4. Добавьте кабинеты, если их не хватает.\n"
                                        "5. Используйте мастер — он подскажет проблему.",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                ],
                                expand=True,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            padding=30,
                            expand=True,
                            bgcolor=BG,
                        ),
                    ],
                ),
            ],
        ),
    )

    page.add(
        ft.Container(
            content=ft.Column(
                [
                    demo_banner,
                    tabs,
                ],
                expand=True,
                spacing=0,
            ),
            bgcolor=BG,
            expand=True,
        )
    )

    # Первичная отрисовка
    render_teachers()
    render_classes()
    render_subjects()
    render_rooms()
    render_demo_banner()

    render_wizard_progress()
    render_wizard()


ft.run(main)