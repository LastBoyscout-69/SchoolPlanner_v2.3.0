MAX_SLOTS_PER_WEEK = 35
MAX_SLOTS_PER_DAY = 7


class Problem:
    def __init__(self, severity, title, details, recommendations):
        self.severity = severity          # "error" | "warning" | "info"
        self.title = title
        self.details = details
        self.recommendations = recommendations


def analyze(data):
    problems = []

    teachers = data.get("teachers", [])
    classes = data.get("classes", [])
    subjects = data.get("subjects", [])
    rooms = data.get("rooms", [])

    # --- 1. Базовые проверки ---
    if not teachers:
        problems.append(Problem("error", "Нет ни одного учителя",
            "Без учителей расписание составить невозможно.",
            ["Добавь хотя бы одного учителя на вкладке «Учителя»."]))
    if not classes:
        problems.append(Problem("error", "Нет ни одного класса",
            "Без классов расписание составить невозможно.",
            ["Добавь хотя бы один класс на вкладке «Классы»."]))
    if not subjects:
        problems.append(Problem("error", "Нет ни одного предмета",
            "Без предметов расписание составить невозможно.",
            ["Добавь хотя бы один предмет на вкладке «Предметы»."]))
    if not rooms:
        problems.append(Problem("error", "Нет ни одного кабинета",
            "Без кабинетов расписание составить невозможно.",
            ["Добавь хотя бы один кабинет на вкладке «Кабинеты»."]))

    if problems:
        return problems

    # --- 2. Учителя без предметов ---
    for t in teachers:
        if not t.get("subjects"):
            problems.append(Problem("warning",
                f"Учитель без предметов: {t['name']}",
                "Учителю не назначено ни одного предмета — он не попадёт в расписание.",
                [f"Открой «Учителя» и назначь предметы для {t['name']}."]))

    # --- 3. Нагрузка по классам ---
    for cls in classes:
        cname = cls["name"]
        total = sum(s.get("hours", {}).get(cname, 0) for s in subjects)

        if total > MAX_SLOTS_PER_WEEK:
            heavy = sorted(
                [(s["name"], s.get("hours", {}).get(cname, 0)) for s in subjects],
                key=lambda x: -x[1]
            )[:3]
            heavy_text = ", ".join(f"«{n}» ({h} ч)" for n, h in heavy if h > 0)

            problems.append(Problem("error",
                f"Перегрузка класса {cname}",
                f"Сумма часов: {total} при максимуме {MAX_SLOTS_PER_WEEK} "
                f"(5 дней × 7 уроков).",
                [
                    f"Уменьши нагрузку у класса {cname} минимум на "
                    f"{total - MAX_SLOTS_PER_WEEK} ч.",
                    f"Самые тяжёлые предметы: {heavy_text}.",
                    "Проверь вкладку «Предметы» — возможно, где-то лишние часы."
                ]))
        elif total == 0:
            problems.append(Problem("warning",
                f"Класс {cname} без нагрузки",
                "У класса нет ни одного предмета с часами больше нуля.",
                [f"Открой «Предметы» и поставь часы для класса {cname}."]))

    # --- 4. Предметы без учителя ---
    for s in subjects:
        has_hours = any(h > 0 for h in s.get("hours", {}).values())
        if not has_hours:
            continue

        teachers_for_subj = [
            t for t in teachers if s["name"] in t.get("subjects", [])
        ]
        if not teachers_for_subj:
            # ищем похожих учителей
            similar = []
            subj_words = [w for w in s["name"].lower().split() if len(w) > 3]
            for t in teachers:
                for ts in t.get("subjects", []):
                    if any(w in ts.lower() for w in subj_words):
                        similar.append(f"{t['name']} (ведёт «{ts}»)")
                        break
                if not t.get("subjects"):
                    similar.append(f"{t['name']} (свободен)")

            recs = [f"Открой «Учителя» и добавь предмет «{s['name']}» кому-нибудь."]
            if similar:
                recs.append(f"Возможные кандидаты: {', '.join(similar[:3])}.")

            problems.append(Problem("error",
                f"Нет учителя для предмета «{s['name']}»",
                f"Предмету «{s['name']}» назначены часы, "
                f"но ни один учитель его не ведёт.",
                recs))

    # --- 5. Нагрузка учителей ---
    for t in teachers:
        load = 0
        for s in subjects:
            if s["name"] in t.get("subjects", []):
                teachers_map = s.get("teachers", {})
                for cname, hours in s.get("hours", {}).items():
                    if teachers_map.get(cname) == t["name"]:
                        load += hours

        unavailable = len(t.get("unavailable_slots", []))
        available = MAX_SLOTS_PER_WEEK - unavailable

        if load > available:
            # кого можно привлечь?
            candidates = []
            for other in teachers:
                if other["id"] == t["id"]:
                    continue
                for s in subjects:
                    if s["name"] in other.get("subjects", []):
                        candidates.append(other["name"])
                        break

            recs = [
                f"Передай часть часов ({load - available} ч.) другому учителю.",
                f"Или уменьши нагрузку предметов, которые ведёт {t['name']}."
            ]
            if unavailable > 0:
                recs.append(f"Или сними часть запретов (сейчас их {unavailable}).")
            if candidates:
                recs.append(f"Другие учителя: {', '.join(set(candidates[:3]))}.")

            problems.append(Problem("error",
                f"Перегрузка учителя: {t['name']}",
                f"Нагрузка {load} ч., доступно {available} слотов "
                f"(из {MAX_SLOTS_PER_WEEK} минус {unavailable} запрещённых).",
                recs))
        elif load == 0:
            problems.append(Problem("info",
                f"Учитель без нагрузки: {t['name']}",
                "Учителю не назначены часы ни по одному предмету.",
                [f"Проверь, что у {t['name']} есть предметы, и у них есть часы."]))

    # --- 6. Кабинеты ---
    if len(rooms) < len(classes):
        problems.append(Problem("warning",
            "Мало кабинетов",
            f"Кабинетов: {len(rooms)}, классов: {len(classes)}. "
            f"Может не хватить для одновременных уроков.",
            [
                "Добавь кабинеты на вкладке «Кабинеты».",
                f"Рекомендуется минимум {len(classes)} кабинетов."
            ]))

    for cls in classes:
        fit = [r for r in rooms
               if r.get("capacity", 0) >= cls.get("students", 0)]
        if not fit:
            problems.append(Problem("error",
                f"Нет кабинета для класса {cls['name']}",
                f"В классе {cls['students']} учеников, "
                f"но ни один кабинет не вмещает столько.",
                [
                    "Добавь кабинет с большей вместимостью.",
                    f"Или уменьши число учеников в классе {cls['name']}."
                ]))

    if not problems:
        problems.append(Problem("info",
            "Проблем не найдено",
            "Все данные заполнены корректно. Расписание можно составлять.",
            []))

    return problems