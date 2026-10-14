from typing import List
from models import Teacher, SchoolClass, Subject, Room, Lesson

DAYS = 5
SLOTS_PER_DAY = 7
MAX_SLOTS = DAYS * SLOTS_PER_DAY


class Scheduler:
    def __init__(self, teachers, classes, subjects, rooms):
        self.teachers = {t.id: t for t in teachers}
        self.classes = {c.name: c for c in classes}
        self.subjects = {s.name: s for s in subjects}
        self.rooms = {r.id: r for r in rooms}
        self.schedule: List[Lesson] = []

    # ---------------- Проверки выполнимости ----------------
    def _precheck(self) -> str:
        # 1. Суммарная нагрузка класса ≤ числа слотов
        for cls in self.classes.values():
            total = sum(
                self.subjects[s].hours_per_week.get(cls.name, 0)
                for s in self.subjects
            )
            if total > MAX_SLOTS:
                return (f"Класс {cls.name}: суммарная нагрузка {total} ч. "
                        f"превышает {MAX_SLOTS} слотов в неделю.")

        # 2. У каждого предмета с часами есть учитель
        for s in self.subjects.values():
            has_hours = any(v > 0 for v in s.hours_per_week.values())
            if has_hours and not self._find_teacher(s.name):
                return f"Для предмета «{s.name}» не назначен учитель."

        # 3. Нагрузка учителя ≤ доступных слотов
        for t in self.teachers.values():
            load = 0
            for s in self.subjects.values():
                if s.name in t.subjects:
                    load += sum(s.hours_per_week.values())
            available = MAX_SLOTS - len(t.unavailable_slots)
            if load > available:
                return (f"Учитель {t.name}: нагрузка {load} ч. "
                        f"превышает доступные {available} слотов.")

        # 4. Есть кабинеты
        if not self.rooms:
            return "Нет ни одного кабинета."

        return ""

    # ---------------- Вспомогательные методы ----------------
    def _find_teacher(self, subject: str) -> Teacher:
        for t in self.teachers.values():
            if subject in t.subjects:
                return t
        return None

    def _find_rooms_for(self, subject: str, class_name: str) -> List[int]:
        """Кабинеты, подходящие для урока (спец. + обычные)."""
        cls = self.classes[class_name]
        special = []
        normal = []
        for r in self.rooms.values():
            if r.capacity < cls.students:
                continue
            if r.subject_specific == subject:
                special.append(r.id)
            elif not r.subject_specific:
                normal.append(r.id)
        # сначала спец. кабинеты, потом обычные
        return special + normal

    # ---------------- Основной метод ----------------
    def solve(self):
        """Возвращает (успех: bool, сообщение: str)."""
        err = self._precheck()
        if err:
            return False, err

        try:
            from ortools.sat.python import cp_model
        except ImportError:
            return False, "Не установлен OR-Tools. Выполните: pip install ortools"

        model = cp_model.CpModel()

        # ---------- Собираем список уроков ----------
        # lesson_specs[i] = (class_name, subject, teacher_id)
        lesson_specs = []
        for cls in self.classes.values():
            for s in self.subjects.values():
                hours = s.hours_per_week.get(cls.name, 0)
                if hours <= 0:
                    continue
                teacher = self._find_teacher(s.name)
                if not teacher:
                    continue
                for _ in range(hours):
                    lesson_specs.append((cls.name, s.name, teacher.id))

        n = len(lesson_specs)
        if n == 0:
            return False, "Нет ни одного урока для составления."

        # ---------- Переменные: для каждого урока — (day, slot, room) ----------
        # x[i][d][s] = 1, если урок i стоит в день d, слот s
        x = {}
        for i in range(n):
            for d in range(DAYS):
                for s in range(SLOTS_PER_DAY):
                    x[(i, d, s)] = model.NewBoolVar(f"x_{i}_{d}_{s}")

        # каждый урок — ровно в одном слоте
        for i in range(n):
            model.Add(
                sum(x[(i, d, s)] for d in range(DAYS) for s in range(SLOTS_PER_DAY)) == 1
            )

        # ---------- Ограничение: один класс — один урок в слоте ----------
        for cls_name in self.classes:
            for d in range(DAYS):
                for s in range(SLOTS_PER_DAY):
                    lessons_here = [
                        i for i in range(n) if lesson_specs[i][0] == cls_name
                    ]
                    if lessons_here:
                        model.Add(
                            sum(x[(i, d, s)] for i in lessons_here) <= 1
                        )

        # ---------- Ограничение: один учитель — один урок в слоте ----------
        for t_id in self.teachers:
            for d in range(DAYS):
                for s in range(SLOTS_PER_DAY):
                    lessons_here = [
                        i for i in range(n) if lesson_specs[i][2] == t_id
                    ]
                    if lessons_here:
                        model.Add(
                            sum(x[(i, d, s)] for i in lessons_here) <= 1
                        )

        # ---------- Запрещённые слоты у учителей ----------
                # ---------- Запрещённые слоты у учителей ----------
        for i in range(n):
            _, _, t_id = lesson_specs[i]
            teacher = self.teachers[t_id]
            for item in teacher.unavailable_slots:
                # item = [day, slot] или [day, slot, reason]
                day, slot = item[0], item[1]
                if 0 <= day < DAYS and 0 <= slot < SLOTS_PER_DAY:
                    model.Add(x[(i, day, slot)] == 0)

        # ---------- Кабинеты ----------
        # y[i][r][d][s] = 1, если урок i в кабинете r в день d, слот s
        y = {}
        rooms_for_lesson = {}
        for i in range(n):
            _, subj, _ = lesson_specs[i]
            cls_name = lesson_specs[i][0]
            rooms_for_lesson[i] = self._find_rooms_for(subj, cls_name)
            for r in rooms_for_lesson[i]:
                for d in range(DAYS):
                    for s in range(SLOTS_PER_DAY):
                        y[(i, r, d, s)] = model.NewBoolVar(f"y_{i}_{r}_{d}_{s}")

        # каждый урок — в одном кабинете
        for i in range(n):
            model.Add(
                sum(
                    y[(i, r, d, s)]
                    for r in rooms_for_lesson[i]
                    for d in range(DAYS)
                    for s in range(SLOTS_PER_DAY)
                ) == 1
            )

        # связка x и y: если урок в (d, s), то он и в кабинете
        for i in range(n):
            for d in range(DAYS):
                for s in range(SLOTS_PER_DAY):
                    model.Add(
                        sum(y[(i, r, d, s)] for r in rooms_for_lesson[i])
                        == x[(i, d, s)]
                    )

        # один кабинет — один урок в слоте
        for r_id in self.rooms:
            for d in range(DAYS):
                for s in range(SLOTS_PER_DAY):
                    lessons_here = [
                        i for i in range(n) if r_id in rooms_for_lesson[i]
                    ]
                    if lessons_here:
                        model.Add(
                            sum(y[(i, r_id, d, s)] for i in lessons_here) <= 1
                        )

        # ---------- Оптимизация: минимум «окон» у классов ----------
        # Для каждого класса и дня: уроки должны идти подряд с 1-го слота.
        # Введём переменную start[cls][d] — с какого слота начинается день
        # и end[cls][d] — на каком заканчивается. Цель — минимизировать сумму (end - start).
        # Это сложно, поэтому пока пропустим — оставим только базовые ограничения.

        # ---------- Решаем ----------
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        status = solver.Solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return False, ("OR-Tools не нашёл решения за 30 секунд. "
                           "Попробуйте ослабить ограничения.")

        # ---------- Извлекаем расписание ----------
        self.schedule = []
        for i in range(n):
            cls_name, subj, t_id = lesson_specs[i]
            placed = False
            for d in range(DAYS):
                if placed:
                    break
                for s in range(SLOTS_PER_DAY):
                    if solver.Value(x[(i, d, s)]) == 1:
                        room_id = None
                        for r in rooms_for_lesson[i]:
                            if solver.Value(y[(i, r, d, s)]) == 1:
                                room_id = r
                                break
                        self.schedule.append(
                            Lesson(d, s, cls_name, subj, t_id, room_id or 0)
                        )
                        placed = True
                        break

        return True, "OK"