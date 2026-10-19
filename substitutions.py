"""
Поиск замен для урока. Простейшая версия — в памяти, без БД.
"""


def find_substitutes(data, schedule, day, slot, class_name, subject, original_teacher_id):
    """Возвращает список кандидатов на замену.

    Критерии:
      • ведёт этот предмет;
      • свободен в (day, slot) — нет своего урока;
      • слот не в unavailable_slots;
      • не ведёт уже урок в этом классе в этот день (чтобы не спамить один класс).
    """
    candidates = []

    for t in data["teachers"]:
        tid = t["id"]
        if tid == original_teacher_id:
            continue

        # 1. Ведёт ли предмет?
        if subject not in t.get("subjects", []):
            continue

        # 2. Свободен ли в этот слот?
        busy = any(
            l.teacher_id == tid and l.day == day and l.slot == slot
            for l in schedule
        )
        if busy:
            continue

        # 3. Не заблокирован ли слот?
        blocked = any(
            isinstance(item, (list, tuple)) and len(item) >= 2
            and item[0] == day and item[1] == slot
            for item in t.get("unavailable_slots", [])
        )
        if blocked:
            continue

        # 4. Уже ведёт урок в этом классе в этот день?
        already_in_class = any(
            l.teacher_id == tid and l.class_name == class_name and l.day == day
            for l in schedule
        )

        # Нагрузка (сколько уроков в неделю)
        load = sum(1 for l in schedule if l.teacher_id == tid)

        candidates.append({
            "teacher": t,
            "current_load": load,
            "already_in_class": already_in_class,
            "score": 100 - load - (50 if already_in_class else 0),
        })

    candidates.sort(key=lambda c: -c["score"])
    return candidates