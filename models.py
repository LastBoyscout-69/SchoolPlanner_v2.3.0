from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class Teacher:
    id: int
    name: str
    subjects: List[str] = field(default_factory=list)
    unavailable_slots: List[tuple] = field(default_factory=list)
    max_lessons_per_day: int = 6


@dataclass
class SchoolClass:
    id: int
    name: str
    students: int = 25


@dataclass
@dataclass
class Subject:
    name: str
    hours_per_week: Dict[str, int] = field(default_factory=dict)
    teachers: Dict[str, str] = field(default_factory=dict)  # {класс: имя_учителя}


@dataclass
class Room:
    id: int
    name: str
    capacity: int = 30
    subject_specific: Optional[str] = None


@dataclass
class Lesson:
    day: int
    slot: int
    class_name: str
    subject: str
    teacher_id: int
    room_id: int

    def __repr__(self):
        return f"{self.class_name}: {self.subject} (уч.{self.teacher_id}, каб.{self.room_id})"