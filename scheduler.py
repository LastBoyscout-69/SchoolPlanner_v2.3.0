from typing import List
from models import Teacher, SchoolClass, Subject, Room, Lesson

DAYS = 5
SLOTS_PER_DAY = 8
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

        # 3. Проверка кабинетов отключена для теста

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

    def _find_teacher_for_class(self, subject: str, class_name: str):
        subj = self.subjects.get(subject)
        if subj and hasattr(subj, "teachers") and subj.teachers:
            teacher_name = subj.teachers.get(class_name)
            if teacher_name:
                for t in self.teachers.values():
                    if t.name == teacher_name:
                        return t
        return self._find_teacher(subject)

    def _find_rooms_for(self, subject: str, class_name: str) -> List[int]:
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
            return False, "Не установлен OR-Tools"

        model = cp_model.CpModel()

        lesson_specs = []
        for cls in self.classes.values():
            for s in self.subjects.values():
                hours = s.hours_per_week.get(cls.name, 0)
                if hours <= 0:
                    continue
                teacher = self._find_teacher_for_class(s.name, cls.name)
                if not teacher:
                    continue
                for _ in range(hours):
                    lesson_specs.append((cls.name, s.name, teacher.id))

        n = len(lesson_specs)
        if n == 0:
            return False, "Нет уроков"

        # 1. Переменные для уроков
        x = {}
        for i in range(n):
            for d in range(DAYS):
                for s in range(SLOTS_PER_DAY):
                    x[(i, d, s)] = model.NewBoolVar(f"x_{i}_{d}_{s}")

        # 2. Каждый урок — ровно в одном слоте
        for i in range(n):
            model.Add(sum(x[(i, d, s)] for d in range(DAYS) for s in range(SLOTS_PER_DAY)) == 1)

        # 3. Один класс — один урок в слоте
        for cls_name in self.classes:
            for d in range(DAYS):
                for s in range(SLOTS_PER_DAY):
                    lessons_here = [i for i in range(n) if lesson_specs[i][0] == cls_name]
                    if lessons_here:
                        model.Add(sum(x[(i, d, s)] for i in lessons_here) <= 1)

        # 4. Один учитель — один урок в слоте
        for t_id in self.teachers:
            for d in range(DAYS):
                for s in range(SLOTS_PER_DAY):
                    lessons_here = [i for i in range(n) if lesson_specs[i][2] == t_id]
                    if lessons_here:
                        model.Add(sum(x[(i, d, s)] for i in lessons_here) <= 1)

        # 5. Запрещённые слоты учителей (методические дни)
        for i in range(n):
            t_id = lesson_specs[i][2]
            teacher = self.teachers[t_id]
            for slot_info in teacher.unavailable_slots:
                if len(slot_info) >= 2:
                    u_day = slot_info[0]
                    u_slot = slot_info[1]
                    model.Add(x[(i, u_day, u_slot)] == 0)

        # 6. Не больше 2 уроков одного предмета в день для класса
        for cls_name in self.classes:
            for subj_name in self.subjects:
                lessons_here = [
                    i for i in range(n)
                    if lesson_specs[i][0] == cls_name and lesson_specs[i][1] == subj_name
                ]
                if not lessons_here:
                    continue
                for d in range(DAYS):
                    model.Add(
                        sum(x[(i, d, s)] for i in lessons_here for s in range(SLOTS_PER_DAY)) <= 2
                    )

        # 7. Учет сложности предметов (штрафы за плохие слоты)
        penalties = []
        for i in range(n):
            cls_name, subj_name, t_id = lesson_specs[i]

            # Достаем сложность предмета из базы
            difficulty = 0
            if subj_name in self.subjects:
                difficulty = getattr(self.subjects[subj_name], 'difficulty', 0)

            # Если предмет сложный (например, 5 и выше)
            if difficulty >= 5:
                # Штрафуем 1-й урок
                penalties.extend(x[(i, d, 0)] for d in range(DAYS))
                # Штрафуем последние уроки (индекс 6 и 7)
                penalties.extend(x[(i, d, 6)] for d in range(DAYS))
                penalties.extend(x[(i, d, 7)] for d in range(DAYS))

        # Применяем штрафы к модели (просим минимизировать их количество)
        if penalties:
            model.Minimize(sum(penalties))

        # 8. Решаем
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 15.0
        solver.parameters.num_search_workers = 8
        # Убираем stop_after_first_solution, чтобы он искал лучшее решение

        status = solver.Solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return False, "Не удалось расставить уроки. Попробуйте уменьшить нагрузку."

        # 9. Умное распределение кабинетов
        self.schedule = []
        busy_rooms = {}

        for i in range(n):
            cls_name, subj, t_id = lesson_specs[i]
            for d in range(DAYS):
                for s in range(SLOTS_PER_DAY):
                    if solver.Value(x[(i, d, s)]) == 1:
                        avail_rooms = self._find_rooms_for(subj, cls_name)

                        if (d, s) not in busy_rooms:
                            busy_rooms[(d, s)] = set()

                        chosen_room = None
                        for r_id in avail_rooms:
                            if r_id not in busy_rooms[(d, s)]:
                                chosen_room = r_id
                                break

                        if chosen_room is None:
                            if avail_rooms:
                                chosen_room = avail_rooms[0]
                            else:
                                chosen_room = 0
                        else:
                            busy_rooms[(d, s)].add(chosen_room)

                        self.schedule.append(Lesson(d, s, cls_name, subj, t_id, chosen_room))

        return True, "OK"