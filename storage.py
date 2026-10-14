import json
import os

DATA_FILE = "school_data.json"


def default_data():
    return {
        "teachers": [
            {"id": 1, "name": "Иванова А.П.", "subjects": ["Математика"], "unavailable_slots": []},
            {"id": 2, "name": "Петров С.И.", "subjects": ["Русский язык", "Литература"], "unavailable_slots": []},
            {"id": 3, "name": "Сидорова Е.В.", "subjects": ["Физика"], "unavailable_slots": []},
        ],
        "classes": [
            {"id": 1, "name": "5А", "students": 25},
            {"id": 2, "name": "5Б", "students": 27},
        ],
        "subjects": [
            {"name": "Математика", "hours": {"5А": 5, "5Б": 5}},
            {"name": "Русский язык", "hours": {"5А": 4, "5Б": 4}},
            {"name": "Литература", "hours": {"5А": 2, "5Б": 2}},
            {"name": "Физика", "hours": {"5А": 2, "5Б": 2}},
        ],
        "rooms": [
            {"id": 101, "name": "101", "capacity": 30, "subject_specific": ""},
            {"id": 102, "name": "102", "capacity": 30, "subject_specific": ""},
            {"id": 201, "name": "Физика", "capacity": 28, "subject_specific": "Физика"},
        ],
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        return default_data()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # --- Чистим «висячие» классы в предметах ---
    current_classes = {c["name"] for c in data.get("classes", [])}
    for subj in data.get("subjects", []):
        hours = subj.get("hours", {})
        # оставляем только те классы, которые реально существуют
        subj["hours"] = {name: h for name, h in hours.items() if name in current_classes}

    return data


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)