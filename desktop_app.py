import hashlib
import flet as ft
from storage import load_data, save_data
from models import Teacher, SchoolClass, Subject, Room
from scheduler import Scheduler
import license as lic
from excel_export import export_to_excel

DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт"]


def main(page: ft.Page):
    # ---------- Лицензия ----------
    is_activated = lic.is_activated()

    # ---------- Общие настройки окна ----------
    title_suffix = "" if is_activated else " (ДЕМО)"
    page.title = f"SchoolPlanner v2.1.0{title_suffix}"
    page.window.width = 1800
    page.window.height = 1000
    page.window.min_width = 1000
    page.window.min_height = 600
    page.window.left = 80
    page.window.top = 30

    # ---------- Тёмная тема ----------
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed="#6366f1")

    # ---------- Палитра ----------
    BG = "#1e293b"
    ACCENT = "#6366f1"
    ACCENT_2 = "#22d3ee"
    CARD_BG = "#334155"
    CARD_BORDER = "#475569"
    TEXT_MAIN = "#f1f5f9"
    TEXT_MUTED = "#cbd5e1"

    data = load_data()

    # ---------- Состояние редактирования расписания ----------
    editable_schedule = []
    selected_lesson = {"obj": None}
    schedule_container = ft.Column(spacing=4)

    # ---------- Хелперы ----------
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

    def subject_color(subject_name):
        if not subject_name:
            return SUBJECT_COLORS[0]
        for i, s in enumerate(data["subjects"]):
            if s["name"] == subject_name:
                return SUBJECT_COLORS[i % len(SUBJECT_COLORS)]
        return "#64748b"

    def class_badge(name):
        if not name:
            return "?"
        digits = ""
        letter = ""
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
        return name[:1].upper() if name else "?"

    def page_title(text, subtitle=""):
        col = [ft.Text(text, size=26, weight=ft.FontWeight.BOLD, color=TEXT_MAIN)]
        if subtitle:
            col.append(ft.Text(subtitle, size=13, color=TEXT_MUTED))
        return ft.Column(col, spacing=2)

    # ======================= Баннер демо-версии =======================
    demo_banner = ft.Container()

    def render_demo_banner():
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
                                    weight="bold",
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

    # ======================= Диалог активации =======================
    def open_activation_dialog(e):
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
                status_text.value = "❌ Введите ключ."
                status_text.color = "#ef4444"
                status_text.update()
                return
            if not key.startswith("SP-"):
                status_text.value = "❌ Ключ должен начинаться с SP-"
                status_text.color = "#ef4444"
                status_text.update()
                return
            if not lic.is_valid_key(key):
                status_text.value = "❌ Неверный ключ. Проверьте и попробуйте снова."
                status_text.color = "#ef4444"
                status_text.update()
                return
            if lic.save_license(key):
                status_text.value = "✅ Программа активирована!"
                status_text.color = "#10b981"
                status_text.update()
                import time

                time.sleep(0.5)
                dlg.open = False
                page.update()
                render_demo_banner()
                page.title = "SchoolPlanner v2.1.0"
                page.update()
            else:
                status_text.value = "❌ Не удалось сохранить ключ."
                status_text.color = "#ef4444"
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

    # ======================= Учителя =======================
    teachers_list = ft.Column(spacing=10)

    def open_slots_dialog(teacher_idx):
        teacher = data["teachers"][teacher_idx]

        unavailable = {}
        for item in teacher.get("unavailable_slots", []):
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
                            content=ft.Text(d, weight="bold", color=TEXT_MAIN, size=14),
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

            for slot in range(7):
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
                                        tooltip="Снять запрет",
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
                            tooltip="Нажми, чтобы запретить",
                        )
                    row_cells.append(cell)
                grid_container.controls.append(ft.Row(row_cells, spacing=4))

        rebuild_grid()

        def save_and_close(e):
            teacher["unavailable_slots"] = [
                [d, s, reason] for (d, s), reason in unavailable.items()
            ]
            save_data(data)
            dlg.open = False
            page.update()
            render_teachers()

        def close_dialog(e):
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"🚫 Запрещённые слоты: {teacher['name']}", color=TEXT_MAIN),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "🚫 Как это работает",
                                        size=14,
                                        weight="bold",
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
                height=650,
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

    def build_warnings_block(warnings):
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
                                        p.title, size=13, weight="bold", color="#f59e0b"
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
            tooltip="Показать / скрыть предупреждения",
        )

        header = ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        f"⚠️ {len(warnings)} предупреждений",
                        size=13,
                        weight="bold",
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

    def render_teachers():
        teachers_list.controls.clear()
        all_subjects = [s["name"] for s in data["subjects"]]

        valid = set(all_subjects)
        for t in data["teachers"]:
            cleaned = [s for s in t["subjects"] if s in valid]
            if cleaned != t["subjects"]:
                t["subjects"] = cleaned
                save_data(data)

        for i, t in enumerate(data["teachers"]):

            def make_name_handler(idx):
                def handler(e):
                    data["teachers"][idx]["name"] = e.control.value
                    save_data(data)

                return handler

            def make_name_submit(idx):
                def handler(e):
                    data["teachers"][idx]["name"] = e.control.value
                    save_data(data)
                    render_teachers()

                return handler

            def make_del_handler(idx):
                def handler(e):
                    data["teachers"].pop(idx)
                    save_data(data)
                    render_teachers()

                return handler

            def make_subj_selected(idx):
                def handler(e):
                    val = e.control.value
                    if not val:
                        return
                    if val not in data["teachers"][idx]["subjects"]:
                        data["teachers"][idx]["subjects"].append(val)
                        save_data(data)
                        render_teachers()
                    e.control.value = None

                return handler

            name_field = ft.TextField(
                value=t["name"],
                label="ФИО (Enter — обновить)",
                width=300,
                on_change=make_name_handler(i),
                on_submit=make_name_submit(i),
                border_color=CARD_BORDER,
                focused_border_color=ACCENT,
            )

            subj_dropdown = ft.Dropdown(
                label="➕ Добавить предмет",
                width=280,
                options=[ft.DropdownOption(key=s, text=s) for s in all_subjects],
                on_select=make_subj_selected(i),
                border_color=CARD_BORDER,
                focused_border_color=ACCENT,
            )

            chips = ft.Row(spacing=3, wrap=True)
            for s in t["subjects"]:

                def make_remove_subj(idx, subj):
                    def handler(e):
                        data["teachers"][idx]["subjects"].remove(subj)
                        save_data(data)
                        render_teachers()

                    return handler

                chips.controls.append(
                    ft.Chip(label=ft.Text(s), on_delete=make_remove_subj(i, s))
                )

            unavailable_list = t.get("unavailable_slots", [])
            if unavailable_list:
                tooltip_lines = [f"Запрещённых слотов: {len(unavailable_list)}"]
                for item in unavailable_list[:5]:
                    day_num, slot_num = item[0], item[1]
                    reason = item[2] if len(item) > 2 and item[2] else ""
                    line = f"• {DAY_NAMES[day_num]}, {slot_num + 1} урок"
                    if reason:
                        line += f" — {reason}"
                    tooltip_lines.append(line)
                if len(unavailable_list) > 5:
                    tooltip_lines.append(f"...и ещё {len(unavailable_list) - 5}")
                block_tooltip = "\n".join(tooltip_lines)
            else:
                block_tooltip = "Запрещённых слотов нет"

            row = ft.Row(
                [
                    ft.Container(
                        content=ft.Text(
                            teacher_badge(t["name"]),
                            size=20,
                            weight="bold",
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
                        tooltip=(
                            "🚫 Запрещённые слоты\n"
                            "Не ставить уроки учителю в эти часы.\n"
                            "Нажми, чтобы настроить.\n\n" + block_tooltip
                        ),
                        on_click=lambda e, idx=i: open_slots_dialog(idx),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE, icon_color="red", on_click=make_del_handler(i)
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
        new_id = max([t["id"] for t in data["teachers"]], default=0) + 1
        data["teachers"].insert(
            0,
            {
                "id": new_id,
                "name": "Новый",
                "subjects": [],
                "unavailable_slots": [],
            },
        )
        save_data(data)
        render_teachers()

    # ======================= Классы =======================
    classes_list = ft.Column(spacing=12)

    def render_classes():
        classes_list.controls.clear()
        wrapper = ft.Row(wrap=True, spacing=15, run_spacing=15, expand=True)
        classes_list.controls.append(wrapper)

        for i, c in enumerate(data["classes"]):

            def make_name_handler(idx):
                def handler(e):
                    data["classes"][idx]["name"] = e.control.value
                    save_data(data)
                    render_subjects()

                return handler

            def make_name_submit(idx):
                def handler(e):
                    data["classes"][idx]["name"] = e.control.value
                    save_data(data)
                    render_subjects()
                    render_classes()

                return handler

            def make_stud_handler(idx):
                def handler(e):
                    try:
                        data["classes"][idx]["students"] = int(e.control.value)
                        save_data(data)
                    except ValueError:
                        pass

                return handler

            def make_del_handler(idx):
                def handler(e):
                    removed_name = data["classes"][idx]["name"]
                    data["classes"].pop(idx)
                    for subj in data["subjects"]:
                        if removed_name in subj.get("hours", {}):
                            del subj["hours"][removed_name]
                    save_data(data)
                    render_classes()
                    render_subjects()

                return handler

            card_content = ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(
                                    class_badge(c["name"]),
                                    size=18,
                                    weight="bold",
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
                                on_click=make_del_handler(i),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.TextField(
                        value=c["name"],
                        label="Название (Enter — обновить)",
                        on_change=make_name_handler(i),
                        on_submit=make_name_submit(i),
                        border_color=CARD_BORDER,
                        focused_border_color=ACCENT,
                    ),
                    ft.TextField(
                        value=str(c["students"]),
                        label="Учеников",
                        on_change=make_stud_handler(i),
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
        new_id = max([c["id"] for c in data["classes"]], default=0) + 1
        data["classes"].insert(0, {"id": new_id, "name": "Новый", "students": 25})
        save_data(data)
        render_classes()
        render_subjects()

    # ======================= Предметы =======================
    subjects_list = ft.Column(spacing=5)

    def render_subjects():
        subjects_list.controls.clear()
        class_names = [c["name"] for c in data["classes"]]

        for i, s in enumerate(data["subjects"]):

            def make_name_handler(idx):
                def handler(e):
                    old_name = data["subjects"][idx]["name"]
                    new_name = e.control.value
                    if old_name == new_name:
                        return
                    data["subjects"][idx]["name"] = new_name
                    for t in data["teachers"]:
                        t["subjects"] = [
                            new_name if subj == old_name else subj
                            for subj in t["subjects"]
                        ]
                    save_data(data)
                    render_teachers()

                return handler

            def make_hours_handler(idx, cname):
                def handler(e):
                    try:
                        data["subjects"][idx]["hours"][cname] = int(
                            e.control.value or 0
                        )
                        save_data(data)
                    except ValueError:
                        pass

                return handler

            def make_del_handler(idx):
                def handler(e):
                    removed_name = data["subjects"][idx]["name"]
                    for t in data["teachers"]:
                        t["subjects"] = [s for s in t["subjects"] if s != removed_name]
                    data["subjects"].pop(idx)
                    save_data(data)
                    render_subjects()
                    render_teachers()

                return handler

            hours_inputs = []
            for cname in class_names:
                hours_inputs.append(
                    ft.Column(
                        [
                            ft.Text(cname, size=12, color=TEXT_MUTED),
                            ft.TextField(
                                value=str(s["hours"].get(cname, 0)),
                                width=70,
                                on_change=make_hours_handler(i, cname),
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
                                        label="Предмет",
                                        width=250,
                                        on_change=make_name_handler(i),
                                        border_color=CARD_BORDER,
                                        focused_border_color=ACCENT,
                                    ),
                                    ft.IconButton(
                                        ft.Icons.DELETE,
                                        icon_color="red",
                                        on_click=make_del_handler(i),
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
        data["subjects"].insert(0, {"name": "Новый предмет", "hours": {}})
        save_data(data)
        render_subjects()
        render_teachers()

    # ======================= Кабинеты =======================
    rooms_list = ft.Column(spacing=12)

    def render_rooms():
        rooms_list.controls.clear()
        wrapper = ft.Row(wrap=True, spacing=15, run_spacing=15, expand=True)
        rooms_list.controls.append(wrapper)

        for i, r in enumerate(data["rooms"]):

            def make_handler(field, idx):
                def handler(e):
                    val = e.control.value
                    if field == "capacity":
                        try:
                            val = int(val)
                        except ValueError:
                            return
                    data["rooms"][idx][field] = val
                    save_data(data)

                return handler

            def make_del_handler(idx):
                def handler(e):
                    data["rooms"].pop(idx)
                    save_data(data)
                    render_rooms()

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
                                on_click=make_del_handler(i),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.TextField(
                        value=r["name"],
                        label="Название",
                        on_change=make_handler("name", i),
                        border_color=CARD_BORDER,
                        focused_border_color=ACCENT,
                    ),
                    ft.TextField(
                        value=str(r["capacity"]),
                        label="Мест",
                        on_change=make_handler("capacity", i),
                        border_color=CARD_BORDER,
                        focused_border_color=ACCENT,
                    ),
                    ft.TextField(
                        value=r["subject_specific"],
                        label="Спец. для предмета",
                        on_change=make_handler("subject_specific", i),
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
        new_id = max([r["id"] for r in data["rooms"]], default=100) + 1
        data["rooms"].insert(
            0,
            {
                "id": new_id,
                "name": str(new_id),
                "capacity": 30,
                "subject_specific": "",
            },
        )
        save_data(data)
        render_rooms()

    # ======================= Расписание =======================
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

    def move_lesson(clicked_lesson, class_name, teacher_id, day, slot):
        sel = selected_lesson["obj"]

        if clicked_lesson is None:
            if sel is None:
                return
            sel.day = day
            sel.slot = slot
            selected_lesson["obj"] = None
            render_schedule()
            page.update()
            return

        if sel is None:
            selected_lesson["obj"] = clicked_lesson
            render_schedule()
            page.update()
            return

        if sel is clicked_lesson:
            selected_lesson["obj"] = None
            render_schedule()
            page.update()
            return

        sel_day, sel_slot = sel.day, sel.slot
        sel.day, sel.slot = clicked_lesson.day, clicked_lesson.slot
        clicked_lesson.day, clicked_lesson.slot = sel_day, sel_slot
        selected_lesson["obj"] = None
        render_schedule()
        page.update()

    def render_schedule():
        schedule_container.controls.clear()

        schedule_container.controls.append(
            ft.Text("📚 По классам", size=16, weight="bold", color=TEXT_MAIN)
        )

        class_names = sorted(set(l.class_name for l in editable_schedule))
        for cname in class_names:
            schedule_container.controls.append(
                ft.Text(f"Класс {cname}", size=14, weight="bold", color=TEXT_MAIN)
            )

            header_cells = [
                ft.Container(
                    content=ft.Text("Урок", weight="bold", color=TEXT_MAIN),
                    expand=1,
                    padding=8,
                    alignment=ft.Alignment.CENTER,
                )
            ]
            for d in DAY_NAMES:
                header_cells.append(
                    ft.Container(
                        content=ft.Text(d, weight="bold", color=TEXT_MAIN),
                        expand=3,
                        padding=8,
                        alignment=ft.Alignment.CENTER,
                        bgcolor=CARD_BG,
                        border_radius=6,
                    )
                )
            rows = [ft.Row(header_cells, spacing=4)]

            for slot in range(7):
                row_cells = [
                    ft.Container(
                        content=ft.Text(str(slot + 1), color=TEXT_MAIN),
                        expand=1,
                        padding=8,
                        alignment=ft.Alignment.CENTER,
                    )
                ]
                for day in range(5):
                    l = find_lesson(cname, None, day, slot)
                    is_selected = selected_lesson["obj"] is l and l is not None

                    def make_cell_click(lesson, cls, d, s):
                        def handler(e):
                            move_lesson(lesson, cls, None, d, s)

                        return handler

                    if l:
                        border_color = "#facc15" if is_selected else "transparent"
                        border_width = 3 if is_selected else 0
                        row_cells.append(
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text(
                                            l.subject,
                                            color="white",
                                            size=12,
                                            weight="bold",
                                            text_align=ft.TextAlign.CENTER,
                                        ),
                                        ft.Text(
                                            f"каб.{l.room_id}",
                                            color="#f1f5f9",
                                            size=10,
                                            text_align=ft.TextAlign.CENTER,
                                        ),
                                    ],
                                    spacing=0,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                expand=3,
                                padding=8,
                                alignment=ft.Alignment.CENTER,
                                bgcolor=subject_color(l.subject),
                                border_radius=8,
                                border=ft.Border.all(border_width, border_color),
                                on_click=make_cell_click(l, cname, day, slot),
                                ink=True,
                            )
                        )
                    else:
                        row_cells.append(
                            ft.Container(
                                content=ft.Text("—", color="#64748b", size=12),
                                expand=3,
                                padding=8,
                                alignment=ft.Alignment.CENTER,
                                on_click=make_cell_click(None, cname, day, slot),
                                ink=True,
                            )
                        )
                rows.append(ft.Row(row_cells, spacing=4))

            schedule_container.controls.append(ft.Column(rows, spacing=4))
            schedule_container.controls.append(ft.Divider(color=CARD_BORDER))

        schedule_container.controls.append(
            ft.Text("👩‍🏫 По учителям", size=16, weight="bold", color=TEXT_MAIN)
        )

        teacher_ids = sorted(set(l.teacher_id for l in editable_schedule))
        for t_id in teacher_ids:
            t_name = f"Учитель {t_id}"
            for t in data["teachers"]:
                if t["id"] == t_id:
                    t_name = t["name"]
                    break

            schedule_container.controls.append(
                ft.Text(t_name, size=14, weight="bold", color=TEXT_MAIN)
            )

            header_cells = [
                ft.Container(
                    content=ft.Text("Урок", weight="bold", color=TEXT_MAIN),
                    expand=1,
                    padding=8,
                    alignment=ft.Alignment.CENTER,
                )
            ]
            for d in DAY_NAMES:
                header_cells.append(
                    ft.Container(
                        content=ft.Text(d, weight="bold", color=TEXT_MAIN),
                        expand=3,
                        padding=8,
                        alignment=ft.Alignment.CENTER,
                        bgcolor=CARD_BG,
                        border_radius=6,
                    )
                )
            rows = [ft.Row(header_cells, spacing=4)]

            for slot in range(7):
                row_cells = [
                    ft.Container(
                        content=ft.Text(str(slot + 1), color=TEXT_MAIN),
                        expand=1,
                        padding=8,
                        alignment=ft.Alignment.CENTER,
                    )
                ]
                for day in range(5):
                    l = find_lesson(None, t_id, day, slot)
                    is_selected = selected_lesson["obj"] is l and l is not None

                    def make_cell_click(lesson, tid, d, s):
                        def handler(e):
                            move_lesson(lesson, None, tid, d, s)

                        return handler

                    if l:
                        border_color = "#facc15" if is_selected else "transparent"
                        border_width = 3 if is_selected else 0
                        row_cells.append(
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text(
                                            l.class_name,
                                            color="white",
                                            size=12,
                                            weight="bold",
                                            text_align=ft.TextAlign.CENTER,
                                        ),
                                        ft.Text(
                                            l.subject,
                                            color="#f1f5f9",
                                            size=10,
                                            text_align=ft.TextAlign.CENTER,
                                        ),
                                    ],
                                    spacing=0,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                expand=3,
                                padding=8,
                                alignment=ft.Alignment.CENTER,
                                bgcolor=subject_color(l.subject),
                                border_radius=8,
                                border=ft.Border.all(border_width, border_color),
                                on_click=make_cell_click(l, t_id, day, slot),
                                ink=True,
                            )
                        )
                    else:
                        row_cells.append(
                            ft.Container(
                                content=ft.Text("—", color="#64748b", size=12),
                                expand=3,
                                padding=8,
                                alignment=ft.Alignment.CENTER,
                                on_click=make_cell_click(None, t_id, day, slot),
                                ink=True,
                            )
                        )
                rows.append(ft.Row(row_cells, spacing=4))

            schedule_container.controls.append(ft.Column(rows, spacing=4))
            schedule_container.controls.append(ft.Divider(color=CARD_BORDER))

    def export_schedule_to_excel(e):
        """Экспорт текущего расписания в Excel."""
        if not editable_schedule:
            snack = ft.SnackBar(
                content=ft.Text("❌ Сначала составьте расписание!"),
                bgcolor="#ef4444",
            )
            page.overlay.append(snack)
            snack.open = True
            page.update()
            return

        import os
        filepath = os.path.join(os.getcwd(), "Расписание.xlsx")

        ok, message = export_to_excel(editable_schedule, data, filepath)

        color = "#10b981" if ok else "#ef4444"
        icon = "✅" if ok else "❌"
        snack = ft.SnackBar(
            content=ft.Text(f"{icon} {message}", color="white"),
            bgcolor=color,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()


    def build_schedule(e):
        schedule_output.controls.clear()
        selected_lesson["obj"] = None

        if not lic.is_activated():
            if len(data["classes"]) > lic.DEMO_MAX_CLASSES:
                schedule_output.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "🔓 Демо-версия",
                                    size=18,
                                    weight="bold",
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
                return

        from advisor import analyze

        problems = analyze(data)

        errors = [p for p in problems if p.severity == "error"]
        warnings = [p for p in problems if p.severity == "warning"]

        schedule_output.controls.append(
            ft.Row(
                [
                    ft.Text(
                        "🔍 Анализ данных", size=22, weight="bold", color=TEXT_MAIN
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

            color = "#ef4444"
            block_controls = [
                ft.Row(
                    [
                        ft.Text("❌", size=18),
                        ft.Text(p.title, size=16, weight="bold", color=color),
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
                    border=ft.Border.all(1, color),
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
                        weight="bold",
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
        subjects = [Subject(s["name"], s["hours"]) for s in data["subjects"]]
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
            schedule_output.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "🧩 Комбинаторная проблема",
                                size=16,
                                weight="bold",
                                color="#ef4444",
                            ),
                            ft.Text(message, size=13, color=TEXT_MUTED),
                            ft.Text(
                                "Что можно попробовать:",
                                size=13,
                                weight="bold",
                                color=TEXT_MAIN,
                            ),
                            ft.Text(
                                "• Уменьшить нагрузку у самых загруженных классов.\n"
                                "• Добавить ещё одного учителя по «узким» предметам.\n"
                                "• Добавить кабинеты, если их меньше, чем классов.\n"
                                "• Снять запреты на слоты у учителей, если они есть.",
                                size=13,
                                color=TEXT_MAIN,
                            ),
                        ],
                        spacing=8,
                    ),
                    bgcolor=CARD_BG,
                    border=ft.Border.all(1, "#ef4444"),
                    border_radius=10,
                    padding=15,
                )
            )
            page.update()
            return

        editable_schedule.clear()
        editable_schedule.extend(scheduler.schedule)

        header_row = [ft.Text("✅ Расписание составлено!", color="green", size=18)]
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
                header_row, spacing=15, vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

        all_subj_names = sorted(set(l.subject for l in editable_schedule))
        if all_subj_names:
            legend_items = []
            for sname in all_subj_names:
                legend_items.append(
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
                )
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

    # ======================= Вкладки =======================
    tabs = ft.Tabs(
        length=6,
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.Container(
                    content=ft.TabBar(
                        tabs=[
                            ft.Tab(label="📅 Расписание"),
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
                        ft.Container(
                            content=ft.Column(
                                [
                                    page_title("Учителя", "Список и предметы"),
                                    ft.Button(
                                        "➕ Добавить учителя",
                                        on_click=add_teacher,
                                        style=ft.ButtonStyle(
                                            bgcolor=ACCENT,
                                            color="white",
                                            padding=ft.Padding.symmetric(
                                                horizontal=20, vertical=14
                                            ),
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                        ),
                                    ),
                                    teachers_list,
                                ],
                                expand=True,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            padding=30,
                            expand=True,
                            bgcolor=BG,
                        ),
                        ft.Container(
                            content=ft.Column(
                                [
                                    page_title(
                                        "Классы", "Классы и количество учеников"
                                    ),
                                    ft.Button(
                                        "➕ Добавить класс",
                                        on_click=add_class,
                                        style=ft.ButtonStyle(
                                            bgcolor=ACCENT,
                                            color="white",
                                            padding=ft.Padding.symmetric(
                                                horizontal=20, vertical=14
                                            ),
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                        ),
                                    ),
                                    classes_list,
                                ],
                                expand=True,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            padding=30,
                            expand=True,
                            bgcolor=BG,
                        ),
                        ft.Container(
                            content=ft.Column(
                                [
                                    page_title(
                                        "Предметы", "Нагрузка в часах по классам"
                                    ),
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
                                    subjects_list,
                                ],
                                expand=True,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            padding=30,
                            expand=True,
                            bgcolor=BG,
                        ),
                        ft.Container(
                            content=ft.Column(
                                [
                                    page_title("Кабинеты", "Аудитории и вместимость"),
                                    ft.Button(
                                        "➕ Добавить кабинет",
                                        on_click=add_room,
                                        style=ft.ButtonStyle(
                                            bgcolor=ACCENT,
                                            color="white",
                                            padding=ft.Padding.symmetric(
                                                horizontal=20, vertical=14
                                            ),
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                        ),
                                    ),
                                    rooms_list,
                                ],
                                expand=True,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            padding=30,
                            expand=True,
                            bgcolor=BG,
                        ),
                        ft.Container(
                            content=ft.Column(
                                [
                                    page_title("Справка", "Правила и ограничения"),
                                    ft.Text(
                                        "Ниже — что можно и нельзя делать, чтобы расписание составлялось корректно.",
                                        color=TEXT_MUTED,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "🔑 Лицензия",
                                        size=18,
                                        weight="bold",
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "• Демо-версия: не более 5 классов в расписании.\n"
                                        "• Полная версия: без ограничений.\n"
                                        "• Ключ активации: формат SP-XXXX-XXXX-XXXX.\n"
                                        "• Ключ вводится один раз, хранится в системе.\n"
                                        "• При обновлении программы ключ сохраняется.",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "📌 Общие правила",
                                        size=18,
                                        weight="bold",
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "• Всего в неделе: 5 дней × 7 уроков = 35 слотов на класс.\n"
                                        "• Сумма часов по всем предметам у класса не может превышать 35.",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "👩‍🏫 Учителя",
                                        size=18,
                                        weight="bold",
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "• У каждого предмета должен быть хотя бы один учитель.\n"
                                        "• 🚫 Запрещённые слоты — нажми на иконку 🚫 рядом с учителем.",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "🏫 Классы",
                                        size=18,
                                        weight="bold",
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "• Новый класс автоматически появляется во всех предметах с 0 часов.",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "📚 Предметы",
                                        size=18,
                                        weight="bold",
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "• 0 часов = предмет не изучается классом.",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "🚪 Кабинеты",
                                        size=18,
                                        weight="bold",
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "• В одном кабинете не могут идти два урока одновременно.",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "✏️ Редактирование расписания",
                                        size=18,
                                        weight="bold",
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "• Клик по уроку — выделить его.\n"
                                        "• Клик по пустой клетке — переместить урок.\n"
                                        "• Клик по другому уроку — поменять уроки местами.",
                                        color=TEXT_MAIN,
                                        size=13,
                                    ),
                                    ft.Divider(color=CARD_BORDER),
                                    ft.Text(
                                        "⚠️ Если расписание не составляется",
                                        size=18,
                                        weight="bold",
                                        color=TEXT_MAIN,
                                    ),
                                    ft.Text(
                                        "1. Проверь, что у каждого предмета есть учитель.\n"
                                        "2. Проверь, что сумма часов у класса ≤ 35.\n"
                                        "3. Добавь учителей или кабинеты.\n"
                                        "4. Уменьши нагрузку у проблемных классов.",
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

    # Баннер демо + вкладки — вертикально
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

    # первичная отрисовка
    render_teachers()
    render_classes()
    render_subjects()
    render_rooms()
    render_demo_banner()


ft.run(main)
